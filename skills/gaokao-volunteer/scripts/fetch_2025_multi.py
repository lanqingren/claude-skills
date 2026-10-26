#!/usr/bin/env python3
"""
多渠道2025年数据采集策略
数据源优先级：
1. 各省考试院官网发布的2025年投档线Excel/CSV
2. 阳光高考院校库API（掌上高考）
3. dxsbb.com（JS渲染，需浏览器）
4. EOL API（限频严重，最后手段）

当前策略：
- 先尝试从考试院官网获取Excel/CSV
- 如果不行，用浏览器从dxsbb.com获取
- 最后才用EOL API（需要等限频恢复）
"""
import requests, json, time, os, re
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
FETCH_DIR = os.path.join(DATA_DIR, "fetch_2025")
LOG_FILE = os.path.join(DATA_DIR, "fetch_2025_v2.log")
os.makedirs(FETCH_DIR, exist_ok=True)

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

# ====== 策略1: 从考试院官网获取Excel/CSV ======
def fetch_from_exam_admin(province_name, exam_admin_url):
    """从考试院官网获取2025年投档线数据"""
    log(f"  📥 尝试 {province_name} 考试院: {exam_admin_url}")
    try:
        r = session.get(exam_admin_url, headers=headers, timeout=15)
        if r.status_code == 200:
            # 检查是否有Excel/CSV链接
            content = r.text
            # 查找Excel文件链接
            excel_links = re.findall(r'href=["\']([^"\']*\.xlsx?|[^"\']*\.csv)["\']', content, re.IGNORECASE)
            if excel_links:
                log(f"    ✅ 找到 {len(excel_links)} 个Excel/CSV文件")
                return excel_links
            else:
                log(f"    ⚪ 未找到Excel/CSV文件")
        else:
            log(f"    ❌ HTTP {r.status_code}")
    except Exception as e:
        log(f"    ❌ Error: {e}")
    return []

# ====== 策略2: 阳光高考院校库API ======
def fetch_from_chsi(province_id, year=2025):
    """从阳光高考院校库获取数据"""
    log(f"  📥 尝试阳光高考院校库 {province_id} {year}")
    # 阳光高考院校库API
    url = f"https://gaokao.chsi.com.cn/score/province?provinceId={province_id}&year={year}"
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            log(f"    ✅ 获取到数据，长度={len(r.text)}")
            return r.text
        else:
            log(f"    ❌ HTTP {r.status_code}")
    except Exception as e:
        log(f"    ❌ Error: {e}")
    return None

# ====== 策略3: 掌上高考API（不同的参数格式）======
def fetch_from_gaokao_cn(province_id, year=2025):
    """从掌上高考获取数据"""
    log(f"  📥 尝试掌上高考 {province_id} {year}")
    # 掌上高考的API可能需要不同的参数格式
    urls = [
        f"https://api.eol.cn/gkcx/api/?uri=apidata/api/gk/score/province&province_id={province_id}&year={year}&page=1&size=20",
        f"https://api.eol.cn/gkcx/api/?uri=apidata/api/gk/score/province&province_id={province_id}&year={year}&page=1&size=20&access_token=&signsafe=",
    ]
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=15)
            data = r.json()
            code = data.get("code", "")
            if code == "0" or code == 0:
                d = data.get("data", {})
                items = d.get("item", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
                log(f"    ✅ 获取到 {len(items)} 条数据")
                return items
            elif code == "1069":
                log(f"    ⏳ 限频，等待30秒...")
                time.sleep(30)
                # 重试
                r = session.get(url, headers=headers, timeout=15)
                data = r.json()
                code = data.get("code", "")
                if code == "0" or code == 0:
                    d = data.get("data", {})
                    items = d.get("item", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
                    log(f"    ✅ 重试成功，获取到 {len(items)} 条数据")
                    return items
                else:
                    log(f"    ❌ 重试后仍然限频: code={code}")
            else:
                log(f"    ❌ code={code}")
        except Exception as e:
            log(f"    ❌ Error: {e}")
    return None

# ====== 策略4: 从dxsbb.com获取（需要浏览器）======
# 这个策略需要浏览器自动化，在子代理中执行

def main():
    log("=" * 60)
    log("🔍 开始2025年数据采集（多渠道）")
    log("=" * 60)
    
    # 先测试EOL API是否恢复
    log("\n--- 步骤1: 测试EOL API ---")
    test_items = fetch_from_gaokao_cn(32, 2025)
    if test_items and len(test_items) > 0:
        log("✅ EOL API已恢复！开始批量采集")
        # 批量采集所有缺数据的省份
        provinces = {
            12: "天津", 14: "山西", 15: "内蒙古",
            21: "辽宁", 22: "吉林", 23: "黑龙江",
            32: "江苏", 34: "安徽", 35: "福建", 36: "江西",
            41: "河南", 42: "湖北", 43: "湖南",
            44: "广东", 45: "广西", 46: "海南",
            50: "重庆", 51: "四川", 53: "云南", 54: "西藏",
            61: "陕西", 62: "甘肃", 63: "青海", 64: "宁夏", 65: "新疆",
        }
        for pid, pname in sorted(provinces.items()):
            log(f"\n--- {pname} (id={pid}) ---")
            items = fetch_from_gaokao_cn(pid, 2025)
            if items and len(items) > 0:
                fpath = os.path.join(FETCH_DIR, f"{pname}_2025_admission.json")
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False)
                log(f"  💾 保存到 {fpath}: {len(items)}条")
            else:
                log(f"  ⚪ 无数据")
            time.sleep(1)
    else:
        log("❌ EOL API仍然限流，尝试其他数据源...")
        
        # 尝试阳光高考院校库
        log("\n--- 步骤2: 尝试阳光高考院校库 ---")
        for pid, pname in [(32, "江苏"), (42, "湖北"), (43, "湖南")]:
            log(f"\n--- {pname} (id={pid}) ---")
            result = fetch_from_chsi(pid, 2025)
            if result:
                log(f"  💾 保存到 {pname}_2025_chsi.html")
                with open(os.path.join(FETCH_DIR, f"{pname}_2025_chsi.html"), "w", encoding="utf-8") as f:
                    f.write(result)
            time.sleep(1)
        
        # 尝试考试院官网
        log("\n--- 步骤3: 尝试考试院官网 ---")
        exam_admins = {
            "江苏": "https://www.jseea.cn/webfile/",
            "湖北": "https://www.hbea.edu.cn/",
            "湖南": "https://www.hneao.edu.cn/",
        }
        for pname, url in exam_admins.items():
            log(f"\n--- {pname} ---")
            links = fetch_from_exam_admin(pname, url)
            if links:
                log(f"  🔗 找到链接: {links[:5]}")
            time.sleep(1)
    
    log("\n🏁 采集完成")

if __name__ == "__main__":
    main()
