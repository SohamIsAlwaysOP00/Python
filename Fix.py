import requests
from bs4 import BeautifulSoup
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ------------------ LOGIN FUNCTION ------------------
def login(driver):
    # 🔹 Put your Instagram username & password here
    username = "trade_nest_official"
    password = "opopop99A#"

    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    time.sleep(5)  # wait for login to complete


# ------------------ PROXY SCRAPER ------------------
def scrape_proxies():
    url = "https://www.sslproxies.org/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    proxies = []
    table = soup.find("table", {"id": "proxylisttable"})
    if table:
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                proxies.append(f"{ip}:{port}")
    return proxies


# ------------------ PROXY VALIDATOR ------------------
def validate_proxy(proxy, test_url="https://httpbin.org/ip"):
    try:
        response = requests.get(
            test_url,
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            timeout=5
        )
        if response.status_code == 200:
            print(f"[VALID] {proxy}")
            return True
    except Exception:
        pass
    return False


# ------------------ REPORT ACCOUNT FUNCTION ------------------
def report_account(account_id, proxy):
    url = f"https://www.instagram.com/{account_id}/report/"
    payload = {
        "action": "report",
        "reason": "N3:0"  # placeholder reason
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            print(f"[SUCCESS] Reported {account_id} using {proxy}")
        else:
            print(f"[FAIL] {proxy} returned {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {proxy} - {e}")


# ------------------ MAIN ------------------
def main():
    print("Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    # Login first
    login(driver)
    print("✅ Logged in successfully")

    # Scrape proxies
    print("Scraping proxies...")
    proxies = scrape_proxies()
    print(f"Scraped {len(proxies)} proxies")

    # Validate proxies
    valid_proxies = []
    for proxy in proxies:
        if validate_proxy(proxy):
            valid_proxies.append(proxy)

    print(f"Total valid proxies: {len(valid_proxies)}")

    # Example target account (replace with real target)
    target_account = "rikta_baral19"

    # Start reporting with first 5 valid proxies
    for proxy in valid_proxies[:5]:
        threading.Thread(target=report_account, args=(target_account, proxy)).start()


if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
