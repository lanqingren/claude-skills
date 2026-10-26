#!/usr/bin/env python3
"""
全国大规模回测引擎 v7 (修正版)
核心逻辑：
  shift = rank_N+1 - rank_N （正=学校变容易，负=学校变难考）
  
  假设考生用Year N数据选校，考生位次=P
  - 冲(500~5000): 学校YearN位次比考生高500~5000名 → S_N = P - offset
    录取条件: S_N+1 >= P → S_N + shift >= P → shift >= offset(500~5000)
    取中值offset=2500: 命中率 = P(shift >= 2500)
  - 稳(0~10000): 学校YearN位次比考生低0~10000名 → S_N = P + offset  
    录取条件: shift >= -offset → 取中值offset=5000: P(shift >= -5000)
  - 保(10000~25000): P(shift >= -17500)
  - 垫(25000+): P(shift >= -30000)
"""

import json
import os
import re
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
SCORES_DIR = os.path.join(DATA_DIR, "province_scores")
OUTPUT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def normalize_category(source, province):
    """从source中提取科类"""
    if "物理" in source:
        return "物理"
    if "历史" in source:
        return "历史"
    if "理科" in source:
        return "理科"
    if "文科" in source:
        return "文科"
    # 综合改革省份
    reform_provinces = {"北京", "山东", "浙江", "上海", "海南", "天津"}
    if province in reform_provinces:
        return "综合"
    return "综合"


def is_undergrad(source):
    """排除专科"""
    return "专科" not in source and "高职" not in source


def normalize_school(name):
    """标准化学校名"""
    if not name:
        return ""
    name = re.sub(r'[\(（\[【].*?[\)）\]】]', '', name)
    for s in ['(公办)', '(民办)', '[公办]', '[民办]']:
        name = name.replace(s, '')
    return name.strip()


