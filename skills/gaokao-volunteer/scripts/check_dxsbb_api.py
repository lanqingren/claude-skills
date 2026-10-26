#!/usr/bin/env python3
"""
新策略：搜索dxsbb.com的sitemap.xml获取所有URL
或者通过搜索引擎查找历史数据页面
"""
import requests, re, os, json

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 策略1: sitemap.xml
print("=== 尝试sitemap.xml ===")
sitemap_urls = [
    "https://www.dxsbb.com/sitemap.xml",
    "https://www.dxsbb.com/sitemap.txt",
    "https://www.dxsbb.com/robots.txt",
]

for url in sitemap_urls:
    try:
        r = session.get(url, headers=headers, timeout=10)
        print(f"  {url}: HTTP {r.status_code}, len={len(r.text)}")
        if r.status_code == 200:
            print(f"  Content: {r.text[:500]}")
    except Exception as e:
        print(f"  {url}: Error: {e}")

# 策略2: 从首页获取所有链接
print("\n=== 从首页获取链接 ===")
try:
    r = session.get("https://www.dxsbb.com/", headers=headers, timeout=10)
    content = r.content
    for enc in ['utf-8', 'gbk', 'gb2312']:
        try:
            text = content.decode(enc)
            break
        except:
            text = content.decode('utf-8', errors='replace')
    
    # 找所有含"投档"的链接
    links = re.findall(r'href=["\']([^"\']+)["\']([^>]*)>([^<]*?)(投档|分数线|录取)', text)
    print(f"  找到 {len(links)} 个相关链接")
    for path, attrs, title, keyword in links[:20]:
        print(f"    {path}: {title.strip()}{keyword}")
except Exception as e:
    print(f"  Error: {e}")

# 策略3: 尝试从dxsbb.com的API获取
print("\n=== 尝试dxsbb.com API ===")
api_urls = [
    "https://www.dxsbb.com/api/news/list?page=1&size=20&keyword=2024%E6%8A%95%E6%A1%A3",
    "https://www.dxsbb.com/api/news/list?page=1&size=20&keyword=2023%E6%8A%95%E6%A1%A3",
    "https://www.dxsbb.com/api/v1/news?keyword=%E6%8A%95%E6%A1%A3&page=1&size=20",
]
for url in api_urls:
    try:
        r = session.get(url, headers=headers, timeout=10)
        print(f"  {url}: HTTP {r.status_code}, len={len(r.text)}")
        if r.status_code == 200:
            print(f"    Content: {r.text[:300]}")
    except Exception as e:
        print(f"  {url}: Error: {e}")
