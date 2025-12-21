from langchain_community.document_loaders import SeleniumURLLoader


URL = "https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5"
BASE_URL = "https://utat-ss.notion.site/"

urls = [
    URL,
    # "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    # "https://goo.gl/maps/NDSHwePEyaHMFGwh8",
]

loader = SeleniumURLLoader(urls=urls)

data = loader.load()
with open("langchain_page_1.txt", 'w', encoding='utf-8') as f:
    f.write(str(data))
print(data)