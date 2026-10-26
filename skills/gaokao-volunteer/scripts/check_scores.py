#!/usr/bin/env python3
"""
检查现有一分一段表数据覆盖情况
并从各省考试院官网获取缺失的2024年一分一段表
"""
import os, json, re
import requests
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
SCORES_DIR = os.path.join(DATA_DIR, "province_scores")

os.makedirs(SCORES_DIR, exist_ok=True)

# 检查现有一分一段表
print("=== 现有一分一段表 ===")
if os.path.exists(SCORES_DIR):
    for f in sorted(os.listdir(SCORES_DIR)):
        fpath = os.path.join(SCORES_DIR, f)
        size = os.path.getsize(fpath)
        if f.endswith('.json'):
            with open(fpath, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            if isinstance(data, list):
                print(f"  {f}: {len(data)}条 ({size}字节)")
            elif isinstance(data, dict):
                print(f"  {f}: {len(data)}键 ({size}字节)")
            else:
                print(f"  {f}: {size}字节")
        else:
            print(f"  {f}: {size}字节")

# 检查哪些省份缺失
existing_provinces = set()
for f in os.listdir(SCORES_DIR):
    # 从文件名提取省份名
    name = f.replace('.json', '').replace('.csv', '').replace('.xlsx', '')
    # 去掉年份后缀
    name = re.sub(r'_?\d{4}$', '', name)
    name = re.sub(r'_\d{4}_', '_', name)
    existing_provinces.add(name)

all_provinces = ['北京','上海','江苏','浙江','广东','湖北','湖南','四川','陕西','河北','山东','山西','河南','安徽','江西','福建','广西','重庆','天津','辽宁','吉林','黑龙江','云南','贵州','甘肃','新疆','内蒙古','海南','宁夏','青海','西藏']

print(f"\n=== 缺失省份 ===")
missing = []
for prov in all_provinces:
    if prov not in existing_provinces:
        missing.append(prov)
        print(f"  ❌ {prov}")

print(f"\n现有: {len(existing_provinces)}省, 缺失: {len(missing)}省")
