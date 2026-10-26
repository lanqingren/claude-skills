#!/usr/bin/env python3
"""Analyze gaokao data coverage"""
import json
import os
from collections import Counter, defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

# 1. Analyze province_classified.json
with open(os.path.join(DATA_DIR, 'province_classified.json'), 'r', encoding='utf-8') as f:
    classified = json.load(f)

print("=" * 60)
print("province_classified.json 分析")
print("=" * 60)

total_pairs = 0
prov_stats = {}

for prov, pdata in sorted(classified.items()):
    ptype = pdata.get('type', '?')
    pairs = pdata.get('pairs', {})
    pair_count = len(pairs)
    total_pairs += pair_count
    
    # Count by year
    years = Counter()
    for key in pairs:
        parts = key.split('|')
        if len(parts) >= 2:
            years[parts[1]] += 1
    
    prov_stats[prov] = {
        'type': ptype,
        'pairs': pair_count,
        'years': dict(sorted(years.items()))
    }

print(f"\n总省份数: {len(classified)}")
print(f"总学校-年份-科类组合数: {total_pairs}")
print()

print(f"{'省份':<8} {'类型':<8} {'组合数':>6}  {'年份分布'}")
print("-" * 60)
for prov in sorted(prov_stats.keys()):
    s = prov_stats[prov]
    years_str = ', '.join(f"{y}:{c}" for y, c in s['years'].items())
    print(f"{prov:<8} {s['type']:<8} {s['pairs']:>6}  {years_str}")

# 2. Analyze province_v9 files
print("\n" + "=" * 60)
print("province_v9/ 文件分析")
print("=" * 60)

v9_dir = os.path.join(DATA_DIR, 'province_v9')
for fn in sorted(os.listdir(v9_dir)):
    if not fn.endswith('.json') or fn.startswith('ocr_'):
        continue
    fp = os.path.join(v9_dir, fn)
    sz = os.path.getsize(fp)
    with open(fp, 'r', encoding='utf-8') as f:
        d = json.load(f)
    
    if isinstance(d, dict):
        # Count records
        rec_count = 0
        for k, v in d.items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if isinstance(v2, list):
                        rec_count += len(v2)
                    elif isinstance(v2, dict):
                        rec_count += len(v2)
        print(f"  {fn:<30} {sz:>10,} bytes  {rec_count:>6} records")
    elif isinstance(d, list):
        print(f"  {fn:<30} {sz:>10,} bytes  {len(d):>6} records")

# 3. Analyze raw_2024.json
print("\n" + "=" * 60)
print("raw_2024.json 分析")
print("=" * 60)

raw_path = os.path.join(DATA_DIR, 'raw_2024.json')
if os.path.exists(raw_path):
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    if isinstance(raw, list):
        print(f"  总记录数: {len(raw)}")
        # By province
        prov_cnt = Counter()
        for item in raw:
            prov_cnt[item.get('province', item.get('省份', '?'))] += 1
        print(f"  省份数: {len(prov_cnt)}")
        for prov, cnt in sorted(prov_cnt.items(), key=lambda x: -x[1]):
            print(f"    {prov}: {cnt}")
    elif isinstance(raw, dict):
        print(f"  Keys: {list(raw.keys())[:10]}")
        print(f"  Type: {type(raw).__name__}")

# 4. Analyze 一分一段表
print("\n" + "=" * 60)
print("一分一段表覆盖")
print("=" * 60)

score_dir = os.path.join(DATA_DIR, 'province_scores')
if os.path.exists(score_dir):
    for fn in sorted(os.listdir(score_dir)):
        if not fn.endswith('.json'):
            continue
        fp = os.path.join(score_dir, fn)
        sz = os.path.getsize(fp)
        print(f"  {fn:<40} {sz:>10,} bytes")

# 5. Check which provinces have 2025 data
print("\n" + "=" * 60)
print("2025年数据覆盖")
print("=" * 60)

has_2025 = []
no_2025 = []
for prov, pdata in sorted(classified.items()):
    pairs = pdata.get('pairs', {})
    has = any('2025' in k for k in pairs.keys())
    if has:
        has_2025.append(prov)
    else:
        no_2025.append(prov)

print(f"有2025年数据的省份 ({len(has_2025)}): {', '.join(has_2025)}")
print(f"缺2025年数据的省份 ({len(no_2025)}): {', '.join(no_2025)}")
