#!/usr/bin/env python3
"""重新分析raw_2024.json，使用正确的字段名"""
import json, os
from collections import Counter, defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

with open(os.path.join(DATA_DIR, 'raw_2024.json'), 'r', encoding='utf-8') as f:
    raw = json.load(f)

print(f"raw_2024.json: {len(raw)} records")

# 正确字段: province_name, local_type_name, name(学校), sg_name(专业), 
# min(最低分), max(最高分), average(平均分), 
# min_section(最低位次), max_section(最高位次),
# proscore(省控线), year

# 看看有哪些字段值
sample = raw[0]
print(f"\n所有字段值概览:")
for k in sorted(sample.keys()):
    v = sample[k]
    if isinstance(v, str) and len(v) > 80:
        v = v[:80] + '...'
    print(f"  {k}: {v}")

# 统计省份
prov_cnt = Counter()
type_cnt = Counter()
year_cnt = Counter()
for item in raw:
    prov = item.get('province_name', '?')
    type_name = item.get('local_type_name', item.get('type_name', '?'))
    year = item.get('year', '?')
    prov_cnt[prov] += 1
    type_cnt[type_name] += 1
    year_cnt[year] += 1

print(f"\n=== 按省份 ({len(prov_cnt)}省) ===")
for prov, cnt in sorted(prov_cnt.items(), key=lambda x: -x[1]):
    print(f"  {prov}: {cnt}")

print(f"\n=== 按类型 ===")
for t, cnt in sorted(type_cnt.items(), key=lambda x: -x[1]):
    print(f"  {t}: {cnt}")

print(f"\n=== 按年份 ===")
for y, cnt in sorted(year_cnt.items()):
    print(f"  {y}: {cnt}")

# 看看科类信息
print(f"\n=== 科类/选科信息 ===")
sg_info = Counter()
sg_fxk = Counter()
for item in raw[:100]:
    sg_info[item.get('sg_info', '')[:50]] += 1
    sg_fxk[item.get('sg_fxk', '')] += 1
print("sg_info (前100):")
for s, c in sg_info.most_common(10):
    print(f"  {s}: {c}")
print("sg_fxk (前100):")
for s, c in sg_fxk.most_common(10):
    print(f"  {s}: {c}")

# 看看学校数量
schools = set()
for item in raw:
    schools.add(item.get('name', ''))
print(f"\n学校数: {len(schools)}")
print(f"前20所学校: {list(schools)[:20]}")

# 看看专业信息
print(f"\n=== 专业信息样本 ===")
for item in raw[:5]:
    print(f"  {item.get('name')}: {item.get('sg_name')} | {item.get('local_type_name')} | 分:{item.get('min')}-{item.get('max')} | 位次:{item.get('min_section')}-{item.get('max_section')}")
