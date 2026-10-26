#!/usr/bin/env python3
"""
获取sitemap中找到的历史数据页面
这些页面标题含"2024"或"2023-2024历年"
需要获取页面内容并解析表格
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

# 加载URL列表
with open(os.path.join(RESULT_DIR, "dxsbb_history_urls_from_sitemap.json"), 'r', encoding='utf-8') as f:
    urls = json.load(f)

print(f"共 {len(urls)} 个页面需要获取")

found_data = {}
for i, (url, title) in enumerate(sorted(urls.items(), key=lambda x: x[1])):
    lid_m = re.search(r'/news/(\d+)\.html', url)
    lid = lid_m.group(1) if lid_m else "?"
    
    text = fetch_page(url)
    if not text:
        continue
    
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    data_tables = []
    
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 5:
            continue
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        if any('院校' in h or '学校' in h for h in header_cells):
            data_tables.append({
                'rows': len(rows),
                'headers': header_cells[:6],
            })
    
    if data_tables:
        total_rows = sum(t['rows'] for t in data_tables)
        found_data[url] = {
            'title': title,
            'lid': lid,
            'tables': len(data_tables),
            'total_rows': total_rows,
        }
        print(f"  [{i+1}/{len(urls)}] ✅ ID {lid}: {title} ({len(data_tables)}个表, {total_rows}行)")
    else:
        print(f"  [{i+1}/{len(urls)}] ❌ ID {lid}: {title} (无数据表)")
    
    time.sleep(0.2)

print(f"\n=== 共找到 {len(found_data)} 个有数据的页面 ===")
for url, info in sorted(found_data.items(), key=lambda x: x[1]['total_rows'], reverse=True):
    print(f"  ID {info['lid']}: {info['title']} ({info['tables']}表, {info['total_rows']}行)")

# 保存
with open(os.path.join(RESULT_DIR, "dxsbb_history_pages.json"), 'w', encoding='utf-8') as f:
    json.dump(found_data, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/dxsbb_history_pages.json")
