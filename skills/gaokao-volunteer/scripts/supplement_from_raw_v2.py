#!/usr/bin/env python3
"""
从raw_2024.json提取数据并补充到province_classified.json
raw_2024.json: 2133条记录，31省物理类，1626所学校
"""
import json, os
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

# 加载数据
with open(os.path.join(DATA_DIR, 'raw_2024.json'), 'r', encoding='utf-8') as f:
    raw = json.load(f)

with open(os.path.join(DATA_DIR, 'province_classified.json'), 'r', encoding='utf-8') as f:
    classified = json.load(f)

print(f"raw_2024.json: {len(raw)} records")
print(f"province_classified.json: {len(classified)} provinces")

# 分析raw_2024.json的数据结构
# 字段: name(学校), local_province_name(省份), local_type_name(科类), 
#       min(最低分), min_section(最低位次), year, province_id

# 按省份+科类聚合
raw_by_prov = defaultdict(lambda: defaultdict(list))
for item in raw:
    prov = item.get('local_province_name', item.get('province_name', '?'))
    cat = item.get('local_type_name', item.get('type_name', '?'))
    school = item.get('name', '?')
    score = item.get('min', None)
    rank = item.get('min_section', None)
    year = item.get('year', '?')
    
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
        'year': str(year),
    })

print(f"\nraw_2024.json 按省份+科类:")
for prov in sorted(raw_by_prov.keys()):
    for cat, items in raw_by_prov[prov].items():
        scores = [i['score'] for i in items if i['score']]
        print(f"  {prov} {cat}: {len(items)}条, 分数范围{min(scores) if scores else 'N/A'}-{max(scores) if scores else 'N/A'}")

# 检查classified中哪些省份有这些数据
print(f"\n=== 当前classified中各省数据量 ===")
classified_stats = {}
for prov, pdata in sorted(classified.items()):
    pairs = pdata.get('pairs', {})
    pair_count = len(pairs)
    classified_stats[prov] = pair_count
    print(f"  {prov}: {pair_count} pairs")

# 策略: 从raw_2024.json中提取的数据作为补充
# 但注意raw_2024.json只有物理类数据，且是不同学校维度的
# classified中的数据是"学校|年份|科类"维度的

# 看看classified中的key格式
print(f"\n=== classified key样本 ===")
for prov in ['江苏', '北京', '贵州']:
    if prov in classified:
        pairs = classified[prov].get('pairs', {})
        for k in list(pairs.keys())[:3]:
            print(f"  {prov}: {k} -> {pairs[k]}")

# 从raw_2024.json构建新的pairs
print(f"\n=== 从raw_2024.json构建新数据 ===")
new_pairs_total = 0
for prov, cats in raw_by_prov.items():
    if prov not in classified:
        classified[prov] = {"type": "unknown", "pairs": {}}
    
    pairs = classified[prov].get("pairs", {})
    new_count = 0
    
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
                # 已有数据，保留分数更低的（最低分）
                existing_score = pairs[key].get('score', 99999)
                if item['score'] and (existing_score == 99999 or item['score'] < existing_score):
                    pairs[key]['score'] = item['score']
                    if item['rank']:
                        pairs[key]['rank'] = item['rank']
    
    classified[prov]["pairs"] = pairs
    new_pairs_total += new_count
    if new_count > 0:
        print(f"  {prov}: 新增 {new_count} 对")

# 保存
with open(os.path.join(DATA_DIR, 'province_classified.json'), 'w', encoding='utf-8') as f:
    json.dump(classified, f, ensure_ascii=False)

print(f"\n✅ province_classified.json 已更新，共新增 {new_pairs_total} 对")

# 重新统计
total_pairs = 0
for prov, pdata in sorted(classified.items()):
    pairs = pdata.get('pairs', {})
    pair_count = len(pairs)
    total_pairs += pair_count
    print(f"  {prov}: {pair_count} pairs")
print(f"\n总计: {total_pairs} pairs")
