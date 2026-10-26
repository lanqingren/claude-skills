#!/usr/bin/env python3
"""
全国高考投档数据回测引擎 v14
- 修复命中率公式（≤10/≤15/≤40）
- 修复科类映射（文→历/理→物）
- OCR处理福建/安徽/江西/贵州 + 上海/天津
- 位次回测（山东等只有位次的省份）
- 全国覆盖最大化
"""
import os, json, re, glob
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
V9_DIR = os.path.join(DATA_DIR, "province_v9")
API_DIR = os.path.join(DATA_DIR, "multi_province")
OCR_DIR = os.path.join(DATA_DIR, "ocr_images")
RESULT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(RESULT_DIR, exist_ok=True)

CAT_MAP = {'文科': '历史', '理科': '物理', '历史': '历史', '物理': '物理', '综合': '综合'}

def ny(y): return str(y).strip()
def nc(c): return CAT_MAP.get(str(c or '').strip(), str(c or '综合').strip())

def load_v9_province(pname):
    """加载v9省份数据"""
    fp = os.path.join(V9_DIR, f'{pname}_v9.json')
    if not os.path.exists(fp): return None, None
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except: return None, None
    if not isinstance(data, list) or len(data) <= 5: return None, None
    
    # Build {year_cat: {school: {score: min, rank: min}}}
    groups = defaultdict(lambda: defaultdict(lambda: {'score': 9999, 'rank': 9999999}))
    for r in data:
        year = ny(r.get('year', ''))
        cat = nc(r.get('category', ''))
        school = r.get('school', r.get('name', ''))
        score = r.get('score') or 0
        rank = r.get('rank')
        
        if not year or not school: continue
        key = f'{year}_{cat}'
        if score and score > 100:
            groups[key][school]['score'] = min(groups[key][school]['score'], score)
        if rank and rank > 0:
            groups[key][school]['rank'] = min(groups[key][school]['rank'], rank)
    
    return dict(groups), data

def cross_year_backtest(groups, year1='2023', year2='2024'):
    """跨年回测，返回分数偏移和位次偏移"""
    score_shifts = []
    rank_shifts = []
    
    cats1 = {k.split('_',1)[1] for k in groups if k.startswith(year1+'_')}
    cats2 = {k.split('_',1)[1] for k in groups if k.startswith(year2+'_')}
    common_cats = cats1 & cats2
    
    for cat in common_cats:
        k1 = f'{year1}_{cat}'
        k2 = f'{year2}_{cat}'
        if k1 not in groups or k2 not in groups: continue
        
        schools = set(groups[k1].keys()) & set(groups[k2].keys())
        if len(schools) < 3: continue
        
        for s in schools:
            d1 = groups[k1][s]
            d2 = groups[k2][s]
            if d1['score'] < 9000 and d2['score'] < 9000:
                score_shifts.append({
                    'school': s, 'cat': cat,
                    's1': d1['score'], 's2': d2['score'],
                    'shift': d2['score'] - d1['score']
                })
            if d1['rank'] < 9999990 and d2['rank'] < 9999990:
                rank_shifts.append({
                    'school': s, 'cat': cat,
                    'r1': d1['rank'], 'r2': d2['rank'],
                    'shift': d2['rank'] - d1['rank']
                })
    
    return score_shifts, rank_shifts

