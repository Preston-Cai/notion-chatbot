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

3. Done - Solve recursion limit issue (replace with an iterative approach)
4. Tune sleep setting
5. Use aynscio to run web scraping asynchronously
    
"""


from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin
import asyncio

URL = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"
BASE_URL = "https://utat-ss.notion.site/"

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
    

    def main(self) -> None:
        """Control the soups baking process. Lannch a playwright broswer, 
        get all links and extract and save text from those pages, and close browser.
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
            print("Browser launched!")

            page = context.new_page()

            self.add_all_links(starting_url=self.starting_url, page=page)
            print("Links all added.")
            
            browser.close()

    @staticmethod
    async def get_html(url: str, page) -> str:
        """Return html document for a given url.

        Preconditions:
        - the url does not prevent playwright automation. 
        - page is a valid playwright browswer tab and playwright is running correctly.
        """

        page.goto(url, wait_until="domcontentloaded")

        # # Wait for Notion main container
        # page.wait_for_selector("div#notion-app", timeout=30000)

        # Scroll to bottom and update until no more content loaded
        previous_height = 0
        while True:
            asyncio.sleep(2)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            current_height = page.evaluate("document.body.scrollHeight")
            if previous_height == current_height:
                break
            previous_height = current_height

        html = page.content()

        print("## html fetched ##")

        return html

    # Parse HTML

    @staticmethod
    def bake_soup(html: str) -> BeautifulSoup:
        """Parse html doc into a soup object and return that object.
        """

        print("## soup baked ##")
        return BeautifulSoup(html, "html.parser")

    async def add_all_links(self, starting_url: tuple[str, str], page) -> None:
        """Add all links associated with (i.e. accessible by) the given url to links.

        Preconditions:
          - page is a valid playwright browswer tab and playwright is running correctly.
        """

        to_visit = [starting_url]
        base_url = starting_url[1]

        while to_visit:
            # Process links in to_visit
            url_this_time, _ = to_visit.pop()
            if url_this_time in self.links:
                continue
            self.links.add(url_this_time)

            # Find links for this page
            more_this_time = set()
            try:
                soup = self.bake_soup(self.get_html(url_this_time, page))
            except Exception:
                print("An error occurs when getting html or baking soup.")
                return
            except KeyboardInterrupt:
                print("Process of adding links stopped. Links added so far:\n", self.links)
                raise

            for link in soup.find_all('a'):
                new_link = link.get('href')
                if new_link is None:
                    continue

                # Convert relative URLs to absolute
                new_link = urljoin(url_this_time, new_link)

                # Only keep links within the same base
                if not new_link.startswith(base_url):
                    continue
                
                more_this_time.add((new_link, base_url))

            # See what links are found each time (these are not added to self.links yet)
            print("Links found this time: ", more_this_time)
                
            # Add the links found to to_visit
            to_visit += list(more_this_time)

if __name__ == '__main__':
    soupsmaker = SoupsMaker(starting_url=(URL, BASE_URL))
    soupsmaker.main()
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
