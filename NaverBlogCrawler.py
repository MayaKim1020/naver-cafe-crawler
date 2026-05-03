from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from datetime import datetime

# ==========================================
# 카테고리 분류 규칙 (위에서부터 우선순위)
# ==========================================
CATEGORY_RULES = [
    ("신청글", ["수강신청", "비교과", "특강", "채용", "프로그램", "모집"]),
    ("공모전", ["공모전"]),
    ("이벤트", ["이벤트"]),
    ("안내글", ["안내"]),
    # 공지글은 키워드가 아닌 "전체공지 태그"로 별도 분류
]

def classify(title, is_notice):
    """제목과 공지 여부로 카테고리 분류"""
    if is_notice:
        return "공지글"
    for category, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword in title:
                return category
    return "기타"

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
# 2. 카페 게시판 접속 및 대기
# ==========================================
TARGET_CLUB_ID = "22694512"
TARGET_MENU_ID = "111"
url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid={TARGET_CLUB_ID}&search.menuid={TARGET_MENU_ID}&search.boardtype=L"

driver.get(url)
print("✅ 게시판 접속 완료! 데이터를 읽어옵니다...")
time.sleep(3)

# ==========================================
# 3. 데이터 추출 + 카테고리 분류
# ==========================================
articles = driver.find_elements(By.CSS_SELECTOR, "a.article")

# 카테고리별로 묶을 dict
categorized = {
    "공지글": [],
    "신청글": [],
    "공모전": [],
    "안내글": [],
    "이벤트": [],
    "기타": []
}

if articles:
    print(f"🎉 총 {len(articles)}개의 최신 글을 찾았습니다!")
    for article in articles:
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

        # ⭐ 전체공지 여부 확인 (board-tag 클래스가 있으면 전체공지)
        try:
            row.find_element(By.CSS_SELECTOR, "em.board-tag")
            is_notice = True
        except:
            is_notice = False

        # 카테고리 분류
        category = classify(title, is_notice)

        categorized[category].append({
            "title": title,
            "author": author,
            "date": date,
            "link": link
        })

driver.quit()
print("✅ 브라우저 종료 완료")

# ==========================================
# 4. JSON 파일로 저장
# ==========================================
total = sum(len(v) for v in categorized.values())

output = {
    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total": total,
    "categories": categorized
}

with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# 콘솔에 분류 결과 출력
print(f"\n📊 카테고리별 분류 결과:")
for category, items in categorized.items():
    print(f"  - {category}: {len(items)}개")
print(f"\n✅ articles.json 저장 완료 (총 {total}개)")