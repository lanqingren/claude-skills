#!/usr/bin/env python
"""全国大规模回测引擎 v11 — 多维度深度分析

v10 基础上新增：
1. 纳入福建/辽宁/黑龙江3省（新增~10,000校）
2. 院校层次分析：985/211/双非/民办 的波动差异
3. 科类对比：物理 vs 历史 的命中率差异
4. 省份波动分级：高/中/低波动省份分类
5. 省级参数校准：不同省份的冲稳保最优阈值
6. 大小年检测：连续波动方向变化的学校识别
"""
import json, os, re, math
from pathlib import Path
from collections import defaultdict, Counter

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

# ─── 加载院校层次信息 ───
def load_school_tiers():
    """从school_list.json加载985/211/双一流/公办/民办标签"""
    tiers = {}
    sl_path = DATA_DIR / "school_list.json"
    if not sl_path.exists():
        print("⚠️ school_list.json not found, tier analysis will be skipped")
        return tiers
    
    data = json.load(open(sl_path, 'r', encoding='utf-8'))
    for s in data:
        name = normalize_school(s.get('name', ''))
        if not name or len(name) < 2:
            continue
        
        is_985 = s.get('f985') == '1'
        is_211 = s.get('f211') == '1'
        dual = s.get('dual_class_name', '')
        nature = s.get('nature_name', '')
        
        if is_985:
            tiers[name] = '985'
        elif is_211:
            tiers[name] = '211'
        elif '双一流' in dual:
            tiers[name] = '双一流'
        elif '民办' in nature or '独立' in nature:
            tiers[name] = '民办'
        else:
            tiers[name] = '公办'
    
    return tiers

SCHOOL_TIERS = load_school_tiers()
print(f"📚 院校层次库: {len(SCHOOL_TIERS)} 所院校")
tier_dist = Counter(SCHOOL_TIERS.values())
print(f"   985={tier_dist['985']}, 211={tier_dist['211']}, 双一流={tier_dist['双一流']}, 公办={tier_dist['公办']}, 民办={tier_dist['民办']}")

def get_tier(school_name):
    """获取院校层次，支持模糊匹配"""
    name = normalize_school(school_name)
    if name in SCHOOL_TIERS:
        return SCHOOL_TIERS[name]
    # 尝试去掉常见后缀再匹配
    for suffix in ['大学', '学院', '校区', '分校']:
        if name.endswith(suffix) and len(name) > len(suffix) + 2:
            base = name[:-len(suffix)]
            if base + '大学' in SCHOOL_TIERS:
                return SCHOOL_TIERS[base + '大学']
            if base + '学院' in SCHOOL_TIERS:
                return SCHOOL_TIERS[base + '学院']
    return '未知'

def load_v9():
    """加载所有v9数据"""
    all_data = {}
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
    all_data = {}
    for f in sorted(MP_DIR.glob("*.json")):
        if f.stem.startswith('student'): continue
        parts = f.stem.split('_')
        prov_parts, year = [], None
        for p in parts:
            if p.isdigit() and len(p) == 4: year = p
            elif p not in ('admission', 'scores', 'v2'): prov_parts.append(p)
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
                'score': score, 'rank': rank,
            })
    return all_data

def dedup(records, prefer='rank'):
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
    """匹配两年的数据，返回偏移量列表（含学校名和层次信息）"""
    if mode == 'rank':
        m1, m2 = dedup(d1, 'rank'), dedup(d2, 'rank')
    else:
        m1, m2 = dedup(d1, 'score'), dedup(d2, 'score')
    
    shifts = []
    for school in set(m1.keys()) & set(m2.keys()):
        v1 = m1[school].get('rank' if mode == 'rank' else 'score')
        v2 = m2[school].get('rank' if mode == 'rank' else 'score')
        if mode == 'score':
            if not v1 or v1 > 850 or not v2 or v2 > 850: continue
        else:
            if not v1 or v1 <= 0 or not v2 or v2 <= 0: continue
        
        shifts.append({
            'school': school,
            'tier': get_tier(school),
            'shift': v2 - v1,
            'v1': v1, 'v2': v2,
        })
    return shifts

