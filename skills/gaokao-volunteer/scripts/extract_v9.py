#!/usr/bin/env python3
"""
精确数据提取器 v9 - 解决列识别问题
针对每种已知表格格式精确解析
"""

import json
import os
import re
import time
import requests
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
OUTPUT_DIR = os.path.join(DATA_DIR, "province_v9")
os.makedirs(OUTPUT_DIR, exist_ok=True)
BASE = "https://www.dxsbb.com"


def get_session():
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    return s


def extract_tables(html):
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.S)
    results = []
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.S)
        table_data = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)
            cells = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').replace('\r', '').replace('\n', '').strip() for c in cells]
            cells = [c for c in cells if c]
            if cells:
                table_data.append(cells)
        if len(table_data) > 3:  # 至少4行才算有效表格
            results.append(table_data)
    return results


def identify_columns(header_row, table_data=None):
    """
    根据表头精确识别列位置
    返回 dict: {school, score, rank, category}
    """
    cols = {'school': None, 'score': None, 'rank': None, 'category': None}
    # 清理表头
    header_clean = [re.sub(r'&nbsp;', ' ', h).strip() for h in header_row]
    
    for i, h in enumerate(header_clean):
        h = h.strip()
        
        # === 学校名 ===
        if cols['school'] is None:
            if h in ('院校名称', '学校名称', '招生院校', '院校'):
                cols['school'] = i
            elif '院校名称' in h or '学校名称' in h or '招生院校' in h:
                cols['school'] = i
            elif '院校代号及名称' in h or '院校代码及名称' in h:
                cols['school'] = i
        
        # === 分数 ===
        if cols['score'] is None:
            if '排序' in h or '同分' in h or '单科' in h:
                continue
            # 标准分数列名
            if any(kw in h for kw in ['投档最低分', '投档线', '投档分', '最低分', '分数线', '录取最低分']):
                cols['score'] = i
            elif h in ('总分',):
                cols['score'] = i
            # 广西2023格式: "文史类"/"理工类"作为列名，值是分数
            elif h in ('文史类', '理工类', '物理类', '历史类', '文科', '理科', '普通类'):
                cols['score'] = i
            # 带&nbsp;的: "  投档最低分"
            elif '投档' in h and ('分' in h or '线' in h):
                cols['score'] = i
        
        # === 位次 ===
        if cols['rank'] is None:
            if '最低位次' in h or h in ('位次', '排位', '排名'):
                cols['rank'] = i
            elif '位次' in h or '排位' in h:
                cols['rank'] = i
        
        # === 科类 ===
        if cols['category'] is None:
            if h in ('科类', '首选科目', '科类名称'):
                cols['category'] = i
    
    # 如果没有找到score/rank，用启发式：看数据行
    if cols['score'] is None and cols['rank'] is None and table_data and len(table_data) > 2:
        for row in table_data[1:4]:  # 检查前几行数据
            for j, cell in enumerate(row):
                if j == cols['school']:
                    continue
                # 清理 &nbsp; 和小数
                cell_clean = re.sub(r'&nbsp;', '', cell).strip()
                try:
                    val = float(cell_clean)
                    if 300 <= val <= 800:
                        if cols['score'] is None:
                            cols['score'] = j
                    elif val > 1000:
                        if cols['rank'] is None:
                            cols['rank'] = j
                except (ValueError, TypeError):
                    pass
    
    return cols


def find_header_row(table_data):
    """找到表头行（包含'院校'或'学校'关键词的行）"""
    for i, row in enumerate(table_data[:8]):
        row_text = '|'.join(row)
        if ('院校' in row_text or '学校' in row_text or '招生院校' in row_text):
            if len(row) >= 3:  # 至少3列
                if any(kw in row_text for kw in ['分数', '投档', '位次', '最低', '总分', '文史', '理工', '物理', '历史', '文科', '理科', '线']):
                    return i
    return None


def extract_school_name(raw):
    """从原始单元格中提取干净的学校名"""
    # 去除HTML残留
    name = re.sub(r'<[^>]+>', '', raw).strip()
    # 山东格式: "A001北京大学" → 去代号
    name = re.sub(r'^[A-Z]\d{3,4}', '', name)
    # 去专业组后缀
    name = re.sub(r'\d+专业组.*$', '', name)
    name = re.sub(r'第\d+组.*$', '', name)
    # 去括号内容
    name = re.sub(r'[\(（].*?[\)）]', '', name)
    # 去城市标注
    name = re.sub(r'\[.*?\]', '', name)
    return name.strip()


