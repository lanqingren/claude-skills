#!/usr/bin/env python3
"""
从raw_2024.json中提取各省详细数据
raw_2024.json有2133条记录，31省，包含学校、专业、分数、位次
之前只提取了学校维度的数据，现在提取更详细的专业维度数据
"""
import json, os
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

with open(os.path.join(DATA_DIR, 'raw_2024.json'), 'r', encoding='utf-8') as f:
    raw = json.load(f)

print(f"raw_2024.json: {len(raw)} records")

# 分析数据结构
# 字段: name(学校), sg_name(专业), local_type_name(科类), 
#       min(最低分), min_section(最低位次), 
#       max(最高分), max_section(最高位次),
#       average(平均分), proscore(省控线),
#       province_name(省份), year

# 按省份+科类+学校+专业聚合
by_prov = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for item in raw:
    prov = item.get('province_name', '?')
    cat = item.get('local_type_name', '?')
    school = item.get('name', '?')
    major = item.get('sg_name', '')
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
    
    by_prov[prov][cat][school].append({
        'major': major,
        'score': score,
        'rank': rank,
        'year': year,
    })

# 统计
print(f"\n=== raw_2024.json 按省份+科类 ===")
total_details = 0
for prov in sorted(by_prov.keys()):
    for cat, schools in sorted(by_prov[prov].items()):
        school_count = len(schools)
        detail_count = sum(len(v) for v in schools.values())
        total_details += detail_count
        scores = []
        for school_majors in schools.values():
            for m in school_majors:
                if m['score']:
                    scores.append(m['score'])
        
        score_range = f"{min(scores)}-{max(scores)}" if scores else "N/A"
        print(f"  {prov} {cat}: {school_count}校, {detail_count}专业, 分数{score_range}")

print(f"\n总计: {total_details} 条专业维度数据")

# 看看哪些省份有详细的专业数据（sg_name非空）
print(f"\n=== 有专业名称的记录 ===")
has_major = 0
no_major = 0
for item in raw:
    major = item.get('sg_name', '')
    if major:
        has_major += 1
    else:
        no_major += 1
print(f"  有专业名称: {has_major}")
print(f"  无专业名称: {no_major}")

# 看看哪些省份有位次数据
has_rank = sum(1 for item in raw if item.get('min_section') and item.get('min_section') != '-')
print(f"  有位次数据: {has_rank}")
print(f"  无位次数据: {len(raw) - has_rank}")
