"""Next step: 
1. Figure out whether I can achieve not openning the browser every time.
2. Figure out how to also find the links that are not in href form (like clickables.
one idea may be to simulate clicking "suspicious" element in the virtual browser,
and if page.url is different, collect it.)

    potential clickables: 
    1. Use this to see:
    document.querySelectorAll("[data-block-id].notion-page-block").forEach(el => {
    el.style.outline = "2px solid red";});  // highlight element

    2. Proceed Anyway button: 
    <a rel="noopener noreferrer" class="notion-link" style="display: inline; color: inherit; text-decoration: underline; user-select: none; cursor: pointer;">proceed anyway</a>
"""


from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
from typing import Optional
from urllib.parse import urljoin

URL = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"
BASE_URL = "https://utat-ss.notion.site/"

URL2 = "https://books.toscrape.com"
BASE_URL2 = URL2

URL3 = "https://utat-ss.notion.site/2b64b90381df4cc2a25a8e7e32456d16?v=d974053aa7bd4671a805f8720f872f76"
BASE_URL3 = BASE_URL

URL4 = "https://utat-ss.notion.site/62a846dca6b34dac84e63ecccd395535?v=80edfc04b21a4754b23f69e69e468cef"
BASE_URL4 = BASE_URL

class SoupsMaker():
    """A class that represents the process of
    making soups given one ingredient (the url).
    
    Instance Attributes:
      - url: the given url tuple in the form of (url, base_url), where base_url is the base site to be scraped.
      - links: all the distict urls associated with the starting url.
      - soups_are_ready: whether all the soups are prepared and ready for use.
      - soups: soups that have been made.
    
    """

    starting_url: Optional[tuple[str, str]] = None
    links: set[str]
    soups_are_ready: bool
    soups: list[BeautifulSoup]
    
    def __init__(self, starting_url: Optional[tuple[str, str]] = None) -> None:
        self.starting_url = starting_url
        self.links = set()
        self.soups_made = False
        self.soups = []

    @staticmethod
    def get_html(url: str) -> str:
        """Return html document for a given url.

        Preconditions:
        - the url does not prevent playwright automation. 
        """

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

            # # Wait for Notion main container
            # page.wait_for_selector("div#notion-app", timeout=30000)

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

            print("## html fetched ##")

            return html

    # Parse HTML

    @staticmethod
    def bake_soup(html: str) -> BeautifulSoup:
        """Parse html doc into a soup object and return that object.
        """

        print("## soup baked ##")
        return BeautifulSoup(html, "html.parser")

    def add_all_links(self, starting_url: tuple[str, str]) -> None:
        """Add all links associated with (i.e. accessible by) the given url to links.
        Check recursively for links until all links are included.
        """
        url, base = starting_url

        # Return if already visited
        if url in self.links:
            return
        
        # Immediately add to self.links
        self.links.add(url)

        # print number of links added (and the set of urls so far)
        print("Number of links added: ", len(self.links))
        # print("Links added so far: ", self.links)


        # Add more links
        added_this_time = set()
        try:
            soup = self.bake_soup(self.get_html(url))
        except Exception:
            print("An error occurs when getting html or baking soup.")
            return
        except KeyboardInterrupt:
            print("process of adding links stopped. Links added so far:\n", self.links)
            raise

        for link in soup.find_all('a'):
            new_link = link.get('href')
            if new_link is None:
                continue

            # Convert relative URLs to absolute
            new_link = urljoin(url, new_link)

            # Only keep links within the same base
            if not new_link.startswith(base):
                continue
            
            added_this_time.add(new_link)

        # See what links are found each time (these are not added to self.links yet)
        print(added_this_time)
        
        # Recursion: repeat the same steps for the newly added links
        for link in added_this_time:
            self.add_all_links((link, base))

if __name__ == '__main__':
    soupsmaker = SoupsMaker()
    soupsmaker.add_all_links(starting_url=(URL4, BASE_URL4))
    print(soupsmaker.links)
    
    

# # Extract clean text
# text = "\n".join(
#     line.strip()
#     for line in soup.get_text("\n").split("\n")
#     if line.strip()
# )

# # Write text and html to file
# with open("webtext.txt", "w", encoding="utf-8") as f:
#     f.write(text)

# with open("parsed.html", "w", encoding="utf-8") as f:
#     f.write(soup.prettify())
