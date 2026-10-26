#!/usr/bin/env python3
"""
从各省考试院官网获取2025年投档线数据
策略：直接访问各省考试院的"录取数据"或"投档线"页面
"""
import requests, json, re, os, time
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "exam_admin_2025")
os.makedirs(RESULT_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, "exam_admin_fetch.log")

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

# 各省考试院2025年投档线数据页面URL
# 这些URL需要根据实际情况调整
PROVINCE_URLS = {
    "江苏": [
        "https://www.jseea.cn/webfile/",
        "https://www.jseea.cn/zkzk/2025/",
    ],
    "浙江": [
        "https://www.zjzs.net/zkzs/2025/",
    ],
    "广东": [
        "https://eea.gd.gov.cn/zkzk/2025/",
    ],
    "湖北": [
        "https://www.hbea.edu.cn/zkzk/2025/",
    ],
    "湖南": [
        "https://www.hneao.edu.cn/zkzk/2025/",
    ],
    "四川": [
        "https://www.sceea.cn/zkzk/2025/",
    ],
    "陕西": [
        "https://www.sneea.cn/zkzk/2025/",
    ],
}

# 先尝试一个更直接的方法：搜索阳光高考的院校分数线数据
# 阳光高考 gaokao.chsi.com.cn 有院校库，可以通过API获取
# 院校库API: https://gaokao.chsi.com.cn/api/school/search?keyword=&page=1&size=20

# 尝试阳光高考API
def test_chsi_api():
    """测试阳光高考API"""
    log("=== 测试阳光高考API ===")
    
    # 院校搜索API
    urls = [
        "https://gaokao.chsi.com.cn/api/school/search?keyword=南京大学&page=1&size=5",
        "https://gaokao.chsi.com.cn/api/v1/school/list?keyword=南京大学&page=1&size=5",
        "https://gaokao.chsi.com.cn/api/v1/score/province?provinceId=32&year=2025&page=1&size=5",
    ]
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=10)
            log(f"  {url}: HTTP {r.status_code}, len={len(r.text)}")
            if r.status_code == 200:
                try:
                    data = json.loads(r.text)
                    log(f"    JSON: code={data.get('code')}, msg={data.get('message','')[:100]}")
                    if data.get('code') == 0 or data.get('code') == '0':
                        items = data.get('data', {}).get('item', []) if isinstance(data.get('data'), dict) else []
                        log(f"    Items: {len(items)}")
                        if items:
                            log(f"    Sample: {json.dumps(items[0], ensure_ascii=False)[:200]}")
                except:
                    if len(r.text) < 500:
                        log(f"    Text: {r.text[:200]}")
        except Exception as e:
            log(f"  {url}: Error: {e}")
        time.sleep(1)

# 尝试各省考试院
def test_exam_admin():
    """测试各省考试院官网"""
    log("=== 测试各省考试院官网 ===")
    
    for prov, urls in PROVINCE_URLS.items():
        for url in urls:
            try:
                r = session.get(url, headers=headers, timeout=10)
                log(f"  {prov} {url}: HTTP {r.status_code}, len={len(r.text)}")
                
                if r.status_code == 200:
                    # 查找Excel/CSV链接
                    excel_links = re.findall(r'href=["\']([^"\']*\.xlsx?|[^"\']*\.csv)["\']', r.text, re.IGNORECASE)
                    if excel_links:
                        log(f"    ✅ 找到 {len(excel_links)} 个Excel/CSV链接")
                        for link in excel_links[:3]:
                            log(f"      {link}")
                    
                    # 查找2025年投档线相关链接
                    score_links = re.findall(r'href=["\']([^"\']*2025[^"\']*)["\']', r.text, re.IGNORECASE)
                    if score_links:
                        log(f"    🔗 找到 {len(score_links)} 个2025年链接")
                        for link in score_links[:3]:
                            log(f"      {link}")
            except Exception as e:
                log(f"  {prov} {url}: Error: {e}")
            time.sleep(0.5)

# 尝试dxsbb.com（JS渲染，但之前北京/江苏/海南/辽宁有table标签）
def test_dxsbb():
    """测试dxsbb.com"""
    log("=== 测试dxsbb.com ===")
    # dxsbb.com的2025年数据页面
    # 之前的脚本已经有一些成功的URL
    urls = [
        "https://www.dxsbb.com/news/149119.html",  # 北京2025
        "https://www.dxsbb.com/news/149121.html",  # 上海2025
    ]
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=10)
            log(f"  {url}: HTTP {r.status_code}, len={len(r.text)}")
            # 检查是否有table标签
            tables = re.findall(r'<table[^>]*>', r.text)
            log(f"    Tables: {len(tables)}")
            if tables:
                # 提取表格行
                rows = re.findall(r'<tr[^>]*>(.*?)</tr>', r.text, re.DOTALL)
                log(f"    Rows: {len(rows)}")
                if rows:
                    cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
                    log(f"    First row cells: {[c.strip()[:30] for c in cells[:8]]}")
        except Exception as e:
            log(f"  {url}: Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    log("🔍 开始测试各数据源")
    test_chsi_api()
    test_exam_admin()
    test_dxsbb()
    log("\n✅ 测试完成")