def calc_stats_score(shifts):
    """分数模式统计 — 正确公式: 冲≤10/稳≤15/保≤40"""
    if not shifts or len(shifts) < 3: return None
    n = len(shifts)
    vals = sorted([s['shift'] for s in shifts])
    return {
        'mode': 'score', 'total_schools': n,
        'median_shift': vals[n // 2],
        'p25_shift': vals[int(n * 0.25)],
        'p75_shift': vals[int(n * 0.75)],
        'iqr': vals[int(n * 0.75)] - vals[int(n * 0.25)],
        'up_pct': round(sum(1 for v in vals if v > 0) / n * 100, 1),
        'chong_rate': round(sum(1 for v in vals if v <= 10) / n * 100, 1),
        'wen_rate': round(sum(1 for v in vals if v <= 15) / n * 100, 1),
        'bao_rate': round(sum(1 for v in vals if v <= 40) / n * 100, 1),
    }

def calc_stats_rank(shifts):
    """位次模式统计 — 正确公式: 冲≥2500/稳≥-500/保≥-17500"""
    if not shifts or len(shifts) < 3: return None
    n = len(shifts)
    vals = sorted([s['shift'] for s in shifts])
    return {
        'mode': 'rank', 'total_schools': n,
        'median_shift': vals[n // 2],
        'p25_shift': vals[int(n * 0.25)],
        'p75_shift': vals[int(n * 0.75)],
        'iqr': vals[int(n * 0.75)] - vals[int(n * 0.25)],
        'forward_pct': round(sum(1 for v in vals if v < 0) / n * 100, 1),
        'chong_rate': round(sum(1 for v in vals if v >= 2500) / n * 100, 1),
        'wen_rate': round(sum(1 for v in vals if v >= -500) / n * 100, 1),
        'bao_rate': round(sum(1 for v in vals if v >= -17500) / n * 100, 1),
    }

def ocr_images_for_prefix(prefix):
    """OCR处理指定前缀的所有图片，返回学校列表"""
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    records = []
    files = sorted(glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.png')) + 
                   glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.jpg')))
    
    for fp in files:
        result, _ = engine(fp)
        if not result: continue
        texts = [c[1].strip() for c in result]
        
        # Find Chinese school name + following score
        i = 0
        while i < len(texts):
            text = texts[i]
            cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            if cn >= 2 and len(text) >= 4:
                # Look for score in next few items
                for j in range(i+1, min(i+4, len(texts))):
                    num = texts[j].replace(',', '').replace('，', '')
                    if re.match(r'^-?\d+$', num):
                        val = int(num)
                        if 200 <= val <= 750:
                            name = re.sub(r'[\(（][\dQ\d]+[\)）]', '', text).strip()
                            name = re.sub(r'^[\d\s]+', '', name).strip()
                            if len(name) >= 4:
                                records.append({'name': name, 'score': val})
                                i = j + 1
                                break
                else:
                    i += 1
                continue
            i += 1
    
    # Deduplicate, keep min score
    seen = {}
    for r in records:
        if r['name'] not in seen or r['score'] < seen[r['name']]['score']:
            seen[r['name']] = r
    return list(seen.values())

def get_ocr_data(province_prefix, category):
    """获取OCR处理后的数据"""
    cache_key = f'{province_prefix}_{category}'
    cache_file = os.path.join(V9_DIR, f'ocr_cache_{cache_key}.json')
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    
    result = ocr_images_for_prefix(cache_key)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result

def main():
    results = {
        'version': 'v14',
        'description': '全国高考投档分数跨年回测（修复版）',
        'provinces': {},
        'national_summary': {},
    }
    
    all_score_shifts = []
    all_rank_shifts = []
    province_count = 0
    
    ALL_PROVINCES = [
        '北京','天津','河北','山西','内蒙古','辽宁','吉林','黑龙江',
        '上海','江苏','浙江','安徽','福建','江西','山东',
        '河南','湖北','湖南','广东','广西','海南',
        '重庆','四川','贵州','云南','西藏','陕西','甘肃','青海','宁夏','新疆'
    ]
    
    # OCR省份映射: {显示名: [(year, category, file_prefix)]}
    OCR_CONFIG = {
        '上海': [('2023','综合','shanghai_2023'), ('2024','综合','shanghai_2024')],
        '天津': [('2023','综合','tianjin_2023'), ('2024','综合','tianjin_2024')],
        '福建': [
            ('2023','物理','fujian_2023_wuli'), ('2023','历史','fujian_2023_lishi'),
            ('2024','物理','fujian_2024_wuli'), ('2024','历史','fujian_2024_lishi'),
        ],
        '安徽': [('2024','物理','anhui_2024_wuli'), ('2024','历史','anhui_2024_lishi')],
        '江西': [('2024','物理','jiangxi_2024_wuli'), ('2024','历史','jiangxi_2024_lishi')],
        '贵州': [('2024','物理','guizhou_2024_wuli'), ('2024','历史','guizhou_2024_lishi')],
    }
    
    print("=" * 80)
    print("V9 Data Processing")
    print("=" * 80)
    
    for pname in ALL_PROVINCES:
        groups, raw_data = load_v9_province(pname)
        
        # If v9 has insufficient data, try OCR
        if not groups or sum(len(v) for v in groups.values()) < 20:
            if pname in OCR_CONFIG:
                groups = {}
                for year, cat, prefix in OCR_CONFIG[pname]:
                    records = get_ocr_data(pname.lower(), prefix)
                    if records:
                        key = f'{year}_{cat}'
                        groups[key] = {}
                        for r in records:
                            name = r['name']
                            score = r['score']
                            # Filter noise
                            if any(x in name for x in ['分以上','分及以','注：','投档','院校','名称','序号','合计']):
                                continue
                            if len(name) < 4 or score < 200:
                                continue
                            if name not in groups[key] or score < groups[key][name]:
                                groups[key][name] = score
        
        if not groups:
            print(f"  ❌ {pname}: 无数据")
            continue
        
        score_shifts, rank_shifts = cross_year_backtest(groups)
        
        # Prefer score data; use rank if no score
        has_score = len(score_shifts) >= 3
        has_rank = len(rank_shifts) >= 3
        
        if not has_score and not has_rank:
            # Maybe only 1 year of data
            years = set(k.split('_')[0] for k in groups.keys())
            print(f"  ⚠️ {pname}: 仅有 {years} 数据, 无法跨年")
            results['provinces'][pname] = {
                'source': 'ocr' if pname in OCR_CONFIG else 'v9',
                'note': f'仅有 {sorted(years)} 年数据',
                'total_schools': sum(len(v) for v in groups.values()),
                'years': sorted(list(years)),
            }
            continue
        
        stats = calc_stats_score(score_shifts) if has_score else calc_stats_rank(rank_shifts)
        if not stats: continue
        
        source = 'ocr' if pname in OCR_CONFIG and not has_score else 'v9'
        # Override: if we used OCR data for this province
        if pname in OCR_CONFIG and has_score:
            # Check if v9 originally had data
            v9_groups, _ = load_v9_province(pname)
            if not v9_groups or sum(len(v) for v in v9_groups.values()) < 20:
                source = 'ocr'
        
        results['provinces'][pname] = {'source': source, **stats}
        
        if has_score:
            all_score_shifts.extend(score_shifts)
        if has_rank:
            all_rank_shifts.extend(rank_shifts)
        province_count += 1
        
        sym = '📊' if has_score else '📍'
        cats = sorted(set(k.split('_',1)[1] for k in groups.keys()))
        print(f"  {sym} {pname:6s}: {stats['total_schools']:5d}校 | {','.join(cats):8s} | "
              f"偏移{stats['median_shift']:+5d} | IQR={stats['iqr']:3d} | "
              f"冲{stats['chong_rate']:.0f}%/稳{stats['wen_rate']:.0f}%/保{stats['bao_rate']:.0f}%")
    
    # API provinces
    print("\n" + "=" * 80)
    print("API Data Processing")
    print("=" * 80)
    
    for f in sorted(os.listdir(API_DIR)):
        if not f.endswith('_admission.json'): continue
        parts = f.replace('_admission.json', '').split('_')
        if len(parts) != 2: continue
        pname_api, year = parts
        # Will be processed below
    
    # Load API data grouped
    api_data = defaultdict(dict)
    for f in sorted(os.listdir(API_DIR)):
        if not f.endswith('_admission.json'): continue
        parts = f.replace('_admission.json', '').split('_')
        if len(parts) != 2: continue
        pname_api, year = parts
        fp = os.path.join(API_DIR, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            if isinstance(data, list) and len(data) > 5:
                scores = {}
                for r in data:
                    name = r.get('name', '')
                    score = r.get('min') or r.get('score') or 0
                    if name and score and score > 100:
                        if name not in scores or score < scores[name]:
                            scores[name] = score
                if scores:
                    api_data[pname_api][year] = scores
        except: pass
    
    for pname_api, years_data in sorted(api_data.items()):
        sorted_years = sorted(years_data.keys())
        for i in range(len(sorted_years) - 1):
            y1, y2 = sorted_years[i], sorted_years[i+1]
            m1, m2 = years_data[y1], years_data[y2]
            common = set(m1.keys()) & set(m2.keys())
            if len(common) < 5: continue
            
            shifts = [{'school': s, 's1': m1[s], 's2': m2[s], 'shift': m2[s] - m1[s], 'cat': '综合'}
                      for s in common]
            stats = calc_stats_score(shifts)
            if not stats: continue
            
            key = f'{pname_api}_API_{y1}_{y2}'
            results['provinces'][key] = {'source': 'api', **stats}
            all_score_shifts.extend(shifts)
            province_count += 1
            print(f"  📊 {key:25s}: {stats['total_schools']:5d}校 | "
                  f"偏移{stats['median_shift']:+5d} | IQR={stats['iqr']:3d} | "
                  f"冲{stats['chong_rate']:.0f}%/稳{stats['wen_rate']:.0f}%/保{stats['bao_rate']:.0f}%")
    
    # National Summary
    print("\n" + "=" * 80)
    print("National Summary")
    print("=" * 80)
    
    if all_score_shifts:
        n = len(all_score_shifts)
        vals = sorted([s['shift'] for s in all_score_shifts])
        score_summary = {
            'total_schools': n,
            'median_shift': vals[n // 2],
            'p25_shift': vals[int(n * 0.25)],
            'p75_shift': vals[int(n * 0.75)],
            'iqr': vals[int(n * 0.75)] - vals[int(n * 0.25)],
            'up_pct': round(sum(1 for v in vals if v > 0) / n * 100, 1),
            'chong_rate': round(sum(1 for v in vals if v <= 10) / n * 100, 1),
            'wen_rate': round(sum(1 for v in vals if v <= 15) / n * 100, 1),
            'bao_rate': round(sum(1 for v in vals if v <= 40) / n * 100, 1),
        }
        results['national_summary']['score'] = score_summary
        s = score_summary
        print(f"\n  📊 分数回测 ({n:,}校, {province_count}省组)")
        print(f"     中位偏移: {s['median_shift']:+d}分 | P25-P75: {s['p25_shift']:+d}~{s['p75_shift']:+d} (IQR={s['iqr']})")
        print(f"     上涨: {s['up_pct']}% | 冲: {s['chong_rate']}% / 稳: {s['wen_rate']}% / 保: {s['bao_rate']}%")
    
    if all_rank_shifts:
        n = len(all_rank_shifts)
        vals = sorted([s['shift'] for s in all_rank_shifts])
        rank_summary = {
            'total_schools': n,
            'median_shift': vals[n // 2],
            'p25_shift': vals[int(n * 0.25)],
            'p75_shift': vals[int(n * 0.75)],
            'iqr': vals[int(n * 0.75)] - vals[int(n * 0.25)],
            'forward_pct': round(sum(1 for v in vals if v < 0) / n * 100, 1),
            'chong_rate': round(sum(1 for v in vals if v >= 2500) / n * 100, 1),
            'wen_rate': round(sum(1 for v in vals if v >= -500) / n * 100, 1),
            'bao_rate': round(sum(1 for v in vals if v >= -17500) / n * 100, 1),
        }
        results['national_summary']['rank'] = rank_summary
        s = rank_summary
        print(f"\n  📍 位次回测 ({n:,}校)")
        print(f"     中位偏移: {s['median_shift']:+,}名 | P25-P75: {s['p25_shift']:+,}~{s['p75_shift']:+,}")
        print(f"     前移: {s['forward_pct']}% | 冲: {s['chong_rate']}% / 稳: {s['wen_rate']}% / 保: {s['bao_rate']}%")
    
    results['national_summary']['total_province_groups'] = province_count
    
    # Volatility Ranking
    print("\n" + "=" * 80)
    print("Province Volatility Ranking")
    print("=" * 80)
    prov_list = [(k, v) for k, v in results['provinces'].items() if 'iqr' in v]
    prov_list.sort(key=lambda x: x[1]['iqr'], reverse=True)
    
    for pname, stats in prov_list:
        tag = "🔴" if stats['iqr'] >= 30 else ("🟡" if stats['iqr'] >= 15 else "🟢")
        mode = stats.get('mode', 'score')
        print(f"  {tag} {pname:25s}: IQR={stats['iqr']:3d} | 中位={stats['median_shift']:+5d} | "
              f"{stats['total_schools']:5d}校 | {stats.get('source','?')}")
    
    # Missing provinces
    covered = set(k.split('_API')[0] for k in results['provinces'].keys())
    missing = [p for p in ALL_PROVINCES if p not in covered]
    if missing:
        print(f"\n  ⚠️ 仍缺: {', '.join(missing)}")
        results['missing_provinces'] = missing
    
    # Save
    outfile = os.path.join(RESULT_DIR, 'backtest_v14.json')
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved {outfile} ({os.path.getsize(outfile):,} bytes)")
    
    return results

if __name__ == '__main__':
    main()
