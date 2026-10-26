#!/usr/bin/env python3
"""
高效搜索dxsbb.com历史数据
策略：从页面列表页获取所有含"投档"的链接
dxsbb.com有分类页面和标签页面
"""
import requests, re, os, time, json
from datetime import datetime

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
RESULT_DIR = os.path.join(DATA_DIR, "dxsbb_history")

os.makedirs(RESULT_DIR, exist_ok=True)

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def fetch_page(url):
    try:
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                text = content.decode(enc)
                return text
            except:
                continue
        return content.decode('utf-8', errors='replace')
    except:
        return None

# 策略1: 从标签页获取
# dxsbb.com的标签页包含"高考分数线"相关文章
tag_urls = [
    "https://www.dxsbb.com/news/tag/1.html",  # 标签页1
    "https://www.dxsbb.com/news/tag/2.html",
    "https://www.dxsbb.com/news/tag/3.html",
]

# 策略2: 从分类页获取
category_urls = [
    "https://www.dxsbb.com/news/list_2.html",  # 分类页
    "https://www.dxsbb.com/news/list_3.html",
    "https://www.dxsbb.com/news/list_4.html",
    "https://www.dxsbb.com/news/list_5.html",
]

# 策略3: 从首页获取链接
index_urls = [
    "https://www.dxsbb.com/",
    "https://www.dxsbb.com/news/",
]

all_links = {}  # {url: title}

print("=== 从页面列表获取链接 ===")

for url in index_urls + category_urls + tag_urls:
    print(f"\n--- {url} ---")
    text = fetch_page(url)
    if not text:
        print(f"  ❌ 无法获取")
        continue
    
    # 找所有链接
    links = re.findall(r'href=["\'](/news/(\d+)\.html)["\']([^>]*)>([^<]+)<', text)
    print(f"  找到 {len(links)} 个链接")
    
    for path, lid, attrs, title in links:
        title = title.strip()
        # 过滤含"投档"或"分数线"的
        if '投档' in title or '分数线' in title or '录取' in title:
            full_url = f"https://www.dxsbb.com{path}"
            all_links[full_url] = title
            print(f"    {lid}: {title}")

print(f"\n=== 共找到 {len(all_links)} 个相关链接 ===")
for url, title in sorted(all_links.items(), key=lambda x: x[1]):
    print(f"  {url}: {title}")

# 保存
with open(os.path.join(RESULT_DIR, "dxsbb_history_links.json"), 'w', encoding='utf-8') as f:
    json.dump(all_links, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/dxsbb_history_links.json")
