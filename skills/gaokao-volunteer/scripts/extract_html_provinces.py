#!/usr/bin/env python
"""精确提取江苏/北京/海南的HTML表格数据（3省各有不同表头格式）。"""
import json, os, re
from pathlib import Path

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data")
HTML_DIR = DATA_DIR / "dxsbb_html"
V9_DIR   = DATA_DIR / "province_v9"

def extract_table_rows(html):
    """提取HTML中第一个大表格的所有行（返回二维列表）"""
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
    all_rows = []
    for t in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.DOTALL)
        table_rows = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells_clean = []
            for c in cells:
                c = re.sub(r'<[^>]+>', '', c)
                c = c.replace('&nbsp;', ' ').strip()
                c = re.sub(r'\s+', ' ', c).strip()
                cells_clean.append(c)
            if cells_clean and any(c for c in cells_clean):
                table_rows.append(cells_clean)
        if len(table_rows) > 5:  # 只保留有内容的表格
            all_rows.extend(table_rows)
    return all_rows


def extract_jiangsu():
    """江苏：院校代号 | 院校、专业组（再选科目要求） | 投档最低分"""
    results = []
    configs = [
        ("江苏_2023物理.html", "2023", "物理"),
        ("江苏_2023历史.html", "2023", "历史"),
        ("江苏_2024物理.html", "2024", "物理"),
        ("江苏_2024历史.html", "2024", "历史"),
    ]
    for fname, year, category in configs:
        path = HTML_DIR / fname
        if not path.exists():
            print(f"  ⚠️ {fname} 不存在")
            continue
        html = path.read_text(encoding='utf-8', errors='replace')
        rows = extract_table_rows(html)
        count = 0
        for row in rows:
            if len(row) < 3:
                continue
            # 跳过表头
            if '院校代号' in row[0] or '院校' in row[0] and '代号' in ' '.join(row):
                continue
            # 数据行：code | school+group | score
            code = row[0].strip()
            school_field = row[1].strip()
            score_str = row[2].strip()
            # 提取分数
            try:
                score = int(float(score_str))
            except:
                continue
            if score < 200 or score > 800:
                continue
            # 从 "陆军工程大学04专业组(不限)" 提取学校名
            school = re.match(r'^(.+?)(\d+专业组|$)', school_field)
            if school:
                school = school.group(1).strip()
            else:
                school = school_field
            # 清理学校名
            school = re.sub(r'\d+专业组.*$', '', school).strip()
            if not school or len(school) < 2:
                continue
            results.append({
                'province': '江苏', 'year': year, 'category': category,
                'batch': '本科', 'school': school, 'score': score, 'rank': None
            })
            count += 1
        print(f"  📊 {fname}: {count} 条")
    return results


def extract_beijing():
    """北京：序号 | 院校代号 | 院校 | 专业组 | 选科 | 投档分 | 语文 | 数学 | 外语 | 三科选考"""
    results = []
    configs = [
        ("北京_2023本科.html", "2023"),
        ("北京_2024本科.html", "2024"),
    ]
    for fname, year in configs:
        path = HTML_DIR / fname
        if not path.exists():
            print(f"  ⚠️ {fname} 不存在")
            continue
        html = path.read_text(encoding='utf-8', errors='replace')
        rows = extract_table_rows(html)
        count = 0
        for row in rows:
            if len(row) < 6:
                continue
            # 跳过表头（包含"序号"、"院校"等关键词）
            if row[0] in ('序号', '院校') or '投档' in row[0]:
                continue
            # 数据行格式：序号 | 代号 | 校名 | 组号 | 选科 | 分数 | ...
            # 找到校名（包含"大学"/"学院"/"学校"的列）
            school = None
            score = None
            for i, cell in enumerate(row):
                if any(k in cell for k in ['大学', '学院', '学校', '分校']):
                    school = cell.strip()
                    # 分数通常在校名后2-3列
                    for j in range(i+1, min(i+4, len(row))):
                        try:
                            val = int(float(row[j].strip()))
                            if 300 <= val <= 750:
                                score = val
                                break
                        except:
                            pass
                    break
            if not school or score is None:
                continue
            results.append({
                'province': '北京', 'year': year, 'category': '综合',
                'batch': '本科', 'school': school, 'score': score, 'rank': None
            })
            count += 1
        print(f"  📊 {fname}: {count} 条")
    return results


def extract_hainan():
    """海南：院校专业组代码 | 院校专业组名称 | 计划数 | 投档数 | 投档线 | 科目要求"""
    results = []
    configs = [
        ("海南_2023本科.html", "2023"),
        ("海南_2024本科.html", "2024"),
    ]
    for fname, year in configs:
        path = HTML_DIR / fname
        if not path.exists():
            print(f"  ⚠️ {fname} 不存在")
            continue
        html = path.read_text(encoding='utf-8', errors='replace')
        rows = extract_table_rows(html)
        count = 0
        for row in rows:
            if len(row) < 5:
                continue
            # 跳过表头
            if '院校' in row[0] and '代码' in row[0]:
                continue
            # 跳过标题行
            if '投档分数线' in ' '.join(row):
                continue
            # 数据行：代码 | 名称 | 计划 | 投档数 | 分数线 | ...
            name_field = row[1].strip() if len(row) > 1 else ''
            score_str = row[4].strip() if len(row) > 4 else ''
            # 提取分数
            try:
                score = int(float(score_str))
            except:
                # 尝试其他列
                score = None
                for cell in row[2:]:
                    try:
                        val = int(float(cell.strip()))
                        if 400 <= val <= 900:
                            score = val
                            break
                    except:
                        pass
            if score is None or score < 400:
                continue
            # 从 "北京大学(02)" 提取学校名
            school = re.sub(r'\(\d+\).*$', '', name_field).strip()
            if not school or len(school) < 2:
                continue
            results.append({
                'province': '海南', 'year': year, 'category': '综合',
                'batch': '本科', 'school': school, 'score': score, 'rank': None
            })
            count += 1
        print(f"  📊 {fname}: {count} 条")
    return results


# ─── 主程序 ───
for name, func in [("江苏", extract_jiangsu), ("北京", extract_beijing), ("海南", extract_hainan)]:
    print(f"\n{'='*50}")
    print(f"提取: {name}")
    print(f"{'='*50}")
    records = func()
    out_path = V9_DIR / f"{name}_v9.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    # 统计
    stats = {}
    for r in records:
        key = f"{r['year']}_{r['category']}"
        stats[key] = stats.get(key, 0) + 1
    print(f"  💾 {len(records)} 条 → {out_path.name}")
    print(f"  📈 {stats}")
    
    # 分数范围检查
    if records:
        scores = [r['score'] for r in records]
        print(f"  📊 分数范围: {min(scores)}-{max(scores)}")
