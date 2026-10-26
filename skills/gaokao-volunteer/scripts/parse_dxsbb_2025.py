#!/usr/bin/env python3
"""
解析dxsbb.com上的2025年投档线数据页面
支持多种表格格式：
1. 北京格式: 序号|院校代码|院校名称|专业组代码|专业组名称|总分|备注
2. 上海格式: 院校专业组代码|院校专业组名称|投档线（含"分及以上"）
3. 浙江格式: 学校代号|学校名称|专业代号|专业名称|分数线
4. 山东格式: 专业代码及名称|院校代码及名称|最低位次
5. 河北格式: 院校代号|院校名称|专业代号|专业名称|投档最低分|备注
"""
import requests, re, os, time, json
from datetime import datetime
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_2025")
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
LOG_FILE = os.path.join(DATA_DIR, "dxsbb_2025_parse.log")

os.makedirs(RESULT_DIR, exist_ok=True)

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
    except Exception as e:
        log(f"  Error fetching {url}: {e}")
        return None

def parse_score(text):
    """解析分数，处理'580分及以上'等格式"""
    if not text or text == '-':
        return None
    text = text.strip()
    # 提取数字
    m = re.match(r'^(\d+)', text)
    if m:
        return int(m.group(1))
    return None

def parse_table(text, prov_name, page_type):
    """解析HTML表格，返回记录列表"""
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    if not tables:
        return []
    
    all_records = []
    
    for ti, table in enumerate(tables):
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 3:
            continue
        
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        
        if not any('院校' in h or '学校' in h for h in header_cells):
            continue
        
        # 找列索引
        school_idx = None
        score_idx = None
        rank_idx = None
        code_idx = None
        
        for i, h in enumerate(header_cells):
            h_lower = h.lower()
            if '院校名称' in h or ('院校' in h and '名称' in h):
                school_idx = i
            elif '学校名称' in h or ('学校' in h and '名称' in h):
                if school_idx is None:
                    school_idx = i
            elif '总分' in h or '分数线' in h or '投档最低分' in h or '投档线' in h or '最低分' in h:
                if score_idx is None:
                    score_idx = i
            elif '最低位次' in h or '位次' in h:
                rank_idx = i
            elif '院校代码' in h or '学校代号' in h or '院校代号' in h:
                code_idx = i
        
        if school_idx is None:
            # 尝试用"院校专业组名称"作为学校列
            for i, h in enumerate(header_cells):
                if '院校专业组名称' in h:
                    school_idx = i
                    break
        
        if school_idx is None:
            continue
        
        log(f"  Table {ti}: {len(rows)}行, 学校={school_idx}, 分数={score_idx}, 位次={rank_idx}")
        
        for row in rows[1:]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            
            if len(cells) <= max(school_idx, score_idx if score_idx else 0):
                continue
            
            school = cells[school_idx].strip()
            # 清理学校名称
            school = re.sub(r'\(\d+\)$', '', school).strip()  # 去掉末尾的(01)等
            school = re.sub(r'\[\d+\]$', '', school).strip()  # 去掉末尾的[01]等
            
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
            
            all_records.append({
                'school': school,
                'score': score,
                'rank': rank,
                'source': f"dxsbb_{prov_name}_{page_type}",
            })
    
    return all_records

# 要解析的页面
pages = [
    ("北京", "本科", "https://www.dxsbb.com/news/149119.html"),
    ("北京", "专科", "https://www.dxsbb.com/news/149120.html"),
    ("上海", "本科", "https://www.dxsbb.com/news/149121.html"),
    ("浙江", "一段", "https://www.dxsbb.com/news/149123.html"),
    ("浙江", "二段", "https://www.dxsbb.com/news/149124.html"),
    ("山东", "第1次", "https://www.dxsbb.com/news/149125.html"),
    ("山东", "第2次", "https://www.dxsbb.com/news/149126.html"),
    ("山东", "第3次", "https://www.dxsbb.com/news/149127.html"),
    ("河北", "物理", "https://www.dxsbb.com/news/149128.html"),
    ("河北", "历史", "https://www.dxsbb.com/news/149129.html"),
]

# 解析所有页面
all_new_data = defaultdict(lambda: defaultdict(list))  # {省份: {科类: [记录]}}

log("=== 开始解析dxsbb.com 2025年数据 ===")

for prov, page_type, url in pages:
    log(f"\n--- {prov} {page_type} ---")
    text = fetch_page(url)
    if not text:
        log(f"  ❌ 无法获取页面")
        continue
    
    records = parse_table(text, prov, page_type)
    if not records:
        log(f"  ❌ 无数据")
        continue
    
    log(f"  ✅ {len(records)} 条记录")
    
    # 按科类分组
    if '物理' in page_type:
        cat = '物理'
    elif '历史' in page_type:
        cat = '历史'
    elif '专科' in page_type:
        cat = '专科'
    else:
        cat = '综合'  # 上海/浙江/山东等不分科类的
    
    all_new_data[prov][cat].extend(records)
    
    # 打印样本
    for r in records[:3]:
        log(f"    {r['school']}: {r['score']}分 位次{r['rank']}")
    
    time.sleep(0.5)

# 统计
log(f"\n=== 解析结果汇总 ===")
total = 0
for prov, cats in sorted(all_new_data.items()):
    for cat, records in sorted(cats.items()):
        scores = [r['score'] for r in records if r['score']]
        ranks = [r['rank'] for r in records if r['rank']]
        log(f"  {prov} {cat}: {len(records)}条, "
            f"分数{min(scores) if scores else 'N/A'}-{max(scores) if scores else 'N/A'}, "
            f"位次{len(ranks)}条有数据")
        total += len(records)
log(f"\n总计: {total} 条新数据")

# 保存原始数据
with open(os.path.join(RESULT_DIR, "dxsbb_2025_raw.json"), 'w', encoding='utf-8') as f:
    json.dump({k: dict(v) for k, v in all_new_data.items()}, f, ensure_ascii=False, indent=2)

log(f"\n✅ 原始数据保存到 {RESULT_DIR}/dxsbb_2025_raw.json")
