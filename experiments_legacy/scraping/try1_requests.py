from bs4 import BeautifulSoup
import requests

url = 'https://utat-ss.notion.site/UTAT-Space-Systems-660068a07b694305b56c483962e927c5'


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/118.0.5993.118 Safari/537.36"
}

res = requests.get(url, headers=headers)

if res.status_code == 200:
    soup = BeautifulSoup(res.text, "html.parser")
    print(soup.get_text()[:10])
else:
    print(f'failed to fetch: {res.status_code}')