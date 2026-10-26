#!/usr/bin/env python
"""全国大规模回测引擎 v10 — 正确方法论
方法论：计算每所学校两年间的分数/位次偏移量(shift)，
然后统计偏移量在冲稳保阈值内的比例。

位次模式：shift = rank_y2 - rank_y1 (正=学校变容易)
  冲: shift >= 2500  (学校位次降了2500+名→冲的人能进)
  稳: shift >= -500  (学校位次没升超过500名→稳的人能进)
  保: shift >= -17500

分数模式：shift = score_y2 - score_y1 (正=分数上涨=变难)
  冲: shift <= 10  (分数没涨超过10分→冲的人能进)
  稳: shift <= 15
  保: shift <= 40
"""
import json, os, re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data")
V9_DIR = DATA_DIR / "province_v9"
MP_DIR = DATA_DIR / "multi_province"
RESULTS_DIR = DATA_DIR / "backtest_results"
RESULTS_DIR.mkdir(exist_ok=True)

# 老高考→新高考科类映射
CAT_MAP = {
    '文科': '历史', '理科': '物理', '文史': '历史', '理工': '物理',
    '文史类': '历史', '理工类': '物理', '综合': '综合',
}

def normalize_cat(cat):
    cat = (cat or '').strip()
    for old, new in CAT_MAP.items():
        if old in cat:
            return new
    return cat

def normalize_school(name):
    if not name: return ""
    name = re.sub(r'[\(（\[][\d]*[）)\]]', '', name)
    name = re.sub(r'\d+专业组.*$', '', name)
    name = re.sub(r'第\d*组.*$', '', name)
    name = re.sub(r'第组.*$', '', name)
    name = re.sub(r'[（(].*?[)）]', '', name)
    name = re.sub(r'\s+', '', name)
    return name.strip()

def load_v9():
    """加载所有v9数据"""
    all_data = {}  # {province: {year: {cat: [records]}}}
    
    for f in sorted(V9_DIR.glob("*_v9.json")):
        prov = f.stem.replace('_v9', '')
        data = json.load(open(f, 'r', encoding='utf-8'))
        if len(data) < 5: continue
        
        all_data.setdefault(prov, defaultdict(lambda: defaultdict(list)))
        for r in data:
            cat = normalize_cat(r.get('category', ''))
            all_data[prov][str(r['year'])][cat].append(r)
    
    return all_data

def load_api():
    """加载API数据（含真实位次min_section）"""
    all_data = {}  # {province: {year: {cat: [records]}}}
    
    for f in sorted(MP_DIR.glob("*.json")):
        # 跳过student文件
        if f.stem.startswith('student'): continue
        
        # 从文件名解析省份和年份: 北京_2023_admission.json → prov=北京, year=2023
        parts = f.stem.split('_')
        # 找到年份部分
        prov_parts = []
        year = None
        for p in parts:
            if p.isdigit() and len(p) == 4:
                year = p
            elif p not in ('admission', 'scores', 'v2'):
                prov_parts.append(p)
        prov = '_'.join(prov_parts) if prov_parts else f.stem
        
        data = json.load(open(f, 'r', encoding='utf-8'))
        if len(data) < 5: continue
        
        all_data.setdefault(prov, defaultdict(lambda: defaultdict(list)))
        for item in data:
            if not isinstance(item, dict): continue
            ms = item.get('min_section', '-')
            rank = None
            if ms and str(ms).strip() not in ('-', '', 'None'):
                try: rank = int(float(str(ms).strip()))
                except: pass
            
            cat = normalize_cat(item.get('local_type_name', '综合'))
            item_year = str(item.get('year', year or ''))
            score = item.get('score')
            try: score = int(score) if score else 0
            except: score = 0
                
            all_data[prov][item_year][cat].append({
                'school': item.get('name', item.get('school', '')),
                'score': score,
                'rank': rank,
            })
    
    return all_data

