from src.scraping.scrape import scrape_single_page
import json
import os

from src.file_config import *


def get_big_context() -> None:
    """Scrape big-picture context from the URLs in key_urls.json
    and write to another json file."""
    
    context = {}
    with open(KEY_URLS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        if data == {}:
            print("Warning: no key urls are specified. Big-picture context will be empty.")
        for key in data:
            url = data[key]
            context[key] = scrape_single_page(url)

    with open(BIG_CONTEXT_PATH, "w") as f:
        json.dump(context, f, indent=4)


def read_big_context() -> str:
    """Read the json file in the current directory named big_context and return 
    a string representation of the content.
    """
    if not os.path.exists(BIG_CONTEXT_PATH):
        get_big_context()

    with open(BIG_CONTEXT_PATH, "r", encoding="utf-8") as f:
        context = f.read()
        print("Total number of characters in big-picture context:", len(context))
        return context

if __name__ == '__main__':
    get_big_context()