#!/usr/bin/env python3
"""
从sitemap.xml中搜索含"2024年"的页面（不是"2025年含2024历年"）
这些页面可能包含2024年的完整投档线数据
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

# 获取sitemap.xml
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

# 获取所有页面标题
print("\n=== 搜索含'2024年'的页面 ===")
matching = {}

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
        
        # 搜索"2024年"开头或"2024年"在标题中的
        if '2024年' in title and '2025' not in title:
            lid_m = re.search(r'/news/(\d+)\.html', url)
            lid = lid_m.group(1) if lid_m else "?"
            matching[url] = title
            print(f"  [{i+1}/{len(all_urls)}] ID {lid}: {title}")
    except:
        pass
    
    if (i+1) % 100 == 0:
        print(f"  进度: {i+1}/{len(all_urls)}")
    
    time.sleep(0.03)

print(f"\n=== 找到 {len(matching)} 个含'2024年'的页面 ===")
for url, title in sorted(matching.items(), key=lambda x: x[1]):
    print(f"  {url}: {title}")

# 保存
with open(os.path.join(RESULT_DIR, "dxsbb_2024_urls.json"), 'w', encoding='utf-8') as f:
    json.dump(matching, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/dxsbb_2024_urls.json")
