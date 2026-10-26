#!/usr/bin/env python3
"""
查看list_4.html的内容，之前发现它有70个链接
"""
import requests, re, os

session = requests.Session()
session.trust_env = False
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# 从list_4.html获取所有链接
url = "https://www.dxsbb.com/news/list_4.html"
r = session.get(url, headers=headers, timeout=10)
content = r.content
for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
    try:
        text = content.decode(enc)
        break
    except:
        text = content.decode('utf-8', errors='replace')

# 找所有链接
links = re.findall(r'href=["\'](/news/(\d+)\.html)["\']([^>]*)>([^<]+)<', text)
print(f"list_4.html: 找到 {len(links)} 个链接")

# 过滤含"投档"或"分数线"的
for path, lid, attrs, title in links:
    title = title.strip()
    if '投档' in title or '分数线' in title or '录取' in title:
        print(f"  {lid}: {title}")

# 打印所有标题（前50个）
print("\n所有链接:")
for path, lid, attrs, title in links[:50]:
    print(f"  {lid}: {title.strip()}")
