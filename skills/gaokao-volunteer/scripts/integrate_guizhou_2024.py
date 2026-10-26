#!/usr/bin/env python3
"""整合贵州2024数据到province_classified.json，创建2024→2025回测配对。

数据源：
- 贵州_2024_物理类_admission.json: 271条，含min_score_2024/min_rank_2024和min_score_2023/min_rank_2023
- province_v9/贵州_v9.json: 18325条2025专业级数据（已聚合为1095条学校级）

输出：更新province_classified.json中贵州的pairs，增加2024和2023年份
"""
import json
import os
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
GUIZHOU_2024_PATH = os.path.join(DATA_DIR, "贵州_2024_物理类_admission.json")

# Load current classified data
with open(CLASSIFIED_PATH, encoding="utf-8") as f:
    classified = json.load(f)

# Load 贵州 2024 data
with open(GUIZHOU_2024_PATH, encoding="utf-8") as f:
    gz2024_raw = json.load(f)

print(f"贵州2024原始数据: {len(gz2024_raw)} 条")
print(f"样本字段: {list(gz2024_raw[0].keys())}")

# Aggregate to school level (take minimum score per school per year)
# 2024 data
school_2024 = {}  # school -> (score, rank)
school_2023 = {}
for rec in gz2024_raw:
    school = rec.get("school", "").strip()
    if not school:
        continue

    # 2024 data
    s24 = rec.get("min_score_2024")
    r24 = rec.get("min_rank_2024")
    if s24 and isinstance(s24, (int, float)):
        if school not in school_2024 or s24 < school_2024[school][0]:
            school_2024[school] = (int(s24), int(r24) if r24 else None)

    # 2023 data
    s23 = rec.get("min_score_2023")
    r23 = rec.get("min_rank_2023")
    if s23 and isinstance(s23, (int, float)):
        if school not in school_2023 or s23 < school_2023[school][0]:
            school_2023[school] = (int(s23), int(r23) if r23 else None)

print(f"\n聚合后:")
print(f"  2024年学校数: {len(school_2024)}")
print(f"  2023年学校数: {len(school_2023)}")

# Get current 贵州 data in classified
gz_info = classified.get("贵州", {})
gz_pairs = gz_info.get("pairs", {})
print(f"  2025年(已有): {len(gz_pairs)} 学校")

# Count how many schools match across years
schools_2025 = set(k.split("|")[0] for k in gz_pairs)
match_2024_2025 = schools_2025 & set(school_2024.keys())
match_2023_2024 = set(school_2024.keys()) & set(school_2023.keys())
match_2023_2024_2025 = schools_2025 & set(school_2024.keys()) & set(school_2023.keys())
print(f"\n跨年匹配:")
print(f"  2024∩2025: {len(match_2024_2025)} 学校")
print(f"  2023∩2024: {len(match_2023_2024)} 学校")
print(f"  三年都有: {len(match_2023_2024_2025)} 学校")

# Add 2024 and 2023 data to 贵州 pairs
added = 0
for school, (score, rank) in school_2024.items():
    key = f"{school}|2024|物理"
    if key not in gz_pairs:
        gz_pairs[key] = {"score": score, "rank": rank}
        added += 1
    else:
        # Update if current is missing or higher
        existing = gz_pairs[key]
        if existing.get("score", 999) > score:
            gz_pairs[key] = {"score": score, "rank": rank}
            added += 1

for school, (score, rank) in school_2023.items():
    key = f"{school}|2023|物理"
    if key not in gz_pairs:
        gz_pairs[key] = {"score": score, "rank": rank}
        added += 1

print(f"\n新增/更新: {added} 条")
print(f"贵州总pairs: {len(gz_pairs)}")

# Update classified
classified["贵州"]["pairs"] = gz_pairs

# Save
with open(CLASSIFIED_PATH, "w", encoding="utf-8") as f:
    json.dump(classified, f, ensure_ascii=False)
print(f"\n✅ 已保存到 {CLASSIFIED_PATH}")

# Also verify the year distribution now
from collections import Counter
years = Counter()
for key in gz_pairs:
    parts = key.split("|")
    if len(parts) >= 2:
        years[parts[1]] += 1
print(f"贵州年份分布: {dict(sorted(years.items()))}")
