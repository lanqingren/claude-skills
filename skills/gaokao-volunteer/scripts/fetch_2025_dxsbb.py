#!/usr/bin/env python3
"""从dxsbb.com HTML页面提取2025年投档线数据，整合到province_classified.json"""
import json, os, re
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
HTML_DIR = os.path.join(DATA_DIR, "dxsbb_html")

# 2025年有数据的省份页面URL -> 省份信息
# 从浏览器列表发现：
PAGES_2025 = {
    "北京_2025本科": {"url_id": "149119", "prov": "北京", "year": "2025", "cat": "综合", "type": "3+3"},
    "上海_2025本科": {"url_id": "149121", "prov": "上海", "year": "2025", "cat": "综合", "type": "3+3"},
    "浙江_2025一段": {"url_id": "149123", "prov": "浙江", "year": "2025", "cat": "综合", "type": "3+3"},
    "河北_2025物理": {"url_id": "149128", "prov": "河北", "year": "2025", "cat": "物理", "type": "3+1+2"},
    "河北_2025历史": {"url_id": "149129", "prov": "河北", "year": "2025", "cat": "历史", "type": "3+1+2"},
    # 山东是位次数据（不是分数），格式不同，单独处理
    "山东_2025常规1": {"url_id": "149125", "prov": "山东", "year": "2025", "cat": "综合", "type": "3+3", "is_rank": True},
    "山东_2025常规2": {"url_id": "149126", "prov": "山东", "year": "2025", "cat": "综合", "type": "3+3", "is_rank": True},
    "山东_2025常规3": {"url_id": "149127", "prov": "山东", "year": "2025", "cat": "综合", "type": "3+3", "is_rank": True},
}

def extract_table_from_html(html_text):
    """从HTML中提取表格数据，返回 [(school, score), ...]"""
    # 提取所有<tr>行
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_text, re.DOTALL)
    data = []
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if len(cells) >= 6:
            # 北京格式: 序号|院校代码|院校名称|专业组代码|专业组名称|总分|备注
            # 上海格式类似
            # 河北格式: 序号|院校代码|院校名称|专业组代码|专业组名称|投档分
            school = cells[2]
            score_str = cells[5]
            try:
                score = int(score_str)
                if school and score > 0:
                    data.append((school, score))
            except ValueError:
                continue
    return data

def extract_table_from_html_rank(html_text):
    """从HTML中提取位次数据（山东），返回 [(school, rank), ...]"""
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_text, re.DOTALL)
    data = []
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        # 山东数据列: 院校 | 专业 | 最低位次 | ...
        if len(cells) >= 3:
            school = cells[0] if len(cells) <= 4 else cells[1]
            for c in cells:
                try:
                    val = int(c)
                    if val > 1000:  # 位次通常>1000
                        data.append((school, val))
                        break
                except ValueError:
                    continue
    return data

# Load classified
with open(CLASSIFIED_PATH, encoding="utf-8") as f:
    classified = json.load(f)

# Process each page
stats = {}
for label, info in PAGES_2025.items():
    prov = info["prov"]
    year = info["year"]
    cat = info["cat"]
    url_id = info["url_id"]
    is_rank = info.get("is_rank", False)
    
    # Download page
    import requests
    session = requests.Session()
    session.trust_env = False
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    url = f"https://www.dxsbb.com/news/{url_id}.html"
    print(f"📥 {label}: {url}")
    try:
        r = session.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"  ❌ HTTP {r.status_code}")
            continue
        
        if is_rank:
            data = extract_table_from_html_rank(r.text)
        else:
            data = extract_table_from_html(r.text)
        
        print(f"  提取 {len(data)} 条记录")
        
        if len(data) < 10:
            print(f"  ⚠️ 数据太少，可能格式不对")
            # Save HTML for debugging
            debug_path = os.path.join(DATA_DIR, f"debug_{label}.html")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(r.text)
            print(f"  HTML saved to {debug_path}")
            continue
        
        stats[label] = len(data)
        
        # Aggregate to school level (min score per school)
        school_scores = {}
        for school, val in data:
            if school not in school_scores or val < school_scores[school]:
                school_scores[school] = val
        
        # Add to classified
        if prov not in classified:
            classified[prov] = {"type": info["type"], "pairs": {}}
        
        pairs = classified[prov].get("pairs", {})
        added = 0
        for school, val in school_scores.items():
            key = f"{school}|{year}|{cat}"
            if is_rank:
                pairs[key] = {"score": None, "rank": val}
            else:
                if key not in pairs or pairs[key].get("score", 99999) > val:
                    pairs[key] = {"score": val, "rank": None}
                    added += 1
        
        classified[prov]["pairs"] = pairs
        print(f"  ✅ {prov}: {len(school_scores)} 学校级记录, 新增{added}条")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Save
with open(CLASSIFIED_PATH, "w", encoding="utf-8") as f:
    json.dump(classified, f, ensure_ascii=False)
print(f"\n✅ province_classified.json 已更新")
print(f"统计: {json.dumps(stats, ensure_ascii=False)}")
