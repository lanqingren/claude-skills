#!/usr/bin/env python3
"""
新策略：
1. 从各省考试院官网获取2024年一分一段表
2. 搜索dxsbb.com上2024年数据的URL（不在sitemap中的）

先处理一分一段表——这是回测的关键数据
"""
import requests, re, os, json, time
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
SCORES_DIR = os.path.join(DATA_DIR, "province_scores")

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 先看看现有的一分一段表数据格式
print("=== 检查现有一分一段表格式 ===")
sample_files = [
    os.path.join(SCORES_DIR, "河北_scores.json"),
    os.path.join(SCORES_DIR, "江苏_scores.json"),
    os.path.join(SCORES_DIR, "浙江_scores.json"),
]

for fpath in sample_files:
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fname = os.path.basename(fpath)
    if isinstance(data, list):
        print(f"\n{fname}: {len(data)}条")
        if data:
            print(f"  字段: {list(data[0].keys())}")
            print(f"  前3条: {json.dumps(data[:3], ensure_ascii=False)[:300]}")
    elif isinstance(data, dict):
        print(f"\n{fname}: {len(data)}键")
        sample_key = list(data.keys())[0]
        print(f"  样本键: {sample_key}")
        print(f"  样本值: {json.dumps(data[sample_key], ensure_ascii=False)[:300]}")

# 检查all_provinces_scores.json的格式
print("\n=== all_provinces_scores.json ===")
fpath = os.path.join(SCORES_DIR, "all_provinces_scores.json")
if os.path.exists(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        print(f"  {len(data)}条")
        if data:
            print(f"  字段: {list(data[0].keys())}")
            # 按省份分组统计
            from collections import Counter
            prov_counts = Counter(item.get('province', item.get('省份', '?')) for item in data)
            print(f"  省份分布: {dict(prov_counts)}")
    elif isinstance(data, dict):
        print(f"  {len(data)}键")
        for k in list(data.keys())[:5]:
            v = data[k]
            if isinstance(v, list):
                print(f"  {k}: {len(v)}条")
            else:
                print(f"  {k}: {type(v).__name__}")
