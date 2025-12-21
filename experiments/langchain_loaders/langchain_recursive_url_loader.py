from langchain_community.document_loaders import RecursiveUrlLoader
from bs4 import BeautifulSoup

URL = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"
loader = RecursiveUrlLoader(
    # "https://docs.python.org/3.9/",
    URL,
    max_depth=5,
    # use_async=False,
    # extractor=None,
    # metadata_extractor=None,
    # exclude_dirs=(),
    # timeout=10,
    # check_response_status=True,
    # continue_on_failure=True,
    # prevent_outside=True,
    # base_url=None,
    # ...
)

docs = loader.load()
html_string = docs[0].page_content
soup = BeautifulSoup(html_string, 'html.parser')

print(docs[0].metadata)
with open("scraped-by-langchain.html", 'w', encoding='utf-8') as f:
    f.write(soup.prettify())
    print("html saved")


print(docs[0].page_content[:300])
print("number of docs found: ", len(docs))