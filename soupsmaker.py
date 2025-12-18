"""
Next step: 
1. Figure out how to also find the links that are not in href form (like clickables.
one idea may be to simulate clicking "suspicious" element in the virtual browser,
and if page.url is different, collect it.)

    potential clickables: 
    1. Use this to see:
    document.querySelectorAll("[data-block-id].notion-page-block").forEach(el => {
    el.style.outline = "2px solid red";});  // highlight element

    2. (solved) Proceed Anyway button: 
    <a rel="noopener noreferrer" class="notion-link" style="display: inline; color: inherit; text-decoration: underline; user-select: none; cursor: pointer;">proceed anyway</a>

2. Tune sleep setting.     
3. Fix potential bug of page reuse allocation conflict.
"""


from playwright.async_api import async_playwright, BrowserContext, Page
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio

import os
from typing import Optional
import csv


URL = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"
BASE_URL = "https://utat-ss.notion.site/"

URL2 = "https://utat-ss.notion.site/Data-Processing-661606034b8b4598bc5a13a822d27b7c"

class SoupsMaker():
    """A class that represents the process of
    making soups given one ingredient (the url).
    
    Instance Attributes:
      - url: the given url tuple in the form of (url, base_url), where base_url is the base site to be scraped.
      - links: all the distict urls associated with the starting url.
      - soups: soups that have been made.

    """
    # Private Instance Attributes:
    #   - context: the playwright browser context used to fetch pages.
    #   - cap: maximum number of links to be processed at a time.
    #   - pages: store browswer tabs that will stay oepn throgh the lifetime of SoupsMaker.
    #   - to_visit: set of url tuples that are yet to be visited.
    #   - mode: whether starting from starting_url ('fresh') or continuing from previous progress ('resume').
    #   - _page_lock: an asyncio lock to prevent race condition when allocating pages.

    starting_url: tuple[str, str] = URL, BASE_URL
    links: set[str]
    soups: list[BeautifulSoup]

    _context: Optional[BrowserContext] = None
    _cap: int = 10
    _pages: list[Page]
    _to_visit: set[tuple[str, str]]
    _mode: str = 'fresh' # or 'resume'
    _page_lock: asyncio.Lock

    def __init__(self, starting_url: tuple[str, str] = (URL, BASE_URL),
                 cap: int = 10, mode: str = 'fresh') -> None:
        self.starting_url = starting_url
        self.soups = []

        self._context = None
        self._cap = cap
        self._pages = []
        self._mode = mode
        self._page_lock = asyncio.Lock()

        self._start_by_mode()  # intialize links and to_visit based on the mode 

    async def main(self) -> None:
        """Control the soups baking process. Lannch a playwright broswer, 
        get all links and extract and save text from those pages, and close browser.
        """
        async with async_playwright() as p:
            # Launch real Chromium
            browser = await p.chromium.launch(
                headless=False  # set True later once confirmed working
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                )
            )
            print("Browser launched!")

            # Set context to current context
            self.context = context

            try: 
                await self.add_all_links()
            except Exception as e:
                print("An error occurs when adding all links. Error: ", e)

            print("Links all added.")
            await browser.close()
            self.context = None

    async def add_all_links(self) -> None:
        """Add all links associated with (i.e. accessible by) the given url to links.
        """

        # Process links in to_visit iteratively
        while self.to_visit:
            # Create batch of links
            batch = set()
            while self.to_visit and len(batch) < self._cap: # stop if batch is full or to_visit is empty
                # Do not create tasks if the link has been processed before
                hold = self.to_visit.pop()
                if hold[0] in self.links:
                    continue
                batch.add(hold)

            # Create asyncio tasks
            tasks = [asyncio.create_task(self.process_link(url_this_time))
                        for url_this_time in batch]
            
            # Process links asynchronously
            lists_of_links = await asyncio.gather(*tasks)

            for links in lists_of_links:
                if links is not None:
                    for link in links:
                        if link[0] not in self.links:  # clean unnecessary links
                            self.to_visit.add(link)

            # for debugging only
            print("number of pages stored: ", len(self._pages))
                
            print(f"Number of links in to_visit: {len(self.to_visit)}, "
            "and the links are: ", {url for url, _ in self.to_visit})

    async def process_link(self, url_this_time: tuple[str, str]) -> Optional[set[tuple[str, str]]]:
        """Process the given url tuple and return a new set of url tuples as new found links.
        Return None if nothing new is found.

        """

        url, base_url = url_this_time

        # Return None is this link has already been visited
        if url in self.links:
            return
        # Immediately add to self.links
        self.links.add(url)

        # Find links for this page
        more_this_time = set()
        try:
            soup = self.bake_soup(await self.get_html(url))
        except Exception as e:
            print("An error occurs when getting html or baking soup. Error: ", e)
            return
        
        for link in soup.find_all('a'):
            new_link = link.get('href')
            if new_link is None:
                continue

            # Convert relative URLs to absolute and remove query and fragment parts
            new_link = urlparse(urljoin(url, new_link))._replace(query=None, fragment=None).geturl()

            # Only keep links within the same base
            if not new_link.startswith(base_url):
                continue
            
            more_this_time.add((new_link, base_url))

            # See what links are found each time (these are not added to self.links yet)
            # print("Links found this time: ", {url for url, _ in more_this_time})

        return more_this_time

    async def get_html(self, url: str, page: Optional[Page] = None) -> str:
        """Return html document for a given url.

        Preconditions:
        - the url does not prevent playwright automation. 
        """

        # Prevent "< cap" comparison before the new page is appended (prevent race condition)
        async with self._page_lock:
            if page is not None: # Mainly to handle the recursive call below after clickiing "proceed anyway" 
            # making sure after redirection, it does not grab a new page and breaks round robin
                pass
            # Create a new page if no more than self._cap pages are open
            elif len(self._pages) < self._cap:
                page = await self.context.new_page()
                self._pages.append(page)
            # Otherwise, reuse an existing page (round robin)
            else:
                page = self._pages[0]
                self._pages = self._pages[1:] + [page]

        await page.goto(url, wait_until="domcontentloaded")
        print("page loaded.")

        # # Wait for Notion main container
        # page.wait_for_selector("div#notion-app", timeout=30000)

        # Scroll to bottom and update until no more content loaded
        previous_height = 0
        while True:
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            current_height = await page.evaluate("document.body.scrollHeight")
            if previous_height == current_height:
                break
            previous_height = current_height

        # Click "proceed anyway" if it exists
        link_to_click = await page.query_selector("text=proceed anyway")
        if link_to_click:
            print("'proceed anyway' button link found, clicking it.")
            await link_to_click.click()
            await asyncio.sleep(1)  # Wait for page to load after clicking

            # If page has been redirected after clicking, get html from the new url
            # Remove query params and fragments before comparision
            url_no_query = urlparse(url)._replace(query=None, fragment=None).geturl() 
            if page.url != url_no_query and page.url not in self.links:
                # Call the funciton itself to get the html properly
                print("Page redirected after clicking 'proceed anyway'.")
                html = await self.get_html(page.url, page=page)
                print("## html fetched ##")
                return html

        # Return page html (if the url was not redirected)
        html = await page.content()
        print("## html fetched ##")
        return html

    # Parse HTML
    @staticmethod
    def bake_soup(html: str) -> BeautifulSoup:
        """Parse html doc into a soup object and return that object.
        """
        print("## soup baked ##")
        return BeautifulSoup(html, "html.parser")
    
    def _start_by_mode(self) -> None:
        """__init__ helper method to initialize links and to_visit based on mode.

        Preconditions:
          - self._mode in {'fresh', 'resume'}
          - if self._mode is 'resume', progress files must in csv format
           and only contain urls (not the base url).
        """
        # fresh mode
        if self._mode == 'fresh':
            self.links = set()
            self.to_visit = {self.starting_url}
            return
        
        # resume mode
        self.links = set()
        self.to_visit = set()

        # Load links from file
        try:
            with open("progress_links.csv", 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    for url in row:
                        self.links.add(url)
            print(f"Resumed {len(self.links)} links from progress_links.csv")
        except FileNotFoundError:
            print("No progress_links.csv file found." \
            " Set _mode to 'fresh' and try again.")
        
        # Load to_visit from file
        try:
            with open("progress_to_visit.csv", 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    for url in row:
                        self.to_visit.add((url, self.starting_url[1]))
            print(f"Resumed {len(self.to_visit)} to_visit links from progress_to_visit.csv")
        except FileNotFoundError:
            print("No progress_to_visit.csv file found. " \
            "Set _mode to 'fresh' and try again.")

    def save_progress(self) -> None:
        """Save the current progress (self.links and self.to_visit) to csv files.
        """

        if not os.path.exists("progress"):
            os.makedirs("progress")

        mode = 'a' if self._mode == 'resume' else 'w'
        with open("progress/progress_links.csv", mode, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(list(self.links))

        with open("progress/progress_to_visit.csv", mode, newline='') as f:
            writer = csv.writer(f)
            writer.writerow([url_tuple[0] for url_tuple in self.to_visit])


async def run_soups_maker():
    """ Run SoupsMaker and save progress on KeyboardInterrupt.
    """
    soupsmaker = SoupsMaker(starting_url=(URL2, BASE_URL), cap=3)
    try:
        await soupsmaker.main()
    except KeyboardInterrupt:
        print("Process of adding links interrupted. ")
        print("Number of links added so far:\n", len(soupsmaker.links))
        soupsmaker.save_progress()
        raise


if __name__ == '__main__':
    asyncio.run(run_soups_maker())
    # soupsmaker = SoupsMaker(starting_url=(URL, BASE_URL), cap=3, mode='fresh')
    # try:
    #     asyncio.run(soupsmaker.main())
    # except KeyboardInterrupt:
    #     print("Process of adding links interrupted. ")
    #     print("Number of links added so far:\n", len(soupsmaker.links))
    #     soupsmaker.save_progress()
    #     raise
    # print(soupsmaker.links)
    
    

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
