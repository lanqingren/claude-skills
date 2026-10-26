#!/usr/bin/env python3
"""
完整修复dxsbb.com数据并整合到province_classified.json
"""
import requests, re, os, time, json
from datetime import datetime
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_2025")
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
LOG_FILE = os.path.join(DATA_DIR, "dxsbb_2025_integrate.log")

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def fetch_page(url):
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                text = content.decode(enc)
                if '院校' in text or '学校' in text:
                    return text
            except:
                continue
        return content.decode('utf-8', errors='replace')
    except:
        return None

def parse_score(text):
    if not text or text == '-':
        return None
    text = text.strip()
    m = re.match(r'^(\d+)', text)
    return int(m.group(1)) if m else None

def extract_school_name(raw_name):
    """从原始学校名称中提取干净名称"""
    # 去掉 [公办] [民办] 等后缀
    name = re.sub(r'\[.*?\]', '', raw_name).strip()
    # 去掉 (中外合办) 等后缀
    name = re.sub(r'\(.*?\)', '', name).strip()
    # 去掉 院校代号前缀（如A422山东大学 -> 山东大学）
    name = re.sub(r'^[A-Z]\d{3}', '', name).strip()
    return name

# 加载已分类数据
with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
    classified = json.load(f)

old_total = sum(len(p.get('pairs', {})) for p in classified.values())
log(f"当前数据: {old_total} pairs")

# 定义要处理的页面
pages = [
    # (省份, 科类标记, URL, 表格格式)
    # 格式: school_idx, score_idx, rank_idx, 需要清理学校名
    ("北京", "综合", "https://www.dxsbb.com/news/149119.html", 2, 5, None, False),  # 本科
    ("北京", "专科", "https://www.dxsbb.com/news/149120.html", 2, 5, None, False),  # 专科
    ("上海", "综合", "https://www.dxsbb.com/news/149121.html", 1, 2, None, False),  # 特殊格式
    ("浙江", "综合", "https://www.dxsbb.com/news/149123.html", 1, 4, None, False),  # 一段
    ("浙江", "综合", "https://www.dxsbb.com/news/149124.html", 1, 4, None, False),  # 二段
    ("山东", "综合", "https://www.dxsbb.com/news/149125.html", 1, None, 2, True),   # 位次
    ("山东", "综合", "https://www.dxsbb.com/news/149126.html", 3, None, 4, True),   # 位次
    ("山东", "综合", "https://www.dxsbb.com/news/149127.html", 1, None, 2, True),   # 位次
    ("河北", "物理", "https://www.dxsbb.com/news/149128.html", 1, 4, None, True),   # 物理
    ("河北", "历史", "https://www.dxsbb.com/news/149129.html", 1, 4, None, True),   # 历史
]

total_new = 0
total_updated = 0
integrate_stats = defaultdict(int)

for prov, cat, url, school_idx, score_idx, rank_idx, clean_name in pages:
    log(f"\n--- {prov} {cat} ---")
    text = fetch_page(url)
    if not text:
        log(f"  ❌ 无法获取")
        continue
    
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 3:
            continue
        
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        
        if not any('院校' in h or '学校' in h for h in header_cells):
            continue
        
        # 上海特殊处理：分数是"580分及以上"
        is_shanghai = (prov == "上海")
        # 山东特殊处理：只有位次没有分数
        is_shandong = (prov == "山东")
        
        new_count = 0
        updated_count = 0
        
        for row in rows[1:]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            
            if len(cells) <= max(school_idx, score_idx or 0, rank_idx or 0):
                continue
            
            raw_school = cells[school_idx].strip()
            if clean_name:
                school = extract_school_name(raw_school)
            else:
                school = raw_school
            
            if not school or len(school) < 2:
                continue
            
            score = None
            if score_idx is not None and len(cells) > score_idx:
                score = parse_score(cells[score_idx])
            
            rank = None
            if rank_idx is not None and len(cells) > rank_idx:
                rank_str = cells[rank_idx].strip().replace(',', '').replace('，', '')
                try:
                    rank = int(rank_str)
                except:
                    pass
            
            # 上海特殊处理：分数是"580分及以上"
            if is_shanghai and score is not None:
                # 保持原始分数（最低门槛分）
                pass
            
            # 构建key
            year = "2025"
            key = f"{school}|{year}|{cat}"
            
            if prov not in classified:
                classified[prov] = {"type": "unknown", "pairs": {}}
            
            pairs = classified[prov].get("pairs", {})
            
            if key not in pairs:
                pairs[key] = {"score": score, "rank": rank}
                new_count += 1
            else:
                existing = pairs[key]
                if score and not existing.get('score'):
                    existing['score'] = score
                    updated_count += 1
                if rank and not existing.get('rank'):
                    existing['rank'] = rank
                    updated_count += 1
        
        classified[prov]["pairs"] = pairs
        total_new += new_count
        total_updated += updated_count
        integrate_stats[f"{prov}_{cat}"] = new_count
        log(f"  ✅ 新增 {new_count}, 更新 {updated_count}")

# 保存
with open(CLASSIFIED_PATH, 'w', encoding='utf-8') as f:
    json.dump(classified, f, ensure_ascii=False)

new_total = sum(len(p.get('pairs', {})) for p in classified.values())

log(f"\n{'='*60}")
log(f"✅ 数据整合完成")
log(f"   新增: {total_new} 对")
log(f"   更新: {total_updated} 对")
log(f"   总量: {old_total} → {new_total} ({new_total-old_total:+d})")
log(f"\n=== 各页面对比 ===")
for k, v in sorted(integrate_stats.items()):
    log(f"   {k}: +{v}")

# 最终统计
log(f"\n=== 最终数据覆盖 ===")
for prov, pdata in sorted(classified.items()):
    pairs = pdata.get('pairs', {})
    years = set()
    for k in pairs:
        parts = k.split('|')
        if len(parts) >= 2:
            years.add(parts[1])
    ptype = pdata.get('type', '?')
    log(f"  {prov}({ptype}): {len(pairs)} pairs [{','.join(sorted(years))}]")
