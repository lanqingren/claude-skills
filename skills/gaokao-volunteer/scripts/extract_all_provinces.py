#!/usr/bin/env python3
"""从大学生必备网批量提取全国各省投档线HTML表格数据（无需OCR）"""

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
        "Referer": BASE,
    })
    return s


def extract_tables(html):
    """从HTML中提取所有表格数据"""
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.S)
    results = []
    
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.S)
        table_data = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)
            cells = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').strip() for c in cells]
            cells = [c for c in cells if c]  # 去空
            if cells:
                table_data.append(cells)
        if table_data:
            results.append(table_data)
    
    return results


def parse_score_table(table_data, province, year, title):
    """解析投档线表格，提取学校+分数/位次"""
    if not table_data:
        return []
    
    # 第一行是表头
    header = table_data[0]
    header_text = '|'.join(header)
    
    # 识别列含义
    school_col = None
    score_col = None
    rank_col = None
    major_col = None
    
    for i, h in enumerate(header):
        h_lower = h.lower()
        if '院校' in h and ('名称' in h or '代号' in h):
            if school_col is None:
                school_col = i
        if '分数' in h or '投档分' in h or '最低分' in h:
            score_col = i
        if '位次' in h or '排位' in h:
            rank_col = i
        if '专业' in h:
            major_col = i
    
    # 如果表头没有明确列名，尝试第二行
    if school_col is None and len(table_data) > 1:
        # 有些表第一行不是表头
        # 看看数据行中哪列包含学校名（含有A/B/C+数字开头）
        sample = table_data[1] if len(table_data) > 1 else []
        for i, cell in enumerate(sample):
            if re.match(r'^[A-Z]\d{3}', cell):
                school_col = i
                break
            # 或者直接是中文大学名
            if '大学' in cell or '学院' in cell:
                school_col = i
                break
    
    records = []
    for row in table_data[1:]:  # 跳过表头
        if len(row) < 2:
            continue
        
        record = {"province": province, "year": year, "source": title}
        
        # 尝试提取学校名
        for i, cell in enumerate(row):
            # 山东格式: A001北京大学
            m = re.match(r'^([A-Z]\d{3})(.+)', cell)
            if m:
                record["school_code"] = m.group(1)
                record["school"] = m.group(2).strip()
                # 这个cell后面的可能是专业
                continue
            
            # 其他格式: 直接是学校名
            if '大学' in cell or '学院' in cell:
                if 'school' not in record:
                    record["school"] = cell.strip()
                continue
        
        # 提取分数（纯数字，在合理范围）
        numbers = []
        for cell in row:
            try:
                n = int(cell.replace(',', ''))
                if 100 <= n <= 100000:  # 分数或位次范围
                    numbers.append(n)
            except:
                pass
        
        # 分配分数和位次
        if rank_col is not None and rank_col < len(row):
            try:
                record["rank"] = int(row[rank_col].replace(',', ''))
            except:
                pass
        
        if score_col is not None and score_col < len(row):
            try:
                record["score"] = int(row[score_col].replace(',', ''))
            except:
                pass
        
        # 如果没找到score/rank列，用数字大小判断
        if 'rank' not in record and 'score' not in record:
            for n in numbers:
                if n > 1000:  # 大于1000可能是位次
                    record["rank"] = n
                elif n > 100:
                    record["score"] = n
        
        # 必须有学校名
        if 'school' in record:
            records.append(record)
    
    return records


def main():
    s = get_session()
    
    # 加载文章列表
    with open(os.path.join(DATA_DIR, "articles.json"), "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    # 只保留本科批次
    undergrad = {}
    for key, art in articles.items():
        if "专科" in art["title"]:
            continue
        undergrad[key] = art
    
    print(f"本科投档线文章: {len(undergrad)}篇")
    
    all_records = []
    success = 0
    fail = 0
    
    # 按省份分组
    by_prov = defaultdict(list)
    for key, art in undergrad.items():
        by_prov[art["province"]].append((key, art))
    
    for prov in sorted(by_prov.keys()):
        items = by_prov[prov]
        prov_records = []
        
        for key, art in items:
            title = art["title"]
            url = art["url"]
            
            # 提取年份
            year_match = re.search(r'(20\d{2})', title)
            year = int(year_match.group(1)) if year_match else 0
            
            try:
                r = s.get(url, timeout=15)
                r.encoding = "utf-8"
                
                tables = extract_tables(r.text)
                
                if tables:
                    # 取最大的表格（通常是数据表）
                    biggest = max(tables, key=len)
                    records = parse_score_table(biggest, prov, year, title)
                    
                    if records:
                        prov_records.extend(records)
                        success += 1
                        print(f"  ✅ {prov} {title[:35]}: {len(records)}条")
                    else:
                        fail += 1
                        # 可能数据在图片中
                        print(f"  ⚠️ {prov} {title[:35]}: 表格{len(biggest)}行但无法解析")
                else:
                    fail += 1
                    # 没有表格，可能是图片
                    print(f"  ❌ {prov} {title[:35]}: 无HTML表格(可能是图片)")
                
            except Exception as e:
                fail += 1
                print(f"  ❌ {prov} {title[:35]}: {str(e)[:50]}")
            
            time.sleep(0.3)
        
        # 保存该省数据
        if prov_records:
            outfile = os.path.join(OUTPUT_DIR, f"{prov}_scores.json")
            with open(outfile, "w", encoding="utf-8") as f:
                json.dump(prov_records, f, ensure_ascii=False, indent=2)
            all_records.extend(prov_records)
            print(f"  → {prov}: 共{len(prov_records)}条，已保存\n")
    
    # 保存全部
    with open(os.path.join(OUTPUT_DIR, "all_provinces_scores.json"), "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"总计: {len(all_records)}条记录, 成功{success}篇, 失败{fail}篇")
    
    # 按省份统计
    prov_stats = defaultdict(int)
    year_stats = defaultdict(int)
    for r in all_records:
        prov_stats[r["province"]] += 1
        year_stats[r["year"]] += 1
    
    print(f"\n按省份:")
    for prov, count in sorted(prov_stats.items(), key=lambda x: -x[1]):
        print(f"  {prov}: {count}条")
    
    print(f"\n按年份:")
    for year, count in sorted(year_stats.items()):
        print(f"  {year}: {count}条")


if __name__ == "__main__":
    main()
