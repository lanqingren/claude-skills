#!/usr/bin/env python3
"""
全国高考投档数据回测引擎 v13 — 正确处理v9数据结构
- v9数据: 每条记录含 year/school/score/category 字段
- 按年份拆分，跨年匹配同校同类别
- 处理科类映射: 文科→历史, 理科→物理
- 统一 v9 + OCR + API 数据源
"""
import os, json, re
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
V9_DIR = os.path.join(DATA_DIR, "province_v9")
API_DIR = os.path.join(DATA_DIR, "multi_province")
RESULT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(RESULT_DIR, exist_ok=True)

# Category mapping: old gaokao → new gaokao
CAT_MAP = {
    '文科': '历史', '理科': '物理',
    '历史': '历史', '物理': '物理', '综合': '综合',
}

def normalize_year(y):
    """统一年份为字符串"""
    return str(y).strip()

def normalize_category(cat):
    """统一科类"""
    if not cat:
        return '综合'
    cat = str(cat).strip()
    return CAT_MAP.get(cat, cat)

def load_v9_province(pname):
    """加载单个v9省份数据，返回 {(year, category): {school: min_score}}"""
    filepath = os.path.join(V9_DIR, f'{pname}_v9.json')
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        return None
    if not isinstance(data, list) or len(data) <= 5:
        return None
    
    # Group by (year, category) → school → min_score
    groups = defaultdict(lambda: defaultdict(lambda: 9999))
    for r in data:
        year = normalize_year(r.get('year', ''))
        cat = normalize_category(r.get('category', ''))
        school = r.get('school', r.get('name', ''))
        score = r.get('score', 0)
        
        if not year or not school or not score or score < 100:
            continue
        
        key = (year, cat)
        if score < groups[key][school]:
            groups[key][school] = score
    
    return dict(groups)

