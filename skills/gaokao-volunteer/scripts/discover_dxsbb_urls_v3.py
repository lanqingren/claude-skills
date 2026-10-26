#!/usr/bin/env python3
"""
搜索dxsbb.com上所有可能的2025年高考数据页面
搜索范围: 149000-150000
已知数据都在149119-149129范围内，可能还有其他范围
同时搜索2025年分数线汇总页面
"""
import requests, re, os, time, json

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_2025")

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

def extract_table_rows(text):
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) >= 10:
            header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
            header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
            if any('院校' in h or '学校' in h for h in header_cells):
                return len(rows), header_cells[:8]
    return 0, []

# 搜索148500-149500（跳过已知的149119-149129）
print("=== 搜索更大范围 ===")
found = {}

# 批量搜索
for lid in range(148500, 150000):
    if 149119 <= lid <= 149129:
        continue  # 已知的
    
    url = f"https://www.dxsbb.com/news/{lid}.html"
    text = fetch_page(url)
    if text:
        title = extract_title(text)
        rows, headers = extract_table_rows(text)
        if rows >= 50:
            print(f"  ID {lid}: {title} ({rows}行, {headers[:3]})")
            found[lid] = f"{title}"
    
    if lid % 100 == 0:
        print(f"  搜索到 {lid}...")
    
    time.sleep(0.15)

print(f"\n=== 找到 {len(found)} 个新页面 ===")
for lid, title in sorted(found.items()):
    print(f"  {lid}: {title}")

# 保存
all_urls = {
    "149119": "北京(本科)",
    "149120": "北京(专科)",
    "149121": "上海",
    "149123": "浙江(一段)",
    "149124": "浙江(二段)",
    "149125": "山东(第1次)",
    "149126": "山东(第2次)",
    "149127": "山东(第3次)",
    "149128": "河北(物理)",
    "149129": "河北(历史)",
}
for lid, title in found.items():
    all_urls[str(lid)] = title

with open(os.path.join(RESULT_DIR, "dxsbb_all_urls.json"), 'w', encoding='utf-8') as f:
    json.dump(all_urls, f, ensure_ascii=False, indent=2)
