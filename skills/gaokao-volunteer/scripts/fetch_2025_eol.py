#!/usr/bin/env python3
"""
采集2025年各省高考投档线数据（EOL API）
- 针对当前缺2025年数据的25个省份
- 支持断点续传
- 限频自动重试
- 结果保存到独立目录，后续手动整合
"""
import requests, json, time, os, sys
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
FETCH_DIR = os.path.join(DATA_DIR, "fetch_2025")
LOG_FILE = os.path.join(DATA_DIR, "fetch_2025.log")
os.makedirs(FETCH_DIR, exist_ok=True)

# 缺2025年数据的省份（已有2025数据的6省：上海、北京、山东、河北、浙江、贵州 跳过）
PROVINCES = {
    12: "天津", 14: "山西", 15: "内蒙古",
    21: "辽宁", 22: "吉林", 23: "黑龙江",
    32: "江苏", 34: "安徽", 35: "福建", 36: "江西",
    41: "河南", 42: "湖北", 43: "湖南",
    44: "广东", 45: "广西", 46: "海南",
    50: "重庆", 51: "四川", 52: "贵州", 53: "云南", 54: "西藏",
    61: "陕西", 62: "甘肃", 63: "青海", 64: "宁夏", 65: "新疆",
}
# 注意：贵州已有2025数据但量不大(1095)，可以补更多
# 上海/北京/山东/河北/浙江 已有充足2025数据，跳过

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

def fetch(pid, pname, year=2025, max_pages=200):
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
        for attempt in range(5):
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
                if page % 10 == 0:
                    log(f"  📄 {pname} {year} p{page}: {len(all_items)}条")
                time.sleep(0.4)
                break
            except Exception as e:
                if attempt < 4:
                    time.sleep(3)
                else:
                    log(f"  ❌ {pname} {year} p{page}: {e}")
                    return all_items
        time.sleep(0.4)
    return all_items

def main():
    # 清空日志
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== 2025年数据采集开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    log(f"🚀 开始采集 {len(PROVINCES)}个省份的2025年数据")
    start = time.time()
    results = {}
    
    for idx, (pid, pname) in enumerate(sorted(PROVINCES.items()), 1):
        fname = f"{pname}_2025_admission.json"
        fpath = os.path.join(FETCH_DIR, fname)
        
        # 断点续传
        if os.path.exists(fpath):
            try:
                existing = json.load(open(fpath, "r", encoding="utf-8"))
                if isinstance(existing, list) and len(existing) >= 50:
                    log(f"[{idx}/{len(PROVINCES)}] ⏭️ {pname} 2025: 已有{len(existing)}条，跳过")
                    results[pname] = len(existing)
                    continue
            except:
                pass
        
        log(f"[{idx}/{len(PROVINCES)}] 📥 {pname} 2025...")
        items = fetch(pid, pname, 2025)
        
        if items:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False)
            log(f"  ✅ {pname} 2025: {len(items)}条")
            results[pname] = len(items)
        else:
            log(f"  ⚪ {pname} 2025: 无数据")
            results[pname] = 0
        
        elapsed = time.time() - start
        log(f"  ⏱️ 进度 {idx}/{len(PROVINCES)} | {elapsed/60:.1f}分钟")
    
    # 汇总
    log(f"\n{'='*50}")
    log(f"🏁 2025年数据采集完成! 总耗时 {elapsed/60:.1f}分钟")
    log(f"{'='*50}")
    total = 0
    for pname, cnt in sorted(results.items(), key=lambda x: -x[1]):
        status = "✅" if cnt > 0 else "❌"
        log(f"  {status} {pname}: {cnt}条")
        total += cnt
    log(f"\n总计: {total}条")

if __name__ == "__main__":
    main()
