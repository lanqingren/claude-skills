#!/usr/bin/env python3
"""
从dxsbb.com拉取历史年份数据（2024/2023/2022）
策略：搜索更大范围的ID，找含"投档"或"分数线"的页面
已知2025年数据在149119-149129
"""
import requests, re, os, time, json
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
                if '院校' in text or '学校' in text or '投档' in text or '分数线' in text:
                    return text
            except:
                continue
        return None
    except:
        return None

def extract_title(text):
    m = re.search(r'<title[^>]*>([^<]+)</title>', text)
    return m.group(1).strip() if m else ""

def has_data_table(text):
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) >= 10:
            header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
            header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
            if any('院校' in h or '学校' in h for h in header_cells):
                return len(rows), header_cells[:6]
    return 0, []

# 搜索范围：140000-149200（跳过已知的2025年范围）
print("=== 搜索dxsbb.com历史年份数据 ===")
found = {}

# 先搜索148000-149200（2024年数据可能在这个范围）
for lid in range(148000, 149100):
    url = f"https://www.dxsbb.com/news/{lid}.html"
    text = fetch_page(url)
    if text:
        title = extract_title(text)
        rows, headers = has_data_table(text)
        if rows >= 50:
            year_match = re.search(r'(202[0-4])', title)
            year = year_match.group(1) if year_match else "?"
            print(f"  ID {lid}: {title} ({rows}行, 年份={year})")
            found[lid] = {"title": title, "rows": rows, "year": year}
    
    if lid % 200 == 0 and lid > 148000:
        print(f"  搜索到 {lid}...")
    
    time.sleep(0.1)

print(f"\n=== 找到 {len(found)} 个历史数据页面 ===")
for lid, info in sorted(found.items()):
    print(f"  {lid}: {info['title']} ({info['rows']}行, {info['year']})")

with open(os.path.join(RESULT_DIR, "dxsbb_history_urls.json"), 'w', encoding='utf-8') as f:
    json.dump({str(k): v for k, v in found.items()}, f, ensure_ascii=False, indent=2)
