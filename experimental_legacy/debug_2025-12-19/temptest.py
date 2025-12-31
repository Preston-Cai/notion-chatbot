from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

url = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"

with sync_playwright() as p:
    # Launch real Chromium
    browser = p.chromium.launch(
        headless=False  # set True later once confirmed working
    )

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    )

    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded")

    # Wait for Notion main container
    page.wait_for_selector("div#notion-app", timeout=30000)

    # Scroll to bottom and update until no more content loaded
    previous_height = 0
    while True:
        time.sleep(2)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        current_height = page.evaluate("document.body.scrollHeight")
        if previous_height == current_height:
            break
        previous_height = current_height

    html = page.content()
    browser.close()

# Parse HTML
soup = BeautifulSoup(html, "html.parser")

# Extract clean text
text = "\n".join(
    line.strip()
    for line in soup.get_text("\n").split("\n")
    if line.strip()
)

# Write text and html to file
with open("webtext.txt", "w", encoding="utf-8") as f:
    f.write(text)

with open("parsed.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())

print("##### Done. Content extracted #####")