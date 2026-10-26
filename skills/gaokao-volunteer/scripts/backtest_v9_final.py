#!/usr/bin/env python3
"""
全国回测引擎 v9-final
- 排除贵州API偏差数据
- 黑龙江综合→物理/历史跨年映射
- 输出干净版全国统计
"""

import json
import os
import re
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
V9_DIR = os.path.join(DATA_DIR, "province_v9")
API_DIR = os.path.join(DATA_DIR, "multi_province")
OUTPUT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def normalize_school(name):
    if not name:
        return ""
    name = re.sub(r'[\(（\[【].*?[\)）\]】]', '', name)
    name = re.sub(r'\d+专业组.*$', '', name)
    name = re.sub(r'第\d+组.*$', '', name)
    return name.strip()


def dedup(records, prefer='rank'):
    seen = {}
    for r in records:
        name = normalize_school(r.get('school', ''))
        if len(name) < 4:
            continue
        r = dict(r)
        r['school_n'] = name
        if name not in seen:
            seen[name] = r
        else:
            if prefer == 'rank' and r.get('rank') and seen[name].get('rank'):
                if r['rank'] < seen[name]['rank']:
                    seen[name] = r
            elif prefer == 'score' and r.get('score') and seen[name].get('score'):
                if r['score'] > seen[name]['score']:
                    seen[name] = r
    return seen


def match(d_n, d_n1, mode='rank'):
    if mode == 'rank':
        dn = dedup(d_n, 'rank')
        dn1 = dedup(d_n1, 'rank')
    else:
        dn = dedup(d_n, 'score')
        dn1 = dedup(d_n1, 'score')
    
    matched = []
    for school in set(dn.keys()) & set(dn1.keys()):
        if mode == 'rank':
            v1, v2 = dn[school].get('rank'), dn1[school].get('rank')
        else:
            v1, v2 = dn[school].get('score'), dn1[school].get('score')
            if v1 and v1 > 850: continue
            if v2 and v2 > 850: continue
        
        if v1 and v2 and v1 > 0 and v2 > 0:
            matched.append({'school': school, 'shift': v2 - v1})
    return matched


