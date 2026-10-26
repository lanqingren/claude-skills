#!/usr/bin/env python3
"""
继续搜索dxsbb.com上更多省份的2025年数据
已知ID范围: 149119-149129
搜索更大范围: 149100-149300
"""
import requests, re, os, time, json
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_2025")

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def fetch_page(url):
    try:
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                text = content.decode(enc)
                if '院校' in text or '学校' in text or '投档' in text:
                    return text
            except:
                continue
        return content.decode('utf-8', errors='replace')
    except:
        return None

def extract_title(text):
    m = re.search(r'<title[^>]*>([^<]+)</title>', text)
    return m.group(1).strip() if m else ""

def extract_table_info(text):
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    if not tables:
        return None
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 3:
            continue
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        if any('院校' in h or '学校' in h for h in header_cells):
            return {'rows': len(rows), 'headers': header_cells[:8]}
    return None

# 已知URL
known = {
    149119: "北京(本科)",
    149120: "北京(专科)",
    149121: "上海",
    149123: "浙江(一段)",
    149124: "浙江(二段)",
    149125: "山东(第1次)",
    149126: "山东(第2次)",
    149127: "山东(第3次)",
    149128: "河北(物理)",
    149129: "河北(历史)",
}

# 搜索149130-149300
print("=== 搜索149130-149300 ===")
found = dict(known)

for lid in range(149130, 149300):
    url = f"https://www.dxsbb.com/news/{lid}.html"
    text = fetch_page(url)
    if text:
        title = extract_title(text)
        info = extract_table_info(text)
        if info and info['rows'] > 10:
            province = "未知"
            for prov in ['北京','上海','江苏','浙江','广东','湖北','湖南','四川','陕西','河北','山东','山西','河南','安徽','江西','福建','广西','重庆','天津','辽宁','吉林','黑龙江','云南','贵州','甘肃','新疆','内蒙古','海南','宁夏','青海','西藏']:
                if prov in title:
                    province = prov
                    break
            
            print(f"  ID {lid}: {title} -> {province} ({info['rows']}行)")
            found[lid] = f"{province}:{title}"
    
    time.sleep(0.2)

# 保存
print(f"\n=== 共找到 {len(found)} 个数据页面 ===")
for lid, info in sorted(found.items()):
    print(f"  {lid}: {info}")

with open(os.path.join(RESULT_DIR, "dxsbb_2025_urls_full.json"), 'w', encoding='utf-8') as f:
    json.dump({str(k): v for k, v in found.items()}, f, ensure_ascii=False, indent=2)

print(f"\n✅ 结果保存到 {RESULT_DIR}/dxsbb_2025_urls_full.json")
