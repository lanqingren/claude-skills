#!/usr/bin/env python3
"""
贵州2025年本科批投档PDF完整提取器
==================================
从406页PDF提取全部投档记录（专业级别）
"""

import fitz
import json
import os
from pathlib import Path

PDF_PATH = Path(r"D:\GitHub\hermescn\data\gaokao-data\贵州_2025_物理类_本科批投档.pdf")
OUTPUT_PATH = Path(r"D:\GitHub\hermescn\data\gaokao-data\贵州_2025_物理类_本科批投档_complete.json")


def extract_all_pages():
    doc = fitz.open(str(PDF_PATH))
    total_pages = len(doc)
    all_records = []
    
    print(f"PDF总页数: {total_pages}")
    
    for page_num in range(total_pages):
        page = doc[page_num]
        tabs = page.find_tables()
        
        if not tabs.tables:
            continue
        
        tab = tabs.tables[0]
        rows = tab.extract()
        
        for row in rows:
            # 跳过表头行
            if row[0] == '序号' or row[0] is None:
                continue
            if not str(row[0]).strip().isdigit():
                continue
            
            # 解析行
            try:
                record = {
                    "seq": int(row[0]),
                    "school_code": str(row[1] or '').strip(),
                    "school": str(row[2] or '').strip(),
                    "major_code": str(row[3] or '').strip(),
                    "major": str(row[4] or '').strip(),
                    "exam_type": str(row[5] or '').strip(),
                    "plan_count": int(row[6]) if str(row[6] or '0').strip().isdigit() else None,
                    "admit_count": int(row[7]) if str(row[7] or '0').strip().isdigit() else None,
                    "min_score": int(row[8]) if str(row[8] or '').strip().isdigit() else None,
                    "min_rank": int(row[9]) if str(row[9] or '').strip().isdigit() else None,
                }
                all_records.append(record)
            except (ValueError, IndexError) as e:
                # 跳过解析失败的行
                continue
        
        if (page_num + 1) % 50 == 0:
            print(f"  已处理 {page_num+1}/{total_pages} 页, 累计 {len(all_records)} 条")
    
    doc.close()
    return all_records


def aggregate_to_school_level(records):
    """将专业级数据聚合到学校级别（取最低位次=最容易进的专业）"""
    schools = {}
    for r in records:
        name = r.get("school", "").strip()
        rank = r.get("min_rank")
        if not name or not rank:
            continue
        if name not in schools or rank > schools[name]["min_rank"]:
            schools[name] = {
                "school": name,
                "min_score": r.get("min_score"),
                "min_rank": rank,
                "school_code": r.get("school_code"),
                "best_major": r.get("major"),  # 最低分专业
                "total_majors": 0,
            }
        # 统计该校总专业数
        if name in schools:
            schools[name]["total_majors"] = schools[name].get("total_majors", 0) + 1
    
    return list(schools.values())


def main():
    print(f"📥 开始提取 {PDF_PATH.name}")
    records = extract_all_pages()
    print(f"\n✅ 提取完成: {len(records)} 条专业级记录")
    
    # 保存完整专业级数据
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"📁 专业级数据 → {OUTPUT_PATH.name}")
    
    # 聚合到学校级
    schools = aggregate_to_school_level(records)
    schools.sort(key=lambda x: x["min_rank"])
    
    school_output = OUTPUT_PATH.parent / "贵州_2025_物理类_本科批投档_schools.json"
    with open(school_output, 'w', encoding='utf-8') as f:
        json.dump(schools, f, ensure_ascii=False, indent=2)
    print(f"📁 学校级数据 → {school_output.name} ({len(schools)} 所)")
    
    # 统计
    print(f"\n📊 数据统计:")
    print(f"  专业级记录: {len(records)} 条")
    print(f"  学校数: {len(schools)} 所")
    
    scores = [r["min_score"] for r in records if r.get("min_score")]
    ranks = [r["min_rank"] for r in records if r.get("min_rank")]
    if scores:
        print(f"  分数范围: {min(scores)} ~ {max(scores)}")
    if ranks:
        print(f"  位次范围: {min(ranks):,} ~ {max(ranks):,}")
    
    # 字母分布
    from collections import Counter
    first_chars = Counter(s["school"][0] for s in schools if s.get("school"))
    print(f"  学校首字覆盖: {len(first_chars)} 个不同首字")


if __name__ == "__main__":
    main()