def parse_table(table_data, province, year, title):
    """解析一张表格，返回记录列表"""
    header_idx = find_header_row(table_data)
    if header_idx is None:
        return []
    
    header = table_data[header_idx]
    cols = identify_columns(header, table_data)
    
    if cols['school'] is None:
        return []
    
    records = []
    for row in table_data[header_idx + 1:]:
        if len(row) < 3:
            continue
        
        school = extract_school_name(row[cols['school']]) if cols['school'] < len(row) else ''
        if len(school) < 4 or '说明' in school:
            continue
        if not any(kw in school for kw in ['大学', '学院', '学校']):
            continue
        
        record = {
            'province': province,
            'year': year,
            'source': title,
            'school': school,
        }
        
        # 科类
        cat = '综合'
        if cols['category'] is not None and cols['category'] < len(row):
            cat_raw = row[cols['category']]
            if '物理' in cat_raw:
                cat = '物理'
            elif '历史' in cat_raw:
                cat = '历史'
            elif '理科' in cat_raw:
                cat = '理科'
            elif '文科' in cat_raw:
                cat = '文科'
        else:
            # 从title推断
            if '物理' in title:
                cat = '物理'
            elif '历史' in title:
                cat = '历史'
            elif '理科' in title:
                cat = '理科'
            elif '文科' in title:
                cat = '文科'
        record['category'] = cat
        
        # 分数
        if cols['score'] is not None and cols['score'] < len(row):
            try:
                val = row[cols['score']].replace(',', '').replace('&nbsp;', '').strip()
                score = int(float(val))  # 处理浮点如337.000000000
                if 200 <= score <= 850:
                    record['score'] = score
            except (ValueError, TypeError):
                pass
        
        # 位次
        if cols['rank'] is not None and cols['rank'] < len(row):
            try:
                val = row[cols['rank']].replace(',', '').replace('&nbsp;', '').strip()
                rank = int(float(val))
                if rank > 0:
                    record['rank'] = rank
            except (ValueError, TypeError):
                pass
        
        if 'score' in record or 'rank' in record:
            records.append(record)
    
    return records


def main():
    s = get_session()
    
    articles_path = os.path.join(DATA_DIR, "dxsbb_data", "articles.json")
    with open(articles_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    # 按省份分组，只取本科
    by_prov = defaultdict(list)
    for key, art in articles.items():
        title = art['title']
        if '专科' in title or '高职' in title or '预科' in title:
            continue
        if not any(b in title for b in ['本科', '一本', '二本', '一段', '常规', 'A段', 'B段', 'A类', 'B类', 'C类', 'I段', 'K段', 'C段', 'G段', 'J段']):
            continue
        by_prov[art['province']].append(art)
    
    print(f"本科文章覆盖省份: {len(by_prov)}个\n")
    
    all_data = {}
    stats = {}
    
    for prov in sorted(by_prov.keys()):
        prov_records = []
        art_stats = {'total': 0, 'ok': 0, 'fail': 0, 'with_rank': 0, 'with_score': 0}
        
        for art in by_prov[prov]:
            title = art['title']
            url = art['url']
            year_m = re.search(r'(20\d{2})', title)
            year = int(year_m.group(1)) if year_m else 0
            if year not in (2023, 2024):
                continue
            
            art_stats['total'] += 1
            
            try:
                r = s.get(url, timeout=15)
                r.encoding = 'utf-8'
                tables = extract_tables(r.text)
                
                if tables:
                    biggest = max(tables, key=len)
                    if len(biggest) > 5:  # 有效表格至少6行
                        records = parse_table(biggest, prov, year, title)
                        if records:
                            prov_records.extend(records)
                            art_stats['ok'] += 1
                            for rec in records:
                                if 'rank' in rec:
                                    art_stats['with_rank'] += 1
                                if 'score' in rec:
                                    art_stats['with_score'] += 1
                        else:
                            art_stats['fail'] += 1
                    else:
                        art_stats['fail'] += 1
                else:
                    art_stats['fail'] += 1
            except Exception as e:
                art_stats['fail'] += 1
            
            time.sleep(0.15)
        
        if prov_records:
            all_data[prov] = prov_records
            stats[prov] = art_stats
            wr = art_stats['with_rank']
            ws = art_stats['with_score']
            print(f"✅ {prov}: {len(prov_records)}条 (rank={wr}, score={ws}, 成功{art_stats['ok']}/{art_stats['total']}篇)")
        else:
            print(f"❌ {prov}: 0条 (尝试{art_stats['total']}篇)")
    
    # 保存
    for prov, records in all_data.items():
        outfile = os.path.join(OUTPUT_DIR, f"{prov}_v9.json")
        with open(outfile, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    
    # 汇总
    total = sum(len(v) for v in all_data.values())
    rank_total = sum(s['with_rank'] for s in stats.values())
    score_total = sum(s['with_score'] for s in stats.values())
    print(f"\n{'='*60}")
    print(f"总计: {total}条, 覆盖{len(all_data)}省")
    print(f"有rank: {rank_total}条, 有score: {score_total}条")
    
    return all_data


if __name__ == '__main__':
    main()
