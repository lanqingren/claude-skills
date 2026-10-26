#!/usr/bin/env python3
"""
精确提取+回测引擎 v8
1. 精确解析HTML表格（正确识别分数列/位次列/学校列）
2. 分数回测 + 位次回测双轨
3. 全国覆盖最大化
"""

import json
import os
import re
import time
import requests
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
SCORES_DIR = os.path.join(DATA_DIR, "province_scores")
OUTPUT_DIR = os.path.join(DATA_DIR, "backtest_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE = "https://www.dxsbb.com"


def get_session():
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE,
    })
    return s


def extract_tables(html):
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.S)
    results = []
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.S)
        table_data = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)
            cells = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').strip() for c in cells]
            cells = [c for c in cells if c]
            if cells:
                table_data.append(cells)
        if table_data:
            results.append(table_data)
    return results


def find_columns(header):
    """智能识别列含义，返回 {school_col, score_col, rank_col}"""
    result = {'school_col': None, 'score_col': None, 'rank_col': None}
    
    for i, h in enumerate(header):
        h_lower = h.lower() if isinstance(h, str) else ''
        
        # 学校名（优先匹配"院校名称"/"学校名称"/"院校"）
        if result['school_col'] is None:
            if any(kw in h for kw in ['院校名称', '学校名称', '招生院校', '院校名称及']):
                result['school_col'] = i
                continue
        
        # 位次（精确匹配）
        if result['rank_col'] is None:
            if any(kw in h for kw in ['最低位次', '位次', '排位', '排名']):
                result['rank_col'] = i
                continue
        
        # 分数（精确匹配投档分/最低分）
        if result['score_col'] is None:
            if any(kw in h for kw in ['投档最低分', '投档线', '最低分', '投档分', '录取最低分']):
                # 排除"同分排序"类干扰列
                if '排序' not in h and '同分' not in h:
                    result['score_col'] = i
                    continue
            # 山东格式: 没有分数列只有位次
            if h in ['分数线', '总分']:
                result['score_col'] = i
                continue
    
    return result


def parse_table_data(table_data, province, year, title):
    """解析一张表格"""
    if len(table_data) < 3:
        return []
    
    # 找到表头行（包含关键词的行）
    header_idx = None
    cols = None
    for i, row in enumerate(table_data[:6]):
        row_text = '|'.join(row)
        if any(kw in row_text for kw in ['院校', '学校', '招生院校']):
            if any(kw in row_text for kw in ['分数', '投档', '位次', '最低']):
                header_idx = i
                cols = find_columns(row)
                break
    
    if header_idx is None or cols is None:
        return []
    if cols['school_col'] is None:
        return []
    
    # 如果既没score也没rank，用启发式
    if cols['score_col'] is None and cols['rank_col'] is None:
        # 看数据行中的数字
        for row in table_data[header_idx+1:header_idx+5]:
            for j, cell in enumerate(row):
                if j == cols['school_col']:
                    continue
                try:
                    n = int(cell.replace(',', ''))
                    if 300 <= n <= 800:
                        cols['score_col'] = j
                        break
                    elif n > 1000:
                        cols['rank_col'] = j
                except:
                    pass
    
    records = []
    for row in table_data[header_idx+1:]:
        if len(row) <= max(filter(lambda x: x is not None, [cols['school_col'], cols['score_col'], cols['rank_col']]), default=0):
            continue
        
        # 学校名
        school_raw = row[cols['school_col']] if cols['school_col'] < len(row) else ''
        # 去掉专业组后缀、代号前缀
        school = re.sub(r'\d+专业组.*', '', school_raw)
        school = re.sub(r'^[\u4e00-\u9fa5]{2,4}段', '', school)  # 去掉批次段
        school = re.sub(r'\(.*?\)', '', school).strip()
        school = re.sub(r'（.*?）', '', school).strip()
        if len(school) < 4 or '说明' in school:
            continue
        
        record = {
            'province': province,
            'year': year,
            'source': title,
            'school': school,
            'school_raw': school_raw,
        }
        
        if cols['score_col'] is not None and cols['score_col'] < len(row):
            try:
                score = int(row[cols['score_col']].replace(',', ''))
                if 1 <= score <= 850:
                    record['score'] = score
            except:
                pass
        
        if cols['rank_col'] is not None and cols['rank_col'] < len(row):
            try:
                rank = int(row[cols['rank_col']].replace(',', ''))
                if rank > 0:
                    record['rank'] = rank
            except:
                pass
        
        if 'score' in record or 'rank' in record:
            records.append(record)
    
    return records