def dedup(records, prefer='rank'):
    """去重：同校取最低位次/最高分"""
    seen = {}
    for r in records:
        name = normalize_school(r.get('school', ''))
        if len(name) < 2: continue
        if name not in seen:
            seen[name] = r
        else:
            if prefer == 'rank':
                old_r = seen[name].get('rank')
                new_r = r.get('rank')
                if new_r and (not old_r or new_r < old_r):
                    seen[name] = r
            else:
                old_s = seen[name].get('score')
                new_s = r.get('score')
                if new_s and (not old_s or new_s < new_s):
                    seen[name] = r
    return seen

def match_and_shift(d1, d2, mode='rank'):
    """匹配两年的数据，返回每所学校的偏移量列表"""
    if mode == 'rank':
        m1 = dedup(d1, 'rank')
        m2 = dedup(d2, 'rank')
    else:
        m1 = dedup(d1, 'score')
        m2 = dedup(d2, 'score')
    
    shifts = []
    for school in set(m1.keys()) & set(m2.keys()):
        v1 = m1[school].get('rank' if mode == 'rank' else 'score')
        v2 = m2[school].get('rank' if mode == 'rank' else 'score')
        
        if mode == 'score':
            if not v1 or v1 > 850 or not v2 or v2 > 850: continue
        else:
            if not v1 or v1 <= 0 or not v2 or v2 <= 0: continue
        
        shifts.append(v2 - v1)
    
    return shifts