def load_province_data(prov):
    """加载省份数据，按year+category组织"""
    fname = os.path.join(SCORES_DIR, f"{prov}_scores.json")
    if not os.path.exists(fname):
        return None
    
    with open(fname, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    organized = defaultdict(lambda: defaultdict(list))
    
    for item in data:
        source = item.get('source', '')
        if not is_undergrad(source):
            continue
        year = item.get('year', 0)
        if year not in (2023, 2024):
            continue
        
        rank = item.get('rank')
        if not rank or int(rank) <= 0:
            continue
        rank = int(rank)
        
        cat = normalize_category(source, prov)
        school = normalize_school(item.get('school', ''))
        if len(school) < 4:
            continue
        
        organized[year][cat].append({
            'school': school,
            'rank': rank,
            'source': source,
        })
    
    return organized


def match_and_backtest(data_n, data_n1, group_name):
    """匹配两年数据并回测"""
    # 去重：同一学校取最低rank（最难考的专业）
    def dedup(records):
        seen = {}
        for r in records:
            name = r['school']
            if name not in seen or r['rank'] < seen[name]['rank']:
                seen[name] = r
        return seen
    
    dict_n = dedup(data_n)
    dict_n1 = dedup(data_n1)
    
    # 匹配同名学校
    matched = []
    for school in set(dict_n.keys()) & set(dict_n1.keys()):
        r_n = dict_n[school]['rank']
        r_n1 = dict_n1[school]['rank']
        if r_n > 0 and r_n1 > 0:
            matched.append({
                'school': school,
                'rank_n': r_n,
                'rank_n1': r_n1,
                'shift': r_n1 - r_n,
            })
    
    if len(matched) < 10:
        return None, matched
    
    shifts = [m['shift'] for m in matched]
    total = len(shifts)
    
    # 基本统计
    shifts_sorted = sorted(shifts)
    median_shift = shifts_sorted[total // 2]
    forward = sum(1 for s in shifts if s < 0)  # 变难
    backward = sum(1 for s in shifts if s > 0)  # 变容易
    
    # 命中率计算（核心逻辑）
    # 冲(offset=2500): P(shift >= 2500)
    rush_rate = sum(1 for s in shifts if s >= 2500) / total * 100
    # 稳上(offset=500): P(shift >= -500)
    steady_up_rate = sum(1 for s in shifts if s >= -500) / total * 100
    # 稳下(offset=5000): P(shift >= -5000)
    steady_lo_rate = sum(1 for s in shifts if s >= -5000) / total * 100
    # 保(offset=17500): P(shift >= -17500)
    safe_rate = sum(1 for s in shifts if s >= -17500) / total * 100
    # 垫(offset=30000): P(shift >= -30000)
    bottom_rate = sum(1 for s in shifts if s >= -30000) / total * 100
    
    # 各档位样本数
    rush_n = sum(1 for s in shifts if -5000 <= s < -500)
    steady_n = sum(1 for s in shifts if -500 <= s <= 10000)
    safe_n = sum(1 for s in shifts if 10000 < s <= 25000)
    bottom_n = sum(1 for s in shifts if s > 25000)
    
    result = {
        'group': group_name,
        'total': total,
        'median_shift': median_shift,
        'forward_pct': round(forward / total * 100, 1),
        'backward_pct': round(backward / total * 100, 1),
        'rush_hit': round(rush_rate, 1),
        'steady_up_hit': round(steady_up_rate, 1),
        'steady_lo_hit': round(steady_lo_rate, 1),
        'safe_hit': round(safe_rate, 1),
        'bottom_hit': round(bottom_rate, 1),
        'rush_sample': rush_n,
        'steady_sample': steady_n,
        'safe_sample': safe_n,
        'bottom_sample': bottom_n,
    }
    
    return result, matched


def main():
    # 找所有有数据的省份
    prov_files = [f for f in os.listdir(SCORES_DIR) if f.endswith('_scores.json') and not f.startswith('all_')]
    provinces = sorted(set(f.replace('_scores.json', '') for f in prov_files))
    print(f"有数据省份: {len(provinces)}个 - {provinces}\n")
    
    all_results = []
    all_shifts = []
    
    for prov in provinces:
        organized = load_province_data(prov)
        if not organized:
            continue
        
        years = sorted(organized.keys())
        if len(years) < 2:
            print(f"⚠️ {prov}: 仅{years}年")
            continue
        
        cats_23 = set(organized.get(2023, {}).keys())
        cats_24 = set(organized.get(2024, {}).keys())
        common = cats_23 & cats_24
        
        # 跨年映射（老高考→新高考）
        cross_map = [('理科', '物理'), ('文科', '历史')]
        
        for cat_old, cat_new in cross_map + [(c, c) for c in common]:
            data_n = organized.get(2023, {}).get(cat_old, [])
            data_n1 = organized.get(2024, {}).get(cat_new, [])
            
            if not data_n or not data_n1:
                continue
            
            label = f"{cat_old}→{cat_new}" if cat_old != cat_new else cat_new
            group = f"{prov} {label}"
            
            result, matched = match_and_backtest(data_n, data_n1, group)
            if result:
                all_results.append(result)
                all_shifts.extend([m['shift'] for m in matched])
                print(f"  ✅ {group}: {len(matched)}校, 中位偏移={result['median_shift']:+,}, 前移={result['forward_pct']}%")
    
    # ====== 全国汇总 ======
    print(f"\n{'='*90}")
    print(f"📊 全国大规模回测汇总 (v7)")
    print(f"{'='*90}")
    
    total_schools = sum(r['total'] for r in all_results)
    print(f"回测组数: {len(all_results)}组")
    print(f"总匹配院校: {total_schools:,}所")
    
    if not all_shifts:
        print("❌ 无数据")
        return
    
    N = len(all_shifts)
    shifts_sorted = sorted(all_shifts)
    nat_median = shifts_sorted[N // 2]
    nat_forward = sum(1 for s in all_shifts if s < 0) / N * 100
    
    # 全国P25/P75
    p25 = shifts_sorted[N // 4]
    p75 = shifts_sorted[3 * N // 4]
    
    print(f"\n全国位次偏移统计 ({N:,}校):")
    print(f"  中位偏移: {nat_median:+,}名")
    print(f"  P25~P75: {p25:+,} ~ {p75:+,}名")
    print(f"  位次前移(变难): {nat_forward:.1f}%")
    print(f"  位次后移(变容易): {100-nat_forward:.1f}%")
    
    # 全国命中率
    print(f"\n全国冲稳保参数命中率:")
    
    metrics = [
        ('🏃 冲', 'rush_hit', 2500, '学校高于考生500~5000名'),
        ('⚖️ 稳上', 'steady_up_hit', -500, '学校≈考生位次(-500~+500)'),
        ('⚖️ 稳下', 'steady_lo_hit', -5000, '学校低于考生0~10000名'),
        ('🛡️ 保', 'safe_hit', -17500, '学校低于考生10000~25000名'),
        ('🔒 垫', 'bottom_hit', -30000, '学校低于考生25000名以上'),
    ]
    
    for label, key, threshold, desc in metrics:
        count = sum(1 for s in all_shifts if s >= threshold)
        rate = count / N * 100
        print(f"  {label} ({desc})")
        print(f"    命中率: {rate:.1f}% ({count:,}/{N:,})")
    
    # 分省详情表
    print(f"\n{'='*90}")
    print(f"📋 分省回测详情")
    print(f"{'='*90}")
    header = f"{'组名':<28} {'匹配':>5} {'中位偏移':>10} {'前移%':>6} {'冲%':>6} {'稳上%':>6} {'稳下%':>6} {'保%':>6} {'垫%':>6}"
    print(header)
    print("-" * 90)
    for r in sorted(all_results, key=lambda x: -x['total']):
        print(f"{r['group']:<28} {r['total']:>5} {r['median_shift']:>+10,} {r['forward_pct']:>5.1f}% {r['rush_hit']:>5.1f}% {r['steady_up_hit']:>5.1f}% {r['steady_lo_hit']:>5.1f}% {r['safe_hit']:>5.1f}% {r['bottom_hit']:>5.1f}%")
    
    # 保存
    output = {
        'version': 'v7',
        'total_groups': len(all_results),
        'total_schools': total_schools,
        'national': {
            'total_shifts': N,
            'median_shift': nat_median,
            'p25': p25,
            'p75': p75,
            'forward_pct': round(nat_forward, 1),
            'rush_rate': round(sum(1 for s in all_shifts if s >= 2500) / N * 100, 1),
            'steady_up_rate': round(sum(1 for s in all_shifts if s >= -500) / N * 100, 1),
            'steady_lo_rate': round(sum(1 for s in all_shifts if s >= -5000) / N * 100, 1),
            'safe_rate': round(sum(1 for s in all_shifts if s >= -17500) / N * 100, 1),
            'bottom_rate': round(sum(1 for s in all_shifts if s >= -30000) / N * 100, 1),
        },
        'groups': all_results,
    }
    
    out_path = os.path.join(OUTPUT_DIR, "backtest_v7_national.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存: {out_path}")


if __name__ == '__main__':
    main()
