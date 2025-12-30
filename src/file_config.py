"""Config file for computing absolute file path and dir paths."""

from pathlib import Path

# Root dir for data storage
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Scraping dirs
SCRAPING_DIR = DATA_DIR / "scraping"
HTML_DIR = SCRAPING_DIR / "html_docs"
TEXT_DIR = SCRAPING_DIR / "text_docs"
JSON_DIR = SCRAPING_DIR / "json_docs"
PROGRESS_DIR = SCRAPING_DIR / "progress"

# Context dirs
CONTEXT_DIR = DATA_DIR / "context"

# DB dir
DB_DIR = DATA_DIR / "chroma_langchain_db"

# Ensure directories exist
for d in [
    HTML_DIR,
    TEXT_DIR,
    JSON_DIR,
    PROGRESS_DIR,
    CONTEXT_DIR,
    DB_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)

# Progress files
ALL_LINKS_PATH = PROGRESS_DIR / "all_links_visited.csv"
VISITED_LINKS_PATH = PROGRESS_DIR / "progress_links.csv"
TO_VISIT_LINKS_PATH = PROGRESS_DIR / "progress_to_visit.csv"
FAILED_LINKS_PATH = PROGRESS_DIR / "progress_failed_links.csv"

# Context files
BIG_CONTEXT_PATH = CONTEXT_DIR / "big_context.json"
KEY_URLS_PATH = CONTEXT_DIR / "key_urls.json"

# Create empty key_urls.json if not exists
KEY_URLS_PATH.touch(exist_ok=True)