#!/usr/bin/env python3
"""
分科类三年回测：按科类分别做回测，更准确
同时做全国21省v24回测的科类细分
"""
import json, os, sys
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
RESULT_DIR = os.path.join(DATA_DIR, "backtest_results")

os.makedirs(RESULT_DIR, exist_ok=True)

with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
    classified = json.load(f)

def backtest_all_provinces():
    """对所有有2年以上数据的省份做分科类回测"""
    
    # 收集所有省份的配对
    all_pairs = {}  # {prov: {cat: {school: {year: score}}}}
    
    for prov, pdata in classified.items():
        pairs_data = pdata.get('pairs', {})
        prov_pairs = defaultdict(lambda: defaultdict(dict))
        
        for key, val in pairs_data.items():
            parts = key.split('|')
            if len(parts) >= 3:
                school = parts[0]
                year = parts[1]
                cat = parts[2]
                score = val.get('score') if isinstance(val, dict) else val
                if score is not None:
                    try:
                        score = int(score)
                        if score > 0:
                            prov_pairs[cat][school][year] = score
                    except:
                        continue
        
        if prov_pairs:
            all_pairs[prov] = dict(prov_pairs)
    
    # 对每个省份的每个科类做回测
    results_by_prov = {}
    total_tests = 0
    
    for prov, cats in all_pairs.items():
        prov_results = {}
        
        for cat, schools in cats.items():
            # 找出有2年数据的学校
            valid_schools = {}
            for school, years in schools.items():
                if len(years) >= 2:
                    valid_schools[school] = years
            
            if len(valid_schools) < 4:
                continue
            
            # 对每对年份做回测
            years_list = sorted(set(y for s in valid_schools.values() for y in s.keys()))
            
            for i in range(len(years_list)):
                for j in range(i+1, len(years_list)):
                    y_from = years_list[i]
                    y_to = years_list[j]
                    
                    # 收集偏移量
                    offsets = []
                    school_data = {}
                    
                    for school, years in valid_schools.items():
                        if y_from in years and y_to in years:
                            sf = years[y_from]
                            st = years[y_to]
                            offset = st - sf
                            offsets.append(offset)
                            school_data[school] = {'from': sf, 'to': st, 'offset': offset}
                    
                    if len(school_data) < 4:
                        continue
                    
                    # IQR
                    sorted_offsets = sorted(offsets)
                    n = len(sorted_offsets)
                    q1 = sorted_offsets[n // 4]
                    q3 = sorted_offsets[3 * n // 4]
                    iqr = q3 - q1
                    median_offset = sorted_offsets[n // 2]
                    
                    # 回测
                    cat_results = {'冲': {'hit': 0, 'total': 0}, '稳': {'hit': 0, 'total': 0}, '保': {'hit': 0, 'total': 0}}
                    
                    for school, data in school_data.items():
                        predicted = data['from'] + median_offset
                        actual = data['to']
                        diff = actual - predicted
                        
                        if diff < q1:
                            category = '冲'
                        elif diff > q3:
                            category = '保'
                        else:
                            category = '稳'
                        
                        hit = False
                        if category == '冲':
                            hit = predicted >= actual
                        elif category == '稳':
                            hit = abs(predicted - actual) <= max(iqr, 5)
                        elif category == '保':
                            hit = predicted <= actual
                        
                        cat_results[category]['total'] += 1
                        if hit:
                            cat_results[category]['hit'] += 1
                    
                    pair_key = f"{y_from}_{y_to}"
                    if pair_key not in prov_results:
                        prov_results[pair_key] = {
                            'pairs': len(school_data),
                            'cats': {},
                        }
                    
                    prov_results[pair_key]['cats'][cat] = cat_results
                    total_tests += 1
        
        if prov_results:
            results_by_prov[prov] = prov_results
    
    return results_by_prov, total_tests

print("=== 全国分科类回测 ===\n")
results, total = backtest_all_provinces()
print(f"总测试数: {total}")

# 汇总
print(f"\n{'省份':<8} {'年份对':<12} {'科类':<10} {'配对':>6} {'冲':>12} {'稳':>12} {'保':>12}")
print("-" * 80)

national = {'冲': {'hit': 0, 'total': 0}, '稳': {'hit': 0, 'total': 0}, '保': {'hit': 0, 'total': 0}}

for prov in sorted(results.keys()):
    for year_pair in sorted(results[prov].keys()):
        pair_info = results[prov][year_pair]
        for cat in sorted(pair_info['cats'].keys()):
            cat_r = pair_info['cats'][cat]
            ch = cat_r['冲']['hit']
            ct = cat_r['冲']['total']
            wh = cat_r['稳']['hit']
            wt = cat_r['稳']['total']
            bh = cat_r['保']['hit']
            bt = cat_r['保']['total']
            
            cr = f"{ch}/{ct}={ch/ct*100:.1f}%" if ct > 0 else "N/A"
            wr = f"{wh}/{wt}={wh/wt*100:.1f}%" if wt > 0 else "N/A"
            br = f"{bh}/{bt}={bh/bt*100:.1f}%" if bt > 0 else "N/A"
            
            print(f"{prov:<8} {year_pair:<12} {cat:<10} {pair_info['pairs']:>6} {cr:>12} {wr:>12} {br:>12}")
            
            for c in ['冲', '稳', '保']:
                national[c]['hit'] += cat_r[c]['hit']
                national[c]['total'] += cat_r[c]['total']

print("\n" + "=" * 80)
print(f"{'全国汇总':<8} {'':12} {'':10} {'':>6}", end="")
for c in ['冲', '稳', '保']:
    h = national[c]['hit']
    t = national[c]['total']
    r = h/t*100 if t > 0 else 0
    print(f" {h}/{t}={r:.1f}%".rjust(12), end="")
print()

# 保存
with open(os.path.join(RESULT_DIR, "backtest_by_cat.json"), 'w', encoding='utf-8') as f:
    json.dump({
        'by_province': results,
        'national': national,
    }, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/backtest_by_cat.json")
