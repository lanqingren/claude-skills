#!/usr/bin/env python3
"""
基于v24回测数据重新计算差异化阈值和分数通胀校正
使用分科类回测v2的结果
"""
import json, os, sys, math
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "backtest_results")

# 加载分科类回测v2结果
with open(os.path.join(RESULT_DIR, "backtest_by_cat_v2.json"), 'r', encoding='utf-8') as f:
    bt = json.load(f)

# 加载province_classified.json
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
    classified = json.load(f)

# 计算每个省份+科类的详细统计
prov_cat_stats = defaultdict(lambda: defaultdict(lambda: {'offsets': [], 'years': set()}))

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
            prov_cat_stats[prov][cat]['offsets'].append(offset)
            prov_cat_stats[prov][cat]['years'].add(y1)
            prov_cat_stats[prov][cat]['years'].add(y2)

# 计算统计量
print("=== 各省份+科类 详细统计（用于更新附录A） ===")
print(f"{'省份':<8} {'科类':<10} {'偏移数':>6} {'均值':>8} {'中位数':>8} {'std':>8} {'Q1':>8} {'Q3':>8} {'IQR':>8}")
print("-" * 90)

for prov in sorted(prov_cat_stats.keys()):
    for cat in sorted(prov_cat_stats[prov].keys()):
        stats = prov_cat_stats[prov][cat]
        offsets = stats['offsets']
        if len(offsets) < 3:
            continue
        
        n = len(offsets)
        mean = sum(offsets) / n
        sorted_offsets = sorted(offsets)
        median = sorted_offsets[n // 2]
        q1 = sorted_offsets[n // 4]
        q3 = sorted_offsets[3 * n // 4]
        iqr = q3 - q1
        variance = sum((x - mean) ** 2 for x in offsets) / n
        std = math.sqrt(variance)
        
        print(f"{prov:<8} {cat:<10} {n:>6} {mean:>8.1f} {median:>8.1f} {std:>8.1f} {q1:>8.1f} {q3:>8.1f} {iqr:>8.1f}")

# 计算分数通胀校正
print("\n=== 分数通胀校正（用于更新A.3） ===")
print(f"{'省份':<8} {'科类':<10} {'中位偏移':>10} {'通胀等级'}")
print("-" * 50)

for prov in sorted(prov_cat_stats.keys()):
    for cat in sorted(prov_cat_stats[prov].keys()):
        stats = prov_cat_stats[prov][cat]
        offsets = stats['offsets']
        if len(offsets) < 3:
            continue
        
        sorted_offsets = sorted(offsets)
        median = sorted_offsets[len(offsets) // 2]
        
        if median > 25:
            level = "严重通胀"
        elif median > 10:
            level = "中度通胀"
        elif median > 5:
            level = "温和通胀"
        else:
            level = "稳定/通缩"
        
        print(f"{prov:<8} {cat:<10} {median:>10.1f} {level}")
