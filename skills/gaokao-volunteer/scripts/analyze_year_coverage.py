#!/usr/bin/env python3
"""
分析当前数据中各省份的年份分布
找出哪些省份缺历史数据（只有1年或2年）
"""
import json, os
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")

with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
    classified = json.load(f)

print("=== 各省份年份分布 ===")
print(f"{'省份':<8} {'类型':<10} {'总pairs':>8} {'年份':<20} {'各科类对数'}")
print("-" * 80)

for prov, pdata in sorted(classified.items()):
    pairs = pdata.get('pairs', {})
    ptype = pdata.get('type', '?')
    
    # 按年份+科类统计
    year_cat = defaultdict(lambda: defaultdict(int))
    for key in pairs:
        parts = key.split('|')
        if len(parts) >= 3:
            year = parts[1]
            cat = parts[2]
            year_cat[year][cat] += 1
    
    years = sorted(year_cat.keys())
    year_str = ','.join(years)
    
    cat_details = []
    for y in years:
        cats = year_cat[y]
        cat_str = '+'.join(f"{c}:{n}" for c, n in sorted(cats.items()))
        cat_details.append(f"{y}({cat_str})")
    
    print(f"{prov:<8} {ptype:<10} {len(pairs):>8} {year_str:<20} {' | '.join(cat_details)}")

# 统计有3年以上数据的省份（可以做更好的回测）
print("\n=== 数据质量分级 ===")
tier_3plus = []  # 3年以上
tier_2 = []      # 2年
tier_1 = []      # 1年

for prov, pdata in sorted(classified.items()):
    pairs = pdata.get('pairs', {})
    years = set()
    for key in pairs:
        parts = key.split('|')
        if len(parts) >= 2:
            years.add(parts[1])
    
    if len(years) >= 3:
        tier_3plus.append((prov, len(years), len(pairs)))
    elif len(years) == 2:
        tier_2.append((prov, len(years), len(pairs)))
    else:
        tier_1.append((prov, len(years), len(pairs)))

print(f"\n🟢 3年以上数据 ({len(tier_3plus)}省):")
for prov, yc, pc in tier_3plus:
    print(f"  {prov}: {yc}年, {pc}对")

print(f"\n🟡 2年数据 ({len(tier_2)}省):")
for prov, yc, pc in tier_2:
    print(f"  {prov}: {yc}年, {pc}对")

print(f"\n🔴 1年数据 ({len(tier_1)}省):")
for prov, yc, pc in tier_1:
    print(f"  {prov}: {yc}年, {pc}对")
