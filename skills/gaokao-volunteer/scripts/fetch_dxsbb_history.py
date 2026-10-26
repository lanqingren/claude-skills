#!/usr/bin/env python3
"""
从dxsbb.com的sitemap.xml提取所有含"投档"或"分数线"的URL
然后获取这些页面的内容
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

def fetch_page(url):
    try:
        r = session.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return None
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                text = content.decode(enc)
                if '院校' in text or '学校' in text:
                    return text
            except:
                continue
        return None
    except:
        return None

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

# 提取所有URL
all_urls = re.findall(r'<loc>([^<]+)</loc>', sitemap)
print(f"sitemap.xml: {len(all_urls)} 个URL")

# 过滤含"投档"或"分数线"的（从URL路径判断）
# dxsbb.com的URL格式: /news/{id}.html
# 需要获取页面标题来判断
# 先提取所有ID
url_ids = {}
for url in all_urls:
    m = re.search(r'/news/(\d+)\.html', url)
    if m:
        lid = int(m.group(1))
        url_ids[lid] = url

print(f"  有效页面ID: {len(url_ids)} 个")

# 2. 从分类页获取链接
print("\n=== 从分类页获取链接 ===")
list_pages = [
    "https://www.dxsbb.com/news/list_1001.html",  # 投档
    "https://www.dxsbb.com/news/list_168.html",   # 录取
    "https://www.dxsbb.com/news/list_553.html",   # 录取
    "https://www.dxsbb.com/news/list_565.html",   # 录取
]

history_links = {}  # {url: title}

for url in list_pages:
    try:
        r = session.get(url, headers=headers, timeout=10)
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                text = content.decode(enc)
                break
            except:
                text = content.decode('utf-8', errors='replace')
        
        links = re.findall(r'href=["\'](/news/(\d+)\.html)["\']([^>]*)>([^<]+)<', text)
        for path, lid, attrs, title in links:
            title = title.strip()
            if '2024' in title or '2023' in title or '2022' in title:
                if '投档' in title or '分数线' in title or '录取' in title:
                    full_url = f"https://www.dxsbb.com{path}"
                    history_links[full_url] = title
                    print(f"  {lid}: {title}")
    except Exception as e:
        print(f"  {url}: Error: {e}")
    time.sleep(0.5)

print(f"\n=== 找到 {len(history_links)} 个历史数据链接 ===")

# 3. 获取这些页面的内容
print("\n=== 获取历史数据页面 ===")
found_data = {}

for url, title in sorted(history_links.items(), key=lambda x: x[1]):
    lid_match = re.search(r'/news/(\d+)\.html', url)
    lid = lid_match.group(1) if lid_match else "?"
    
    text = fetch_page(url)
    if not text:
        continue
    
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 10:
            continue
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        if any('院校' in h or '学校' in h for h in header_cells):
            found_data[url] = {
                'title': title,
                'lid': lid,
                'rows': len(rows),
                'headers': header_cells[:6],
            }
            print(f"  ✅ ID {lid}: {title} ({len(rows)}行, {header_cells[:3]})")
            break
    
    time.sleep(0.3)

print(f"\n=== 共找到 {len(found_data)} 个有数据的历史页面 ===")
for url, info in sorted(found_data.items(), key=lambda x: x[1]['rows'], reverse=True):
    print(f"  ID {info['lid']}: {info['title']} ({info['rows']}行)")

# 保存
with open(os.path.join(RESULT_DIR, "dxsbb_history_data.json"), 'w', encoding='utf-8') as f:
    json.dump(found_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/dxsbb_history_data.json")
