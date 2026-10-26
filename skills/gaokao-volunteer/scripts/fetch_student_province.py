#!/usr/bin/env python3
"""
多省份考生投档数据下载器（正确版）
====================================
关键修正：province_id 是「学校所在省」，不是「考生所在省」。
要获取某省考生的投档数据，需要查询多个province_id并按local_province_name筛选。

策略：遍历主要省份ID，聚合后按考生省份分组。
"""

import requests
import json
import time
import os
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data\multi_province")
DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.trust_env = False  # 关闭系统代理

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.gaokao.cn/',
}

# 所有省级行政区ID
ALL_PROVINCE_IDS = list(range(11, 16)) + list(range(21, 24)) + list(range(31, 38)) + list(range(41, 47)) + list(range(50, 55)) + list(range(61, 66))


def fetch_page(province_id, year, page, size=20):
    params = {
        'access_token': '', 'signsafe': '',
        'uri': 'apidata/api/gk/score/province',
        'province_id': str(province_id),
        'year': str(year),
        'page': str(page),
        'size': str(size),
    }
    try:
        r = SESSION.get('https://api.eol.cn/gkcx/api/', params=params, headers=HEADERS, timeout=15)
        data = r.json()
        code = data.get('code')
        if code and code != '0000':
            return None, code
        items = data.get('data', {}).get('item', [])
        return items, '0000'
    except Exception as e:
        return None, str(e)


def fetch_province_all(province_id, year, max_pages=120):
    all_items = []
    for page in range(1, max_pages + 1):
        items, code = fetch_page(province_id, year, page)
        if code == '1069':
            return all_items, 'RATE_LIMITED'
        if code != '0000' or items is None:
            return all_items, code
        if not items:
            return all_items, 'DONE'
        all_items.extend(items)
        if len(items) < 20:
            break
        time.sleep(0.2)
    return all_items, 'DONE'


def main():
    year = 2024
    
    # 我们要的考生省份
    target_student_provinces = {'广东', '北京', '上海', '湖北', '四川', '贵州', '江苏', '浙江', '山东', '河南'}
    
    # 已下载的数据先合并
    existing_data = []
    for f in DATA_DIR.glob('*_2024_admission.json'):
        with open(f, 'r', encoding='utf-8') as fh:
            existing_data.extend(json.load(fh))
    print(f"已有2024数据: {len(existing_data)}条", flush=True)
    
    # 按考生省份筛选已有数据
    by_student = defaultdict(list)
    for d in existing_data:
        sp = d.get('local_province_name', '')
        if sp in target_student_provinces:
            by_student[sp].append(d)
    
    for prov in sorted(target_student_provinces):
        records = by_student.get(prov, [])
        print(f"  {prov}: {len(records)}条", flush=True)
    
    # 尝试下载更多省份（遍历所有province_id来收集更多考生省份的数据）
    already_queried = {44, 11, 31, 42, 51, 52, 32, 33, 37, 41}  # 已查询过的
    to_query = [pid for pid in ALL_PROVINCE_IDS if pid not in already_queried]
    
    print(f"\n📥 查询剩余 {len(to_query)} 个省份的2024年数据...", flush=True)
    
    for i, pid in enumerate(to_query):
        items, status = fetch_province_all(pid, year)
        
        if status == 'RATE_LIMITED':
            print(f"  [{i+1}/{len(to_query)}] province_id={pid}: 被限频! 已获取{len(items)}条", flush=True)
            existing_data.extend(items)
            # 保存当前进度
            break
        
        if items:
            existing_data.extend(items)
            # 筛选目标省份的新记录
            new_for_target = [d for d in items if d.get('local_province_name','') in target_student_provinces]
            if new_for_target:
                types = set(d.get('local_type_name','') for d in new_for_target)
                print(f"  [{i+1}/{len(to_query)}] pid={pid}: {len(items)}条 (目标省份新增{len(new_for_target)}条, 科类:{types})", flush=True)
        
        time.sleep(0.3)
    
    # 最终按考生省份分组保存
    print(f"\n📊 最终统计:", flush=True)
    by_student = defaultdict(list)
    for d in existing_data:
        sp = d.get('local_province_name', '')
        if sp in target_student_provinces:
            by_student[sp].append(d)
    
    for prov in sorted(by_student.keys()):
        records = by_student[prov]
        # 按科类分
        types = defaultdict(list)
        for r in records:
            types[r.get('local_type_name', '未知')].append(r)
        
        # 保存
        filepath = DATA_DIR / f"student_{prov}_{year}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False)
        
        type_str = ', '.join(f"{t}:{len(v)}" for t, v in sorted(types.items()))
        print(f"  {prov}: {len(records)}条 ({type_str}) → {filepath.name}", flush=True)
    
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