def backtest(matched, name, mode):
    if len(matched) < 20:
        return None
    shifts = sorted([m['shift'] for m in matched])
    n = len(shifts)
    r = {'group': name, 'mode': mode, 'total': n, 'median': shifts[n//2], 'p25': shifts[n//4], 'p75': shifts[3*n//4]}
    if mode == 'rank':
        r['forward_pct'] = round(sum(1 for s in shifts if s < 0) / n * 100, 1)
        r['rush'] = round(sum(1 for s in shifts if s >= 2500) / n * 100, 1)
        r['steady'] = round(sum(1 for s in shifts if s >= -500) / n * 100, 1)
        r['safe'] = round(sum(1 for s in shifts if s >= -17500) / n * 100, 1)
    else:
        r['up_pct'] = round(sum(1 for s in shifts if s > 0) / n * 100, 1)
        r['rush'] = round(sum(1 for s in shifts if s <= 10) / n * 100, 1)
        r['steady'] = round(sum(1 for s in shifts if s <= 15) / n * 100, 1)
        r['safe'] = round(sum(1 for s in shifts if s <= 40) / n * 100, 1)
    return r


def main():
    print("=" * 80)
    print("📊 全国回测引擎 v9-final（排除偏差数据）")
    print("=" * 80)
    
    all_results = []
    all_rank_shifts = []
    all_score_shifts = []
    
    # ===== API数据（北京、广东）=====
    for prov, files in [('北京', ['北京_2023_admission.json', '北京_2024_admission.json']),
                         ('广东', ['广东_2022_admission.json', '广东_2023_admission.json', '广东_2024_admission.json'])]:
        records = []
        for fname in files:
            fpath = os.path.join(API_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    for item in json.load(f):
                        ms = item.get('min_section', '-')
                        try:
                            rank = int(ms)
                            if rank > 0:
                                records.append({'school': item.get('name', ''), 'rank': rank,
                                               'year': int(item.get('year', 0)), 'category': item.get('local_type_name', '综合')})
                        except: pass
        
        by_yc = defaultdict(lambda: defaultdict(list))
        for r in records:
            by_yc[r['year']][r['category']].append(r)
        
        years = sorted(by_yc.keys())
        for yi in range(len(years) - 1):
            yn, yn1 = years[yi], years[yi+1]
            for cat in sorted(set(by_yc[yn]) & set(by_yc[yn1])):
                m = match(by_yc[yn][cat], by_yc[yn1][cat], 'rank')
                if len(m) >= 20:
                    res = backtest(m, f"{prov} {cat} {yn}→{yn1}", 'rank')
                    if res:
                        all_results.append(res)
                        all_rank_shifts.extend([x['shift'] for x in m])
    
    # ===== dxsbb v9 数据 =====
    for prov_file in sorted(os.listdir(V9_DIR)):
        if not prov_file.endswith('_v9.json'): continue
        prov = prov_file.replace('_v9.json', '')
        with open(os.path.join(V9_DIR, prov_file), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        by_yc = defaultdict(lambda: defaultdict(list))
        for r in data:
            by_yc[r['year']][r['category']].append(r)
        
        years = sorted(by_yc.keys())
        if len(years) < 2: continue
        
        c23 = set(by_yc.get(2023, {}).keys())
        c24 = set(by_yc.get(2024, {}).keys())
        
        # 匹配对
        pairs = [(c, c) for c in sorted(c23 & c24)]
        if '理科' in c23 and '物理' in c24: pairs.append(('理科', '物理'))
        if '文科' in c23 and '历史' in c24: pairs.append(('文科', '历史'))
        # 黑龙江特例: 综合→物理/历史
        if prov == '黑龙江' and '综合' in c23:
            pairs.append(('综合', '物理'))
            pairs.append(('综合', '历史'))
        
        for co, cn in pairs:
            d23 = by_yc.get(2023, {}).get(co, [])
            d24 = by_yc.get(2024, {}).get(cn, [])
            if not d23 or not d24: continue
            
            label = f"{co}→{cn}" if co != cn else cn
            # 甘肃理科→物理的跨批次比较不可靠，标记
            unreliable = prov == '甘肃' and co == '理科'
            
            # 优先位次
            mr = match(d23, d24, 'rank')
            if len(mr) >= 20:
                res = backtest(mr, f"{prov} {label} 2023→2024 [位次]", 'rank')
                if res:
                    if unreliable: res['note'] = '跨批次参考'
                    all_results.append(res)
                    if not unreliable:
                        all_rank_shifts.extend([x['shift'] for x in mr])
                continue
            
            ms = match(d23, d24, 'score')
            if len(ms) >= 20:
                res = backtest(ms, f"{prov} {label} 2023→2024 [分数]", 'score')
                if res:
                    if unreliable: res['note'] = '跨批次参考'
                    all_results.append(res)
                    if not unreliable:
                        all_score_shifts.extend([x['shift'] for x in ms])
    
    # ===== 全国汇总 =====
    print(f"\n回测组数: {len(all_results)}组")
    total = sum(r['total'] for r in all_results)
    print(f"总匹配院校: {total:,}所")
    
    rank_groups = [r for r in all_results if r['mode'] == 'rank']
    score_groups = [r for r in all_results if r['mode'] == 'score']
    
    if all_rank_shifts:
        N = len(all_rank_shifts)
        ss = sorted(all_rank_shifts)
        print(f"\n📈 位次回测 ({N:,}校, {len(rank_groups)}组):")
        print(f"  中位偏移: {ss[N//2]:+,}名")
        print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}名")
        print(f"  冲(≥2500): {sum(1 for s in all_rank_shifts if s>=2500)/N*100:.1f}%")
        print(f"  稳(≥-500): {sum(1 for s in all_rank_shifts if s>=-500)/N*100:.1f}%")
        print(f"  保(≥-17500): {sum(1 for s in all_rank_shifts if s>=-17500)/N*100:.1f}%")
    
    if all_score_shifts:
        N = len(all_score_shifts)
        ss = sorted(all_score_shifts)
        print(f"\n📈 分数回测 ({N:,}校, {len(score_groups)}组):")
        print(f"  中位偏移: {ss[N//2]:+,}分")
        print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}分")
        print(f"  冲(≤10分): {sum(1 for s in all_score_shifts if s<=10)/N*100:.1f}%")
        print(f"  稳(≤15分): {sum(1 for s in all_score_shifts if s<=15)/N*100:.1f}%")
        print(f"  保(≤40分): {sum(1 for s in all_score_shifts if s<=40)/N*100:.1f}%")
        print(f"  分数上涨: {sum(1 for s in all_score_shifts if s>0)/N*100:.1f}%")
    
    # 详情表
    print(f"\n{'='*100}")
    print(f"{'组名':<35} {'模式':>4} {'匹配':>5} {'中位':>8} {'P25':>8} {'P75':>8} {'冲%':>6} {'稳%':>6} {'保%':>6}")
    print("-" * 100)
    for r in sorted(all_results, key=lambda x: -x['total']):
        note = f" [{r.get('note','')}]" if r.get('note') else ''
        print(f"{r['group']:<35} {r['mode']:>4} {r['total']:>5} {r['median']:>+8,} {r['p25']:>+8,} {r['p75']:>+8,} {r['rush']:>5.1f}% {r['steady']:>5.1f}% {r['safe']:>5.1f}%{note}")
    
    # 保存
    output = {
        'version': 'v9-final',
        'total_groups': len(all_results),
        'total_schools': total,
        'national_rank': {
            'total': len(all_rank_shifts),
            'groups': len(rank_groups),
            'median': sorted(all_rank_shifts)[len(all_rank_shifts)//2] if all_rank_shifts else 0,
            'rush_rate': round(sum(1 for s in all_rank_shifts if s>=2500)/max(len(all_rank_shifts),1)*100, 1),
            'steady_rate': round(sum(1 for s in all_rank_shifts if s>=-500)/max(len(all_rank_shifts),1)*100, 1),
            'safe_rate': round(sum(1 for s in all_rank_shifts if s>=-17500)/max(len(all_rank_shifts),1)*100, 1),
        },
        'national_score': {
            'total': len(all_score_shifts),
            'groups': len(score_groups),
            'median': sorted(all_score_shifts)[len(all_score_shifts)//2] if all_score_shifts else 0,
            'rush_rate': round(sum(1 for s in all_score_shifts if s<=10)/max(len(all_score_shifts),1)*100, 1),
            'steady_rate': round(sum(1 for s in all_score_shifts if s<=15)/max(len(all_score_shifts),1)*100, 1),
            'safe_rate': round(sum(1 for s in all_score_shifts if s<=40)/max(len(all_score_shifts),1)*100, 1),
        },
        'groups': all_results,
    }
    
    out_path = os.path.join(OUTPUT_DIR, "backtest_v9_final.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存: {out_path}")


if __name__ == '__main__':
    main()
