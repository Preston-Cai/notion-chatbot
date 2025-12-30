from src.file_config import *
from pathlib import Path
import csv

old_links = set()
new_links = set()

old_links_path = Path(__file__).parent / "temp" / "scraping" / "progress" / "all_links_visited.csv"
new_links_path = ALL_LINKS_PATH

with open(old_links_path, "r", encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        for link in row:
            old_links.add(link)

with open(new_links_path, "r", encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        for link in row:
            new_links.add(link)

print("leng old links:", len(old_links))
print("leng new links:", len(new_links))
disjoint_links = old_links ^ new_links
intersection_links = old_links.intersection(new_links)
disjoint_list = list(disjoint_links)

print("disjoint:", len(disjoint_links))
print("intersection:", len(intersection_links))


print("New ", list(new_links)[:5])
print("Old", list(old_links)[:5])

with open("disjoint_links.csv", "w", encoding='utf-8') as f:
    writer = csv.writer(f)
    for i in range(0, len(disjoint_list), 5):
        writer.writerow(disjoint_list[i:i+5])
