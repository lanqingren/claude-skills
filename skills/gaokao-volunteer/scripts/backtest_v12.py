#!/usr/bin/env python3
"""
高考志愿回测引擎 v12 — 五维度扩展分析
1. 大小年检测（3年趋势反弹分析）
2. 新高考vs老高考省份波动对比
3. 省内外院校波动差异
4. 专业组级别波动分析
5. 2024→2025跨年验证（如果2025数据可用）
"""
import json, os, sys, math
from collections import defaultdict, Counter
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
V9_DIR = os.path.join(DATA_DIR, "province_v9")
API_DIR = os.path.join(DATA_DIR, "multi_province")
RESULT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(RESULT_DIR, exist_ok=True)

# ============================================================
# 数据加载
# ============================================================
def load_v9():
    """加载province_v9数据，按省份→年份组织"""
    prov_data = {}
    for f in sorted(os.listdir(V9_DIR)):
        if not f.endswith('_v9.json'): continue
        prov = f.replace('_v9.json', '')
        records = json.load(open(os.path.join(V9_DIR, f), encoding='utf-8'))
        if not records: continue
        prov_data[prov] = records
    return prov_data

def load_school_list():
    """加载院校基础信息"""
    return json.load(open(os.path.join(DATA_DIR, 'school_list.json'), encoding='utf-8'))

def load_api(prov, year):
    """加载API数据"""
    path = os.path.join(API_DIR, f'{prov}_{year}_admission.json')
    if not os.path.exists(path): return None
    return json.load(open(path, encoding='utf-8'))

def get_school_province_map(school_list):
    """构建 院校名→省份 映射"""
    return {s['name']: s.get('province_name', '') for s in school_list}

def classify_school(school_name, school_map):
    """获取院校所在省份"""
    return school_map.get(school_name, '未知')

def get_tier(school_name, school_list_map):
    """获取院校层次"""
    info = school_list_map.get(school_name)
    if not info: return '其他'
    if info.get('f985') == '1': return '985'
    if info.get('f211') == '1': return '211'
    if info.get('dual_class_name') == '双一流': return '双一流'
    if info.get('nature_name') == '民办': return '民办'
    return '公办普通'

