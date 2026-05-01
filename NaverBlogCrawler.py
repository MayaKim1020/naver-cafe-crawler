from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import os

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
# 3. 데이터 추출 (제목, 작성자, 날짜, 링크)
# ==========================================
articles = driver.find_elements(By.CSS_SELECTOR, "a.article")
driver.quit()

# ==========================================
# 4. 디스코드 웹훅으로 전송
# ==========================================
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord(message):
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

if not articles:
    send_discord("🤔 글 목록을 찾지 못했습니다.")
else:
    print(f"🎉 총 {len(articles)}개의 최신 글을 찾았습니다!")

    send_discord(f"📋 **네이버 카페 최신글 알림** (총 {len(articles)}개 중 최신 5개)\n{'='*30}")

    for article in articles[:5]:
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

        message = (
            f"📌 **{title}**\n"
            f"👤 작성자: {author}　📅 날짜: {date}\n"
            f"🔗 {link}"
        )
        send_discord(message)
        print(f"전송 완료: {title}")
        time.sleep(0.5)