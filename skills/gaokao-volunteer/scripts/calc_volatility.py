#!/usr/bin/env python3
"""
基于v24回测数据重新计算各省波动性分档
输出markdown格式的A.1表格
"""
import json, os, sys, math
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")

with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
    classified = json.load(f)

# 计算每个省份+科类的分数偏移标准差
prov_cat_offsets = defaultdict(lambda: defaultdict(list))

for prov, pdata in classified.items():
    pairs_data = pdata.get('pairs', {})
    
    school_cat_years = defaultdict(lambda: defaultdict(dict))
    for key, val in pairs_data.items():
        parts = key.split('|')
        if len(parts) >= 3:
            school = parts[0]
            year = parts[1]
            cat = parts[2]
            score = val.get('score') if isinstance(val, dict) else val
            if score is not None:
                try:
                    score = int(score)
                    if score > 0:
                        school_cat_years[(school, cat)][year] = score
                except:
                    continue
    
    for (school, cat), years in school_cat_years.items():
        year_list = sorted(years.keys())
        for i in range(len(year_list) - 1):
            y1 = year_list[i]
            y2 = year_list[i + 1]
            offset = years[y2] - years[y1]
            prov_cat_offsets[prov][cat].append(offset)

# 计算每个省份+科类的std
print("=== 各省份+科类 分数偏移标准差 ===")
print(f"{'省份':<8} {'科类':<10} {'偏移数':>6} {'均值':>8} {'中位数':>8} {'std':>8} {'档位'}")
print("-" * 70)

stable = []    # std < 20
medium = []   # 20 <= std < 40
high = []     # std >= 40

prov_cat_std = {}

for prov in sorted(prov_cat_offsets.keys()):
    for cat in sorted(prov_cat_offsets[prov].keys()):
        offsets = prov_cat_offsets[prov][cat]
        if len(offsets) < 3:
            continue
        
        n = len(offsets)
        mean = sum(offsets) / n
        sorted_offsets = sorted(offsets)
        median = sorted_offsets[n // 2]
        variance = sum((x - mean) ** 2 for x in offsets) / n
        std = math.sqrt(variance)
        
        if std < 20:
            tier = "稳定"
            stable.append((prov, cat, std, len(offsets)))
        elif std < 40:
            tier = "中等"
            medium.append((prov, cat, std, len(offsets)))
        else:
            tier = "高波动"
            high.append((prov, cat, std, len(offsets)))
        
        prov_cat_std[(prov, cat)] = {'std': std, 'mean': mean, 'median': median, 'n': n, 'tier': tier}
        print(f"{prov:<8} {cat:<10} {n:>6} {mean:>8.1f} {median:>8.1f} {std:>8.1f} {tier}")

print(f"\n=== 分档汇总 ===")
print(f"\n稳定 ({len(stable)}组):")
for prov, cat, std, n in sorted(stable, key=lambda x: x[2]):
    print(f"  {prov} {cat}: std={std:.1f}, {n}个偏移")

print(f"\n中等 ({len(medium)}组):")
for prov, cat, std, n in sorted(medium, key=lambda x: x[2]):
    print(f"  {prov} {cat}: std={std:.1f}, {n}个偏移")

print(f"\n高波动 ({len(high)}组):")
for prov, cat, std, n in sorted(high, key=lambda x: x[2]):
    print(f"  {prov} {cat}: std={std:.1f}, {n}个偏移")
