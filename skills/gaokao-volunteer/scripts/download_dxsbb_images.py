#!/usr/bin/env python3
"""从大学生必备网批量下载全国各省投档线图片，然后用OCR提取数据"""

import requests
import re
import json
import os
import time
from urllib.parse import urljoin

BASE = "https://www.dxsbb.com"
DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data\dxsbb_data"
IMG_DIR = r"D:\GitHub\hermescn\data\gaokao-data\dxsbb_images"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)


def get_session():
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE,
    })
    return s


def main():
    s = get_session()

    # 加载文章列表
    with open(os.path.join(DATA_DIR, "articles.json"), "r", encoding="utf-8") as f:
        articles = json.load(f)

    # 只保留本科批次的（排除专科）
    undergrad = {}
    for key, art in articles.items():
        title = art["title"]
        if "专科" in title:
            continue
        # 只保留本科批次
        undergrad[key] = art

    print(f"本科投档线文章: {len(undergrad)}篇（已排除专科）")

    # 按省份分组
    from collections import defaultdict
    by_prov = defaultdict(list)
    for key, art in undergrad.items():
        by_prov[art["province"]].append((key, art))

    # 从每篇文章提取图片URL并下载
    img_map = {}
    total_imgs = 0

    for prov, items in sorted(by_prov.items()):
        prov_imgs = 0
        for key, art in items:
            title = art["title"]
            url = art["url"]
            
            try:
                r = s.get(url, timeout=15)
                r.encoding = "utf-8"
                
                # 找文章内容区的图片 - data-echo属性或src
                imgs = re.findall(r'data-echo=["\']([^"\']+)["\']', r.text)
                if not imgs:
                    imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', r.text)
                
                # 过滤掉logo等
                content_imgs = []
                for img in imgs:
                    if any(kw in img.lower() for kw in ["logo", "banner", "ad_", "icon", "btn", "echo.gif"]):
                        continue
                    full_url = urljoin(BASE, img)
                    content_imgs.append(full_url)
                
                if content_imgs:
                    img_map[key] = {
                        "province": prov,
                        "title": title,
                        "images": content_imgs,
                    }
                    prov_imgs += len(content_imgs)
                    total_imgs += len(content_imgs)
                    
                    # 下载图片
                    for i, img_url in enumerate(content_imgs):
                        ext = ".jpg"
                        if ".png" in img_url.lower():
                            ext = ".png"
                        safe_title = re.sub(r'[^\w]', '_', title)[:30]
                        fname = f"{prov}_{safe_title}_{i}{ext}"
                        fpath = os.path.join(IMG_DIR, fname)
                        
                        if not os.path.exists(fpath):
                            try:
                                r2 = s.get(img_url, timeout=15)
                                if r2.status_code == 200 and len(r2.content) > 5000:
                                    with open(fpath, "wb") as f:
                                        f.write(r2.content)
                            except Exception as e:
                                print(f"  下载失败: {img_url[:50]} - {e}")
                            time.sleep(0.2)
                
            except Exception as e:
                print(f"  获取失败: {title[:30]} - {e}")
            
            time.sleep(0.3)
        
        print(f"  {prov}: {len(items)}篇, {prov_imgs}张图片")

    # 保存图片映射
    with open(os.path.join(DATA_DIR, "image_map.json"), "w", encoding="utf-8") as f:
        json.dump(img_map, f, ensure_ascii=False, indent=2)

    # 统计下载的文件
    downloaded_files = [f for f in os.listdir(IMG_DIR) if f.endswith(('.jpg', '.png'))]
    print(f"\n总计: {len(img_map)}篇文章, {total_imgs}张图片URL")
    print(f"已下载图片文件: {len(downloaded_files)}张")


if __name__ == "__main__":
    main()
