#!/usr/bin/env python3
"""对比v22和v23回测结果"""
import json, os
import numpy as np
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

# 加载v22结果
with open(os.path.join(DATA_DIR, 'backtest_results', 'backtest_v22.json'), 'r', encoding='utf-8') as f:
    v22 = json.load(f)

# 加载v23结果
with open(os.path.join(DATA_DIR, 'backtest_results', 'backtest_v23.json'), 'r', encoding='utf-8') as f:
    v23 = json.load(f)

# 加载当前数据
with open(os.path.join(DATA_DIR, 'province_classified.json'), 'r', encoding='utf-8') as f:
    classified = json.load(f)

# 统计v22的数据
v22_total_pairs = 0
v22_provinces = 0
v22_national_c = []
v22_national_w = []
v22_national_b = []
v22_detail = {}

for prov, pdata in v22.items():
    ptype = pdata.get('type', '?')
    for cat, metrics in pdata.get('cats', {}).items():
        v22_provinces += 1
        v22_total_pairs += metrics['pairs']
        v22_national_c.append(metrics['hit_c'])
        v22_national_w.append(metrics['hit_w'])
        v22_national_b.append(metrics['hit_b'])
        v22_detail[f"{prov}({cat})"] = metrics

v23_total_pairs = v23['total_pairs']
v23_provinces = v23['total_provinces']
v23_national = v23['national']

print("=" * 70)
print("📊 v22 vs v23 回测结果对比")
print("=" * 70)

print(f"\n{'指标':<20} {'v22':>15} {'v23':>15} {'变化':>10}")
print("-" * 60)
print(f"{'覆盖省份/科类数':<20} {v22_provinces:>15} {v23_provinces:>15} {v23_provinces-v22_provinces:>+10}")
print(f"{'总数据对':<20} {v22_total_pairs:>15,} {v23_total_pairs:>15,} {v23_total_pairs-v22_total_pairs:>+10,}")

print(f"\n{'冲命中率(均值)':<20} {np.mean(v22_national_c):>14.1f}% {v23_national['hit_c_mean']:>14.1f}% {v23_national['hit_c_mean']-np.mean(v22_national_c):>+9.1f}pp")
print(f"{'稳命中率(均值)':<20} {np.mean(v22_national_w):>14.1f}% {v23_national['hit_w_mean']:>14.1f}% {v23_national['hit_w_mean']-np.mean(v22_national_w):>+9.1f}pp")
print(f"{'保命中率(均值)':<20} {np.mean(v22_national_b):>14.1f}% {v23_national['hit_b_mean']:>14.1f}% {v23_national['hit_b_mean']-np.mean(v22_national_b):>+9.1f}pp")

print(f"\n{'冲命中率(范围)':<20} {min(v22_national_c):.1f}-{max(v22_national_c):.1f}% {v23_national['hit_c_min']:.1f}-{v23_national['hit_c_max']:.1f}%")
print(f"{'稳命中率(范围)':<20} {min(v22_national_w):.1f}-{max(v22_national_w):.1f}% {v23_national['hit_w_min']:.1f}-{v23_national['hit_w_max']:.1f}%")
print(f"{'保命中率(范围)':<20} {min(v22_national_b):.1f}-{max(v22_national_b):.1f}% {v23_national['hit_b_min']:.1f}-{v23_national['hit_b_max']:.1f}%")

# 数据增量
print(f"\n{'='*70}")
print(f"📈 数据增量统计")
print(f"{'='*70}")
old_total = sum(len(pdata.get('pairs', {})) for pdata in classified.values())
# 实际上old_total就是当前数据，因为v23用的是最新数据
print(f"当前数据总量: {old_total} pairs")

# 看看新增的raw_2024.json数据分布在哪些省份
print(f"\n{'='*70}")
print(f"📋 v23新增/变化的省份/科类")
print(f"{'='*70}")

v23_detail = {r['province']: r for r in v23['provinces']}
for key, r22 in sorted(v22_detail.items()):
    prov = key.split('(')[0]
    r23 = v23_detail.get(prov)
    if r23:
        pair_chg = r23['pairs'] - r22['pairs']
        if pair_chg != 0:
            print(f"  {key}: {r22['pairs']}→{r23['pairs']}对 ({pair_chg:+d}), "
                  f"冲{r22['hit_c']}%→{r23['hit_c']}%, "
                  f"稳{r22['hit_w']}%→{r23['hit_w']}%, "
                  f"保{r22['hit_b']}%→{r23['hit_b']}%")
    else:
        print(f"  {key}: 在v23中未找到")