# ============================================================
# 维度1: 大小年检测
# ============================================================
def analyze_size_year(school_list):
    """分析连续3年位次方向变化，识别大小年模式"""
    print("\n" + "="*60)
    print("📊 维度1: 大小年检测（3年趋势分析）")
    print("="*60)

    results = {'available': False, 'provinces_analyzed': [], 'summary': {}}

    # 广东有2022/2023/2024三年API数据
    api_3year = {}
    for prov in ['广东']:
        data_by_year = {}
        for year in [2022, 2023, 2024]:
            data = load_api(prov, year)
            if data:
                data_by_year[year] = data
        if len(data_by_year) >= 3:
            api_3year[prov] = data_by_year

    # 也检查v9数据是否有连续3年的省份（目前只有2年）
    # 如果2025数据可用，则可以用v9+2025构成3年

    if not api_3year:
        print("  ⚠️ 缺少3年连续数据，尝试使用v9数据的2年变化方向分析")
        # 使用v9数据做2年代理分析
        v9_data = load_v9()
        school_map = {s['name']: s for s in school_list}

        shift_patterns = []
        for prov, records in v9_data.items():
            by_year_school = defaultdict(dict)
            for r in records:
                if not r.get('score'): continue
                key = r['school']
                by_year_school[key][r['year']] = r['score']

            for school, years in by_year_school.items():
                if '2023' in years and '2024' in years:
                    shift = years['2024'] - years['2023']
                    shift_patterns.append({
                        'province': prov,
                        'school': school,
                        'score_2023': years['2023'],
                        'score_2024': years['2024'],
                        'shift': shift,
                        'tier': get_tier(school, school_map),
                    })

        # 分析shift分布
        all_shifts = [p['shift'] for p in shift_patterns]
        if all_shifts:
            n = len(all_shifts)
            mean_shift = sum(all_shifts) / n
            sorted_shifts = sorted(all_shifts)
            median = sorted_shifts[n // 2]
            q1 = sorted_shifts[n // 4]
            q3 = sorted_shifts[(3 * n) // 4]
            iqr = q3 - q1
            # 大幅波动 = 超出IQR范围1.5倍
            big_up = sum(1 for s in all_shifts if s > q3 + 1.5 * iqr)
            big_down = sum(1 for s in all_shifts if s < q1 - 1.5 * iqr)

            results['available'] = True
            results['mode'] = '2year_proxy'
            results['summary'] = {
                'total_schools': n,
                'mean_shift': round(mean_shift, 1),
                'median_shift': median,
                'iqr': iqr,
                'q1': q1, 'q3': q3,
                'big_up_count': big_up,
                'big_down_count': big_down,
                'big_up_pct': round(big_up / n * 100, 1),
                'big_down_pct': round(big_down / n * 100, 1),
            }
            print(f"  分析学校数: {n}")
            print(f"  平均shift: {mean_shift:.1f}分, 中位数: {median}分")
            print(f"  IQR: [{q1}, {q3}] = {iqr}分")
            print(f"  大幅上涨(>+1.5IQR): {big_up}所 ({big_up/n*100:.1f}%)")
            print(f"  大幅下跌(<-1.5IQR): {big_down}所 ({big_down/n*100:.1f}%)")

            # 按层次分析大幅波动
            tier_shifts = defaultdict(list)
            for p in shift_patterns:
                tier_shifts[p['tier']].append(p['shift'])

            tier_volatility = {}
            for tier, shifts in sorted(tier_shifts.items()):
                if len(shifts) < 10: continue
                t_sorted = sorted(shifts)
                tn = len(t_sorted)
                t_iqr = t_sorted[3*tn//4] - t_sorted[tn//4]
                # 波动系数 = IQR / 中位数
                t_med = t_sorted[tn//2]
                cv = t_iqr / abs(t_med) * 100 if t_med else 0
                tier_volatility[tier] = {
                    'count': tn,
                    'median_shift': t_med,
                    'iqr': t_iqr,
                    'volatility_cv': round(cv, 1),
                }
                print(f"  [{tier}] {tn}所, 中位shift={t_med}, IQR={t_iqr}, 波动系数={cv:.1f}%")
            results['tier_volatility'] = tier_volatility

        return results

    # 有3年API数据 — 真正的大小年分析
    for prov, data_by_year in api_3year.items():
        print(f"\n  📈 {prov} 3年数据 ({sorted(data_by_year.keys())})")

        # 按学校+专业组建表
        school_year_rank = defaultdict(dict)
        school_year_score = defaultdict(dict)

        for year, records in data_by_year.items():
            for r in records:
                name = r.get('name', '')
                sg = r.get('sg_name', '')
                key = f"{name}{sg}" if sg else name
                rank = r.get('min_section', None)
                score = r.get('min', None)
                if rank and str(rank).isdigit():
                    school_year_rank[key][year] = int(rank)
                if score and str(score).isdigit():
                    school_year_score[key][year] = int(score)

        # 找有3年数据的学校
        zigzag_schools = []
        monotone_schools = []
        stable_schools = []
        total_3year = 0

        for key, year_ranks in school_year_rank.items():
            years_sorted = sorted(year_ranks.keys())
            if len(years_sorted) < 3: continue
            total_3year += 1

            y1, y2, y3 = years_sorted[-3], years_sorted[-2], years_sorted[-1]
            r1, r2, r3 = year_ranks[y1], year_ranks[y2], year_ranks[y3]

            # 方向：位次下降=分数上涨（好），位次上升=分数下降（差）
            d1 = r2 - r1  # y1→y2 变化
            d2 = r3 - r2  # y2→y3 变化

            # 大小年 = 方向反转且幅度显著
            threshold = 500  # 位次变化>500名算显著
            if d1 * d2 < 0 and (abs(d1) > threshold or abs(d2) > threshold):
                zigzag_schools.append({
                    'school': key, 'years': [y1, y2, y3],
                    'ranks': [r1, r2, r3],
                    'directions': [d1, d2],
                })
            elif d1 * d2 > 0 and (abs(d1) > threshold or abs(d2) > threshold):
                monotone_schools.append({
                    'school': key, 'years': [y1, y2, y3],
                    'ranks': [r1, r2, r3],
                })
            else:
                stable_schools.append({
                    'school': key, 'ranks': [r1, r2, r3],
                })

        zigzag_pct = len(zigzag_schools) / total_3year * 100 if total_3year else 0
        monotone_pct = len(monotone_schools) / total_3year * 100 if total_3year else 0
        stable_pct = len(stable_schools) / total_3year * 100 if total_3year else 0

        results['available'] = True
        results['mode'] = '3year_zigzag'
        results['provinces_analyzed'].append({
            'province': prov,
            'years': sorted(data_by_year.keys()),
            'total_3year_schools': total_3year,
            'zigzag': len(zigzag_schools),
            'zigzag_pct': round(zigzag_pct, 1),
            'monotone': len(monotone_schools),
            'monotone_pct': round(monotone_pct, 1),
            'stable': len(stable_schools),
            'stable_pct': round(stable_pct, 1),
            'zigzag_examples': zigzag_schools[:10],
        })

        print(f"  3年连续数据学校: {total_3year}")
        print(f"  🔀 大小年(方向反转): {len(zigzag_schools)} ({zigzag_pct:.1f}%)")
        print(f"  📈 单调趋势: {len(monotone_schools)} ({monotone_pct:.1f}%)")
        print(f"  ➖ 稳定: {len(stable_schools)} ({stable_pct:.1f}%)")
        if zigzag_schools:
            print(f"\n  大小年典型案例:")
            for z in zigzag_schools[:5]:
                d1_str = f"↑{-z['directions'][0]}" if z['directions'][0] < 0 else f"↓{z['directions'][0]}"
                d2_str = f"↑{-z['directions'][1]}" if z['directions'][1] < 0 else f"↓{z['directions'][1]}"
                print(f"    {z['school']}: {z['ranks']} → {d1_str}→{d2_str}")

    return results


# ============================================================
# 维度2: 新高考vs老高考波动对比
# ============================================================
def analyze_reform_vs_traditional(prov_data):
    """对比新高考(物理/历史) vs 老高考(文/理) vs 综合 的波动差异"""
    print("\n" + "="*60)
    print("📊 维度2: 新高考 vs 老高考 波动对比")
    print("="*60)

    # 分类省份
    reform_312 = []  # 3+1+2 物理/历史
    reform_33 = []   # 3+3 综合
    traditional = [] # 文/理科

    for prov, records in prov_data.items():
        cats = set(r.get('category', '') for r in records)
        if '物理' in cats or '历史' in cats:
            reform_312.append(prov)
        elif '综合' in cats:
            reform_33.append(prov)
        elif '理科' in cats or '文科' in cats:
            traditional.append(prov)

    print(f"  新高考3+1+2 (物理/历史): {reform_312}")
    print(f"  新高考3+3 (综合): {reform_33}")
    print(f"  老高考 (文/理): {traditional}")

    def calc_group_shifts(provinces, label):
        """计算一组省份的院校分数shift"""
        shifts = []
        for prov in provinces:
            records = prov_data.get(prov, [])
            by_year_school = defaultdict(dict)
            for r in records:
                if not r.get('score'): continue
                by_year_school[r['school']][r['year']] = r['score']

            for school, years in by_year_school.items():
                if '2023' in years and '2024' in years:
                    shifts.append(years['2024'] - years['2023'])

        if not shifts:
            return None

        shifts.sort()
        n = len(shifts)
        mean = sum(shifts) / n
        median = shifts[n // 2]
        q1 = shifts[n // 4]
        q3 = shifts[3 * n // 4]
        iqr = q3 - q1
        std = math.sqrt(sum((s - mean) ** 2 for s in shifts) / n)

        result = {
            'label': label,
            'provinces': provinces,
            'school_count': n,
            'mean': round(mean, 1),
            'median': median,
            'std': round(std, 1),
            'q1': q1, 'q3': q3,
            'iqr': iqr,
        }
        print(f"\n  [{label}] {n}所院校")
        print(f"    平均shift: {mean:.1f}, 中位数: {median}, σ={std:.1f}")
        print(f"    IQR: [{q1}, {q3}] = {iqr}")
        return result

    results = {
        'reform_312': calc_group_shifts(reform_312, '新高考3+1+2(物理/历史)'),
        'reform_33': calc_group_shifts(reform_33, '新高考3+3(综合)'),
        'traditional': calc_group_shifts(traditional, '老高考(文/理)'),
    }

    # 对比分析
    if results['reform_312'] and results['traditional']:
        r = results['reform_312']
        t = results['traditional']
        print(f"\n  📊 对比: 新高考3+1+2 vs 老高考")
        print(f"    波动(IQR): {r['iqr']} vs {t['iqr']}")
        print(f"    标准差: {r['std']} vs {t['std']}")
        ratio = r['iqr'] / t['iqr'] if t['iqr'] else 0
        print(f"    IQR比: {ratio:.2f}x")
        results['comparison'] = {
            'iqr_ratio_312_vs_trad': round(ratio, 2),
            'std_ratio_312_vs_trad': round(r['std'] / t['std'], 2) if t['std'] else 0,
        }

    return results


# ============================================================
# 维度3: 省内外院校波动差异
# ============================================================
def analyze_local_vs_remote(prov_data, school_list):
    """对比本省院校 vs 外省院校的波动差异"""
    print("\n" + "="*60)
    print("📊 维度3: 省内外院校波动差异")
    print("="*60)

    school_map = {s['name']: s for s in school_list}

    local_shifts = []
    remote_shifts = []
    prov_results = []

    for prov, records in prov_data.items():
        if not records: continue
        by_year_school = defaultdict(dict)
        for r in records:
            if not r.get('score'): continue
            by_year_school[r['school']][r['year']] = r['score']

        local_p = []
        remote_p = []
        for school, years in by_year_school.items():
            if '2023' not in years or '2024' not in years: continue
            shift = years['2024'] - years['2023']
            school_prov = school_map.get(school, {}).get('province_name', '未知')
            if school_prov == prov:
                local_p.append(shift)
            else:
                remote_p.append(shift)

        local_shifts.extend(local_p)
        remote_shifts.extend(remote_p)

        if local_p or remote_p:
            def stats(lst):
                if not lst: return None
                lst.sort()
                n = len(lst)
                return {
                    'count': n,
                    'median': lst[n//2],
                    'iqr': lst[3*n//4] - lst[n//4],
                    'mean': round(sum(lst)/n, 1),
                }
            prov_results.append({
                'province': prov,
                'local': stats(local_p),
                'remote': stats(remote_p),
            })

    def group_stats(shifts, label):
        if not shifts: return None
        shifts.sort()
        n = len(shifts)
        mean = sum(shifts) / n
        std = math.sqrt(sum((s - mean)**2 for s in shifts) / n)
        result = {
            'label': label, 'count': n,
            'mean': round(mean, 1),
            'median': shifts[n//2],
            'std': round(std, 1),
            'q1': shifts[n//4], 'q3': shifts[3*n//4],
            'iqr': shifts[3*n//4] - shifts[n//4],
        }
        print(f"  [{label}] {n}所: mean={mean:.1f} median={result['median']} σ={std:.1f} IQR={result['iqr']}")
        return result

    print()
    local_result = group_stats(local_shifts, '本省院校')
    remote_result = group_stats(remote_shifts, '外省院校')

    comparison = {}
    if local_result and remote_result:
        ratio = remote_result['iqr'] / local_result['iqr'] if local_result['iqr'] else 0
        std_ratio = remote_result['std'] / local_result['std'] if local_result['std'] else 0
        comparison = {
            'iqr_ratio': round(ratio, 2),
            'std_ratio': round(std_ratio, 2),
            'finding': '',
        }
        if ratio > 1.2:
            comparison['finding'] = f'外省院校波动比本省大{ratio:.1f}倍'
        elif ratio < 0.8:
            comparison['finding'] = f'本省院校波动比外省大{1/ratio:.1f}倍'
        else:
            comparison['finding'] = '省内外波动差异不大'
        print(f"\n  📊 IQR比(外/本): {ratio:.2f}x, σ比: {std_ratio:.2f}x")
        print(f"  💡 {comparison['finding']}")

    # 省份明细 top5
    print(f"\n  省份明细:")
    for pr in sorted(prov_results, key=lambda x: -(x['local']['iqr'] if x['local'] else 0))[:8]:
        l = pr['local']
        r = pr['remote']
        if l and r:
            print(f"    {pr['province']}: 本省{l['count']}所 IQR={l['iqr']} | 外省{r['count']}所 IQR={r['iqr']}")

    return {
        'local': local_result,
        'remote': remote_result,
        'comparison': comparison,
        'province_details': prov_results,
    }


# ============================================================
# 维度4: 专业组级别波动分析
# ============================================================
def analyze_specialty_group(prov_data, school_list):
    """分析同一院校不同专业组之间的分数线差异"""
    print("\n" + "="*60)
    print("📊 维度4: 专业组级别波动分析")
    print("="*60)

    # 使用API数据（有sg_name字段）
    api_data_by_prov = {}
    for prov in ['北京', '广东']:
        for year in [2023, 2024]:
            data = load_api(prov, year)
            if data:
                key = f"{prov}_{year}"
                api_data_by_prov[key] = data

    if not api_data_by_prov:
        print("  ⚠️ 无API数据可用，使用v9数据中的多分数记录分析")
        return {'available': False}

    results = {'available': True, 'provinces': {}}

    # 需要同一省份两年的API数据
    for prov in ['北京', '广东']:
        d23 = api_data_by_prov.get(f'{prov}_2023')
        d24 = api_data_by_prov.get(f'{prov}_2024')
        if not d23 or not d24: continue

        # 按学校汇总专业组分数
        school_sg_2023 = defaultdict(dict)  # school -> {sg_name: score}
        school_sg_2024 = defaultdict(dict)

        for r in d23:
            name = r.get('name', '')
            sg = r.get('sg_name', '(默认)')
            score = r.get('min', None)
            if score and str(score).isdigit():
                school_sg_2023[name][sg] = int(score)

        for r in d24:
            name = r.get('name', '')
            sg = r.get('sg_name', '(默认)')
            score = r.get('min', None)
            if score and str(score).isdigit():
                school_sg_2024[name][sg] = int(score)

        # 分析：同一学校内专业组的分数离散度
        within_school_spreads = []
        school_shifts_by_sg = []
        multi_sg_schools = 0
        total_schools = 0

        all_schools = set(school_sg_2023.keys()) | set(school_sg_2024.keys())
        for school in all_schools:
            sg23 = school_sg_2023.get(school, {})
            sg24 = school_sg_2024.get(school, {})
            total_schools += 1

            if len(sg23) >= 2:
                scores23 = list(sg23.values())
                spread23 = max(scores23) - min(scores23)
                within_school_spreads.append({
                    'school': school, 'spread': spread23,
                    'n_groups': len(sg23),
                    'min': min(scores23), 'max': max(scores23),
                })
                multi_sg_schools += 1

            # 对齐专业组做shift分析
            common_sgs = set(sg23.keys()) & set(sg24.keys())
            for sg in common_sgs:
                school_shifts_by_sg.append({
                    'school': school, 'sg': sg,
                    'shift': sg24[sg] - sg23[sg],
                })

        # 专业组内离散度统计
        if within_school_spreads:
            spreads = [s['spread'] for s in within_school_spreads]
            spreads.sort()
            n = len(spreads)
            result = {
                'total_schools': total_schools,
                'multi_sg_schools': multi_sg_schools,
                'multi_sg_pct': round(multi_sg_schools / total_schools * 100, 1) if total_schools else 0,
                'spread_median': spreads[n//2],
                'spread_mean': round(sum(spreads) / n, 1),
                'spread_q1': spreads[n//4],
                'spread_q3': spreads[3*n//4],
                'spread_max': spreads[-1],
                'top_spreads': sorted(within_school_spreads, key=lambda x: -x['spread'])[:5],
            }

            # 专业组间shift差异
            if school_shifts_by_sg:
                # 按学校分组，看同一学校不同专业组的shift差
                school_sg_shifts = defaultdict(list)
                for item in school_shifts_by_sg:
                    school_sg_shifts[item['school']].append(item['shift'])

                shift_variances = []
                for school, shifts in school_sg_shifts.items():
                    if len(shifts) >= 2:
                        shift_variances.append({
                            'school': school,
                            'shift_range': max(shifts) - min(shifts),
                            'shifts': shifts,
                        })

                if shift_variances:
                    ranges = [v['shift_range'] for v in shift_variances]
                    ranges.sort()
                    rn = len(ranges)
                    result['shift_range_median'] = ranges[rn//2]
                    result['shift_range_mean'] = round(sum(ranges) / rn, 1)
                    result['shift_range_q3'] = ranges[3*rn//4]
                    result['top_shift_variance'] = sorted(shift_variances, key=lambda x: -x['shift_range'])[:5]

            results['provinces'][prov] = result

            print(f"\n  [{prov}]")
            print(f"    总院校: {total_schools}, 多专业组: {multi_sg_schools} ({result['multi_sg_pct']}%)")
            print(f"    专业组内分数差: 中位数={result['spread_median']}分, 均值={result['spread_mean']}分")
            print(f"    分数差IQR: [{result['spread_q1']}, {result['spread_q3']}], 最大={result['spread_max']}分")
            print(f"    最大离散院校:")
            for s in result.get('top_spreads', []):
                print(f"      {s['school']}: {s['n_groups']}组, 差{s['spread']}分 ({s['min']}-{s['max']})")
            if 'shift_range_median' in result:
                print(f"    同校专业组间shift差: 中位数={result['shift_range_median']}分, Q3={result['shift_range_q3']}分")

    return results


# ============================================================
# 维度5: 2024→2025跨年验证
# ============================================================
def analyze_2025_validation(school_list):
    """如果2025数据可用，做跨年验证"""
    print("\n" + "="*60)
    print("📊 维度5: 2024→2025 跨年验证")
    print("="*60)

    # 检查2025数据是否已下载
    api_2025 = {}
    for prov in ['北京', '广东', '江苏', '湖北', '陕西', '山东', '浙江', '海南', '湖南', '河北']:
        data = load_api(prov, 2025)
        if data and len(data) > 10:
            api_2025[prov] = data
            print(f"  ✅ {prov} 2025: {len(data)}条")

    if not api_2025:
        print("  ⏳ 2025年数据尚未就绪（后台抓取中），跳过此维度")
        print("  💡 可在数据就绪后单独运行此分析")
        return {'available': False, 'reason': '2025数据尚未下载完成'}

    # 使用2024和2025 API数据做验证
    school_map = {s['name']: s for s in school_list}
    results = {'available': True, 'provinces': {}}

    for prov, d2025 in api_2025.items():
        d2024 = load_api(prov, 2024)
        if not d2024: continue

        # 建学校→分数映射（取最低分代表学校）
        school_2024 = {}
        school_2025 = {}
        for r in d2024:
            name = r.get('name', '')
            score = r.get('min', None)
            if score and str(score).isdigit():
                if name not in school_2024 or int(score) < school_2024[name]:
                    school_2024[name] = int(score)

        for r in d2025:
            name = r.get('name', '')
            score = r.get('min', None)
            if score and str(score).isdigit():
                if name not in school_2025 or int(score) < school_2025[name]:
                    school_2025[name] = int(score)

        # 匹配学校
        common = set(school_2024.keys()) & set(school_2025.keys())
        if len(common) < 20: continue

        shifts = [school_2025[s] - school_2024[s] for s in common]
        shifts.sort()
        n = len(shifts)

        # 命中率验证：用v10校准参数预测
        # 冲：预测分+5%, 稳：预测分-5, 保：预测分-15
        hits_chong = sum(1 for s in common if school_2025[s] <= school_2024[s] + 5)
        hits_wen = sum(1 for s in common if school_2025[s] <= school_2024[s] - 5)
        hits_bao = sum(1 for s in common if school_2025[s] <= school_2024[s] - 15)

        prov_result = {
            'common_schools': n,
            'mean_shift': round(sum(shifts) / n, 1),
            'median_shift': shifts[n//2],
            'iqr': shifts[3*n//4] - shifts[n//4],
            'chong_hit': round(hits_chong / n * 100, 1),
            'wen_hit': round(hits_wen / n * 100, 1),
            'bao_hit': round(hits_bao / n * 100, 1),
        }
        results['provinces'][prov] = prov_result

        print(f"\n  [{prov}] {n}所匹配院校")
        print(f"    平均shift: {prov_result['mean_shift']}, 中位数: {prov_result['median_shift']}")
        print(f"    命中率: 冲{prov_result['chong_hit']}% / 稳{prov_result['wen_hit']}% / 保{prov_result['bao_hit']}%")

    return results


# ============================================================
# 主流程
# ============================================================
def main():
    print("="*60)
    print(f"🚀 高考志愿回测引擎 v12 — 五维度扩展分析")
    print(f"   运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 加载数据
    print("\n📂 加载数据...")
    prov_data = load_v9()
    school_list = load_school_list()
    print(f"   v9数据: {len(prov_data)}个省份")
    print(f"   院校库: {len(school_list)}所院校")

    results = {
        'version': 'v12',
        'timestamp': datetime.now().isoformat(),
        'data_summary': {
            'provinces_v9': len(prov_data),
            'schools_total': len(school_list),
        },
    }

    # 执行5个维度分析
    results['dim1_size_year'] = analyze_size_year(school_list)
    results['dim2_reform_vs_traditional'] = analyze_reform_vs_traditional(prov_data)
    results['dim3_local_vs_remote'] = analyze_local_vs_remote(prov_data, school_list)
    results['dim4_specialty_group'] = analyze_specialty_group(prov_data, school_list)
    results['dim5_2025_validation'] = analyze_2025_validation(school_list)

    # 总结
    print("\n" + "="*60)
    print("📋 v12 五维度分析总结")
    print("="*60)

    d1 = results['dim1_size_year']
    if d1.get('available'):
        if d1.get('mode') == '3year_zigzag':
            for p in d1.get('provinces_analyzed', []):
                print(f"  1️⃣ 大小年({p['province']}): {p['zigzag_pct']}%学校出现方向反转")
        else:
            s = d1.get('summary', {})
            print(f"  1️⃣ 大小年(2年代理): 大涨{s.get('big_up_pct',0)}% 大跌{s.get('big_down_pct',0)}%")
    else:
        print(f"  1️⃣ 大小年: 数据不足")

    d2 = results['dim2_reform_vs_traditional']
    comp = d2.get('comparison', {})
    if comp:
        print(f"  2️⃣ 新高考vs老高考: IQR比={comp.get('iqr_ratio_312_vs_trad','?')}x")
    else:
        print(f"  2️⃣ 新高考vs老高考: 数据不足")

    d3 = results['dim3_local_vs_remote']
    if d3.get('comparison'):
        print(f"  3️⃣ 省内外差异: {d3['comparison'].get('finding','?')}")
    else:
        print(f"  3️⃣ 省内外差异: 数据不足")

    d4 = results['dim4_specialty_group']
    if d4.get('available'):
        for prov, info in d4.get('provinces', {}).items():
            print(f"  4️⃣ 专业组({prov}): 多组率{info['multi_sg_pct']}%, 组内差中位={info['spread_median']}分")
    else:
        print(f"  4️⃣ 专业组级别: 数据不足")

    d5 = results['dim5_2025_validation']
    if d5.get('available'):
        for prov, info in d5.get('provinces', {}).items():
            print(f"  5️⃣ 2025验证({prov}): 冲{info['chong_hit']}% 稳{info['wen_hit']}% 保{info['bao_hit']}%")
    else:
        print(f"  5️⃣ 2025验证: {d5.get('reason', '数据不足')}")

    # 保存
    out_path = os.path.join(RESULT_DIR, 'backtest_v12.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 结果已保存: {out_path}")
    print(f"   文件大小: {os.path.getsize(out_path):,} bytes")


if __name__ == '__main__':
    main()
