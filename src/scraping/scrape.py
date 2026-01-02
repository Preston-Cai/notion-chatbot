"""
This file contains:
1. A dynamic, recursive web scraper (`SoupsMaker`);
2. A function to run the scraper (`run_soupsmaker`);
3. A function for a simple single page text extracter (`scrape_single_page`).
"""

from playwright.async_api import async_playwright, BrowserContext, Page
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio
import time

import os
import sys
from typing import Optional
import csv
import json

from src.file_config import *

URL = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"
BASE_URL = "https://utat-ss.notion.site/"

class SoupsMaker():
    """Represents the process of
    "making soups" given one ingredient (the url).
    In other words, a dynamic, recursive web scraping engine.

    SoupsMaker: what it does
        1. Deep crawls all subpages of the given url.
        2. Saves html docs (if enabled) and extracted text of visited pages.
        3. Saves all visted links to csv after finished scraping all links
        4. (Handled by `run_soupsmaker`) if interrupted, save links to visit and links visited as progress.
    
    Instance Attributes:
      - url: the given url tuple in the form of (url, base_url), where base_url is the base site to be scraped.
      - links: all the distict urls associated with the starting url.
      - to_visit: set of url tuples that are yet to be visited.
      - failed_links: link_err tuple that are failed to scrape (e.g. an error occurred)
      - cap: maximum number of links to be processed at a time.
      - resume: whether resume from previous progress or not (start fresh). Default to False.
      - save_html: whether saving scraped html files.
      - save_text: whether saving extracted raw text files.
      - save_json: whether saving json files that has page content and source.
      Warning: If mode is resume, only enable `save_html` if you are consistent with previous sessions.
      Otherwise, it will result in mismatch of html docs and text docs.
    """
    # Private Instance Attributes:
    #   - _context: the playwright browser context used to fetch pages.
    #   - _pages: store browswer tabs that will stay oepn throgh the lifetime of SoupsMaker.
    #   - _page_lock: an asyncio lock to prevent race condition when allocating pages.

    starting_url: tuple[str, str] = URL, BASE_URL
    links: set[str]
    to_visit: set[tuple[str, str]]
    failed_links: set[tuple[str, Exception]]
    cap: int = 10
    resume: bool
    
    save_html: bool
    save_text: bool
    save_json: bool

    _context: Optional[BrowserContext] = None
    _pages: list[Page]
    _page_lock: asyncio.Lock
    

    def __init__(self, starting_url: tuple[str, str] = (URL, BASE_URL), 
                 cap: int = 10, resume: bool = False, save_html: bool = False,
                 save_text: bool = False, save_json: bool = True) -> None:
        
        self.starting_url = starting_url
        self.failed_links = set()
        self.cap = cap
        self.resume = resume
        self.save_html = save_html
        self.save_text = save_text
        self.save_json = save_json

        self._context = None
        self._pages = []
        self._page_lock = asyncio.Lock()

        self._start_by_mode()  # intialize self.links and self.to_visit based on the mode 

    async def main(self) -> None:
        """Control the soups baking process. 
        Lannch a playwright broswer, find all subpages of self.starting_url, 
        extract htmls and text from those pages and save locally.
        After finished, save all links visited and failed links and close the browser.
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
                print("An error occurs when adding all links. Error:", e)

            # Clean up
            await browser.close()
            self.context = None
            
        # Save all failed links
        self.save_failed_links()
        
        # Save all visited links
        with open(ALL_LINKS_PATH, 'w', newline='') as f:
            data = list(self.links)
            num_columns = 10    # write at most 10 items per row
            writer = csv.writer(f, delimiter=',')
            for i in range(0, len(data), num_columns):
                writer.writerow(data[i:i + num_columns])
            
            print("####### All links added!! #######")
            print("Total number of links added: ", len(self.links))

    async def add_all_links(self) -> None:
        """Add all links associated with (i.e. accessible by) the given url to links.
        """

        # Process links in to_visit iteratively
        while self.to_visit:
            # Create batch of links
            batch = set()
            while self.to_visit and len(batch) < self.cap: # stop if batch is full or to_visit is empty
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
                
            print(f"Number of links in to_visit: {len(self.to_visit)}")
            # print("And the links are: ", {url for url, _ in self.to_visit})

    async def process_link(self, url_this_time: tuple[str, str]) -> Optional[set[tuple[str, str]]]:
        """Process the given url tuple and return a new set of url tuples as new found links.
        Return None if nothing new is found.
        Call self.get_html() to extract html docs.

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
            print("An error occurs when getting html or baking soup. Error:", e)
            self.failed_links.add((url, e))
            print("Failed link added to self.failed_links")
            return

        # Save prettified html, extracted text, and json files
        self.save_docs(soup, url)
                
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
            # Create a new page if no more than self.cap pages are open
            elif len(self._pages) < self.cap:
                page = await self.context.new_page()
                self._pages.append(page)
            # Otherwise, reuse an existing page (round robin)
            else:
                page = self._pages[0]
                self._pages = self._pages[1:] + [page]

        await page.goto(url, wait_until="domcontentloaded")
        print("Page loaded.")

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

        # Get page html and return (if the url was not redirected)
        # html = await page.content()

        # Trying a different way to get html
        html = await page.evaluate("""
        () => document.documentElement.outerHTML
            """)
        print("## html fetched ##")

        return html

    # Parse HTML
    @staticmethod
    def bake_soup(html: str) -> BeautifulSoup:
        """Parse html doc into a soup object and return that object.
        """
        print("## soup baked ##")
        return BeautifulSoup(html, "html.parser")
    
    def save_docs(self, soup: BeautifulSoup, url: str) -> None:
        """Save prettified html files, extracted text file, and json files,
        only if each is enabled.
        """

        html_count = len(os.listdir(HTML_DIR))
        text_count = len(os.listdir(TEXT_DIR))
        json_count = len(os.listdir(JSON_DIR))
        filename_html = os.path.join(HTML_DIR, f"page_{html_count + 1}.html")
        filename_text = os.path.join(TEXT_DIR, f"page_{text_count + 1}.txt")
        filename_json = os.path.join(JSON_DIR, f"page_{json_count + 1}.json")

        # Extract clean text
        text = "\n".join(
            line.strip()
            for line in soup.get_text("\n").split("\n")
            if line.strip()
        )

        # Write to html, text, and json files
        if self.save_html:
            with open(filename_html, "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            print(f"HTML file saved as {filename_html}")
        if self.save_text:
            with open(filename_text, 'w', encoding="utf-8") as f:
                f.write(text)
            print(f"Text file saved as {filename_text}")
        if self.save_json:
            with open(filename_json, 'w', encoding="utf-8") as f:
                one_line_text = text.replace('\n', ' ')
                data = {"text": one_line_text, "source": url}
                json.dump(data, f, indent=4)
            print(f"JSON file saved as {filename_json}")

    
    def _start_by_mode(self) -> None:
        """__init__ helper method to initialize links and to_visit based on mode.
        Also, if in fresh mode, clear existing html and text docs.

        Preconditions:
          - if self.resume is True, progress files must in csv format
           and only contain urls (not the base url).
        """
        # fresh mode
        if not self.resume:
            
            # Safety check
            confirm = input("Are you sure you want to start fresh?\n" \
            "All progress will be erased, including extracted html/text.\n" \
            "Type 'yes' to continue: ")

            if confirm.strip().lower() != 'yes':
                print("NOTE: Switched to resume mode.")
                time.sleep(5)
                self.resume = True

            # Confirmed fresh mode
            else:
                self.links = set()
                self.to_visit = {self.starting_url}

                # Clear existing html, text, and json files
                for d in [HTML_DIR, TEXT_DIR, JSON_DIR]:
                    for filename in os.listdir(d):
                        file_path = os.path.join(d, filename)
                        os.remove(file_path)
                return
        
        # resume mode
        self.links = set()
        self.to_visit = set()

        # Load links from file
        try:
            with open(VISITED_LINKS_PATH, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    for url in row:
                        self.links.add(url)
            print(f"Resumed {len(self.links)} visited links from progress_links.csv")
        except FileNotFoundError:
            print("No progress_links.csv file found." \
            " Set resume to False and try again.")
            sys.exit(1)
        
        # Load to_visit from file
        try:
            with open(TO_VISIT_LINKS_PATH, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    for url in row:
                        self.to_visit.add((url, self.starting_url[1]))
            print(f"Resumed {len(self.to_visit)} to-visit links from progress_to_visit.csv")
        except FileNotFoundError:
            print("No progress_to_visit.csv file found. " \
            "Set resume to False and try again.")
            sys.exit(1)

    def save_progress(self) -> None:
        """Save the current progress (self.links, self.to_visit, self.failed_links) to csv files.
        For self.links, self.to_visit, write at most 10 items each row.
        For self.failed_links, call self.save_failed_links to handle.

        Before writing to csv, add urls that the agent is currently visiting
        (but has not done visiting) back to self.to_visit
        """

        # Add current pages back to self.to_visit
        for page in self._pages:
            self.to_visit.add((page.url, self.starting_url[1]))

        mode = 'a' if self.resume else 'w'
        with open(VISITED_LINKS_PATH, mode, newline='') as f:

            data = list(self.links)
            max_col = 10    # write at most 10 items per row

            writer = csv.writer(f, delimiter=',')
            for i in range(0, len(data), max_col):
                writer.writerow(data[i:i + max_col])
            print(f"Saved {len(self.links)} links to progress_links.csv")

        with open(TO_VISIT_LINKS_PATH, mode, newline='') as f:

            data = [url_tuple[0] for url_tuple in self.to_visit]
            max_col = 10    # write at most 10 items per row

            writer = csv.writer(f, delimiter=',')
            for i in range(0, len(data), max_col):
                writer.writerow(data[i:i + max_col])
            print(f"Saved {len(self.to_visit)} links to progress_to_visit.csv")
            
        self.save_failed_links()
    
    def save_failed_links(self) -> None:
        """Save self.failed_links to progress_failed_links.csv.
        Write the failed link and the error each row."""
        mode = 'a' if self.resume else 'w'
        with open(FAILED_LINKS_PATH, mode, newline='') as f:
            writer = csv.writer(f, delimiter=',')
            for link_err in self.failed_links:
                link, e = link_err
                err_msg = str(e).replace('\n', ' ')   # ensure each entry stays in one row
                writer.writerow(list((link, err_msg)))
            print(f"Saved {len(self.failed_links)} failed links to progress_failed_links.csv")


async def run_soupsmaker(starting_url: tuple[str, str] = (URL, BASE_URL),
                 cap: int = 10, resume: bool = False, save_html: bool = False,
                 save_text: bool = False, save_json: bool = True) -> None:
    """Run SoupsMaker and save progress on KeyboardInterrupt.
    """
    soupsmaker = SoupsMaker(starting_url=starting_url, cap=cap, resume=resume,
                            save_html=save_html, save_text=save_text, save_json=save_json)
    try:
        await soupsmaker.main()
    except asyncio.CancelledError:
        print("Process of adding links interrupted. ")
        soupsmaker.save_progress()  # save progress if interrupted


def scrape_single_page(url: str) -> str:
    """Scrape a single given url and return the text contained."""
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

        page.goto(url, wait_until="domcontentloaded")
        print("Page loaded.")

        # Scroll to bottom and update until no more content loaded
        previous_height = 0
        while True:
            time.sleep(2)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            current_height = page.evaluate("document.body.scrollHeight")
            if previous_height == current_height:
                break
            previous_height = current_height
        
        html = page.evaluate("""() => document.documentElement.outerHTML""")

        browser.close()
    
    soup = BeautifulSoup(html, "html.parser")
    text = "\n".join(line.strip() 
                     for line in soup.get_text("\n").split("\n") 
                     if line.strip())

    return text


if __name__ == '__main__':
    asyncio.run(run_soupsmaker(cap=8, resume=False, save_html=False, save_text=False, 
                               save_json=True, starting_url=(URL, BASE_URL)))
