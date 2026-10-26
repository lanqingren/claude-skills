#!/usr/bin/env python3
"""全国各省高考投档数据批量下载器 v4
- 31省 × 2023+2024
- 0.4s间隔（更快）
- 日志写文件
- 断点续传
"""
import requests, json, time, os, sys
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data\multi_province"
LOG_FILE = r"D:\GitHub\hermescn\data\gaokao-data\fetch.log"
os.makedirs(DATA_DIR, exist_ok=True)

PROVINCES = {
    11: "北京", 12: "天津", 13: "河北", 14: "山西", 15: "内蒙古",
    21: "辽宁", 22: "吉林", 23: "黑龙江",
    31: "上海", 32: "江苏", 33: "浙江", 34: "安徽", 35: "福建", 36: "江西", 37: "山东",
    41: "河南", 42: "湖北", 43: "湖南",
    44: "广东", 45: "广西", 46: "海南",
    50: "重庆", 51: "四川", 52: "贵州", 53: "云南", 54: "西藏",
    61: "陕西", 62: "甘肃", 63: "青海", 64: "宁夏", 65: "新疆",
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

def fetch(pid, pname, year, max_pages=100):
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
                if code == "1064":
                    return all_items
                
                d = data.get("data", {})
                items = d.get("item", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
                
                if not items:
                    return all_items
                all_items.extend(items)
                
                if len(items) < 20:
                    return all_items
                break
            except Exception as e:
                if attempt < 3:
                    time.sleep(3)
                else:
                    log(f"  ❌ {pname} {year} p{page}: {e}")
                    return all_items
        
        time.sleep(0.4)
    
    return all_items

def main():
    years = [2023, 2024]
    start = time.time()
    
    # 清空日志
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== 下载开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    log(f"🚀 开始下载 31省×{len(years)}年")
    
    done = 0
    for pid, pname in sorted(PROVINCES.items()):
        done += 1
        
        for year in years:
            fname = f"{pname}_{year}_admission.json"
            fpath = os.path.join(DATA_DIR, fname)
            
            # 断点续传
            if os.path.exists(fpath):
                try:
                    existing = json.load(open(fpath, "r", encoding="utf-8"))
                    if isinstance(existing, list) and len(existing) >= 100:
                        continue  # 已有数据，跳过
                except:
                    pass
            
            items = fetch(pid, pname, year)
            if items:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False)
                log(f"[{done}/31] ✅ {pname} {year}: {len(items)}条")
            else:
                log(f"[{done}/31] ⚪ {pname} {year}: 无数据")
            
            time.sleep(0.2)
        
        elapsed = time.time() - start
        log(f"  ⏱️  进度 {done}/31省 | {elapsed/60:.1f}分钟")
    
    # 汇总
    log("\n🏁 完成! 各省数据量:")
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith("_admission.json") and "type" not in f:
            try:
                d = json.load(open(os.path.join(DATA_DIR, f), "r", encoding="utf-8"))
                log(f"  {f}: {len(d) if isinstance(d,list) else '?'}条")
            except:
                log(f"  {f}: 解析失败")
    
    total_elapsed = time.time() - start
    log(f"\n总耗时: {total_elapsed/60:.1f}分钟")

if __name__ == "__main__":
    main()