def backtest_group(shifts, name, mode):
    """对一组偏移量做回测统计"""
    n = len(shifts)
    if n < 10: return None
    
    ss = sorted(shifts)
    
    if mode == 'rank':
        # 位次模式：shift = rank_y2 - rank_y1 (正=变容易)
        return {
            'group': name, 'mode': 'rank', 'total': n,
            'median': ss[n//2], 'p25': ss[n//4], 'p75': ss[3*n//4],
            'forward_pct': round(sum(1 for s in shifts if s < 0) / n * 100, 1),
            # 冲: 学校位次降了2500+ → 冲的人能进
            'rush': round(sum(1 for s in shifts if s >= 2500) / n * 100, 1),
            # 稳: 学校位次没升超过500 → 稳的人能进
            'steady': round(sum(1 for s in shifts if s >= -500) / n * 100, 1),
            # 保: 学校位次没升超过17500 → 保的人能进
            'safe': round(sum(1 for s in shifts if s >= -17500) / n * 100, 1),
        }
    else:
        # 分数模式：shift = score_y2 - score_y1 (正=变难)
        return {
            'group': name, 'mode': 'score', 'total': n,
            'median': ss[n//2], 'p25': ss[n//4], 'p75': ss[3*n//4],
            'up_pct': round(sum(1 for s in shifts if s > 0) / n * 100, 1),
            # 冲: 分数没涨超过10分 → 冲的人能进
            'rush': round(sum(1 for s in shifts if s <= 10) / n * 100, 1),
            # 稳: 分数没涨超过15分 → 稳的人能进
            'steady': round(sum(1 for s in shifts if s <= 15) / n * 100, 1),
            # 保: 分数没涨超过40分 → 保的人能进
            'safe': round(sum(1 for s in shifts if s <= 40) / n * 100, 1),
        }

# ─── 主程序 ───
print("=" * 80)
print("📊 全国大规模回测引擎 v10（正确方法论）")
print("=" * 80)

v9_data = load_v9()
api_data = load_api()

print(f"\n数据源:")
print(f"  v9精确提取: {len(v9_data)} 省")
print(f"  API数据(含位次): {len(api_data)} 省")

all_results = []
all_rank_shifts = []
all_score_shifts = []
provinces_in_backtest = set()

# ─── 处理v9数据 ───
for prov in sorted(v9_data.keys()):
    years = sorted(v9_data[prov].keys())
    if len(years) < 2: continue
    
    # 匹配年份对
    for yi in range(len(years) - 1):
        y1, y2 = years[yi], years[yi+1]
        cats1 = set(v9_data[prov][y1].keys())
        cats2 = set(v9_data[prov][y2].keys())
        
        # 同科类匹配
        common_cats = sorted(cats1 & cats2)
        common_set = set(common_cats)
        
        # 老高考→新高考映射
        mapped_pairs = []
        for c1 in cats1 - common_set:
            mapped = CAT_MAP.get(c1, c1)
            if mapped in cats2 and mapped not in common_cats:
                mapped_pairs.append((c1, mapped))
        
        for cat in common_cats:
            mapped_pairs.append((cat, cat))
        
        for c1, c2 in mapped_pairs:
            d1 = v9_data[prov][y1][c1]
            d2 = v9_data[prov][y2][c2]
            
            label = f"{c1}" if c1 == c2 else f"{c1}→{c2}"
            group_name = f"{prov} {label} {y1}→{y2}"
            
            # 尝试位次回测
            shifts_r = match_and_shift(d1, d2, 'rank')
            if len(shifts_r) >= 10:
                res = backtest_group(shifts_r, group_name, 'rank')
                if res:
                    all_results.append(res)
                    all_rank_shifts.extend(shifts_r)
                    provinces_in_backtest.add(prov)
                    # 打印
                    print(f"  📊 {group_name} [位次]: {res['total']}校 | "
                          f"中位{res['median']:+,} 前移{res['forward_pct']}% | "
                          f"冲{res['rush']}% 稳{res['steady']}% 保{res['safe']}%")
                continue
            
            # 分数回测
            shifts_s = match_and_shift(d1, d2, 'score')
            if len(shifts_s) >= 10:
                res = backtest_group(shifts_s, group_name, 'score')
                if res:
                    all_results.append(res)
                    all_score_shifts.extend(shifts_s)
                    provinces_in_backtest.add(prov)
                    print(f"  📊 {group_name} [分数]: {res['total']}校 | "
                          f"中位{res['median']:+,}分 涨分{res['up_pct']}% | "
                          f"冲{res['rush']}% 稳{res['steady']}% 保{res['safe']}%")

# ─── 处理API数据 ───
for prov in sorted(api_data.keys()):
    years = sorted(api_data[prov].keys())
    if len(years) < 2: continue
    
    for yi in range(len(years) - 1):
        y1, y2 = years[yi], years[yi+1]
        cats1 = set(api_data[prov][y1].keys())
        cats2 = set(api_data[prov][y2].keys())
        common_cats = sorted(cats1 & cats2)
        
        for cat in common_cats:
            d1 = api_data[prov][y1][cat]
            d2 = api_data[prov][y2][cat]
            group_name = f"{prov}(API) {cat} {y1}→{y2}"
            
            shifts_r = match_and_shift(d1, d2, 'rank')
            if len(shifts_r) >= 10:
                res = backtest_group(shifts_r, group_name, 'rank')
                if res:
                    all_results.append(res)
                    all_rank_shifts.extend(shifts_r)
                    provinces_in_backtest.add(prov)
                    print(f"  📊 {group_name} [位次]: {res['total']}校 | "
                          f"中位{res['median']:+,} 前移{res['forward_pct']}% | "
                          f"冲{res['rush']}% 稳{res['steady']}% 保{res['safe']}%")

# ─── 全国汇总 ───
print(f"\n{'='*80}")
print(f"📋 全国汇总")
print(f"{'='*80}")

rank_groups = [r for r in all_results if r['mode'] == 'rank']
score_groups = [r for r in all_results if r['mode'] == 'score']

print(f"\n总回测组数: {len(all_results)}")
print(f"覆盖省份: {len(provinces_in_backtest)} 个")
print(f"  含位次回测: {len(rank_groups)} 组 ({sum(r['total'] for r in rank_groups):,} 校)")
print(f"  含分数回测: {len(score_groups)} 组 ({sum(r['total'] for r in score_groups):,} 校)")

if all_rank_shifts:
    N = len(all_rank_shifts)
    ss = sorted(all_rank_shifts)
    print(f"\n📈 位次回测汇总 ({N:,}校, {len(rank_groups)}组):")
    print(f"  中位偏移: {ss[N//2]:+,}名")
    print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}名")
    print(f"  前移比例: {sum(1 for s in all_rank_shifts if s<0)/N*100:.1f}%")
    print(f"  冲(≥+2500): {sum(1 for s in all_rank_shifts if s>=2500)/N*100:.1f}%")
    print(f"  稳(≥-500):  {sum(1 for s in all_rank_shifts if s>=-500)/N*100:.1f}%")
    print(f"  保(≥-17500):{sum(1 for s in all_rank_shifts if s>=-17500)/N*100:.1f}%")

if all_score_shifts:
    N = len(all_score_shifts)
    ss = sorted(all_score_shifts)
    print(f"\n📈 分数回测汇总 ({N:,}校, {len(score_groups)}组):")
    print(f"  中位偏移: {ss[N//2]:+,}分")
    print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}分")
    print(f"  涨分比例: {sum(1 for s in all_score_shifts if s>0)/N*100:.1f}%")
    print(f"  冲(≤+10): {sum(1 for s in all_score_shifts if s<=10)/N*100:.1f}%")
    print(f"  稳(≤+15): {sum(1 for s in all_score_shifts if s<=15)/N*100:.1f}%")
    print(f"  保(≤+40): {sum(1 for s in all_score_shifts if s<=40)/N*100:.1f}%")