def get_category(source, province):
    """从source中提取科类"""
    if '物理' in source:
        return '物理'
    if '历史' in source:
        return '历史'
    if '理科' in source:
        return '理科'
    if '文科' in source:
        return '文科'
    # 综合改革省份
    if province in ('北京', '山东', '浙江', '上海', '海南', '天津'):
        return '综合'
    return '综合'


def main():
    s = get_session()
    
    articles_path = os.path.join(DATA_DIR, "dxsbb_data", "articles.json")
    with open(articles_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    # 按省份分组，只取本科
    by_prov = defaultdict(list)
    for key, art in articles.items():
        title = art['title']
        if '专科' in title or '高职' in title:
            continue
        by_prov[art['province']].append(art)
    
    all_data = {}  # all_data[prov] = [records]
    
    for prov in sorted(by_prov.keys()):
        prov_records = []
        prov_stats = {'total': 0, 'with_rank': 0, 'with_score': 0}
        
        for art in by_prov[prov]:
            title = art['title']
            url = art['url']
            year_match = re.search(r'(20\d{2})', title)
            year = int(year_match.group(1)) if year_match else 0
            if year not in (2023, 2024):
                continue
            
            try:
                r = s.get(url, timeout=15)
                r.encoding = 'utf-8'
                tables = extract_tables(r.text)
                
                if tables:
                    biggest = max(tables, key=len)
                    records = parse_table_data(biggest, prov, year, title)
                    prov_records.extend(records)
                    
                    for rec in records:
                        prov_stats['total'] += 1
                        if 'rank' in rec:
                            prov_stats['with_rank'] += 1
                        if 'score' in rec:
                            prov_stats['with_score'] += 1
            except:
                pass
            
            time.sleep(0.2)
        
        if prov_records:
            all_data[prov] = prov_records
            wr = prov_stats['with_rank']
            ws = prov_stats['with_score']
            mode = 'rank' if wr > ws else 'score'
            print(f"✅ {prov}: {prov_stats['total']}条 (rank={wr}, score={ws}, 模式={mode})")
    
    # 保存全部数据
    for prov, records in all_data.items():
        outfile = os.path.join(SCORES_DIR, f"{prov}_scores_v2.json")
        with open(outfile, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"数据提取完成，覆盖{len(all_data)}个省份")
    
    # ====== 回测 ======
    print(f"\n{'='*60}")
    print(f"📊 开始回测...")
    print(f"{'='*60}")
    
    all_results = []
    all_shifts_rank = []  # 位次偏移
    all_shifts_score = []  # 分数偏移
    
    for prov, records in all_data.items():
        # 按年份+科类组织
        organized = defaultdict(lambda: defaultdict(list))
        for rec in records:
            year = rec.get('year', 0)
            cat = get_category(rec.get('source', ''), prov)
            organized[year][cat].append(rec)
        
        years = sorted(organized.keys())
        if len(years) < 2:
            continue
        
        cats_23 = set(organized.get(2023, {}).keys())
        cats_24 = set(organized.get(2024, {}).keys())
        common = cats_23 & cats_24
        cross_map = [('理科', '物理'), ('文科', '历史')]
        
        for cat_old, cat_new in cross_map + [(c, c) for c in common]:
            data_23 = organized.get(2023, {}).get(cat_old, [])
            data_24 = organized.get(2024, {}).get(cat_new, [])
            if not data_23 or not data_24:
                continue
            
            label = f"{cat_old}→{cat_new}" if cat_old != cat_new else cat_new
            group = f"{prov} {label}"
            
            # 去重
            def dedup(data):
                seen = {}
                for r in data:
                    name = r['school']
                    if name not in seen:
                        seen[name] = r
                    else:
                        # 取更好的成绩
                        if 'rank' in r and 'rank' in seen[name]:
                            if r['rank'] < seen[name]['rank']:
                                seen[name] = r
                        elif 'score' in r and 'score' in seen[name]:
                            if r['score'] > seen[name]['score']:
                                seen[name] = r
                return seen
            
            d23 = dedup(data_23)
            d24 = dedup(data_24)
            
            # 匹配
            matched_rank = []
            matched_score = []
            for school in set(d23.keys()) & set(d24.keys()):
                r23 = d23[school]
                r24 = d24[school]
                
                if 'rank' in r23 and 'rank' in r24 and r23['rank'] > 0 and r24['rank'] > 0:
                    shift = r24['rank'] - r23['rank']
                    matched_rank.append({'school': school, 'shift': shift, 'rank_23': r23['rank'], 'rank_24': r24['rank']})
                
                if 'score' in r23 and 'score' in r24 and 0 < r23['score'] < 800 and 0 < r24['score'] < 800:
                    shift = r24['score'] - r23['score']
                    matched_score.append({'school': school, 'shift': shift, 'score_23': r23['score'], 'score_24': r24['score']})
            
            result = {'group': group}
            
            # 位次回测
            if len(matched_rank) >= 20:
                shifts = [m['shift'] for m in matched_rank]
                shifts_sorted = sorted(shifts)
                n = len(shifts)
                median = shifts_sorted[n // 2]
                forward = sum(1 for s in shifts if s < 0)
                
                result['rank_mode'] = True
                result['rank_total'] = n
                result['rank_median'] = median
                result['rank_forward_pct'] = round(forward / n * 100, 1)
                # 冲稳保命中率
                result['rank_rush_hit'] = round(sum(1 for s in shifts if s >= 2500) / n * 100, 1)
                result['rank_steady_hit'] = round(sum(1 for s in shifts if s >= -500) / n * 100, 1)
                result['rank_safe_hit'] = round(sum(1 for s in shifts if s >= -17500) / n * 100, 1)
                
                all_shifts_rank.extend(shifts)
                all_results.append(result)
                print(f"  ✅ {group} [位次]: {n}校, 中位偏移={median:+,}, 冲={result['rank_rush_hit']}% 稳={result['rank_steady_hit']}% 保={result['rank_safe_hit']}%")
            
            # 分数回测
            elif len(matched_score) >= 20:
                shifts = [m['shift'] for m in matched_score]
                shifts_sorted = sorted(shifts)
                n = len(shifts)
                median = shifts_sorted[n // 2]
                up = sum(1 for s in shifts if s > 0)
                
                result['rank_mode'] = False
                result['score_total'] = n
                result['score_median'] = median
                result['score_up_pct'] = round(up / n * 100, 1)
                # 分数偏移冲稳保:
                # 冲(学校比考生高5~20分): P(shift <= 10) - 学校分数下降了就能录
                # 稳(学校比考生低0~20分): P(shift <= 20)
                # 保(学校比考生低20~50分): P(shift <= 50)
                result['score_rush_hit'] = round(sum(1 for s in shifts if s <= 10) / n * 100, 1)
                result['score_steady_hit'] = round(sum(1 for s in shifts if s <= 20) / n * 100, 1)
                result['score_safe_hit'] = round(sum(1 for s in shifts if s <= 50) / n * 100, 1)
                
                all_shifts_score.extend(shifts)
                all_results.append(result)
                print(f"  ✅ {group} [分数]: {n}校, 中位偏移={median:+,}分, 上涨={result['score_up_pct']}%, 冲={result['score_rush_hit']}% 稳={result['score_steady_hit']}% 保={result['score_safe_hit']}%")
    
    # ====== 全国汇总 ======
    print(f"\n{'='*90}")
    print(f"📊 全国回测汇总 (v8)")
    print(f"{'='*90}")
    
    rank_groups = [r for r in all_results if r.get('rank_mode')]
    score_groups = [r for r in all_results if not r.get('rank_mode')]
    print(f"回测组数: {len(rank_groups)}位次组 + {len(score_groups)}分数组 = {len(all_results)}组")
    
    if all_shifts_rank:
        N = len(all_shifts_rank)
        ss = sorted(all_shifts_rank)
        med = ss[N // 2]
        print(f"\n📈 位次回测 ({N:,}校, {len(rank_groups)}组):")
        print(f"  中位偏移: {med:+,}名")
        print(f"  冲(≥2500): {sum(1 for s in all_shifts_rank if s >= 2500)/N*100:.1f}%")
        print(f"  稳(≥-500): {sum(1 for s in all_shifts_rank if s >= -500)/N*100:.1f}%")
        print(f"  保(≥-17500): {sum(1 for s in all_shifts_rank if s >= -17500)/N*100:.1f}%")
    
    if all_shifts_score:
        N = len(all_shifts_score)
        ss = sorted(all_shifts_score)
        med = ss[N // 2]
        p25 = ss[N // 4]
        p75 = ss[3 * N // 4]
        print(f"\n📈 分数回测 ({N:,}校, {len(score_groups)}组):")
        print(f"  中位偏移: {med:+,}分")
        print(f"  P25~P75: {p25:+,} ~ {p75:+,}分")
        print(f"  冲(≤10分): {sum(1 for s in all_shifts_score if s <= 10)/N*100:.1f}%")
        print(f"  稳(≤20分): {sum(1 for s in all_shifts_score if s <= 20)/N*100:.1f}%")
        print(f"  保(≤50分): {sum(1 for s in all_shifts_score if s <= 50)/N*100:.1f}%")
        print(f"  分数上涨%: {sum(1 for s in all_shifts_score if s > 0)/N*100:.1f}%")
        print(f"  分数下降%: {sum(1 for s in all_shifts_score if s < 0)/N*100:.1f}%")
    
    # 分组详情表
    print(f"\n{'='*90}")
    print(f"📋 分组详情")
    print(f"{'='*90}")
    print(f"{'组名':<30} {'模式':>4} {'匹配':>6} {'中位偏移':>10} {'冲%':>6} {'稳%':>6} {'保%':>6}")
    print("-" * 90)
    for r in sorted(all_results, key=lambda x: -(x.get('rank_total', 0) or x.get('score_total', 0))):
        if r.get('rank_mode'):
            print(f"{r['group']:<30} {'位次':>4} {r['rank_total']:>6} {r['rank_median']:>+10,} {r['rank_rush_hit']:>5.1f}% {r['rank_steady_hit']:>5.1f}% {r['rank_safe_hit']:>5.1f}%")
        else:
            print(f"{r['group']:<30} {'分数':>4} {r['score_total']:>6} {r['score_median']:>+10,} {r['score_rush_hit']:>5.1f}% {r['score_steady_hit']:>5.1f}% {r['score_safe_hit']:>5.1f}%")
    
    # 保存
    output = {
        'version': 'v8',
        'total_groups': len(all_results),
        'rank_groups': len(rank_groups),
        'score_groups': len(score_groups),
        'national_rank': {
            'total': len(all_shifts_rank),
            'median_shift': med if all_shifts_rank else 0,
        } if all_shifts_rank else None,
        'national_score': {
            'total': len(all_shifts_score),
            'median_shift': ss[len(all_shifts_score)//2] if all_shifts_score else 0,
        } if all_shifts_score else None,
        'groups': all_results,
    }
    
    out_path = os.path.join(OUTPUT_DIR, "backtest_v8_national.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 结果已保存: {out_path}")


if __name__ == '__main__':
    main()
