#!/usr/bin/env python3
"""
从各省考试院官网获取2024年一分一段表数据
策略：
1. 先检查现有一分一段表覆盖的省份
2. 对缺失的省份，从考试院官网搜索
3. 对已有但数据量不足的省份，补充更多年份
"""
import requests, re, os, json, time
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
SCORES_DIR = os.path.join(DATA_DIR, "province_scores")

os.makedirs(SCORES_DIR, exist_ok=True)

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 检查现有数据
print("=== 现有一分一段表 ===")
existing = {}
for f in sorted(os.listdir(SCORES_DIR)):
    fpath = os.path.join(SCORES_DIR, f)
    if f.endswith('.json') and 'scores' in f:
        size = os.path.getsize(fpath)
        with open(fpath, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        
        name = f.replace('_scores.json', '')
        if isinstance(data, list):
            existing[name] = len(data)
            print(f"  {name}: {len(data)}条 ({size/1024:.0f}KB)")
        elif isinstance(data, dict):
            total = sum(len(v) if isinstance(v, list) else 1 for v in data.values())
            existing[name] = total
            print(f"  {name}: {total}条 ({size/1024:.0f}KB)")

# 检查all_provinces_scores.json
print("\n=== all_provinces_scores.json ===")
fpath = os.path.join(SCORES_DIR, "all_provinces_scores.json")
if os.path.exists(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"  总记录: {len(data)}")
    
    # 按省份统计
    from collections import Counter
    prov_counts = Counter(item.get('province', item.get('省份', '?')) for item in data)
    print(f"  省份分布:")
    for prov, count in sorted(prov_counts.items(), key=lambda x: -x[1]):
        print(f"    {prov}: {count}条")

# 缺失的省份
all_provinces = ['北京','上海','天津','重庆','河北','山西','辽宁','吉林','黑龙江',
                 '江苏','浙江','安徽','福建','江西','山东','河南','湖北','湖南',
                 '广东','广西','海南','四川','贵州','云南','陕西','甘肃','青海',
                 '宁夏','新疆','内蒙古','西藏']

print(f"\n=== 缺失省份 ===")
missing = []
for prov in all_provinces:
    if prov not in existing:
        missing.append(prov)
        print(f"  ❌ {prov}")

print(f"\n现有: {len(existing)}省, 缺失: {len(missing)}省")
print(f"缺失列表: {', '.join(missing)}")
