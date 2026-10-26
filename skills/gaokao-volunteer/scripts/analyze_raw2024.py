#!/usr/bin/env python3
"""
从raw_2024.json中按省份和科类提取详细数据
raw_2024.json有2133条记录，每条包含省份、科类、学校、专业、分数、位次
目标是补充数据量不足的省份
"""
import json, os
from collections import Counter, defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"

# 加载raw_2024.json
with open(os.path.join(DATA_DIR, 'raw_2024.json'), 'r', encoding='utf-8') as f:
    raw = json.load(f)

print(f"raw_2024.json: {len(raw)} records")
print(f"Type: {type(raw).__name__}")

# 分析结构
if isinstance(raw, list) and len(raw) > 0:
    print(f"Sample[0] keys: {list(raw[0].keys())}")
    print(f"Sample[0]: {json.dumps(raw[0], ensure_ascii=False)[:300]}")
    
    # 统计各字段
    prov_cnt = Counter()
    cat_cnt = Counter()
    for item in raw:
        # 尝试不同的字段名
        prov = item.get('province', item.get('省份', item.get('prov', '?')))
        cat = item.get('category', item.get('科类', item.get('type', '?')))
        prov_cnt[prov] += 1
        cat_cnt[cat] += 1
    
    print(f"\n=== 按省份 ===")
    for prov, cnt in sorted(prov_cnt.items(), key=lambda x: -x[1]):
        print(f"  {prov}: {cnt}")
    
    print(f"\n=== 按科类 ===")
    for cat, cnt in sorted(cat_cnt.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")
elif isinstance(raw, dict):
    print(f"Keys: {list(raw.keys())[:10]}")
    for k in list(raw.keys())[:3]:
        v = raw[k]
        print(f"  {k}: type={type(v).__name__}, preview={json.dumps(v, ensure_ascii=False)[:200]}")
