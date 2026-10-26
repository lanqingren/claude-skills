#!/usr/bin/env python3
"""
高考志愿数据采集缺口分析
输出：当前各省各年份数据覆盖情况 + 缺失清单
"""
import json, os
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")

with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
    classified = json.load(f)

TARGET_YEARS = [2023, 2024, 2025]
PROVINCES = sorted(classified.keys())

print("=== 数据覆盖矩阵（院校数） ===")
print(f"{'省份':<8} {'203':>5} {'2024':>5} {'2025':>5} {'总院校':>6} {'状态'}")
print("-" * 50)

gap_list = []
total_by_year = defaultdict(int)

for prov in PROVINCES:
    pdata = classified[prov]
    pair_data = pdata.get('pairs', {})
    
    year_schools = defaultdict(set)
    for key in pair_data:
        parts = key.split('|')
        if len(parts) >= 3:
            school = parts[0]
            try:
                year = int(parts[1])
                year_schools[year].add(school)
            except:
                continue
    
    counts = {}
    for y in TARGET_YEARS:
        counts[y] = len(year_schools.get(y, set()))
        total_by_year[y] += counts[y]
    
    total = len(set().union(*year_schools.values())) if year_schools else 0
    
    # 状态判断
    has_years = [y for y in TARGET_YEARS if counts[y] > 0]
    if len(has_years) == 3:
        status = "✅ 完整"
    elif len(has_years) >= 2:
        status = f"⚠️ 缺{[y for y in TARGET_YEARS if counts[y]==0]}"
    elif len(has_years) == 1:
        status = f"🔴 仅{has_years[0]}"
        gap_list.append((prov, has_years, counts))
    else:
        status = "❌ 无数据"
        gap_list.append((prov, has_years, counts))
    
    print(f"{prov:<8} {counts[2023]:>5} {counts[2024]:>5} {counts[2025]:>5} {total:>6} {status}")

print(f"\n{'合计':<8} {total_by_year[2023]:>5} {total_by_year[2024]:>5} {total_by_year[2025]:>5}")

print(f"\n=== 缺失数据省份（{len(gap_list)}个） ===")
for prov, has_years, counts in gap_list:
    missing = [y for y in TARGET_YEARS if counts[y] == 0]
    print(f"  {prov}: 有{has_years}, 缺{missing}")

# 按年份对统计
print(f"\n=== 各年份数据覆盖 ===")
for y in TARGET_YEARS:
    provs_with = [p for p in PROVINCES if len(classified[p].get('pairs', {})) > 0 and any(k.split('|')[1] == str(y) for k in classified[p].get('pairs', {}))]
    print(f"  {y}: {len(provs_with)}省, {total_by_year[y]}所院校")

# 保存缺口清单
gap_report = {
    'analysis_time': str(__import__('datetime').datetime.now()),
    'total_provinces': len(PROVINCES),
    'total_records': sum(len(p.get('pairs', {})) for p in classified.values()),
    'year_coverage': {str(y): total_by_year[y] for y in TARGET_YEARS},
    'gap_provinces': [
        {'province': p, 'has_years': h, 'missing_years': [y for y in TARGET_YEARS if y not in h]}
        for p, h, c in gap_list
    ],
    'full_provinces': [p for p in PROVINCES if all(len(classified[p].get('pairs', {})) > 0 and any(k.split('|')[1] == str(y) for k in classified[p].get('pairs', {})) for y in TARGET_YEARS)]
}

with open(os.path.join(DATA_DIR, "data_gap_analysis.json"), 'w', encoding='utf-8') as f:
    json.dump(gap_report, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {DATA_DIR}/data_gap_analysis.json")