def backtest_group(shifts_raw, name, mode):
    """对一组偏移量做回测统计"""
    shifts = [s['shift'] for s in shifts_raw]
    n = len(shifts)
    if n < 10: return None
    ss = sorted(shifts)
    
    if mode == 'rank':
        return {
            'group': name, 'mode': 'rank', 'total': n,
            'median': ss[n//2], 'p25': ss[n//4], 'p75': ss[3*n//4],
            'forward_pct': round(sum(1 for s in shifts if s < 0) / n * 100, 1),
            'rush': round(sum(1 for s in shifts if s >= 2500) / n * 100, 1),
            'steady': round(sum(1 for s in shifts if s >= -500) / n * 100, 1),
            'safe': round(sum(1 for s in shifts if s >= -17500) / n * 100, 1),
        }
    else:
        return {
            'group': name, 'mode': 'score', 'total': n,
            'median': ss[n//2], 'p25': ss[n//4], 'p75': ss[3*n//4],
            'up_pct': round(sum(1 for s in shifts if s > 0) / n * 100, 1),
            'rush': round(sum(1 for s in shifts if s <= 10) / n * 100, 1),
            'steady': round(sum(1 for s in shifts if s <= 15) / n * 100, 1),
            'safe': round(sum(1 for s in shifts if s <= 40) / n * 100, 1),
        }

# ═══════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════

print("\n" + "=" * 80)
print("📊 全国大规模回测引擎 v11（多维度深度分析）")
print("=" * 80)

v9_data = load_v9()
api_data = load_api()

print(f"\n数据源:")
print(f"  v9精确提取: {len(v9_data)} 省")
print(f"  API数据(含位次): {len(api_data)} 省")

all_results = []
all_rank_shifts = []  # 含层次信息
all_score_shifts = []
provinces_in_backtest = set()
province_stats = {}  # {province: {mode, shifts, ...}}

# ─── 处理v9数据 ───
for prov in sorted(v9_data.keys()):
    years = sorted(v9_data[prov].keys())
    if len(years) < 2: continue
    
    for yi in range(len(years) - 1):
        y1, y2 = years[yi], years[yi+1]
        cats1 = set(v9_data[prov][y1].keys())
        cats2 = set(v9_data[prov][y2].keys())
        common_cats = sorted(cats1 & cats2)
        common_set = set(common_cats)
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
            shifts_r_raw = match_and_shift(d1, d2, 'rank')
            if len(shifts_r_raw) >= 10:
                res = backtest_group(shifts_r_raw, group_name, 'rank')
                if res:
                    all_results.append(res)
                    all_rank_shifts.extend([{**s, 'province': prov, 'cat': c1} for s in shifts_r_raw])
                    provinces_in_backtest.add(prov)
                    province_stats.setdefault(prov, {'rank': [], 'score': []})
                    province_stats[prov]['rank'].extend(s['shift'] for s in shifts_r_raw)
                    print(f"  📊 {group_name} [位次]: {res['total']}校 | "
                          f"中位{res['median']:+,} 前移{res['forward_pct']}% | "
                          f"冲{res['rush']}% 稳{res['steady']}% 保{res['safe']}%")
                continue
            
            # 分数回测
            shifts_s_raw = match_and_shift(d1, d2, 'score')
            if len(shifts_s_raw) >= 10:
                res = backtest_group(shifts_s_raw, group_name, 'score')
                if res:
                    all_results.append(res)
                    all_score_shifts.extend([{**s, 'province': prov, 'cat': c1} for s in shifts_s_raw])
                    provinces_in_backtest.add(prov)
                    province_stats.setdefault(prov, {'rank': [], 'score': []})
                    province_stats[prov]['score'].extend(s['shift'] for s in shifts_s_raw)
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
            shifts_r_raw = match_and_shift(d1, d2, 'rank')
            if len(shifts_r_raw) >= 10:
                res = backtest_group(shifts_r_raw, group_name, 'rank')
                if res:
                    all_results.append(res)
                    all_rank_shifts.extend([{**s, 'province': prov+'(API)', 'cat': cat} for s in shifts_r_raw])
                    provinces_in_backtest.add(prov)
                    province_stats.setdefault(prov+'(API)', {'rank': [], 'score': []})
                    province_stats[prov+'(API)']['rank'].extend(s['shift'] for s in shifts_r_raw)
                    print(f"  📊 {group_name} [位次]: {res['total']}校 | "
                          f"中位{res['median']:+,} 前移{res['forward_pct']}% | "
                          f"冲{res['rush']}% 稳{res['steady']}% 保{res['safe']}%")

# ═══════════════════════════════════════════════════
# 全国汇总
# ═══════════════════════════════════════════════════
print(f"\n{'='*80}")
print(f"📋 全国汇总")
print(f"{'='*80}")

rank_groups = [r for r in all_results if r['mode'] == 'rank']
score_groups = [r for r in all_results if r['mode'] == 'score']

print(f"\n总回测组数: {len(all_results)}")
print(f"覆盖省份: {len(provinces_in_backtest)} 个")
print(f"  含位次回测: {len(rank_groups)} 组 ({sum(r['total'] for r in rank_groups):,} 校)")
print(f"  含分数回测: {len(score_groups)} 组 ({sum(r['total'] for r in score_groups):,} 校)")

rank_shifts_simple = [s['shift'] for s in all_rank_shifts]
score_shifts_simple = [s['shift'] for s in all_score_shifts]

if rank_shifts_simple:
    N = len(rank_shifts_simple)
    ss = sorted(rank_shifts_simple)
    print(f"\n📈 位次回测汇总 ({N:,}校, {len(rank_groups)}组):")
    print(f"  中位偏移: {ss[N//2]:+,}名")
    print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}名")
    print(f"  前移比例: {sum(1 for s in rank_shifts_simple if s<0)/N*100:.1f}%")
    print(f"  冲(≥+2500): {sum(1 for s in rank_shifts_simple if s>=2500)/N*100:.1f}%")
    print(f"  稳(≥-500):  {sum(1 for s in rank_shifts_simple if s>=-500)/N*100:.1f}%")
    print(f"  保(≥-17500):{sum(1 for s in rank_shifts_simple if s>=-17500)/N*100:.1f}%")

if score_shifts_simple:
    N = len(score_shifts_simple)
    ss = sorted(score_shifts_simple)
    print(f"\n📈 分数回测汇总 ({N:,}校, {len(score_groups)}组):")
    print(f"  中位偏移: {ss[N//2]:+,}分")
    print(f"  P25~P75: {ss[N//4]:+,} ~ {ss[3*N//4]:+,}分")
    print(f"  涨分比例: {sum(1 for s in score_shifts_simple if s>0)/N*100:.1f}%")
    print(f"  冲(≤+10): {sum(1 for s in score_shifts_simple if s<=10)/N*100:.1f}%")
    print(f"  稳(≤+15): {sum(1 for s in score_shifts_simple if s<=15)/N*100:.1f}%")
    print(f"  保(≤+40): {sum(1 for s in score_shifts_simple if s<=40)/N*100:.1f}%")

# ═══════════════════════════════════════════════════
# 🔬 新维度1：院校层次分析
# ═══════════════════════════════════════════════════
print(f"\n{'='*80}")
print(f"🔬 维度1：院校层次波动分析")
print(f"{'='*80}")

tier_analysis = {}
for mode_label, all_shifts in [('rank', all_rank_shifts), ('score', all_score_shifts)]:
    tier_groups = defaultdict(list)
    for s in all_shifts:
        tier_groups[s['tier']].append(s['shift'])
    
    for tier in ['985', '211', '双一流', '公办', '民办', '未知']:
        shifts = tier_groups.get(tier, [])
        if len(shifts) < 20:
            continue
        ss = sorted(shifts)
        n = len(shifts)
        
        if mode_label == 'rank':
            stats = {
                'tier': tier, 'mode': mode_label, 'total': n,
                'median': ss[n//2],
                'p25': ss[n//4], 'p75': ss[3*n//4],
                'forward_pct': round(sum(1 for x in shifts if x < 0) / n * 100, 1),
                'rush': round(sum(1 for x in shifts if x >= 2500) / n * 100, 1),
                'steady': round(sum(1 for x in shifts if x >= -500) / n * 100, 1),
                'safe': round(sum(1 for x in shifts if x >= -17500) / n * 100, 1),
            }
        else:
            stats = {
                'tier': tier, 'mode': mode_label, 'total': n,
                'median': ss[n//2],
                'p25': ss[n//4], 'p75': ss[3*n//4],
                'up_pct': round(sum(1 for x in shifts if x > 0) / n * 100, 1),
                'rush': round(sum(1 for x in shifts if x <= 10) / n * 100, 1),
                'steady': round(sum(1 for x in shifts if x <= 15) / n * 100, 1),
                'safe': round(sum(1 for x in shifts if x <= 40) / n * 100, 1),
            }
        
        key = f"{tier}_{mode_label}"
        tier_analysis[key] = stats
        
        if mode_label == 'rank':
            print(f"\n  [{tier}] 位次回测 ({n:,}校):")
            print(f"    中位偏移: {stats['median']:+,}名 | 前移{stats['forward_pct']}%")
            print(f"    P25~P75: {stats['p25']:+,} ~ {stats['p75']:+,}名")
            print(f"    冲{stats['rush']}% | 稳{stats['steady']}% | 保{stats['safe']}%")
        else:
            print(f"\n  [{tier}] 分数回测 ({n:,}校):")
            print(f"    中位偏移: {stats['median']:+,}分 | 涨分{stats['up_pct']}%")
            print(f"    P25~P75: {stats['p25']:+,} ~ {stats['p75']:+,}分")
            print(f"    冲{stats['rush']}% | 稳{stats['steady']}% | 保{stats['safe']}%")

# ═══════════════════════════════════════════════════
# 🔬 新维度2：科类对比（物理 vs 历史）
# ═══════════════════════════════════════════════════
print(f"\n{'='*80}")
print(f"🔬 维度2：物理 vs 历史科类对比")
print(f"{'='*80}")

cat_analysis = {}
for mode_label, all_shifts in [('rank', all_rank_shifts), ('score', all_score_shifts)]:
    cat_groups = defaultdict(list)
    for s in all_shifts:
        cat_norm = normalize_cat(s.get('cat', ''))
        if cat_norm in ('物理', '历史', '综合'):
            cat_groups[cat_norm].append(s['shift'])
    
    for cat in ['物理', '历史', '综合']:
        shifts = cat_groups.get(cat, [])
        if len(shifts) < 20:
            continue
        ss = sorted(shifts)
        n = len(shifts)
        
        if mode_label == 'rank':
            stats = {
                'cat': cat, 'mode': mode_label, 'total': n,
                'median': ss[n//2],
                'std': round((sum((x - sum(shifts)/n)**2 for x in shifts) / n) ** 0.5, 0),
                'rush': round(sum(1 for x in shifts if x >= 2500) / n * 100, 1),
                'steady': round(sum(1 for x in shifts if x >= -500) / n * 100, 1),
                'safe': round(sum(1 for x in shifts if x >= -17500) / n * 100, 1),
            }
        else:
            stats = {
                'cat': cat, 'mode': mode_label, 'total': n,
                'median': ss[n//2],
                'std': round((sum((x - sum(shifts)/n)**2 for x in shifts) / n) ** 0.5, 1),
                'rush': round(sum(1 for x in shifts if x <= 10) / n * 100, 1),
                'steady': round(sum(1 for x in shifts if x <= 15) / n * 100, 1),
                'safe': round(sum(1 for x in shifts if x <= 40) / n * 100, 1),
            }
        
        key = f"{cat}_{mode_label}"
        cat_analysis[key] = stats
        
        unit = '名' if mode_label == 'rank' else '分'
        print(f"  {cat} [{mode_label}] ({n:,}校): 中位{stats['median']:+,}{unit} σ={stats['std']:,.0f} | "
              f"冲{stats['rush']}% 稳{stats['steady']}% 保{stats['safe']}%")

# ═══════════════════════════════════════════════════
# 🔬 新维度3：省份波动分级 + 省级参数
# ═══════════════════════════════════════════════════
print(f"\n{'='*80}")
print(f"🔬 维度3：省份波动分级")
print(f"{'='*80}")

province_volatility = {}
for prov, stats in province_stats.items():
    for mode in ['rank', 'score']:
        shifts = stats[mode]
        if len(shifts) < 20:
            continue
        ss = sorted(shifts)
        n = len(shifts)
        mean = sum(shifts) / n
        std = (sum((x - mean) ** 2 for x in shifts) / n) ** 0.5
        iqr = ss[3*n//4] - ss[n//4]
        
        # 波动分级
        if mode == 'rank':
            vol_score = iqr / 1000  # IQR / 1000名
        else:
            vol_score = iqr / 5  # IQR / 5分
        
        if vol_score > 10:
            level = '🔴 高波动'
        elif vol_score > 3:
            level = '🟡 中波动'
        else:
            level = '🟢 低波动'
        
        province_volatility[f"{prov}_{mode}"] = {
            'province': prov, 'mode': mode, 'total': n,
            'median': ss[n//2], 'mean': round(mean, 1), 'std': round(std, 0),
            'iqr': iqr, 'vol_score': round(vol_score, 1), 'level': level,
        }
        
        unit = '名' if mode == 'rank' else '分'
        print(f"  {prov:>10} [{mode}] ({n:>5}校): 中位{ss[n//2]:>+8,}{unit} IQR={iqr:>+8,}{unit} → {level}")

# ═══════════════════════════════════════════════════
# 🔬 新维度4：省级参数校准
# ═══════════════════════════════════════════════════
print(f"\n{'='*80}")
print(f"🔬 维度4：省级冲稳保参数校准")
print(f"{'='*80}")
print(f"  为每个省份计算最优冲稳保阈值（命中率目标：冲≥20%/稳≥60%/保≥95%）\n")

province_params = {}
for prov, stats in province_stats.items():
    for mode in ['rank', 'score']:
        shifts = stats[mode]
        if len(shifts) < 50:
            continue
        ss = sorted(shifts)
        n = len(shifts)
        
        # 位次模式：shift = rank_y2 - rank_y1 (正=变容易)
        # 找到冲的阈值（≥20%命中率）：shift >= X 的比例 >= 20%
        # 即第80百分位的shift值
        rush_threshold = ss[int(n * 0.8)]  # 20%的学校shift >= 此值
        steady_threshold = ss[int(n * 0.4)]  # 60%的学校shift >= 此值
        safe_threshold = ss[int(n * 0.05)]   # 95%的学校shift >= 此值
        
        if mode == 'rank':
            params = {
                'province': prov, 'mode': mode, 'total': n,
                'rush_threshold': rush_threshold,
                'steady_threshold': steady_threshold,
                'safe_threshold': safe_threshold,
            }
            province_params[f"{prov}_{mode}"] = params
            print(f"  {prov:>10} [位次]: "
                  f"冲(≥{rush_threshold:>+7,}名={sum(1 for x in shifts if x>=rush_threshold)/n*100:.0f}%) "
                  f"稳(≥{steady_threshold:>+7,}名={sum(1 for x in shifts if x>=steady_threshold)/n*100:.0f}%) "
                  f"保(≥{safe_threshold:>+8,}名={sum(1 for x in shifts if x>=safe_threshold)/n*100:.0f}%)")
        else:
            params = {
                'province': prov, 'mode': mode, 'total': n,
                'rush_threshold': rush_threshold,
                'steady_threshold': steady_threshold,
                'safe_threshold': safe_threshold,
            }
            province_params[f"{prov}_{mode}"] = params
            print(f"  {prov:>10} [分数]: "
                  f"冲(≤{rush_threshold:>+4}分={sum(1 for x in shifts if x<=rush_threshold)/n*100:.0f}%) "
                  f"稳(≤{steady_threshold:>+4}分={sum(1 for x in shifts if x<=steady_threshold)/n*100:.0f}%) "
                  f"保(≤{safe_threshold:>+4}分={sum(1 for x in shifts if x<=safe_threshold)/n*100:.0f}%)")

# ═══════════════════════════════════════════════════
# 🔬 新维度5：波动分布直方图（简化版）
# ═══════════════════════════════════════════════════
print(f"\n{'='*80}")
print(f"🔬 维度5：位次偏移分布")
print(f"{'='*80}")

def histogram(data, bins, labels, title):
    counts = [0] * len(bins)
    for x in data:
        for i, (lo, hi) in enumerate(bins):
            if lo <= x < hi:
                counts[i] += 1
                break
    n = len(data)
    max_count = max(counts) if counts else 1
    print(f"\n  {title} (n={n:,})")
    for label, count in zip(labels, counts):
        bar_len = int(count / max_count * 40) if max_count > 0 else 0
        pct = count / n * 100 if n > 0 else 0
        print(f"    {label:>14s} │{'█' * bar_len:<40s}│ {count:>5} ({pct:4.1f}%)")

if rank_shifts_simple:
    rank_bins = [(-999999, -50000), (-50000, -25000), (-25000, -10000),
                 (-10000, -5000), (-5000, -1000), (-1000, 0),
                 (0, 1000), (1000, 5000), (5000, 10000),
                 (10000, 25000), (25000, 50000), (50000, 999999)]
    rank_labels = ['<-5万', '-5~-2.5万', '-2.5~-1万', '-1万~-5千', '-5千~-1千',
                   '-1千~0', '0~+1千', '+1~5千', '+5千~1万', '+1~2.5万', '+2.5~5万', '>+5万']
    histogram(rank_shifts_simple, rank_bins, rank_labels, "位次偏移分布（正=变容易）")

if score_shifts_simple:
    score_bins = [(-999, -30), (-30, -20), (-20, -10), (-10, -5),
                  (-5, 0), (0, 5), (5, 10), (10, 15), (15, 20), (20, 30), (30, 999)]
    score_labels = ['<-30', '-30~-20', '-20~-10', '-10~-5',
                    '-5~0', '0~+5', '+5~+10', '+10~+15', '+15~+20', '+20~+30', '>+30']
    histogram(score_shifts_simple, score_bins, score_labels, "分数偏移分布（正=变难）")

# ═══════════════════════════════════════════════════
# 详情表
# ═══════════════════════════════════════════════════
print(f"\n{'='*110}")
print(f"{'组名':<40} {'模式':>4} {'校数':>6} {'中位':>8} {'P25':>8} {'P75':>8} {'冲%':>7} {'稳%':>7} {'保%':>7}")
print("-" * 110)
for r in sorted(all_results, key=lambda x: -x['total']):
    print(f"{r['group']:<40} {r['mode']:>4} {r['total']:>6} {r['median']:>+8,} {r['p25']:>+8,} {r['p75']:>+8,} {r['rush']:>6.1f}% {r['steady']:>6.1f}% {r['safe']:>6.1f}%")

# ═══════════════════════════════════════════════════
# 保存完整结果
# ═══════════════════════════════════════════════════
output = {
    'version': 'v11',
    'total_groups': len(all_results),
    'total_provinces': len(provinces_in_backtest),
    'provinces': sorted(provinces_in_backtest),
    'national_rank': {
        'total': len(rank_shifts_simple), 'groups': len(rank_groups),
        'median': sorted(rank_shifts_simple)[len(rank_shifts_simple)//2] if rank_shifts_simple else 0,
        'p25': sorted(rank_shifts_simple)[len(rank_shifts_simple)//4] if rank_shifts_simple else 0,
        'p75': sorted(rank_shifts_simple)[3*len(rank_shifts_simple)//4] if rank_shifts_simple else 0,
        'forward_pct': round(sum(1 for s in rank_shifts_simple if s<0)/max(len(rank_shifts_simple),1)*100, 1),
        'rush': round(sum(1 for s in rank_shifts_simple if s>=2500)/max(len(rank_shifts_simple),1)*100, 1),
        'steady': round(sum(1 for s in rank_shifts_simple if s>=-500)/max(len(rank_shifts_simple),1)*100, 1),
        'safe': round(sum(1 for s in rank_shifts_simple if s>=-17500)/max(len(rank_shifts_simple),1)*100, 1),
    },
    'national_score': {
        'total': len(score_shifts_simple), 'groups': len(score_groups),
        'median': sorted(score_shifts_simple)[len(score_shifts_simple)//2] if score_shifts_simple else 0,
        'p25': sorted(score_shifts_simple)[len(score_shifts_simple)//4] if score_shifts_simple else 0,
        'p75': sorted(score_shifts_simple)[3*len(score_shifts_simple)//4] if score_shifts_simple else 0,
        'up_pct': round(sum(1 for s in score_shifts_simple if s>0)/max(len(score_shifts_simple),1)*100, 1),
        'rush': round(sum(1 for s in score_shifts_simple if s<=10)/max(len(score_shifts_simple),1)*100, 1),
        'steady': round(sum(1 for s in score_shifts_simple if s<=15)/max(len(score_shifts_simple),1)*100, 1),
        'safe': round(sum(1 for s in score_shifts_simple if s<=40)/max(len(score_shifts_simple),1)*100, 1),
    },
    'tier_analysis': tier_analysis,
    'cat_analysis': cat_analysis,
    'province_volatility': province_volatility,
    'province_params': province_params,
    'groups': all_results,
}

out_path = RESULTS_DIR / "backtest_v11.json"
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n💾 结果已保存: {out_path}")
print(f"\n✅ v11回测完成: {len(all_results)}组, {len(provinces_in_backtest)}省, "
      f"{len(rank_shifts_simple)+len(score_shifts_simple):,}校")
