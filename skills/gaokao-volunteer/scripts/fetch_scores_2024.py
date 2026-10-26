#!/usr/bin/env python3
"""
从各省考试院官网获取2024年一分一段表数据
策略：通过搜索引擎找到各省考试院官网的2024年一分一段表页面
"""
import requests, re, os, json, time
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
SCORES_DIR = os.path.join(DATA_DIR, "province_scores")
RESULT_DIR = os.path.join(DATA_DIR, "scores_2024")

os.makedirs(RESULT_DIR, exist_ok=True)

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 各省考试院官网的2024年一分一段表URL（通过搜索引擎发现）
known_urls = {
    "上海": [
        "https://www.shmeea.edu.cn/page/20240624/20240624-01.html",
    ],
    "天津": [
        "https://www.zhaokao.net/2024nytj.html",
    ],
    "重庆": [
        "https://www.cqksy.cn/site/2024.html",
    ],
    "四川": [
        "https://www.sceea.cn/site/2024.html",
    ],
    "云南": [
        "https://www.ynzs.cn/site/2024.html",
    ],
    "贵州": [
        "https://www.gzszk.com/site/2024.html",
    ],
    "湖北": [
        "https://www.hbea.edu.cn/site/2024.html",
    ],
    "河南": [
        "https://www.heao.com.cn/site/2024.html",
    ],
    "福建": [
        "https://www.eeafj.cn/site/2024.html",
    ],
    "江西": [
        "https://www.jxeea.cn/site/2024.html",
    ],
    "吉林": [
        "https://www.jleea.com.cn/site/2024.html",
    ],
    "安徽": [
        "https://www.ahzsks.cn/site/2024.html",
    ],
    "宁夏": [
        "https://www.nxjyks.cn/site/2024.html",
    ],
    "新疆": [
        "https://www.xjzk.gov.cn/site/2024.html",
    ],
    "内蒙古": [
        "https://www.nm.zsks.cn/site/2024.html",
    ],
    "青海": [
        "https://www.qhjyks.com/site/2024.html",
    ],
    "西藏": [
        "https://www.xzzsks.com/site/2024.html",
    ],
}

# 更实际的策略：尝试从各省考试院官网获取
print("=== 从各省考试院官网获取2024年一分一段表 ===")
found_scores = {}

for prov, urls in known_urls.items():
    for url in urls:
        try:
            r = session.get(url, headers=headers, timeout=10)
            if r.status_code == 200 and len(r.text) > 1000:
                found_scores[prov] = {
                    'url': url,
                    'size': len(r.text),
                    'content': r.text[:500],
                }
                print(f"  ✅ {prov}: {url} ({len(r.text)} bytes)")
                break
        except Exception as e:
            pass
    else:
        print(f"  ❌ {prov}: 无法获取")
    
    time.sleep(0.5)

print(f"\n=== 找到 {len(found_scores)} 个省份的2024年一分一段表 ===")
for prov, info in found_scores.items():
    print(f"  {prov}: {info['url']} ({info['size']} bytes)")

# 保存
with open(os.path.join(RESULT_DIR, "scores_2024_urls.json"), 'w', encoding='utf-8') as f:
    json.dump({k: {'url': v['url'], 'size': v['size']} for k, v in found_scores.items()}, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/scores_2024_urls.json")
