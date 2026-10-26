#!/usr/bin/env python3
"""全国各省高考投档数据批量下载器 v3
- 31个省份 × 2023+2024两年
- 不带type参数，获取全部科类
- size=20最大页大小
- 自动限频+重试
"""
import requests, json, time, os, sys
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data\multi_province"
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.gaokao.cn/",
}

stats = {"total_requests": 0, "success": 0, "rate_limited": 0, "errors": 0}


def fetch_province_year(pid, pname, year, max_pages=100):
    """下载某省某年全部投档数据（所有科类混合）"""
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
        
        success = False
        for attempt in range(4):
            try:
                stats["total_requests"] += 1
                r = session.get("https://api.eol.cn/gkcx/api/", params=params, headers=headers, timeout=15)
                data = r.json()
                code = data.get("code", "")
                
                if code == "1069":
                    stats["rate_limited"] += 1
                    wait = 20 * (attempt + 1)
                    print(f"    ⏳ 限频等待{wait}s (p{page})", flush=True)
                    time.sleep(wait)
                    continue
                
                if code == "1064":
                    return all_items  # 接口不存在
                
                d = data.get("data", {})
                if isinstance(d, dict):
                    items = d.get("item", [])
                elif isinstance(d, list):
                    items = d
                else:
                    items = []
                
                stats["success"] += 1
                success = True
                
                if not items:
                    return all_items
                
                all_items.extend(items)
                
                if len(items) < 20:
                    return all_items  # 最后一页
                
                break  # 成功
                
            except Exception as e:
                stats["errors"] += 1
                if attempt < 3:
                    time.sleep(5)
                else:
                    print(f"    ❌ p{page}: {e}", flush=True)
                    return all_items
        
        if not success:
            print(f"    ⚠️ p{page} 重试4次仍失败，跳过", flush=True)
            return all_items
        
        time.sleep(0.8)
    
    return all_items


def main():
    years = [2023, 2024]
    start_time = time.time()
    
    # 命令行参数：指定省份
    target_pids = None
    if len(sys.argv) > 1:
        target_pids = [int(x) for x in sys.argv[1:]]
    
    provinces_to_run = {pid: name for pid, name in PROVINCES.items() if not target_pids or pid in target_pids}
    
    print(f"🚀 全国高考投档数据下载器 v3", flush=True)
    print(f"   省份: {len(provinces_to_run)}个 | 年份: {years} | 页大小: 20", flush=True)
    print(f"   开始: {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print(flush=True)
    
    done_count = 0
    for pid, pname in sorted(provinces_to_run.items()):
        done_count += 1
        
        print(f"[{done_count}/{len(provinces_to_run)}] 📂 {pname}(pid={pid})", flush=True)
        
        for year in years:
            fname = f"{pname}_{year}_admission.json"
            fpath = os.path.join(DATA_DIR, fname)
            
            # 已有>500条则跳过
            if os.path.exists(fpath):
                try:
                    existing = json.load(open(fpath, "r", encoding="utf-8"))
                    if isinstance(existing, list) and len(existing) >= 500:
                        print(f"  ⏭️  {year}: 已有{len(existing)}条，跳过", flush=True)
                        continue
                except:
                    pass
            
            items = fetch_province_year(pid, pname, year, max_pages=100)
            
            if items:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False)
                print(f"  ✅ {year}: {len(items)}条", flush=True)
            else:
                print(f"  ⚪ {year}: 无数据", flush=True)
            
            time.sleep(0.3)
        
        elapsed = time.time() - start_time
        print(f"  ⏱️  耗时{elapsed/60:.1f}分钟 | 请求{stats['total_requests']}次(限频{stats['rate_limited']})", flush=True)
    
    elapsed = time.time() - start_time
    print(f"\n🏁 完成! 耗时{elapsed/60:.1f}分钟 总请求{stats['total_requests']}次", flush=True)
    
    # 统计
    print(f"\n📋 各省数据量:", flush=True)
    province_stats = {}
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith("_admission.json") and "type" not in f:
            pname = f.split("_")[0]
            try:
                data = json.load(open(os.path.join(DATA_DIR, f), "r", encoding="utf-8"))
                count = len(data) if isinstance(data, list) else 0
                province_stats[pname] = province_stats.get(pname, 0) + count
            except:
                pass
    
    total = 0
    for pname in sorted(province_stats.keys(), key=lambda x: province_stats[x], reverse=True):
        print(f"  {pname}: {province_stats[pname]:,}条", flush=True)
        total += province_stats[pname]
    print(f"  ────────", flush=True)
    print(f"  总计: {total:,}条", flush=True)


if __name__ == "__main__":
    main()
