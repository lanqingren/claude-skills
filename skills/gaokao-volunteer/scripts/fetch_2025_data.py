#!/usr/bin/env python3
"""从EOL API抓取2025年各省投档数据"""
import requests, json, time, os
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data\multi_province"
LOG_FILE = r"D:\GitHub\hermescn\data\gaokao-data\fetch_2025.log"
os.makedirs(DATA_DIR, exist_ok=True)

PROVINCES = {
    11: "北京", 44: "广东", 32: "江苏", 42: "湖北",
    61: "陕西", 37: "山东", 33: "浙江", 46: "海南",
    43: "湖南", 13: "河北", 34: "安徽", 36: "江西",
    50: "重庆", 21: "辽宁", 14: "山西", 51: "四川",
    53: "云南", 64: "宁夏", 62: "甘肃", 15: "内蒙古",
}

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.gaokao.cn/",
}

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def fetch(pid, pname, year=2025, max_pages=100):
    all_items = []
    for page in range(1, max_pages + 1):
        params = {
            "access_token": "", "signsafe": "",
            "uri": "apidata/api/gk/score/province",
            "province_id": str(pid),
            "year": str(year),
            "page": str(page),
            "size": "20",
        }
        for attempt in range(4):
            try:
                r = session.get("https://api.eol.cn/gkcx/api/", params=params, headers=headers, timeout=15)
                data = r.json()
                code = data.get("code", "")
                if code == "1069":
                    wait = 15 * (attempt + 1)
                    log(f"  ⏳ {pname} {year} p{page} 限频,等{wait}s")
                    time.sleep(wait)
                    continue
                items = data.get("data", {}).get("item", [])
                if not items:
                    return all_items
                all_items.extend(items)
                if page % 5 == 0:
                    log(f"  📄 {pname} {year} p{page}: {len(all_items)}条")
                time.sleep(0.4)
                break
            except Exception as e:
                log(f"  ❌ {pname} {year} p{page} error: {e}")
                time.sleep(5)
                break
        else:
            log(f"  ⛔ {pname} {year} p{page} 4次失败,跳过")
            return all_items
    return all_items

log("=" * 60)
log("🚀 开始抓取2025年EOL API数据")
log("=" * 60)

for pid, pname in sorted(PROVINCES.items()):
    out_file = os.path.join(DATA_DIR, f"{pname}_2025_admission.json")
    if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
        log(f"✅ {pname} 2025 已存在,跳过")
        continue
    
    log(f"\n📥 抓取 {pname} (id={pid}) 2025...")
    items = fetch(pid, pname, 2025)
    
    if items:
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)
        log(f"💾 {pname} 2025: {len(items)}条 → {out_file}")
    else:
        log(f"⚠️ {pname} 2025 无数据")

log("\n✅ 2025年数据抓取完成")
