#!/usr/bin/env python3
"""
新策略：从dxsbb.com的已知页面ID范围外搜索
重点搜索2024年（148000-149000）和2023年（147000-148000）
同时尝试不同的请求方式绕过限流
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
                if '院校' in text or '学校' in text:
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

# 搜索2024年数据（148000-149000）
# 每50个采样一个，找到有数据的ID后再详细搜索附近
print("=== 粗扫148000-149000（每50个采样） ===")
candidates_2024 = []

for lid in range(148000, 149000, 50):
    url = f"https://www.dxsbb.com/news/{lid}.html"
    text = fetch_page(url)
    if text:
        title = extract_title(text)
        rows, headers = has_data_table(text)
        if rows >= 50:
            print(f"  ID {lid}: {title} ({rows}行)")
            candidates_2024.append((lid, title, rows))
    time.sleep(0.15)

# 对候选ID附近详细搜索
print(f"\n=== 详细搜索候选ID附近（{len(candidates_2024)}个候选） ===")
found_2024 = {}

for base_lid, base_title, base_rows in candidates_2024:
    for offset in range(-25, 26):
        lid = base_lid + offset
        if lid < 148000 or lid >= 149000:
            continue
        url = f"https://www.dxsbb.com/news/{lid}.html"
        text = fetch_page(url)
        if text:
            title = extract_title(text)
            rows, headers = has_data_table(text)
            if rows >= 50:
                year = "2024" if "2024" in title else "?"
                found_2024[lid] = {"title": title, "rows": rows, "year": year}
                print(f"  ID {lid}: {title} ({rows}行)")
        time.sleep(0.1)

# 同样搜索2023年（147000-148000）
print("\n=== 粗扫147000-148000（每50个采样） ===")
candidates_2023 = []

for lid in range(147000, 148000, 50):
    url = f"https://www.dxsbb.com/news/{lid}.html"
    text = fetch_page(url)
    if text:
        title = extract_title(text)
        rows, headers = has_data_table(text)
        if rows >= 50:
            print(f"  ID {lid}: {title} ({rows}行)")
            candidates_2023.append((lid, title, rows))
    time.sleep(0.1)

# 详细搜索2023年候选
print(f"\n=== 详细搜索2023年候选ID附近（{len(candidates_2023)}个候选） ===")
found_2023 = {}

for base_lid, base_title, base_rows in candidates_2023:
    for offset in range(-25, 26):
        lid = base_lid + offset
        if lid < 147000 or lid >= 148000:
            continue
        url = f"https://www.dxsbb.com/news/{lid}.html"
        text = fetch_page(url)
        if text:
            title = extract_title(text)
            rows, headers = has_data_table(text)
            if rows >= 50:
                year = "2023" if "2023" in title else "?"
                found_2023[lid] = {"title": title, "rows": rows, "year": year}
                print(f"  ID {lid}: {title} ({rows}行)")
        time.sleep(0.1)

# 保存
all_found = {**found_2024, **found_2023}
print(f"\n=== 共找到 {len(all_found)} 个历史数据页面 ===")
for lid, info in sorted(all_found.items()):
    print(f"  {lid}: {info['title']} ({info['rows']}行, {info['year']})")

with open(os.path.join(RESULT_DIR, "dxsbb_history_urls_v2.json"), 'w', encoding='utf-8') as f:
    json.dump({str(k): v for k, v in all_found.items()}, f, ensure_ascii=False, indent=2)
