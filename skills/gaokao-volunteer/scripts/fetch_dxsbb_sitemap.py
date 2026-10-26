#!/usr/bin/env python3
"""
从sitemap.xml提取所有URL，批量获取含"投档"或"分数线"的页面
sitemap.xml有1000个URL，直接批量获取
"""
import requests, re, os, json, time
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
        r = session.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return None
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                text = content.decode(enc)
                if '院校' in text or '学校' in text:
                    return text
            except:
                continue
        return None
    except:
        return None

# 1. 获取sitemap.xml
print("=== 获取sitemap.xml ===")
r = session.get("https://www.dxsbb.com/sitemap.xml", headers=headers, timeout=15)
content = r.content
for enc in ['utf-8', 'gbk', 'gb2312']:
    try:
        sitemap = content.decode(enc)
        break
    except:
        sitemap = content.decode('utf-8', errors='replace')

all_urls = re.findall(r'<loc>([^<]+)</loc>', sitemap)
print(f"sitemap.xml: {len(all_urls)} 个URL")

# 2. 获取每个页面的标题，过滤含"投档"或"分数线"的
print("\n=== 批量获取页面标题 ===")
history_urls = {}

for i, url in enumerate(all_urls):
    try:
        r = session.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            continue
        content = r.content
        for enc in ['utf-8', 'gbk', 'gb2312']:
            try:
                text = content.decode(enc)
                break
            except:
                text = content.decode('utf-8', errors='replace')
        
        title_m = re.search(r'<title[^>]*>([^<]+)</title>', text)
        title = title_m.group(1).strip() if title_m else ""
        
        if '投档' in title or '分数线' in title:
            lid_m = re.search(r'/news/(\d+)\.html', url)
            lid = lid_m.group(1) if lid_m else "?"
            history_urls[url] = title
            print(f"  [{i+1}/{len(all_urls)}] ID {lid}: {title}")
    except:
        pass
    
    if (i+1) % 100 == 0:
        print(f"  进度: {i+1}/{len(all_urls)}")
    
    time.sleep(0.05)

print(f"\n=== 找到 {len(history_urls)} 个含'投档/分数线'的页面 ===")
for url, title in sorted(history_urls.items(), key=lambda x: x[1]):
    print(f"  {url}: {title}")

# 保存
with open(os.path.join(RESULT_DIR, "dxsbb_history_urls_from_sitemap.json"), 'w', encoding='utf-8') as f:
    json.dump(history_urls, f, ensure_ascii=False, indent=2)

print(f"\n✅ 保存到 {RESULT_DIR}/dxsbb_history_urls_from_sitemap.json")
