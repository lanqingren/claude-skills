#!/usr/bin/env python3
"""
从sitemap.xml中搜索含"2024年"的页面（不是"2025年含2024历年"）
同时尝试从dxsbb.com的院校库API获取数据
"""
import requests, re, os, json, time
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_history")

os.makedirs(RESULT_DIR, exist_ok=True)

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 1. 获取sitemap.xml
print("=== 获取sitemap.xml ===")
r = session.get("https://www.dxsbb.com/sitemap.xml", headers=headers, timeout=15)
content = r.content
for enc in ['utf-8', 'gbk', 'gb2312']:
    try:
        sitemap = content.decode(enc)
        break
    except:
        sitemap = content.decode('utf-8', errors='replace')

all_urls = re.findall(r'<loc>([^<]+)</loc>', sitemap)
print(f"sitemap.xml: {len(all_urls)} 个URL")

# 2. 获取所有页面标题，找含"2024"的
print("\n=== 搜索含'2024'的页面 ===")
matching_2024 = {}
matching_2023 = {}
matching_2022 = {}

for i, url in enumerate(all_urls):
    try:
        r = session.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            continue
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312']:
            try:
                text = content.decode(enc)
                break
            except:
                text = content.decode('utf-8', errors='replace')
        
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', text)
        title = title_m.group(1).strip() if title_m else ""
        
        lid_m = re.search(r'/news/(\d+)\.html', url)
        lid = lid_m.group(1) if lid_m else "?"
        
        if '2024' in title and '2025' not in title:
            matching_2024[url] = title
            print(f"  [{i+1}/{len(all_urls)}] ID {lid}: {title}")
        elif '2023' in title and '2025' not in title and '2024' not in title:
            matching_2023[url] = title
        elif '2022' in title and '2025' not in title and '2024' not in title and '2023' not in title:
            matching_2022[url] = title
    except:
        pass
    
    if (i+1) % 100 == 0:
        print(f"  进度: {i+1}/{len(all_urls)}, 2024={len(matching_2024)}, 2023={len(matching_2023)}, 2022={len(matching_2022)}")
    
    time.sleep(0.03)

print(f"\n=== 找到 {len(matching_2024)} 个含'2024'的页面 ===")
for url, title in sorted(matching_2024.items(), key=lambda x: x[1]):
    print(f"  {url}: {title}")

print(f"\n=== 找到 {len(matching_2023)} 个含'2023'的页面 ===")
for url, title in sorted(matching_2023.items(), key=lambda x: x[1])[:10]:
    print(f"  {url}: {title}")

print(f"\n=== 找到 {len(matching_2022)} 个含'2022'的页面 ===")
for url, title in sorted(matching_2022.items(), key=lambda x: x[1])[:10]:
    print(f"  {url}: {title}")

# 保存
with open(os.path.join(RESULT_DIR, "dxsbb_2024_urls.json"), 'w', encoding='utf-8') as f:
    json.dump(matching_2024, f, ensure_ascii=False, indent=2)
with open(os.path.join(RESULT_DIR, "dxsbb_2023_urls.json"), 'w', encoding='utf-8') as f:
    json.dump(matching_2023, f, ensure_ascii=False, indent=2)
