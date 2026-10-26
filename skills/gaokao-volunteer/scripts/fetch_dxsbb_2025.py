#!/usr/bin/env python3
"""
从dxsbb.com解析2025年投档线数据
dxsbb.com的页面是JS渲染的，但北京/上海等省份有server-rendered的table标签
需要处理编码问题（页面声明utf-8但实际是gbk/gb2312）
"""
import requests, json, re, os, time
from datetime import datetime
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_2025")
os.makedirs(RESULT_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, "dxsbb_2025_fetch.log")

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

# dxsbb.com 2025年数据页面URL
# 需要找到所有省份的URL
# 先测试已知的URL
DXSBB_URLS = {
    "北京": "https://www.dxsbb.com/news/149119.html",
    "上海": "https://www.dxsbb.com/news/149121.html",
}

def fetch_page(url):
    """获取页面并处理编码"""
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            log(f"  HTTP {r.status_code}")
            return None
        
        # 尝试多种编码
        content = r.content
        for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5']:
            try:
                text = content.decode(encoding)
                # 检查是否有乱码
                if '院校' in text or '专业' in text or '分数' in text or '投档' in text:
                    return text
            except:
                continue
        
        # 如果都不行，尝试从meta标签提取编码
        meta_match = re.search(r'<meta[^>]*charset=["\']?([^"\';\s>]+)', content.decode('ascii', errors='ignore'))
        if meta_match:
            enc = meta_match.group(1).lower()
            try:
                return content.decode(enc)
            except:
                pass
        
        # 最后尝试utf-8（即使有乱码）
        return content.decode('utf-8', errors='replace')
    except Exception as e:
        log(f"  Error: {e}")
        return None

def parse_table(text, prov_name):
    """解析HTML表格数据"""
    # 找所有table
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    if not tables:
        log(f"  无table标签")
        return []
    
    all_records = []
    
    for ti, table in enumerate(tables):
        # 找所有行
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 3:
            continue
        
        # 解析表头
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        
        log(f"  Table {ti}: {len(rows)}行, 表头: {header_cells[:8]}")
        
        # 检查是否是数据表（需要有"院校"或"学校"列）
        has_school = any('院校' in h or '学校' in h for h in header_cells)
        has_score = any('分' in h or '线' in h for h in header_cells)
        
        if not has_school:
            log(f"    跳过（无院校列）")
            continue
        
        # 找列索引
        school_idx = None
        score_idx = None
        rank_idx = None
        batch_idx = None
        type_idx = None
        
        for i, h in enumerate(header_cells):
            if '院校' in h or '学校' in h:
                school_idx = i
            elif '总分' in h or '分数' in h or '投档' in h:
                if score_idx is None:
                    score_idx = i
            elif '位次' in h or '排名' in h:
                rank_idx = i
            elif '批次' in h:
                batch_idx = i
            elif '类型' in h or '科类' in h:
                type_idx = i
        
        if school_idx is None:
            log(f"    跳过（无院校列）")
            continue
        
        log(f"    院校列={school_idx}, 分数列={score_idx}, 位次列={rank_idx}, 批次列={batch_idx}")
        
        # 解析数据行
        records = []
        for row in rows[1:]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            
            if len(cells) <= school_idx:
                continue
            
            school = cells[school_idx].strip()
            if not school or school == '-' or len(school) < 2:
                continue
            
            score = None
            if score_idx is not None and len(cells) > score_idx:
                score_str = cells[score_idx].strip()
                try:
                    score = int(score_str)
                except:
                    pass
            
            rank = None
            if rank_idx is not None and len(cells) > rank_idx:
                rank_str = cells[rank_idx].strip()
                try:
                    rank = int(rank_str)
                except:
                    pass
            
            batch = cells[batch_idx].strip() if batch_idx and len(cells) > batch_idx else ''
            cat = cells[type_idx].strip() if type_idx and len(cells) > type_idx else ''
            
            records.append({
                'school': school,
                'score': score,
                'rank': rank,
                'batch': batch,
                'category': cat,
            })
        
        log(f"    解析出 {len(records)} 条记录")
        all_records.extend(records)
    
    return all_records

# 先测试北京和上海
log("=== 测试dxsbb.com 2025年数据解析 ===")

for prov, url in DXSBB_URLS.items():
    log(f"\n--- {prov} ---")
    text = fetch_page(url)
    if text:
        records = parse_table(text, prov)
        if records:
            log(f"  ✅ {prov}: {len(records)} 条记录")
            # 保存
            out_path = os.path.join(RESULT_DIR, f"{prov}_2025.json")
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            
            # 打印样本
            for r in records[:3]:
                log(f"    {r['school']}: {r['score']}分 位次{r['rank']} {r['batch']} {r['category']}")
        else:
            log(f"  ❌ {prov}: 无数据")
    time.sleep(1)

# 尝试发现更多省份的URL
log("\n=== 尝试发现更多省份URL ===")
# dxsbb.com的URL格式通常是 /news/{id}.html
# 北京=149119, 上海=149121，尝试附近ID
# 先获取页面列表
try:
    # 尝试从dxsbb.com的2025年数据汇总页获取链接
    list_urls = [
        "https://www.dxsbb.com/news/list_1.html",  # 文章列表
    ]
    for url in list_urls:
        try:
            r = session.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                text = r.content.decode('utf-8', errors='replace')
                # 找所有链接
                links = re.findall(r'href=["\'](/news/(\d+)\.html)["\']', text)
                log(f"  {url}: 找到 {len(links)} 个链接")
                for link, lid in links[:20]:
                    # 找链接文本
                    link_text = re.findall(rf'href=["\']{re.escape(link)}["\'][^>]*>([^<]+)<', text)
                    if link_text:
                        log(f"    {link} -> {link_text[0].strip()}")
        except Exception as e:
            log(f"  {url}: Error: {e}")
except Exception as e:
    log(f"  列表获取失败: {e}")

log("\n✅ 测试完成")
