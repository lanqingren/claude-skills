#!/usr/bin/env python3
"""
多渠道2025年数据采集脚本
数据源优先级：
1. 阳光高考网 API（掌上高考）
2. 各省考试院官网（通过浏览器）
3. dxsbb.com（JS渲染，需浏览器）
4. EOL API（限频严重，最后手段）

当前策略：先测试各API可用性，选择最优数据源
"""
import requests, json, time, os
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
LOG_FILE = os.path.join(DATA_DIR, "test_sources.log")

session = requests.Session()
session.trust_env = False

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ====== 数据源1: 掌上高考 API ======
def test_gaokao_cn():
    """掌上高考 gaokao.cn API"""
    log("=== 测试掌上高考 API ===")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.gaokao.cn/",
    }
    # 尝试不同的API端点
    endpoints = [
        "https://www.gaokao.cn/api/gk/score/province",
        "https://api.gaokao.cn/gkcx/api/",
    ]
    for url in endpoints:
        try:
            r = session.get(url, headers=headers, timeout=10)
            log(f"  {url}: HTTP {r.status_code}, len={len(r.text)}")
            if r.status_code == 200:
                log(f"    Preview: {r.text[:200]}")
        except Exception as e:
            log(f"  {url}: Error: {e}")

# ====== 数据源2: 阳光高考 API ======
def test_eol():
    """阳光高考 EOL API"""
    log("=== 测试阳光高考 EOL API ===")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.eol.cn/",
    }
    # 尝试不同的URI
    uris = [
        "apidata/api/gk/score/province",
        "api/gk/score/province",
    ]
    for uri in uris:
        params = {
            "access_token": "", "signsafe": "",
            "uri": uri,
            "province_id": "32",
            "year": "2025",
            "page": "1",
            "size": "3",
        }
        try:
            r = session.get("https://api.eol.cn/gkcx/api/", params=params, headers=headers, timeout=10)
            data = r.json()
            code = data.get("code", "")
            log(f"  URI={uri}: code={code}")
            if code == "0" or code == "1064":
                d = data.get("data", {})
                items = d.get("item", []) if isinstance(d, dict) else []
                log(f"    Items: {len(items)}")
                if items:
                    log(f"    Sample: {json.dumps(items[0], ensure_ascii=False)[:200]}")
            elif code == "1069":
                log(f"    ⏳ 限频，等待后重试...")
                time.sleep(20)
                r2 = session.get("https://api.eol.cn/gkcx/api/", params=params, headers=headers, timeout=10)
                data2 = r2.json()
                code2 = data2.get("code", "")
                log(f"    重试后: code={code2}")
                if code2 == "0":
                    d = data2.get("data", {})
                    items = d.get("item", []) if isinstance(d, dict) else []
                    log(f"    Items: {len(items)}")
        except Exception as e:
            log(f"  URI={uri}: Error: {e}")

# ====== 数据源3: 阳光高考院校库 ======
def test_eol_school():
    """阳光高考院校库API"""
    log("=== 测试阳光高考院校库 API ===")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.eol.cn/",
    }
    # 院校库API
    urls = [
        "https://api.eol.cn/gkcx/api/?uri=apidata/api/gk/school/province&province_id=32&page=1&size=3",
    ]
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=10)
            data = r.json()
            code = data.get("code", "")
            log(f"  {url[:80]}: code={code}")
            if code == "0":
                d = data.get("data", {})
                items = d.get("item", []) if isinstance(d, dict) else []
                log(f"    Items: {len(items)}")
        except Exception as e:
            log(f"  Error: {e}")

# ====== 数据源4: 各省考试院 ======
def test_province_exam():
    """各省考试院官网 - 测试几个主要省份"""
    log("=== 测试各省考试院官网 ===")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    # 江苏省考试院
    urls = [
        ("江苏", "https://www.jseea.cn/webfile/"),
        ("浙江", "https://www.zjzs.net/"),
        ("广东", "https://eea.gd.gov.cn/"),
    ]
    for name, url in urls:
        try:
            r = session.get(url, headers=headers, timeout=10)
            log(f"  {name} {url}: HTTP {r.status_code}, len={len(r.text)}")
        except Exception as e:
            log(f"  {name}: Error: {e}")

if __name__ == "__main__":
    log("🔍 开始测试各数据源可用性")
    test_gaokao_cn()
    test_eol()
    test_eol_school()
    test_province_exam()
    log("\n✅ 测试完成")
