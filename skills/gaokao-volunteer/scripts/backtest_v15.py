#!/usr/bin/env python3
"""
全国高考投档数据回测引擎 v15
- 修复OCR文件前缀匹配
- 修复综合→物理/历史科类映射（改革过渡省份）
- 修复命中率公式（≤10/≤15/≤40 分数；≥2500/≥-500/≥-17500 位次）
- OCR + v9 + API 多源融合
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
    """加载v9省份数据，返回 {year_cat: {school: {score, rank}}}"""
    fp = os.path.join(V9_DIR, f'{pname}_v9.json')
    if not os.path.exists(fp): return None
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except: return None
    if not isinstance(data, list) or len(data) <= 5: return None
    
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
    return dict(groups)

def merge_groups(groups):
    """标记改革过渡省份的综合数据，但不强行合并到物理/历史（分数不可比）"""
    # 综合和物理/历史分数体系不同，不能直接比较
    # 只做标记，不做合并
    return groups

def cross_year_backtest(groups, year1='2023', year2='2024'):
    score_shifts, rank_shifts = [], []
    cats1 = {k.split('_',1)[1] for k in groups if k.startswith(year1+'_')}
    cats2 = {k.split('_',1)[1] for k in groups if k.startswith(year2+'_')}
    common_cats = cats1 & cats2
    
    for cat in common_cats:
        k1, k2 = f'{year1}_{cat}', f'{year2}_{cat}'
        if k1 not in groups or k2 not in groups: continue
        schools = set(groups[k1].keys()) & set(groups[k2].keys())
        if len(schools) < 3: continue
        for s in schools:
            d1, d2 = groups[k1][s], groups[k2][s]
            if d1['score'] < 9000 and d2['score'] < 9000:
                score_shifts.append({'school': s, 'cat': cat,
                    's1': d1['score'], 's2': d2['score'], 'shift': d2['score'] - d1['score']})
            if d1['rank'] < 9999990 and d2['rank'] < 9999990:
                rank_shifts.append({'school': s, 'cat': cat,
                    'r1': d1['rank'], 'r2': d2['rank'], 'shift': d2['rank'] - d1['rank']})
    return score_shifts, rank_shifts

def calc_score(shifts):
    if not shifts or len(shifts) < 3: return None
    n = len(shifts)
    vals = sorted([s['shift'] for s in shifts])
    return {'mode':'score','total_schools':n,'median_shift':vals[n//2],
        'p25_shift':vals[int(n*0.25)],'p75_shift':vals[int(n*0.75)],
        'iqr':vals[int(n*0.75)]-vals[int(n*0.25)],
        'up_pct':round(sum(1 for v in vals if v>0)/n*100,1),
        'chong_rate':round(sum(1 for v in vals if v<=10)/n*100,1),
        'wen_rate':round(sum(1 for v in vals if v<=15)/n*100,1),
        'bao_rate':round(sum(1 for v in vals if v<=40)/n*100,1)}

def calc_rank(shifts):
    if not shifts or len(shifts) < 3: return None
    n = len(shifts)
    vals = sorted([s['shift'] for s in shifts])
    return {'mode':'rank','total_schools':n,'median_shift':vals[n//2],
        'p25_shift':vals[int(n*0.25)],'p75_shift':vals[int(n*0.75)],
        'iqr':vals[int(n*0.75)]-vals[int(n*0.25)],
        'forward_pct':round(sum(1 for v in vals if v<0)/n*100,1),
        'chong_rate':round(sum(1 for v in vals if v>=2500)/n*100,1),
        'wen_rate':round(sum(1 for v in vals if v>=-500)/n*100,1),
        'bao_rate':round(sum(1 for v in vals if v>=-17500)/n*100,1)}

_ocr_engine = None
def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine

def ocr_images(prefix):
    """OCR处理，prefix直接是文件名前缀如 'tianjin_2023'"""
    engine = get_ocr_engine()
    records = []
    files = sorted(glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.png')) +
                   glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.jpg')))
    
    for fp in files:
        result, _ = engine(fp)
        if not result: continue
        texts = [c[1].strip() for c in result]
        i = 0
        while i < len(texts):
            text = texts[i]
            cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            if cn >= 2 and len(text) >= 4:
                for j in range(i+1, min(i+4, len(texts))):
                    num = texts[j].replace(',', '').replace('，', '')
                    if re.match(r'^-?\d+$', num):
                        val = int(num)
                        if 200 <= val <= 750:
                            name = re.sub(r'[\(（][\dQ\d]+[\)）]', '', text).strip()
                            name = re.sub(r'^[\d\s]+', '', name).strip()
                            # Filter noise
                            if any(x in name for x in ['分以上','分及以','注：','投档','院校','名称','序号','合计','公示','选考','外语','语文','数学']):
                                break
                            if len(name) >= 4:
                                records.append({'name': name, 'score': val})
                                i = j + 1
                                break
                else:
                    i += 1
                continue
            i += 1
    seen = {}
    for r in records:
        if r['name'] not in seen or r['score'] < seen[r['name']]['score']:
            seen[r['name']] = r
    return list(seen.values())

def get_ocr_cached(prefix):
    """带缓存的OCR - 只用已有缓存，不触发新OCR（太慢）"""
    cache_file = os.path.join(V9_DIR, f'ocr_cache_{prefix}.json')
    # Also check old v14 format cache
    for cf in [cache_file]:
        if os.path.exists(cf) and os.path.getsize(cf) > 10:
            try:
                with open(cf, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                if d: return d
            except: pass
    # Try old v14 naming: ocr_cache_{pname}_{prefix}.json
    # e.g. ocr_cache_上海_shanghai_2023.json
    for f in os.listdir(V9_DIR):
        if f.startswith('ocr_cache_') and prefix in f and f.endswith('.json'):
            fp = os.path.join(V9_DIR, f)
            if os.path.getsize(fp) > 10:
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        d = json.load(fh)
                    if d: return d
                except: pass
    return []  # No cache, return empty

# OCR省份配置: {显示名: [(year, category, file_prefix)]}
OCR_CONFIG = {
    '上海': [('2023','综合','shanghai_2023'), ('2024','综合','shanghai_2024')],
    '天津': [('2023','综合','tianjin_2023'), ('2024','综合','tianjin_2024')],
    '福建': [('2023','物理','fujian_2023_wuli'), ('2023','历史','fujian_2023_lishi'),
             ('2024','物理','fujian_2024_wuli'), ('2024','历史','fujian_2024_lishi')],
    '安徽': [('2024','物理','anhui_2024_wuli'), ('2024','历史','anhui_2024_lishi')],
    '江西': [('2024','物理','jiangxi_2024_wuli'), ('2024','历史','jiangxi_2024_lishi')],
    '贵州': [('2024','物理','guizhou_2024_wuli'), ('2024','历史','guizhou_2024_lishi')],
}

ALL_PROVINCES = [
    '北京','天津','河北','山西','内蒙古','辽宁','吉林','黑龙江',
    '上海','江苏','浙江','安徽','福建','江西','山东',
    '河南','湖北','湖南','广东','广西','海南',
    '重庆','四川','贵州','云南','西藏','陕西','甘肃','青海','宁夏','新疆'
]

def main():
    results = {'version':'v15','description':'全国高考投档分数跨年回测',
               'provinces':{}, 'national_summary':{}}
    
    all_score_shifts, all_rank_shifts = [], []
    province_count = 0
    
    print("=" * 90)
    print("全国高考投档分数跨年回测 v15")
    print("=" * 90)
    
    for pname in ALL_PROVINCES:
        groups = load_v9_province(pname)
        v9_total = sum(len(v) for v in groups.values()) if groups else 0
        used_ocr = False
        
        # If v9 insufficient OR specific year_cat has too few records, supplement with OCR
        if pname in OCR_CONFIG:
            if not groups:
                # v9 has no data at all - use OCR entirely
                groups = {}
            for year, cat, prefix in OCR_CONFIG[pname]:
                key = f'{year}_{cat}'
                v9_count = len(groups.get(key, {}))
                if v9_count < 30:
                    records = get_ocr_cached(prefix)
                    if records:
                        if key not in groups:
                            groups[key] = {}
                        for r in records:
                            name = r['name']
                            score = r['score']
                            if name not in groups[key] or (isinstance(groups[key][name], dict) and score < groups[key][name]['score']):
                                groups[key][name] = {'score': score, 'rank': 9999999}
                            elif not isinstance(groups[key][name], dict):
                                if score < groups[key][name]:
                                    groups[key][name] = {'score': score, 'rank': 9999999}
                        used_ocr = True
                        new_count = len(groups[key])
                        if new_count > v9_count:
                            print(f"    ↳ {pname} {key}: OCR补充 {v9_count}→{new_count}校")
        
        if not groups:
            print(f"  ❌ {pname:6s}: 无数据")
            continue
        
        # Merge 综合 into 物理/历史 for transition provinces
        groups = merge_groups(groups)
        
        score_shifts, rank_shifts = cross_year_backtest(groups)
        has_score = len(score_shifts) >= 3
        has_rank = len(rank_shifts) >= 3
        
        if not has_score and not has_rank:
            years = sorted(set(k.split('_')[0] for k in groups.keys()))
            total_schools = sum(len(v) for v in groups.values())
            print(f"  ⚠️ {pname:6s}: {years} | {total_schools}校 | 无法跨年匹配")
            results['provinces'][pname] = {
                'source': 'ocr' if used_ocr else 'v9',
                'note': f'单年数据({",".join(years)})',
                'total_schools': total_schools, 'years': years
            }
            continue
        
        stats = calc_score(score_shifts) if has_score else calc_rank(rank_shifts)
        if not stats: continue
        
        source = 'ocr' if used_ocr else 'v9'
        results['provinces'][pname] = {'source': source, **stats}
        all_score_shifts.extend(score_shifts if has_score else [])
        all_rank_shifts.extend(rank_shifts if has_rank else [])
        province_count += 1
        
        sym = '📊' if has_score else '📍'
        cats = sorted(set(k.split('_',1)[1] for k in groups.keys()))
        print(f"  {sym} {pname:6s}: {stats['total_schools']:5d}校 | {','.join(cats):12s} | "
              f"偏移{stats['median_shift']:+5d} | IQR={stats['iqr']:4d} | "
              f"冲{stats['chong_rate']:4.0f}%/稳{stats['wen_rate']:4.0f}%/保{stats['bao_rate']:4.0f}% | {source}")
    
    # API Data
    print("\n" + "-" * 90)
    print("API Data")
    print("-" * 90)
    
    api_data = defaultdict(dict)  # {pname: {year: {school: {'score':x, 'rank':y}}}}
    for f in sorted(os.listdir(API_DIR)):
        if not f.endswith('_admission.json'): continue
        parts = f.replace('_admission.json', '').split('_')
        if len(parts) != 2: continue
        pname_api, year = parts
        fp = os.path.join(API_DIR, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            schools = {}
            for r in data:
                name = r.get('name', '')
                raw_score = r.get('min') or r.get('score') or r.get('filing') or 0
                raw_section = r.get('min_section') or 0
                cat = r.get('local_type_name', '综合')
                # 强制转数字，非数字跳过
                try:
                    score = int(raw_score) if raw_score else 0
                except (ValueError, TypeError):
                    score = 0
                try:
                    section = int(raw_section) if raw_section else 0
                except (ValueError, TypeError):
                    section = 0
                if name and score and score > 100:
                    if name not in schools:
                        schools[name] = {'score': score, 'rank': section if section > 0 else 9999999, 'cat': cat}
                    else:
                        if score < schools[name]['score']:
                            schools[name]['score'] = score
                        if section > 0 and section < schools[name]['rank']:
                            schools[name]['rank'] = section
            if schools: api_data[pname_api][year] = schools
        except: pass

    for pname_api, years_data in sorted(api_data.items()):
        sorted_years = sorted(years_data.keys())
        for i in range(len(sorted_years) - 1):
            y1, y2 = sorted_years[i], sorted_years[i+1]
            s1, s2 = years_data[y1], years_data[y2]
            common = set(s1.keys()) & set(s2.keys())
            if len(common) < 3: continue
            
            # Score backtest
            score_shifts = [{'school': n, 'cat': s1[n].get('cat','综合'),
                's1': s1[n]['score'], 's2': s2[n]['score'], 'shift': s2[n]['score'] - s1[n]['score']}
                for n in common if s1[n]['score'] < 9000 and s2[n]['score'] < 9000]
            
            # Rank backtest  
            rank_shifts = [{'school': n, 'cat': s1[n].get('cat','综合'),
                'r1': s1[n]['rank'], 'r2': s2[n]['rank'], 'shift': s2[n]['rank'] - s1[n]['rank']}
                for n in common if s1[n]['rank'] < 9999990 and s2[n]['rank'] < 9999990]
            # Score stats
            score_stats = calc_score(score_shifts) if len(score_shifts) >= 3 else None
            rank_stats = calc_rank(rank_shifts) if len(rank_shifts) >= 3 else None
            key = f'{pname_api}_API_{y1}_{y2}'
            
            if score_stats:
                results['provinces'][key] = {'source':'api', **score_stats}
                all_score_shifts.extend(score_shifts)
            if rank_stats:
                results['provinces'][f'{key}_RANK'] = {'source':'api', **rank_stats}
                all_rank_shifts.extend(rank_shifts)
            
            province_count += 1
            stats = score_stats or rank_stats
            if stats:
                extra = f" / 位次冲{rank_stats['chong_rate']:.0f}%/稳{rank_stats['wen_rate']:.0f}%/保{rank_stats['bao_rate']:.0f}%" if rank_stats else ""
                print(f"  📊 {key:25s}: {stats['total_schools']:5d}校 | 偏移{stats['median_shift']:+5d} | "
                      f"IQR={stats['iqr']:3d} | 冲{stats['chong_rate']:.0f}%/稳{stats['wen_rate']:.0f}%/保{stats['bao_rate']:.0f}%{extra}")
    
    # Student API Data (补充数据源)
    print("\n" + "-" * 90)
    print("Student API Data (补充)")
    print("-" * 90)
    
    for f in sorted(os.listdir(API_DIR)):
        if not f.startswith('student_') or not f.endswith('.json'): continue
        parts = f.replace('student_', '').replace('.json', '').split('_')
        if len(parts) != 2: continue
        pname_s, year = parts
        fp = os.path.join(API_DIR, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except: continue
        if not isinstance(data, list) or len(data) < 10: continue
        
        # Group by local_type_name
        groups_api = defaultdict(dict)
        for r in data:
            name = r.get('name', '')
            score = r.get('min') or r.get('filing') or 0
            if isinstance(score, str):
                try: score = int(score)
                except: score = 0
            cat = r.get('local_type_name', '综合')
            cat = nc(cat)
            if name and score and score > 100:
                key = f'{year}_{cat}'
                if name not in groups_api[key] or score < groups_api[key][name]['score']:
                    groups_api[key][name] = {'score': score, 'rank': 9999999}
        
        total = sum(len(v) for v in groups_api.values())
        if total < 10: continue
        
        # Check if this province already has good backtest data
        already = any(k.startswith(pname_s) and 'iqr' in v for k, v in results['provinces'].items())
        if already:
            print(f"  ⏭️ {pname_s} {year}: 已有更好数据 ({total}校)")
            continue
        
        # Save as single-year data for reference
        key = f'{pname_s}_student_{year}'
        if pname_s not in results['provinces'] or 'note' in results['provinces'].get(pname_s, {}):
            results['provinces'][key] = {
                'source': 'student_api',
                'note': f'单年数据({year})',
                'total_schools': total,
                'categories': sorted(set(k.split('_',1)[1] for k in groups_api.keys())),
            }
            print(f"  📝 {pname_s} {year}: {total}校 ({','.join(set(k.split('_',1)[1] for k in groups_api.keys()))})")
    
    # National Summary
    print("\n" + "=" * 90)
    print("全国汇总")
    print("=" * 90)
    
    if all_score_shifts:
        n = len(all_score_shifts)
        vals = sorted([s['shift'] for s in all_score_shifts])
        s = {'total_schools':n,'median_shift':vals[n//2],'p25_shift':vals[int(n*0.25)],
             'p75_shift':vals[int(n*0.75)],'iqr':vals[int(n*0.75)]-vals[int(n*0.25)],
             'up_pct':round(sum(1 for v in vals if v>0)/n*100,1),
             'chong_rate':round(sum(1 for v in vals if v<=10)/n*100,1),
             'wen_rate':round(sum(1 for v in vals if v<=15)/n*100,1),
             'bao_rate':round(sum(1 for v in vals if v<=40)/n*100,1)}
        results['national_summary']['score'] = s
        print(f"\n  📊 分数回测: {n:,}校 / {province_count}省组")
        print(f"     中位偏移 {s['median_shift']:+d}分 | P25-P75: {s['p25_shift']:+d}~{s['p75_shift']:+d} (IQR={s['iqr']})")
        print(f"     上涨 {s['up_pct']}% | 冲{s['chong_rate']}% / 稳{s['wen_rate']}% / 保{s['bao_rate']}%")
    
    if all_rank_shifts:
        n = len(all_rank_shifts)
        vals = sorted([s['shift'] for s in all_rank_shifts])
        s = {'total_schools':n,'median_shift':vals[n//2],'p25_shift':vals[int(n*0.25)],
             'p75_shift':vals[int(n*0.75)],'iqr':vals[int(n*0.75)]-vals[int(n*0.25)],
             'forward_pct':round(sum(1 for v in vals if v<0)/n*100,1),
             'chong_rate':round(sum(1 for v in vals if v>=2500)/n*100,1),
             'wen_rate':round(sum(1 for v in vals if v>=-500)/n*100,1),
             'bao_rate':round(sum(1 for v in vals if v>=-17500)/n*100,1)}
        results['national_summary']['rank'] = s
        print(f"\n  📍 位次回测: {n:,}校")
        print(f"     中位偏移 {s['median_shift']:+,}名 | P25-P75: {s['p25_shift']:+,}~{s['p75_shift']:+,}")
        print(f"     前移 {s['forward_pct']}% | 冲{s['chong_rate']}% / 稳{s['wen_rate']}% / 保{s['bao_rate']}%")
    
    results['national_summary']['total_province_groups'] = province_count
    
    # Volatility Ranking
    print("\n" + "-" * 90)
    print("省份波动排行")
    print("-" * 90)
    prov_list = [(k,v) for k,v in results['provinces'].items() if 'iqr' in v]
    prov_list.sort(key=lambda x: x[1]['iqr'], reverse=True)
    for pname, stats in prov_list:
        tag = "🔴" if stats['iqr']>=30 else ("🟡" if stats['iqr']>=15 else "🟢")
        print(f"  {tag} {pname:25s}: IQR={stats['iqr']:5d} | 中位={stats['median_shift']:+6d} | "
              f"{stats['total_schools']:5d}校 | {stats.get('source','?')}")
    
    # Coverage report
    covered = set()
    for k in results['provinces']:
        base = k.split('_API')[0]
        covered.add(base)
    missing = [p for p in ALL_PROVINCES if p not in covered]
    single_year = {k: v for k, v in results['provinces'].items() if 'note' in v}
    has_data = {k: v for k, v in results['provinces'].items() if 'iqr' in v}
    
    print(f"\n{'='*90}")
    print(f"覆盖报告: ✅{len(has_data)}省有跨年回测 | ⚠️{len(single_year)}省单年 | ❌{len(missing)}省无数据")
    if single_year:
        for k, v in single_year.items():
            print(f"  ⚠️ {k}: {v.get('note','')} ({v.get('total_schools',0)}校)")
    if missing:
        print(f"  ❌ 仍缺: {', '.join(missing)}")
    print(f"{'='*90}")
    
    outfile = os.path.join(RESULT_DIR, 'backtest_v15.json')
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved {outfile} ({os.path.getsize(outfile):,} bytes)")

if __name__ == '__main__':
    main()
