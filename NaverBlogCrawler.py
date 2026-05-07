from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import requests
from datetime import datetime

# ==========================================
# ⚙️ 설정값
# ==========================================
START_DATE = "2026.04.01."  # 이 날짜 이후 글만 수집 (포함)
MAX_ARTICLES = 50           # 최대 수집 개수
MAX_PAGES = 10              # 최대 탐색 페이지 (안전장치)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# ==========================================
# 카테고리 분류 규칙 (위에서부터 우선순위)
# ==========================================
CATEGORY_RULES = [
    ("공모전", ["공모전"]),
    ("신청글", [
        "수강", "신청", "비교과", "특강", "채용", "프로그램", "모집",
        "창업", "사업", "지원", "공고", "선발", "참가자", "참여자",
        "육성", "발굴", "장학", "인턴", "교육생"
    ]),
    ("이벤트", ["이벤트"]),
]
GUIDE_KEYWORDS = ["안내", "홍보", "행사"]

def classify(title, is_notice):
    """제목과 공지 여부로 카테고리 분류"""
    if is_notice:
        return "공지글"
    for category, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword in title:
                return category
    for keyword in GUIDE_KEYWORDS:
        if keyword in title:
            return "홍보/안내"
    return "기타"

def parse_date(date_str):
    try:
        cleaned = date_str.strip().rstrip(".")
        return datetime.strptime(cleaned, "%Y.%m.%d")
    except:
        return None

START_DATETIME = parse_date(START_DATE)

# ==========================================
# 링크 정규화 (페이지 정보 제거)
# 같은 글인데 page=1, page=2로 다르게 저장되는 문제 해결
# ==========================================
import re

def normalize_link(link):
    """링크에서 page 파라미터를 제거해 같은 글을 같은 키로 만듦"""
    # &page=N 또는 ?page=N 부분을 제거
    cleaned = re.sub(r'[?&]page=\d+', '', link)
    return cleaned

# ==========================================
# 디스코드 알림 함수
# ==========================================
def send_discord_notification(article, category):
    """새 글 알림을 디스코드로 전송"""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL이 설정되지 않아 알림 생략")
        return

    message = (
        f"🆕 **새 글 알림** [{category}]\n"
        f"📌 **{article['title']}**\n"
        f"👤 작성자: {article['author']}　📅 날짜: {article['date']}\n"
        f"🔗 {article['link']}"
    )

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        print(f"📬 디스코드 알림 전송: {article['title']}")
    except Exception as e:
        print(f"❌ 디스코드 전송 실패: {e}")

# ==========================================
# 이전 글 목록 불러오기 (link 집합)
# ==========================================
previous_links = set()
if os.path.exists("articles.json"):
    try:
        with open("articles.json", "r", encoding="utf-8") as f:
            prev_data = json.load(f)
            for category_articles in prev_data.get("categories", {}).values():
                for article in category_articles:
                    previous_links.add(normalize_link(article["link"]))
        print(f"📂 이전 글 {len(previous_links)}개 로드 완료")
    except Exception as e:
        print(f"⚠️ 이전 글 로드 실패: {e}")
else:
    print("📂 이전 글 데이터 없음 (최초 실행)")

# ==========================================
# 1. 크롬 브라우저 세팅 (headless 모드)
# ==========================================
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# ==========================================
# 2. 카페 게시판 접속 (페이지 순회)
# ==========================================
TARGET_CLUB_ID = "22694512"
TARGET_MENU_ID = "111"

categorized = {
    "공지글": [],
    "공모전": [],
    "신청글": [],
    "이벤트": [],
    "홍보/안내": [],
    "기타": []
}

# 새 글들을 (article, category) 튜플 형태로 저장
new_articles = []

total_collected = 0
should_stop = False
is_first_run = (len(previous_links) == 0)  # 최초 실행 여부

for page in range(1, MAX_PAGES + 1):
    if should_stop or total_collected >= MAX_ARTICLES:
        break

    url = (f"https://cafe.naver.com/ArticleList.nhn?"
           f"search.clubid={TARGET_CLUB_ID}&search.menuid={TARGET_MENU_ID}"
           f"&search.boardtype=L&search.page={page}")

    driver.get(url)
    print(f"📄 {page}페이지 접속 중...")
    time.sleep(3)

    articles = driver.find_elements(By.CSS_SELECTOR, "a.article")

    if not articles:
        print(f"⚠️ {page}페이지에서 글을 찾지 못함, 중단")
        break

    for article in articles:
        if total_collected >= MAX_ARTICLES:
            should_stop = True
            break

        title = article.text.strip()
        link = article.get_attribute("href")

        row = article.find_element(By.XPATH, "./ancestor::tr")

        try:
            author = row.find_element(By.CSS_SELECTOR, "span.nickname").text.strip()
        except:
            author = "알 수 없음"

        try:
            date = row.find_element(By.CSS_SELECTOR, "td.type_date").text.strip()
        except:
            date = "알 수 없음"

        try:
            row.find_element(By.CSS_SELECTOR, "em.board-tag")
            is_notice = True
        except:
            is_notice = False

        article_date = parse_date(date)
        if not is_notice and article_date and article_date < START_DATETIME:
            print(f"⏹️ 기준일({START_DATE})보다 오래된 글 발견, 수집 종료")
            should_stop = True
            break

        category = classify(title, is_notice)

        article_data = {
            "title": title,
            "author": author,
            "date": date,
            "link": link
        }

        categorized[category].append(article_data)
        total_collected += 1

        # ⭐ 새 글 감지: 이전 목록에 없고, 최근(오늘/어제) 작성된 글만
        # (페이지 파라미터 제거한 링크로 비교)
        if normalize_link(link) not in previous_links:
            # 작성일이 오늘 또는 어제여야 진짜 "새 글"로 판단
            today = datetime.now().date()
            if article_date and (today - article_date.date()).days <= 1:
                new_articles.append((article_data, category))
            else:
                print(f"⏭️ 새 링크지만 오래된 글이라 알림 제외: {title} ({date})")

driver.quit()
print(f"\n✅ 브라우저 종료 완료 (총 {total_collected}개 수집)")

# ==========================================
# 3. 새 글 알림 전송
# ==========================================
if is_first_run:
    print(f"\n🔔 최초 실행이므로 알림은 보내지 않습니다 ({len(new_articles)}개 글 저장만)")
elif new_articles:
    print(f"\n🆕 새 글 {len(new_articles)}개 발견! 디스코드 알림 전송 중...")
    for article_data, category in new_articles:
        send_discord_notification(article_data, category)
        time.sleep(0.5)  # rate limit 방지
else:
    print(f"\n✨ 새 글 없음")

# ==========================================
# 4. JSON 파일로 저장
# ==========================================
output = {
    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "start_date": START_DATE,
    "total": total_collected,
    "categories": categorized
}

with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n📊 카테고리별 분류 결과:")
for category, items in categorized.items():
    print(f"  - {category}: {len(items)}개")
print(f"\n✅ articles.json 저장 완료")