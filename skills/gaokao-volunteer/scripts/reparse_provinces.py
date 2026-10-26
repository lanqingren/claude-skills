#!/usr/bin/env python3
"""重新解析全国投档线数据 - 严格区分位次/分数/院校代号"""

import requests
import re
import json
import os
import time
from collections import defaultdict

BASE = "https://www.dxsbb.com"
DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data\dxsbb_data"
OUTPUT_DIR = r"D:\GitHub\hermescn\data\gaokao-data\province_scores"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_session():
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    return s


def find_real_header(rows, max_scan=5):
    """有些表格第1行是标题/说明，真正的表头在第2或第3行"""
    for i in range(min(max_scan, len(rows))):
        cells = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[i], re.S)]
        cells = [c for c in cells if c]
        # 表头特征: 含有 "代号"/"代码"/"名称"/"分数"/"位次" 等关键词
        joined = '|'.join(cells)
        if any(kw in joined for kw in ['代号', '代码', '名称', '分数', '位次', '院校', '学校']):
            return cells, i  # 返回表头和行索引
    return None, 0


def identify_columns(header):
    """识别每列的含义: school_code, school_name, rank, score"""
    cols = {}
    for i, h in enumerate(header):
        h_lower = h.strip()
        if any(kw in h_lower for kw in ['院校代号', '院校代码', '院校编号', '学校代号', '学校代码']):
            cols['school_code'] = i
        elif any(kw in h_lower for kw in ['院校名称', '院校、专业组', '院校专业组名称', '学校名称', '招生院校']):
            cols['school_name'] = i
        elif any(kw in h_lower for kw in ['最低位次', '位次', '排位']):
            cols['rank'] = i
        elif any(kw in h_lower for kw in ['投档最低分', '最低分', '投档线', '投档分数', '总分', '分数线']):
            if 'score' not in cols:
                cols['score'] = i
    
    return cols


def extract_school_name(raw):
    """从原始字符串中提取干净的学校名"""
    # 山东格式: A442山东医学高等专科学校
    m = re.match(r'^[A-Z]\d{3,4}(.+)', raw)
    if m:
        return m.group(1).strip()
    
    # 带专业组的: 陆军工程大学06专业组(不限)
    name = re.sub(r'\d+专业组.*$', '', raw)
    # 去括号
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    return name.strip()


def parse_province_article(html, province, year, title):
    """解析单篇文章的投档线表格"""
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.S)
    if not tables:
        return [], 'no_table'
    
    biggest = max(tables, key=len)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', biggest, re.S)
    if len(rows) < 3:
        return [], 'too_few_rows'
    
    # 找真正的表头
    header, header_idx = find_real_header(rows)
    if not header:
        return [], 'no_header_found'
    
    cols = identify_columns(header)
    
    has_rank = 'rank' in cols
    has_score = 'score' in cols
    has_school = 'school_name' in cols or 'school_code' in cols
    
    if not has_school:
        return [], 'no_school_col'
    
    records = []
    school_col = cols.get('school_name', cols.get('school_code', 0))
    
    for row in rows[header_idx + 1:]:
        cells = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)]
        cells = [c for c in cells if c != '']
        
        if len(cells) < 2:
            continue
        
        # 跳过说明行/空行
        if any(kw in ''.join(cells) for kw in ['说明：', '注：', '备注', '--------']):
            continue
        
        record = {"province": province, "year": year, "source": title}
        
        # 学校名
        if school_col < len(cells):
            school_raw = cells[school_col]
            record["school"] = extract_school_name(school_raw)
        
        if not record.get("school") or len(record["school"]) < 2:
            continue
        
        # 位次
        if has_rank and 'rank' in cols and cols['rank'] < len(cells):
            try:
                rank_val = int(cells[cols['rank']].replace(',', '').replace(' ', ''))
                if rank_val > 0:
                    record["rank"] = rank_val
            except:
                pass
        
        # 分数
        if has_score and 'score' in cols and cols['score'] < len(cells):
            try:
                score_str = cells[cols['score']].replace(',', '').split('.')[0].strip()
                score_val = int(score_str)
                if 0 < score_val < 1000:
                    record["score"] = score_val
            except:
                pass
        
        # 必须有rank或score
        if 'rank' in record or 'score' in record:
            record["has_rank"] = has_rank
            records.append(record)
    
    data_type = 'rank' if has_rank else 'score_only'
    return records, data_type


def main():
    s = get_session()
    
    with open(os.path.join(DATA_DIR, "articles.json"), "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    undergrad = {k: v for k, v in articles.items() if '专科' not in v['title']}
    print(f"本科投档线文章: {len(undergrad)}篇\n")
    
    all_records = []
    stats = defaultdict(lambda: {'articles': 0, 'records': 0, 'rank_articles': 0, 'score_articles': 0})
    
    for key, art in sorted(undergrad.items()):
        prov = art['province']
        title = art['title']
        url = art['url']
        
        year_match = re.search(r'(20\d{2})', title)
        year = int(year_match.group(1)) if year_match else 0
        
        try:
            r = s.get(url, timeout=15)
            r.encoding = 'utf-8'
            
            records, dtype = parse_province_article(r.text, prov, year, title)
            
            stats[prov]['articles'] += 1
            stats[prov]['records'] += len(records)
            
            if dtype == 'rank':
                stats[prov]['rank_articles'] += 1
            elif dtype == 'score_only':
                stats[prov]['score_articles'] += 1
            
            if records:
                all_records.extend(records)
                type_tag = '📍位次' if dtype == 'rank' else '📄分数'
                print(f"  ✅ {prov} {title[:30]}: {len(records)}条 {type_tag}")
            else:
                print(f"  ⚠️ {prov} {title[:30]}: {dtype}")
        except Exception as e:
            print(f"  ❌ {prov} {title[:30]}: {str(e)[:40]}")
        
        time.sleep(0.3)
    
    # 保存
    outfile = os.path.join(OUTPUT_DIR, "all_provinces_v2.json")
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"总计: {len(all_records)}条记录")
    print(f"\n按省份统计:")
    print(f"{'省份':<8} {'文章':>4} {'位次篇':>6} {'分数篇':>6} {'记录数':>6}")
    print("-" * 35)
    for prov in sorted(stats.keys()):
        st = stats[prov]
        print(f"  {prov:<6} {st['articles']:>4} {st['rank_articles']:>6} {st['score_articles']:>6} {st['records']:>6}")
    
    # 统计有位次的数据
    rank_records = [r for r in all_records if r.get('has_rank') and r.get('rank')]
    score_records = [r for r in all_records if not r.get('has_rank')]
    print(f"\n位次数据: {len(rank_records)}条 (可用于回测)")
    print(f"纯分数数据: {len(score_records)}条 (需要转换)")


if __name__ == "__main__":
    main()
