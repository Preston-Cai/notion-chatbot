from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


# configure chrome
chrome_options = Options()
# chrome_options.add_argument("--headless")  

# hides automation
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

chrome_options.add_argument("--disable-gpu")

chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.265 Safari/537.36"
)

# Initialize web driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Opens target web
url = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"
driver.get(url)

# Wait for dynamic content to load
WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "notion-app"))
    )

# Get and parse the page source
html = driver.page_source
driver.quit()

soup = BeautifulSoup(html, "html.parser")
# print(soup.prettify())

text = soup.get_text()
print(text)
# with open("webtext.txt", 'w') as f:
#     f.write(text)
# with open("webtext.txt", 'r') as f:
#     print(f.read())

with open("parsed.text", 'w') as f:
    f.write(soup.prettify())
