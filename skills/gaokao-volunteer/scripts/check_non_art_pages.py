#!/usr/bin/env python3
"""
从已发现的57个页面中，获取非艺术类的普通本科数据
"""
import requests, re, os, json, time
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_history")

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

# 加载URL列表
with open(os.path.join(RESULT_DIR, "dxsbb_history_urls_from_sitemap.json"), 'r', encoding='utf-8') as f:
    urls = json.load(f)

# 过滤非艺术类的页面
non_art_urls = {}
for url, title in urls.items():
    if '艺术' not in title and '中外合作' not in title:
        non_art_urls[url] = title

print(f"非艺术类页面: {len(non_art_urls)} 个")
for url, title in sorted(non_art_urls.items(), key=lambda x: x[1]):
    lid = url.split('/')[-1].replace('.html', '')
    print(f"  {lid}: {title}")

# 获取前5个页面的内容
print("\n=== 获取前5个非艺术类页面 ===")
for i, (url, title) in enumerate(sorted(non_art_urls.items(), key=lambda x: x[1])[:5]):
    lid = url.split('/')[-1].replace('.html', '')
    print(f"\n--- ID {lid}: {title} ---")
    
    text = fetch_page(url)
    if not text:
        print("  ❌ 无法获取")
        continue
    
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    for ti, table in enumerate(tables):
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 5:
            continue
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        print(f"  Table {ti}: {len(rows)}行, 表头: {header_cells[:6]}")
        
        # 打印前3行数据
        for row in rows[1:4]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            print(f"    {cells[:6]}")
    
    time.sleep(0.3)
