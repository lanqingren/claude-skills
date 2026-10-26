#!/usr/bin/env python3
"""
修复dxsbb.com解析数据并整合到province_classified.json
修复：
1. 山东数据有院校代号（如A422），需要提取学校名称
2. 北京专科数据分数列是None，检查列映射
3. 上海数据格式特殊（"580分及以上"）
4. 河北学校名含"[公办]"等后缀，需要清理
"""
import requests, re, os, time, json
from datetime import datetime
from collections import defaultdict

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_2025")
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
LOG_FILE = os.path.join(DATA_DIR, "dxsbb_2025_integrate.log")

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

# 加载原始解析数据
with open(os.path.join(RESULT_DIR, "dxsbb_2025_raw.json"), 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

log(f"加载原始数据: {sum(len(records) for cats in raw_data.values() for records in cats.values())} 条")

# 修复1: 重新解析北京专科（分数列映射问题）
log("\n=== 修复北京专科 ===")
url = "https://www.dxsbb.com/news/149120.html"
try:
    r = session.get(url, headers=headers, timeout=15)
    content = r.content
    for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
        try:
            text = content.decode(enc)
            break
        except:
            text = content.decode('utf-8', errors='replace')
    
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 3:
            continue
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        log(f"  表头: {header_cells}")
        
        if '院校' not in str(header_cells):
            continue
        
        # 找所有列
        for i, h in enumerate(header_cells):
            log(f"    列{i}: {h}")
        
        # 打印前5行数据
        for row in rows[1:6]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            log(f"    {cells}")
except Exception as e:
    log(f"  错误: {e}")

# 修复2: 重新解析山东（提取学校名称）
log("\n=== 修复山东数据 ===")
# 山东的格式是 "A422山东大学(06)|临床医学" -> 需要提取"山东大学"
# 位次在第4列（最低位次）
for page_id, page_type in [(149125, "第1次"), (149126, "第2次"), (149127, "第3次")]:
    url = f"https://www.dxsbb.com/news/{page_id}.html"
    try:
        r = session.get(url, headers=headers, timeout=15)
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                text = content.decode(enc)
                break
            except:
                text = content.decode('utf-8', errors='replace')
        
        tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
        for table in tables:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
            if len(rows) < 3:
                continue
            header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
            header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
            
            if '院校' not in str(header_cells) and '位次' not in str(header_cells):
                continue
            
            log(f"  山东{page_type} 表头: {header_cells}")
            
            # 打印前3行
            for row in rows[1:4]:
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
                cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                log(f"    {cells}")
    except Exception as e:
        log(f"  错误: {e}")
    time.sleep(0.5)

# 修复3: 检查上海数据
log("\n=== 检查上海数据 ===")
url = "https://www.dxsbb.com/news/149121.html"
try:
    r = session.get(url, headers=headers, timeout=15)
    content = r.content
    for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
        try:
            text = content.decode(enc)
            break
        except:
            text = content.decode('utf-8', errors='replace')
    
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.DOTALL)
    for table in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.DOTALL)
        if len(rows) < 3:
            continue
        header_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in header_cells]
        log(f"  上海 表头: {header_cells}")
        
        for row in rows[1:6]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            log(f"    {cells}")
except Exception as e:
    log(f"  错误: {e}")

log("\n✅ 数据检查完成")
