#!/usr/bin/env python3
"""
从raw_2024.json提取31省数据并补充到province_classified.json
注意: 用province_name(生源地省份)，不是local_province_name
先恢复贵州的原始数据，再正确补充所有省份
"""
import json, os
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
classified_path = os.path.join(DATA_DIR, 'province_classified.json')

with open(os.path.join(DATA_DIR, 'raw_2024.json'), 'r', encoding='utf-8') as f:
    raw = json.load(f)

with open(classified_path, 'r', encoding='utf-8') as f:
    classified = json.load(f)

print(f"raw_2024.json: {len(raw)} records")

# 先恢复贵州的数据（去掉之前错误添加的local_province_name=贵州的数据）
# 贵州的原始数据是1366 pairs，现在有2992 pairs
# 需要去掉那些key中包含"2024|物理"但score在280-688范围的（这是raw_2024.json的数据）
# 更简单的方法：贵州的原始数据是2024+2025年的，raw_2024.json也是2024年的
# 所以只需要去掉重复添加的

# 实际上，之前的脚本用local_province_name=贵州提取了所有2133条
# 这些数据的key是"学校|2024|物理类"，可能和已有的贵州2024数据重复
# 让我先恢复贵州到原始状态

# 恢复贵州：只保留原始key（不含raw_2024.json中添加的）
# 原始贵州数据有1366 pairs，年份包括2024和2025
# raw_2024.json添加的是2024|物理类的数据

# 看看贵州现有的key
guizhou_pairs = classified.get('贵州', {}).get('pairs', {})
print(f"贵州当前: {len(guizhou_pairs)} pairs")

# 统计哪些是2024年的
pairs_2024 = {k:v for k,v in guizhou_pairs.items() if '2024' in k}
pairs_2025 = {k:v for k,v in guizhou_pairs.items() if '2025' in k}
pairs_other = {k:v for k,v in guizhou_pairs.items() if '2024' not in k and '2025' not in k}
print(f"  2024: {len(pairs_2024)}")
print(f"  2025: {len(pairs_2025)}")
print(f"  other: {len(pairs_other)}")

# 原始贵州数据应该是1366 pairs（2024+2025）
# 现在2992 = 1366 + 1626（来自raw_2024.json的贵州数据）
# 需要去掉那1626条

# 看看raw_2024.json中贵州的数据
raw_guizhou = [item for item in raw if item.get('province_name') == '贵州']
print(f"\nraw_2024.json中贵州数据: {len(raw_guizhou)}")

# 这些数据的school名称
raw_schools = set(item['name'] for item in raw_guizhou)
print(f"  学校数: {len(raw_schools)}")

# 从贵州的pairs中去掉这些学校2024年的数据
# 但要注意：有些学校可能确实在贵州招生，不能误删
# 策略：只去掉那些score在raw_2024.json中出现的（分数完全匹配的）
raw_score_school = set()
for item in raw_guizhou:
    score = item.get('min', None)
    school = item.get('name', '')
    if score and score != '-':
        raw_score_school.add((school, int(score)))

print(f"  (学校,分数)对: {len(raw_score_school)}")

# 从贵州pairs中移除匹配的
removed = 0
to_remove = []
for k, v in guizhou_pairs.items():
    if '2024' in k and '物理' in k:
        school = k.split('|')[0]
        score = v.get('score', None)
        if score and (school, score) in raw_score_school:
            to_remove.append(k)
            removed += 1

print(f"  需要移除: {removed}")

for k in to_remove:
    del guizhou_pairs[k]

classified['贵州']['pairs'] = guizhou_pairs
print(f"  贵州恢复后: {len(guizhou_pairs)} pairs")

# 现在用正确的方式从raw_2024.json提取31省数据
# 按province_name分组
raw_by_prov = defaultdict(lambda: defaultdict(list))
for item in raw:
    prov = item.get('province_name', '?')
    cat = item.get('local_type_name', item.get('type_name', '?'))
    school = item.get('name', '?')
    score = item.get('min', None)
    rank = item.get('min_section', None)
    year = str(item.get('year', '?'))
    
    try:
        score = int(score) if score and score != '-' else None
    except:
        score = None
    try:
        rank = int(rank) if rank and rank != '-' else None
    except:
        rank = None
    
    raw_by_prov[prov][cat].append({
        'school': school,
        'score': score,
        'rank': rank,
        'year': year,
    })

print(f"\n=== 从raw_2024.json补充31省数据 ===")
new_pairs_total = 0
updated_provinces = []

for prov, cats in sorted(raw_by_prov.items()):
    if prov not in classified:
        classified[prov] = {"type": "unknown", "pairs": {}}
    
    pairs = classified[prov].get("pairs", {})
    old_count = len(pairs)
    new_count = 0
    updated_count = 0
    
    for cat, items in cats.items():
        for item in items:
            school = item['school']
            year = item['year']
            key = f"{school}|{year}|{cat}"
            
            if key not in pairs:
                pairs[key] = {
                    "score": item['score'],
                    "rank": item['rank'],
                }
                new_count += 1
            else:
                # 已有数据，补充缺失字段
                existing = pairs[key]
                if item['rank'] and not existing.get('rank'):
                    existing['rank'] = item['rank']
                    updated_count += 1
                if item['score'] and not existing.get('score'):
                    existing['score'] = item['score']
                    updated_count += 1
    
    classified[prov]["pairs"] = pairs
    total_new = new_count + updated_count
    new_pairs_total += total_new
    if total_new > 0:
        updated_provinces.append(f"{prov}: +{new_count}新, +{updated_count}更新, 总{len(pairs)}")

for v in updated_provinces:
    print(f"  {v}")

# 保存
with open(classified_path, 'w', encoding='utf-8') as f:
    json.dump(classified, f, ensure_ascii=False)

print(f"\n✅ province_classified.json 已更新")
print(f"   新增数据对: {new_pairs_total}")

# 最终统计
total_pairs = 0
print(f"\n=== 最终数据覆盖 ===")
for prov, pdata in sorted(classified.items()):
    pairs = pdata.get('pairs', {})
    pair_count = len(pairs)
    total_pairs += pair_count
    ptype = pdata.get('type', '?')
    years = set()
    for k in pairs:
        parts = k.split('|')
        if len(parts) >= 2:
            years.add(parts[1])
    years_str = ','.join(sorted(years))
    print(f"  {prov}({ptype}): {pair_count} pairs [{years_str}]")

print(f"\n总计: {len(classified)}省, {total_pairs} pairs")
