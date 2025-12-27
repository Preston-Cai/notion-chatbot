from scrape import scrape_single_page
import json
import os

def get_big_context() -> None:
    """Get big-picture context from key_urls.json and write to another json file."""
    
    context = {}
    with open("key_urls.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
        for key in data:
            url = data[key]
            context[key] = scrape_single_page(url)

    with open("big_context.json", "w") as f:
        json.dump(context, f, indent=4)


def read_big_context() -> str:
    """Read the json file in the current directory named big_context and return 
    a string representation of the content.
    Note: run big_context.py to generate that file first.
    """
    if not os.path.exists("big_context.json"):
        get_big_context()

    with open("big_context.json", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == '__main__':
    get_big_context()