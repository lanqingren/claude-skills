#!/usr/bin/env python3
"""
全国回测引擎 v9 - 最终版
数据源：
  1. dxsbb v9提取 (多省分数+部分位次)
  2. EOL API (北京/广东位次)
  3. 贵州PDF (18325条位次)
回测模式：
  - 位次回测 (rank shift)
  - 分数回测 (score shift)  
  - 综合回测 (加权合并)
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


def load_v9_data():
    """加载v9提取的各省数据"""
    data = {}
    if not os.path.exists(V9_DIR):
        return data
    for f in os.listdir(V9_DIR):
        if f.endswith('_v9.json'):
            prov = f.replace('_v9.json', '')
            with open(os.path.join(V9_DIR, f), 'r', encoding='utf-8') as fh:
                data[prov] = json.load(fh)
    return data


def load_api_data():
    """加载API数据（北京/广东）"""
    data = {}
    api_files = {
        '北京': ['北京_2023_admission.json', '北京_2024_admission.json'],
        '广东': ['广东_2022_admission.json', '广东_2023_admission.json', '广东_2024_admission.json'],
    }
    for prov, files in api_files.items():
        records = []
        for fname in files:
            fpath = os.path.join(API_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                    for item in items:
                        ms = item.get('min_section', '-')
                        try:
                            rank = int(ms)
                            if rank > 0:
                                min_val = item.get('min', '-')
                                try:
                                    score = int(min_val) if min_val and min_val != '-' else None
                                except (ValueError, TypeError):
                                    score = None
                                records.append({
                                    'school': item.get('name', ''),
                                    'rank': rank,
                                    'score': score,
                                    'year': int(item.get('year', 0)),
                                    'category': item.get('local_type_name', '综合'),
                                    'source': 'EOL_API',
                                })
                        except (ValueError, TypeError):
                            pass
        if records:
            data[prov] = records
    return data


def load_guizhou_pdf():
    """加载贵州PDF数据"""
    fpath = os.path.join(DATA_DIR, "贵州_2025_物理类_本科批投档_complete.json")
    if not os.path.exists(fpath):
        return {}
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # 格式转换
    records = []
    for item in data:
        rank = item.get('min_rank') or item.get('rank')
        score = item.get('min_score') or item.get('score')
        school = item.get('school_name') or item.get('school') or item.get('name')
        if school and rank:
            records.append({
                'school': school.strip(),
                'rank': int(rank),
                'score': int(score) if score else None,
                'year': 2025,
                'category': '物理',
                'source': '贵州PDF',
            })
    return {'贵州': records} if records else {}


def normalize_school(name):
    """标准化学校名"""
    if not name:
        return ""
    name = re.sub(r'[\(（\[【].*?[\)）\]】]', '', name)
    name = re.sub(r'\d+专业组.*$', '', name)
    name = re.sub(r'第\d+组.*$', '', name)
    return name.strip()


def dedup_by_school(records, prefer='best_rank'):
    """按学校去重，同一学校取最低rank或最高score"""
    seen = {}
    for r in records:
        name = normalize_school(r.get('school', ''))
        if len(name) < 4:
            continue
        r['school_n'] = name
        
        if name not in seen:
            seen[name] = r
        else:
            if prefer == 'best_rank' and 'rank' in r and 'rank' in seen[name]:
                if r['rank'] < seen[name]['rank']:
                    seen[name] = r
            elif prefer == 'best_score' and 'score' in r and 'score' in seen[name]:
                if r['score'] > seen[name]['score']:
                    seen[name] = r
    return seen


def match_years(data_n, data_n1, mode='rank'):
    """匹配两年数据"""
    if mode == 'rank':
        d_n = dedup_by_school(data_n, 'best_rank')
        d_n1 = dedup_by_school(data_n1, 'best_rank')
    else:
        d_n = dedup_by_school(data_n, 'best_score')
        d_n1 = dedup_by_school(data_n1, 'best_score')
    
    matched = []
    for school in set(d_n.keys()) & set(d_n1.keys()):
        r_n = d_n[school]
        r_n1 = d_n1[school]
        
        if mode == 'rank':
            v_n = r_n.get('rank')
            v_n1 = r_n1.get('rank')
        else:
            v_n = r_n.get('score')
            v_n1 = r_n1.get('score')
        
        if v_n and v_n1 and v_n > 0 and v_n1 > 0:
            if mode == 'score':
                if v_n > 850 or v_n1 > 850:  # 不合理分数跳过
                    continue
            matched.append({
                'school': school,
                'v_n': v_n,
                'v_n1': v_n1,
                'shift': v_n1 - v_n,
            })
    return matched


def backtest_group(matched, group_name, mode='rank'):
    """回测一组数据"""
    if len(matched) < 20:
        return None
    
    shifts = [m['shift'] for m in matched]
    n = len(shifts)
    ss = sorted(shifts)
    
    result = {
        'group': group_name,
        'mode': mode,
        'total': n,
        'median': ss[n // 2],
        'p25': ss[n // 4],
        'p75': ss[3 * n // 4],
    }
    
    if mode == 'rank':
        # 位次模式：shift>0=变容易, shift<0=变难
        result['forward_pct'] = round(sum(1 for s in shifts if s < 0) / n * 100, 1)
        # 冲(offset=2500): P(shift >= 2500)
        result['rush_hit'] = round(sum(1 for s in shifts if s >= 2500) / n * 100, 1)
        # 稳(offset=-500): P(shift >= -500)
        result['steady_hit'] = round(sum(1 for s in shifts if s >= -500) / n * 100, 1)
        # 保(offset=-17500): P(shift >= -17500)
        result['safe_hit'] = round(sum(1 for s in shifts if s >= -17500) / n * 100, 1)
    else:
        # 分数模式：shift>0=分数上涨(变难), shift<0=分数下降(变容易)
        result['up_pct'] = round(sum(1 for s in shifts if s > 0) / n * 100, 1)
        # 冲(学校比考生高5~15分): 录取=P(shift <= 10)
        result['rush_hit'] = round(sum(1 for s in shifts if s <= 10) / n * 100, 1)
        # 稳(学校比考生低0~15分): 录取=P(shift <= 15)
        result['steady_hit'] = round(sum(1 for s in shifts if s <= 15) / n * 100, 1)
        # 保(学校比考生低15~40分): 录取=P(shift <= 40)
        result['safe_hit'] = round(sum(1 for s in shifts if s <= 40) / n * 100, 1)
    
    return result


def main():
    print("=" * 80)
    print("📊 全国回测引擎 v9")
    print("=" * 80)
    
    # 加载所有数据源
    v9_data = load_v9_data()
    api_data = load_api_data()
    gz_data = load_guizhou_pdf()
    
    print(f"\n数据源:")
    print(f"  dxsbb v9: {len(v9_data)}省")
    for prov, recs in sorted(v9_data.items()):
        wr = sum(1 for r in recs if 'rank' in r)
        ws = sum(1 for r in recs if 'score' in r)
        print(f"    {prov}: {len(recs)}条 (rank={wr}, score={ws})")
    print(f"  EOL API: {len(api_data)}省")
    for prov, recs in sorted(api_data.items()):
        print(f"    {prov}: {len(recs)}条 (全有rank)")
    print(f"  贵州PDF: {len(gz_data.get('贵州', []))}条")
    
    all_results = []
    all_rank_shifts = []
    all_score_shifts = []
    
    # ===== 1. API数据回测（北京、广东）- 位次模式 =====
    print(f"\n{'='*60}")
    print("📍 API数据回测（位次模式）")
    print(f"{'='*60}")
    
    for prov in ['北京', '广东']:
        records = api_data.get(prov, [])
        if not records:
            continue
        
        by_year_cat = defaultdict(lambda: defaultdict(list))
        for r in records:
            by_year_cat[r['year']][r['category']].append(r)
        
        years = sorted(by_year_cat.keys())
        
        for yi in range(len(years) - 1):
            y_n = years[yi]
            y_n1 = years[yi + 1]
            
            cats_n = set(by_year_cat[y_n].keys())
            cats_n1 = set(by_year_cat[y_n1].keys())
            
            for cat in sorted(cats_n & cats_n1):
                matched = match_years(by_year_cat[y_n][cat], by_year_cat[y_n1][cat], 'rank')
                if len(matched) >= 20:
                    group = f"{prov} {cat} {y_n}→{y_n1}"
                    result = backtest_group(matched, group, 'rank')
                    if result:
                        all_results.append(result)
                        all_rank_shifts.extend([m['shift'] for m in matched])
                        print(f"  ✅ {group}: {len(matched)}校, 中位={result['median']:+,}, 冲={result['rush_hit']}% 稳={result['steady_hit']}% 保={result['safe_hit']}%")
    
    # ===== 2. 贵州PDF数据 - 只有2025年，无法跨年 =====
    # 但可以用贵州API 2024 vs PDF 2025
    gz_api_path = os.path.join(DATA_DIR, "raw_2024.json")
    if os.path.exists(gz_api_path) and gz_data:
        try:
            with open(gz_api_path, 'r', encoding='utf-8') as f:
                gz_api = json.load(f)
            # API格式可能不同，尝试提取
            if isinstance(gz_api, dict) and 'data' in gz_api:
                gz_items = gz_api['data'].get('item', [])
            else:
                gz_items = gz_api if isinstance(gz_api, list) else []
            
            gz_2024 = []
            for item in gz_items:
                ms = item.get('min_section', '-')
                try:
                    rank = int(ms)
                    if rank > 0 and item.get('local_province_name') == '贵州':
                        gz_2024.append({
                            'school': item.get('name', ''),
                            'rank': rank,
                            'year': 2024,
                            'category': item.get('local_type_name', ''),
                        })
                except:
                    pass
            
            if gz_2024 and gz_data.get('贵州'):
                matched = match_years(gz_2024, gz_data['贵州'], 'rank')
                if len(matched) >= 20:
                    group = "贵州 物理 2024→2025 (API→PDF)"
                    result = backtest_group(matched, group, 'rank')
                    if result:
                        all_results.append(result)
                        all_rank_shifts.extend([m['shift'] for m in matched])
                        print(f"  ✅ {group}: {len(matched)}校, 中位={result['median']:+,}")
        except Exception as e:
            print(f"  ⚠️ 贵州跨年回测失败: {e}")
    
    # ===== 3. dxsbb v9数据回测 =====
    print(f"\n{'='*60}")
    print("📍 dxsbb数据回测")
    print(f"{'='*60}")
    
    for prov, records in sorted(v9_data.items()):
        by_year_cat = defaultdict(lambda: defaultdict(list))
        for r in records:
            by_year_cat[r['year']][r['category']].append(r)
        
        years = sorted(by_year_cat.keys())
        if len(years) < 2:
            continue
        
        cats_23 = set(by_year_cat.get(2023, {}).keys())
        cats_24 = set(by_year_cat.get(2024, {}).keys())
        
        # 跨年映射
        pairs = []
        for c in sorted(cats_23 & cats_24):
            pairs.append((c, c))
        # 老高考→新高考
        if '理科' in cats_23 and '物理' in cats_24:
            pairs.append(('理科', '物理'))
        if '文科' in cats_23 and '历史' in cats_24:
            pairs.append(('文科', '历史'))
        
        for cat_old, cat_new in pairs:
            d_23 = by_year_cat.get(2023, {}).get(cat_old, [])
            d_24 = by_year_cat.get(2024, {}).get(cat_new, [])
            
            if not d_23 or not d_24:
                continue
            
            label = f"{cat_old}→{cat_new}" if cat_old != cat_new else cat_new
            
            # 优先位次回测
            matched_rank = match_years(d_23, d_24, 'rank')
            if len(matched_rank) >= 20:
                group = f"{prov} {label} 2023→2024 [位次]"
                result = backtest_group(matched_rank, group, 'rank')
                if result:
                    all_results.append(result)
                    all_rank_shifts.extend([m['shift'] for m in matched_rank])
                    print(f"  ✅ {group}: {len(matched_rank)}校, 中位={result['median']:+,}, 冲={result['rush_hit']}% 稳={result['steady_hit']}% 保={result['safe_hit']}%")
                continue
            
            # 分数回测
            matched_score = match_years(d_23, d_24, 'score')
            if len(matched_score) >= 20:
                group = f"{prov} {label} 2023→2024 [分数]"
                result = backtest_group(matched_score, group, 'score')
                if result:
                    all_results.append(result)
                    all_score_shifts.extend([m['shift'] for m in matched_score])
                    print(f"  ✅ {group}: {len(matched_score)}校, 中位={result['median']:+,}分, 冲={result['rush_hit']}% 稳={result['steady_hit']}% 保={result['safe_hit']}%")
    
    # ===== 全国汇总 =====
    print(f"\n{'='*80}")
    print(f"📊 全国回测汇总 (v9)")
    print(f"{'='*80}")
    
    rank_results = [r for r in all_results if r['mode'] == 'rank']
    score_results = [r for r in all_results if r['mode'] == 'score']
    total_schools = sum(r['total'] for r in all_results)
    
    print(f"\n回测组数: {len(all_results)}组 ({len(rank_results)}位次 + {len(score_results)}分数)")
    print(f"总匹配院校: {total_schools:,}所")
    
    if all_rank_shifts:
        N = len(all_rank_shifts)
        ss = sorted(all_rank_shifts)
        print(f"\n📈 位次回测 ({N:,}校, {len(rank_results)}组):")
        print(f"  中位偏移: {ss[N//2]:+,}名")
        print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}名")
        print(f"  冲(≥2500): {sum(1 for s in all_rank_shifts if s >= 2500)/N*100:.1f}%")
        print(f"  稳(≥-500): {sum(1 for s in all_rank_shifts if s >= -500)/N*100:.1f}%")
        print(f"  保(≥-17500): {sum(1 for s in all_rank_shifts if s >= -17500)/N*100:.1f}%")
    
    if all_score_shifts:
        N = len(all_score_shifts)
        ss = sorted(all_score_shifts)
        print(f"\n📈 分数回测 ({N:,}校, {len(score_results)}组):")
        print(f"  中位偏移: {ss[N//2]:+,}分")
        print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}分")
        print(f"  冲(≤10分): {sum(1 for s in all_score_shifts if s <= 10)/N*100:.1f}%")
        print(f"  稳(≤15分): {sum(1 for s in all_score_shifts if s <= 15)/N*100:.1f}%")
        print(f"  保(≤40分): {sum(1 for s in all_score_shifts if s <= 40)/N*100:.1f}%")
        print(f"  分数上涨: {sum(1 for s in all_score_shifts if s > 0)/N*100:.1f}%")
        print(f"  分数下降: {sum(1 for s in all_score_shifts if s < 0)/N*100:.1f}%")
    
    # 分组详情
    print(f"\n{'='*80}")
    print(f"📋 全部分组详情")
    print(f"{'='*80}")
    print(f"{'组名':<35} {'模式':>4} {'匹配':>6} {'中位':>10} {'P25':>10} {'P75':>10} {'冲%':>6} {'稳%':>6} {'保%':>6}")
    print("-" * 100)
    for r in sorted(all_results, key=lambda x: -x['total']):
        print(f"{r['group']:<35} {r['mode']:>4} {r['total']:>6} {r['median']:>+10,} {r['p25']:>+10,} {r['p75']:>+10,} {r['rush_hit']:>5.1f}% {r['steady_hit']:>5.1f}% {r['safe_hit']:>5.1f}%")
    
    # 保存
    output = {
        'version': 'v9',
        'total_groups': len(all_results),
        'total_schools': total_schools,
        'rank_groups': len(rank_results),
        'score_groups': len(score_results),
        'national_rank': {
            'total': len(all_rank_shifts),
            'median': ss[len(all_rank_shifts)//2] if all_rank_shifts else 0,
            'rush_rate': round(sum(1 for s in all_rank_shifts if s >= 2500)/max(len(all_rank_shifts),1)*100, 1),
            'steady_rate': round(sum(1 for s in all_rank_shifts if s >= -500)/max(len(all_rank_shifts),1)*100, 1),
            'safe_rate': round(sum(1 for s in all_rank_shifts if s >= -17500)/max(len(all_rank_shifts),1)*100, 1),
        } if all_rank_shifts else None,
        'national_score': {
            'total': len(all_score_shifts),
            'median': sorted(all_score_shifts)[len(all_score_shifts)//2] if all_score_shifts else 0,
        } if all_score_shifts else None,
        'groups': all_results,
    }
    
    out_path = os.path.join(OUTPUT_DIR, "backtest_v9_national.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存: {out_path}")


if __name__ == '__main__':
    main()
