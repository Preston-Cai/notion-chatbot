from scrapling.fetchers import DynamicFetcher
from bs4 import BeautifulSoup

# Target URL of a dynamic page
url = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"

# Fetch the page and wait for the paragraphs to load
page = DynamicFetcher.fetch(
    url,
    wait_selector="div#notion-app", # Wait for nodes to be populated
    headless=True # Run in headless mode
)
# page is a python object

html = page.text
soup = BeautifulSoup(html, "html.parser")
text = soup.get_text(separator="\n")
print(text != '')
print(text[:500]) # tomorrow: figure out why it is not printing