# ─── 详情表 ───
print(f"\n{'='*110}")
print(f"{'组名':<40} {'模式':>4} {'校数':>6} {'中位':>8} {'P25':>8} {'P75':>8} {'冲%':>7} {'稳%':>7} {'保%':>7}")
print("-" * 110)
for r in sorted(all_results, key=lambda x: -x['total']):
    print(f"{r['group']:<40} {r['mode']:>4} {r['total']:>6} {r['median']:>+8,} {r['p25']:>+8,} {r['p75']:>+8,} {r['rush']:>6.1f}% {r['steady']:>6.1f}% {r['safe']:>6.1f}%")

# ─── 保存 ───
output = {
    'version': 'v10',
    'total_groups': len(all_results),
    'total_provinces': len(provinces_in_backtest),
    'provinces': sorted(provinces_in_backtest),
    'national_rank': {
        'total': len(all_rank_shifts), 'groups': len(rank_groups),
        'median': sorted(all_rank_shifts)[len(all_rank_shifts)//2] if all_rank_shifts else 0,
        'p25': sorted(all_rank_shifts)[len(all_rank_shifts)//4] if all_rank_shifts else 0,
        'p75': sorted(all_rank_shifts)[3*len(all_rank_shifts)//4] if all_rank_shifts else 0,
        'forward_pct': round(sum(1 for s in all_rank_shifts if s<0)/max(len(all_rank_shifts),1)*100, 1),
        'rush': round(sum(1 for s in all_rank_shifts if s>=2500)/max(len(all_rank_shifts),1)*100, 1),
        'steady': round(sum(1 for s in all_rank_shifts if s>=-500)/max(len(all_rank_shifts),1)*100, 1),
        'safe': round(sum(1 for s in all_rank_shifts if s>=-17500)/max(len(all_rank_shifts),1)*100, 1),
    },
    'national_score': {
        'total': len(all_score_shifts), 'groups': len(score_groups),
        'median': sorted(all_score_shifts)[len(all_score_shifts)//2] if all_score_shifts else 0,
        'p25': sorted(all_score_shifts)[len(all_score_shifts)//4] if all_score_shifts else 0,
        'p75': sorted(all_score_shifts)[3*len(all_score_shifts)//4] if all_score_shifts else 0,
        'up_pct': round(sum(1 for s in all_score_shifts if s>0)/max(len(all_score_shifts),1)*100, 1),
        'rush': round(sum(1 for s in all_score_shifts if s<=10)/max(len(all_score_shifts),1)*100, 1),
        'steady': round(sum(1 for s in all_score_shifts if s<=15)/max(len(all_score_shifts),1)*100, 1),
        'safe': round(sum(1 for s in all_score_shifts if s<=40)/max(len(all_score_shifts),1)*100, 1),
    },
    'groups': all_results,
}

out_path = RESULTS_DIR / "backtest_v10.json"
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n💾 结果已保存: {out_path}")
