#!/usr/bin/env python3
"""
发现dxsbb.com上所有省份的2025年投档线数据URL
策略：从已知ID(北京149119,上海149121)向外扩展搜索
"""
import requests, re, os, time, json
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_2025")
os.makedirs(RESULT_DIR, exist_ok=True)

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
    """提取页面标题"""
    m = re.search(r'<title[^>]*>([^<]+)</title>', text)
    if m:
        return m.group(1).strip()
    return ""

def extract_table_info(text):
    """提取表格信息"""
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
            return {
                'rows': len(rows),
                'headers': header_cells[:8],
            }
    
    return None

# 已知URL
known = {
    149119: "北京",
    149121: "上海",
}

# 搜索策略：在已知ID附近扩展
# 先搜索149100-149200范围
print("=== 搜索dxsbb.com 2025年数据URL ===")
found = dict(known)

# 从149100到149200搜索
for lid in range(149100, 149200):
    if lid in known:
        continue
    url = f"https://www.dxsbb.com/news/{lid}.html"
    text = fetch_page(url)
    if text:
        title = extract_title(text)
        info = extract_table_info(text)
        if info and info['rows'] > 10:
            # 可能是数据页面
            province = "未知"
            # 从标题提取省份
            for prov in ['北京','上海','江苏','浙江','广东','湖北','湖南','四川','陕西','河北','山东','山西','河南','安徽','江西','福建','广西','重庆','天津','辽宁','吉林','黑龙江','云南','贵州','甘肃','新疆','内蒙古','海南','宁夏','青海','西藏']:
                if prov in title:
                    province = prov
                    break
            
            print(f"  ID {lid}: {title} -> {province} ({info['rows']}行, {info['headers']})")
            found[lid] = province
    
    time.sleep(0.3)

# 保存结果
print(f"\n=== 找到 {len(found)} 个数据页面 ===")
for lid, prov in sorted(found.items()):
    print(f"  {lid}: {prov}")

# 保存到文件
with open(os.path.join(RESULT_DIR, "dxsbb_2025_urls.json"), 'w', encoding='utf-8') as f:
    json.dump({str(k): v for k, v in found.items()}, f, ensure_ascii=False, indent=2)
