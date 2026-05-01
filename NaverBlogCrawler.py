from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from datetime import datetime

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
# 3. 데이터 추출
# ==========================================
articles = driver.find_elements(By.CSS_SELECTOR, "a.article")

results = []

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

        results.append({
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
output = {
    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),  # 마지막 크롤링 시각
    "total": len(results),
    "articles": results
}

with open("articles.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ articles.json 저장 완료 ({len(results)}개)")