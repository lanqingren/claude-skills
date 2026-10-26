#!/usr/bin/env python3
"""
三年回测：用有3年数据的5省（上海/北京/山东/河北/浙江）做2023→2024→2025三年回测
同时做两年回测（2023→2024和2024→2025）
"""
import json, os, sys
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
RESULT_DIR = os.path.join(DATA_DIR, "backtest_results")

os.makedirs(RESULT_DIR, exist_ok=True)

with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
    classified = json.load(f)

# 有3年数据的省份
three_year_provinces = ['上海', '北京', '山东', '河北', '浙江']

# 构建配对数据
# 格式: {province: {cat: {school: {year: score}}}}
def build_pairs(provinces):
    pairs = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    
    for prov in provinces:
        if prov not in classified:
            continue
        pdata = classified[prov]
        pairs_data = pdata.get('pairs', {})
        
        for key, val in pairs_data.items():
            parts = key.split('|')
            if len(parts) >= 3:
                school = parts[0]
                year = parts[1]
                cat = parts[2]
                # val 是 {'score': xxx, 'rank': xxx} 这样的dict
                score = val.get('score') if isinstance(val, dict) else val
                if score is not None:
                    pairs[prov][cat][school][year] = score
    
    return pairs

def backtest_year_pairs(pairs, year_from, year_to):
    """做单年对回测，使用IQR自适应阈值"""
    results = {
        '冲': {'hit': 0, 'total': 0},
        '稳': {'hit': 0, 'total': 0},
        '保': {'hit': 0, 'total': 0},
    }
    details = []
    skipped = 0
    
    for prov, cats in pairs.items():
        for cat, schools in cats.items():
            # 收集所有学校的偏移量
            offsets = []
            school_data = {}
            
            for school, years in schools.items():
                if year_from in years and year_to in years:
                    score_from = years[year_from]
                    score_to = years[year_to]
                    try:
                        score_from = int(score_from)
                        score_to = int(score_to)
                    except:
                        continue
                    if score_from <= 0 or score_to <= 0:
                        continue
                    offset = score_to - score_from
                    offsets.append(offset)
                    school_data[school] = {
                        'score_from': score_from,
                        'score_to': score_to,
                        'offset': offset,
                    }
            
            if len(school_data) < 4:
                skipped += len(school_data)
                continue
            
            # 计算IQR阈值
            sorted_offsets = sorted(offsets)
            n = len(sorted_offsets)
            q1 = sorted_offsets[n // 4]
            q3 = sorted_offsets[3 * n // 4]
            iqr = q3 - q1
            median_offset = sorted_offsets[n // 2]
            
            for school, data in school_data.items():
                predicted = data['score_from'] + median_offset
                actual = data['score_to']
                diff = actual - predicted  # 正数=实际分比预测高（预测偏保守）
                
                # 分类：
                # 冲：diff < Q1（实际分比预测低很多→分数下降→冲更安全）
                # 稳：Q1 <= diff <= Q3
                # 保：diff > Q3（实际分比预测高很多→分数上升→保更安全）
                
                if diff < q1:
                    category = '冲'
                elif diff > q3:
                    category = '保'
                else:
                    category = '稳'
                
                # 命中判断：
                # 冲：预测分 >= 实际分（predicted >= actual → diff <= 0）
                # 稳：|diff| <= IQR
                # 保：预测分 < 实际分（predicted < actual → diff > 0）
                
                # 重新理解：
                # 冲：冲的学校→预测分接近或高于实际分→diff <= 0 命中
                # 稳：稳的学校→预测分接近实际分→|diff| <= IQR 命中
                # 保：保的学校→预测分低于实际分→diff > 0 命中
                
                hit = False
                if category == '冲':
                    hit = predicted >= actual  # 预测能考上
                elif category == '稳':
                    hit = abs(predicted - actual) <= max(iqr, 5)  # 允许5分误差
                elif category == '保':
                    hit = predicted <= actual  # 保底安全
                
                results[category]['total'] += 1
                if hit:
                    results[category]['hit'] += 1
                
                details.append({
                    'prov': prov,
                    'cat': cat,
                    'school': school,
                    'year_from': year_from,
                    'year_to': year_to,
                    'score_from': data['score_from'],
                    'score_to': data['score_to'],
                    'predicted': predicted,
                    'diff': diff,
                    'category': category,
                    'hit': hit,
                })
    
    return results, details, skipped

# 构建所有配对
all_pairs = build_pairs(three_year_provinces)

print("=== 三年回测（5省：上海/北京/山东/河北/浙江） ===\n")

# 统计配对数
print("配对数统计:")
for prov, cats in all_pairs.items():
    for cat, schools in cats.items():
        pair_23_24 = sum(1 for s, y in schools.items() if '2023' in y and '2024' in y)
        pair_24_25 = sum(1 for s, y in schools.items() if '2024' in y and '2025' in y)
        pair_23_25 = sum(1 for s, y in schools.items() if '2023' in y and '2025' in y)
        if pair_23_24 > 0 or pair_24_25 > 0 or pair_23_25 > 0:
            print(f"  {prov} {cat}: 23→24={pair_23_24}, 24→25={pair_24_25}, 23→25={pair_23_25}")

# 做回测
print("\n--- 2023→2024 回测 ---")
results_23_24, details_23_24, skip_23_24 = backtest_year_pairs(all_pairs, '2023', '2024')
total_23_24 = sum(r['total'] for r in results_23_24.values())
hit_23_24 = sum(r['hit'] for r in results_23_24.values())
print(f"  总配对: {total_23_24} (跳过{skip_23_24}对<4校)")
for cat in ['冲', '稳', '保']:
    r = results_23_24[cat]
    rate = r['hit'] / r['total'] * 100 if r['total'] > 0 else 0
    print(f"  {cat}: {r['hit']}/{r['total']} = {rate:.1f}%")
overall_23_24 = hit_23_24 / total_23_24 * 100 if total_23_24 > 0 else 0
print(f"  总体: {hit_23_24}/{total_23_24} = {overall_23_24:.1f}%")

print("\n--- 2024→2025 回测 ---")
results_24_25, details_24_25, skip_24_25 = backtest_year_pairs(all_pairs, '2024', '2025')
total_24_25 = sum(r['total'] for r in results_24_25.values())
hit_24_25 = sum(r['hit'] for r in results_24_25.values())
print(f"  总配对: {total_24_25} (跳过{skip_24_25}对<4校)")
for cat in ['冲', '稳', '保']:
    r = results_24_25[cat]
    rate = r['hit'] / r['total'] * 100 if r['total'] > 0 else 0
    print(f"  {cat}: {r['hit']}/{r['total']} = {rate:.1f}%")
overall_24_25 = hit_24_25 / total_24_25 * 100 if total_24_25 > 0 else 0
print(f"  总体: {hit_24_25}/{total_24_25} = {overall_24_25:.1f}%")

print("\n--- 2023→2025 回测（两年跨度） ---")
results_23_25, details_23_25, skip_23_25 = backtest_year_pairs(all_pairs, '2023', '2025')
total_23_25 = sum(r['total'] for r in results_23_25.values())
hit_23_25 = sum(r['hit'] for r in results_23_25.values())
print(f"  总配对: {total_23_25} (跳过{skip_23_25}对<4校)")
for cat in ['冲', '稳', '保']:
    r = results_23_25[cat]
    rate = r['hit'] / r['total'] * 100 if r['total'] > 0 else 0
    print(f"  {cat}: {r['hit']}/{r['total']} = {rate:.1f}%")
overall_23_25 = hit_23_25 / total_23_25 * 100 if total_23_25 > 0 else 0
print(f"  总体: {hit_23_25}/{total_23_25} = {overall_23_25:.1f}%")

# 保存结果
backtest_3year = {
    'provinces': three_year_provinces,
    'total_records': sum(len(classified[p]['pairs']) for p in three_year_provinces if p in classified),
    'tests': {
        '2023_2024': {
            'results': {k: v for k, v in results_23_24.items()},
            'total_pairs': total_23_24,
            'skipped': skip_23_24,
        },
        '2024_2025': {
            'results': {k: v for k, v in results_24_25.items()},
            'total_pairs': total_24_25,
            'skipped': skip_24_25,
        },
        '2023_2025': {
            'results': {k: v for k, v in results_23_25.items()},
            'total_pairs': total_23_25,
            'skipped': skip_23_25,
        },
    }
}

with open(os.path.join(RESULT_DIR, "backtest_3year.json"), 'w', encoding='utf-8') as f:
    json.dump(backtest_3year, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/backtest_3year.json")