def load_ocr_province(pname):
    """加载OCR省份数据"""
    result = {}
    for f in os.listdir(V9_DIR):
        if f.startswith(f'{pname}_ocr_') and f.endswith('.json'):
            year = f.replace(f'{pname}_ocr_', '').replace('.json', '')
            filepath = os.path.join(V9_DIR, f)
            try:
                with open(filepath, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
            except:
                continue
            
            scores = {}
            for r in data:
                name = r.get('name', '')
                score = r.get('score', 0)
                # Filter noise
                if any(x in name for x in ['分以上', '分及以', '注：', '投档', '院校', '名称', '序号']):
                    continue
                if len(name) < 4 or score < 200 or score > 750:
                    continue
                name = re.sub(r'[\(（][\dQ\d]+[\)）]', '', name).strip()
                name = re.sub(r'^[\d\s]+', '', name).strip()
                if len(name) < 4:
                    continue
                if name not in scores or score < scores[name]:
                    scores[name] = score
            
            if scores:
                key = (year, '综合')
                result[key] = scores
    return result

def cross_year_shift(groups, year1='2023', year2='2024'):
    """计算跨年分数偏移，按科类分别计算"""
    results = []
    
    # Find matching categories across years
    cats1 = {cat for (y, cat) in groups.keys() if y == year1}
    cats2 = {cat for (y, cat) in groups.keys() if y == year2}
    common_cats = cats1 & cats2
    
    for cat in common_cats:
        key1 = (year1, cat)
        key2 = (year2, cat)
        if key1 not in groups or key2 not in groups:
            continue
        
        map1 = groups[key1]
        map2 = groups[key2]
        
        common_schools = set(map1.keys()) & set(map2.keys())
        if len(common_schools) < 3:
            continue
        
        for school in common_schools:
            s1 = map1[school]
            s2 = map2[school]
            if s1 > 0 and s2 > 0:
                results.append({
                    'school': school,
                    'category': cat,
                    'y1_score': s1,
                    'y2_score': s2,
                    'shift': s2 - s1,
                })
    
    return results

def calc_stats(shifts):
    """计算统计指标"""
    if not shifts:
        return None
    n = len(shifts)
    vals = sorted([s['shift'] for s in shifts])
    
    return {
        'total_schools': n,
        'median_shift': vals[n // 2],
        'p25_shift': vals[int(n * 0.25)],
        'p75_shift': vals[int(n * 0.75)],
        'iqr': vals[int(n * 0.75)] - vals[int(n * 0.25)],
        'up_pct': round(sum(1 for v in vals if v > 0) / n * 100, 1),
        'down_pct': round(sum(1 for v in vals if v < 0) / n * 100, 1),
        # 冲: student 0~10 above school Y1 → hits if shift <= student's advantage
        'chong_rate': round(sum(1 for v in vals if v <= 10) / n * 100, 1),
        # 稳: student 0~15 below school Y1 → hits if shift <= -15  
        'wen_rate': round(sum(1 for v in vals if v <= -15) / n * 100, 1),
        # 保: student 15~40 below school Y1 → hits if shift <= -40
        'bao_rate': round(sum(1 for v in vals if v <= -40) / n * 100, 1),
    }

# Province lists
ALL_PROVINCES = [
    '北京','天津','河北','山西','内蒙古','辽宁','吉林','黑龙江',
    '上海','江苏','浙江','安徽','福建','江西','山东',
    '河南','湖北','湖南','广东','广西','海南',
    '重庆','四川','贵州','云南','西藏','陕西','甘肃','青海','宁夏','新疆'
]

OCR_PROVINCES = ['上海', '天津']

# API province mapping
API_PROVINCES = {
    '北京_API': {'dir_name': '北京', 'year_field': 'year', 'score_field': 'min'},
    '广东_API': {'dir_name': '广东', 'year_field': 'year', 'score_field': 'min'},
}

def load_api_province(config):
    """加载API省份跨年数据"""
    dir_name = config['dir_name']
    score_field = config['score_field']
    groups = {}
    
    for f in os.listdir(API_DIR):
        if f.startswith(f'{dir_name}_') and f.endswith('_admission.json'):
            year = f.replace(f'{dir_name}_', '').replace('_admission.json', '')
            filepath = os.path.join(API_DIR, f)
            try:
                with open(filepath, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
            except:
                continue
            
            scores = defaultdict(lambda: 9999)
            for r in data:
                name = r.get('name', '')
                score = r.get(score_field, 0)
                if not score or score < 100:
                    score = r.get('filing', 0)
                if not score or score < 100:
                    continue
                if name and score < scores[name]:
                    scores[name] = score
            
            if scores:
                groups[(year, '综合')] = dict(scores)
    
    return groups

def main():
    results = {
        'version': 'v13',
        'description': '全国高考投档分数跨年回测（统一数据源）',
        'provinces': {},
        'national_summary': {},
        'data_sources': {'v9': 0, 'ocr': 0, 'api': 0},
    }
    
    all_shifts = []
    province_count = 0
    missing = []
    
    # === Process V9 provinces ===
    print("=" * 70)
    print("V9 Data Processing")
    print("=" * 70)
    
    for pname in ALL_PROVINCES:
        groups = load_v9_province(pname)
        if not groups:
            # Try OCR
            if pname in OCR_PROVINCES:
                groups = load_ocr_province(pname)
                if groups:
                    results['data_sources']['ocr'] += 1
            if not groups:
                missing.append(pname)
                continue
        
        shifts = cross_year_shift(groups)
        if not shifts or len(shifts) < 3:
            if pname not in OCR_PROVINCES:
                missing.append(pname)
            continue
        
        stats = calc_stats(shifts)
        if not stats:
            continue
        
        # Determine source
        source = 'ocr' if pname in OCR_PROVINCES and stats else 'v9'
        if source == 'v9':
            results['data_sources']['v9'] += 1
        else:
            results['data_sources']['ocr'] += 1
        
        results['provinces'][pname] = {
            'source': source,
            **stats
        }
        all_shifts.extend(shifts)
        province_count += 1
        
        print(f"  ✅ {pname:6s}: {stats['total_schools']:5d}校 | "
              f"偏移{stats['median_shift']:+4d} | IQR={stats['iqr']:3d} | "
              f"↑{stats['up_pct']:.0f}% | "
              f"冲{stats['chong_rate']:.0f}%/稳{stats['wen_rate']:.0f}%/保{stats['bao_rate']:.0f}%")
    
    # === Process API provinces ===
    print("\n" + "=" * 70)
    print("API Data Processing")
    print("=" * 70)
    
    for api_name, config in API_PROVINCES.items():
        groups = load_api_province(config)
        if not groups:
            continue
        
        # Process each year pair
        years = sorted(set(y for (y, c) in groups.keys()))
        for i in range(len(years) - 1):
            y1, y2 = years[i], years[i+1]
            shifts = cross_year_shift(groups, y1, y2)
            if not shifts or len(shifts) < 5:
                continue
            
            stats = calc_stats(shifts)
            if not stats:
                continue
            
            key = f"{api_name}_{y1}_{y2}"
            results['provinces'][key] = {'source': 'api', **stats}
            all_shifts.extend(shifts)
            province_count += 1
            results['data_sources']['api'] += 1
            
            print(f"  ✅ {key:20s}: {stats['total_schools']:5d}校 | "
                  f"偏移{stats['median_shift']:+4d} | IQR={stats['iqr']:3d} | "
                  f"冲{stats['chong_rate']:.0f}%/稳{stats['wen_rate']:.0f}%/保{stats['bao_rate']:.0f}%")
    
    # === National Summary ===
    print("\n" + "=" * 70)
    print("National Summary")
    print("=" * 70)
    
    if all_shifts:
        n = len(all_shifts)
        vals = sorted([s['shift'] for s in all_shifts])
        results['national_summary'] = {
            'total_province_groups': province_count,
            'total_schools': n,
            'median_shift': vals[n // 2],
            'p25_shift': vals[int(n * 0.25)],
            'p75_shift': vals[int(n * 0.75)],
            'iqr': vals[int(n * 0.75)] - vals[int(n * 0.25)],
            'up_pct': round(sum(1 for v in vals if v > 0) / n * 100, 1),
            'chong_rate': round(sum(1 for v in vals if v <= 10) / n * 100, 1),
            'wen_rate': round(sum(1 for v in vals if v <= -15) / n * 100, 1),
            'bao_rate': round(sum(1 for v in vals if v <= -40) / n * 100, 1),
        }
        
        s = results['national_summary']
        print(f"  省份组数: {s['total_province_groups']}")
        print(f"  总院校数: {s['total_schools']}")
        print(f"  中位偏移: {s['median_shift']:+d}分")
        print(f"  P25-P75: {s['p25_shift']:+d} ~ {s['p75_shift']:+d}分 (IQR={s['iqr']}分)")
        print(f"  上涨占比: {s['up_pct']}%")
        print(f"  冲: {s['chong_rate']}% / 稳: {s['wen_rate']}% / 保: {s['bao_rate']}%")
    
    # Missing provinces
    if missing:
        print(f"\n  ⚠️ 缺失省份: {', '.join(missing)}")
        results['missing_provinces'] = missing
    
    # Province ranking
    print("\n" + "=" * 70)
    print("Province Volatility Ranking (by IQR)")
    print("=" * 70)
    prov_list = sorted(results['provinces'].items(), 
                       key=lambda x: x[1]['iqr'], reverse=True)
    
    for i, (pname, stats) in enumerate(prov_list):
        tag = "🔴" if stats['iqr'] >= 30 else ("🟡" if stats['iqr'] >= 15 else "🟢")
        print(f"  {tag} {pname:20s}: IQR={stats['iqr']:3d} | 中位={stats['median_shift']:+4d} | "
              f"{stats['total_schools']:5d}校 | {stats['source']}")
    
    # Save
    outfile = os.path.join(RESULT_DIR, 'backtest_v13.json')
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved to {outfile} ({os.path.getsize(outfile):,} bytes)")
    
    return results

if __name__ == '__main__':
    main()
