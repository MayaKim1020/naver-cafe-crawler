from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from datetime import datetime

# ==========================================
# ⚙️ 설정값
# ==========================================
START_DATE = "2026.04.01."  # 이 날짜 이후 글만 수집 (포함)
MAX_ARTICLES = 50           # 최대 수집 개수
MAX_PAGES = 10              # 최대 탐색 페이지 (안전장치)

# ==========================================
# 카테고리 분류 규칙 (위에서부터 우선순위)
# 안내글은 최하위 → 다른 키워드가 하나도 없을 때만 분류
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
GUIDE_KEYWORDS = ["안내", "홍보", "행사"]  # 홍보/안내 키워드 (최하위)

def classify(title, is_notice):
    """제목과 공지 여부로 카테고리 분류"""
    if is_notice:
        return "공지글"

    # 1순위: 신청글 / 공모전 / 이벤트 키워드 검사
    for category, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword in title:
                return category

    # 2순위 (최하위): 홍보/안내 - 위 키워드가 하나도 없을 때만 검사
    for keyword in GUIDE_KEYWORDS:
        if keyword in title:
            return "홍보/안내"

    return "기타"

def parse_date(date_str):
    """'2026.03.26.' 같은 문자열을 datetime으로 변환"""
    try:
        cleaned = date_str.strip().rstrip(".")
        return datetime.strptime(cleaned, "%Y.%m.%d")
    except:
        return None

START_DATETIME = parse_date(START_DATE)

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

# 카테고리별 dict
categorized = {
    "공지글": [],
    "공모전": [],
    "신청글": [],
    "이벤트": [],
    "홍보/안내": [],
    "기타": []
}

total_collected = 0
should_stop = False

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

        # 전체공지 여부 (board-tag 클래스)
        try:
            row.find_element(By.CSS_SELECTOR, "em.board-tag")
            is_notice = True
        except:
            is_notice = False

        # ⭐ 날짜 필터링 (전체공지는 날짜 무관하게 항상 포함)
        article_date = parse_date(date)
        if not is_notice and article_date and article_date < START_DATETIME:
            # 일반 글이 기준일보다 오래됐으면 → 더 볼 필요 없음
            print(f"⏹️ 기준일({START_DATE})보다 오래된 글 발견, 수집 종료")
            should_stop = True
            break

        # 카테고리 분류
        category = classify(title, is_notice)

        categorized[category].append({
            "title": title,
            "author": author,
            "date": date,
            "link": link
        })
        total_collected += 1

driver.quit()
print(f"\n✅ 브라우저 종료 완료 (총 {total_collected}개 수집)")

# ==========================================
# 3. JSON 파일로 저장
# ==========================================
output = {
    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "start_date": START_DATE,
    "total": total_collected,
    "categories": categorized
}

with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# 콘솔에 분류 결과 출력
print(f"\n📊 카테고리별 분류 결과:")
for category, items in categorized.items():
    print(f"  - {category}: {len(items)}개")
print(f"\n✅ articles.json 저장 완료")