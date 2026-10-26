#!/usr/bin/env python3
"""从大学生必备网(dxsbb.com)爬取全国各省高考投档线数据"""

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

# 省份 -> 分类页URL
PROV_PAGES = {
    "北京": "/news/list_923.html", "江苏": "/news/list_924.html",
    "山东": "/news/list_925.html", "广东": "/news/list_926.html",
    "浙江": "/news/list_155.html", "河南": "/news/list_927.html",
    "湖北": "/news/list_928.html", "湖南": "/news/list_929.html",
    "河北": "/news/list_930.html", "安徽": "/news/list_931.html",
    "辽宁": "/news/list_932.html", "陕西": "/news/list_933.html",
    "四川": "/news/list_934.html", "江西": "/news/list_935.html",
    "福建": "/news/list_936.html", "黑龙江": "/news/list_937.html",
    "山西": "/news/list_938.html", "广西": "/news/list_939.html",
    "上海": "/news/list_940.html", "重庆": "/news/list_941.html",
    "云南": "/news/list_942.html", "天津": "/news/list_944.html",
    "贵州": "/news/list_945.html", "甘肃": "/news/list_947.html",
    "新疆": "/news/list_948.html", "海南": "/news/list_949.html",
    "宁夏": "/news/list_950.html", "青海": "/news/list_951.html",
}


def get_session():
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE,
    })
    return s


def fetch_province_articles(s, prov_name, list_url):
    """获取某省份投档线分类页中的文章列表"""
    url = BASE + list_url
    r = s.get(url, timeout=15)
    r.encoding = "utf-8"
    
    # 找所有文章链接 - 在dxsbb上文章链接格式是 /news/数字.html
    # 但列表页内容可能通过JS加载，试试找data属性或AJAX链接
    articles = []
    
    # 方法1: 直接从HTML提取 /news/数字.html
    for m in re.finditer(r'href="(/news/(\d+)\.html)"[^>]*>([^<]*)</a>', r.text):
        href, nid, title = m.group(1), m.group(2), m.group(3).strip()
        if title and len(title) > 3 and ("投档" in title or "分数" in title):
            articles.append({"url": BASE + href, "id": nid, "title": title})
    
    # 方法2: 找onclick或data-url属性
    if not articles:
        for m in re.finditer(r'data-url="([^"]+)"[^>]*>([^<]+)', r.text):
            url_val, title = m.group(1), m.group(2).strip()
            articles.append({"url": url_val, "id": "", "title": title})
    
    # 方法3: 从JS变量中提取
    if not articles:
        for m in re.finditer(r'"url"\s*:\s*"([^"]+)"[^}]*"title"\s*:\s*"([^"]+)"', r.text):
            url_val, title = m.group(1), m.group(2).strip()
            if "投档" in title or "分数" in title:
                articles.append({"url": url_val, "id": "", "title": title})
    
    # 方法4: 搜索所有数字ID形式的链接
    if not articles:
        all_ids = set(re.findall(r'/news/(\d{4,6})\.html', r.text))
        # 过滤掉导航菜单的ID（已知导航ID）
        nav_ids = {"97","180","223","1001","822","88","75","652","651","178","642","620",
                    "712","192","76","181","449","888","174","220","457","17","821","553",
                    "923","924","925","926","155","927","928","929","930","931","932","933",
                    "934","935","936","937","938","939","940","941","942","944","945","947",
                    "948","949","950","951"}
        article_ids = all_ids - nav_ids
        for aid in article_ids:
            articles.append({"url": f"{BASE}/news/{aid}.html", "id": aid, "title": "unknown"})
    
    return articles


def fetch_article_images(s, article_url):
    """从文章页面提取所有投档线表格图片"""
    r = s.get(article_url, timeout=15)
    r.encoding = "utf-8"
    
    # 找文章内容区的图片
    imgs = re.findall(r'<img[^>]+src="([^"]+\.(?:jpg|png|jpeg|gif))"[^>]*>', r.text, re.I)
    
    # 过滤掉logo、广告等小图片
    content_imgs = []
    for img in imgs:
        if any(kw in img.lower() for kw in ["logo", "banner", "ad_", "icon", "btn"]):
            continue
        full_url = urljoin(BASE, img)
        content_imgs.append(full_url)
    
    return content_imgs


def main():
    s = get_session()
    
    all_articles = {}
    
    for prov_name, list_url in PROV_PAGES.items():
        articles = fetch_province_articles(s, prov_name, list_url)
        print(f"{prov_name}: {len(articles)}篇文章")
        
        # 过滤出2023/2024年本科投档线
        for art in articles:
            title = art["title"]
            if any(y in title for y in ["2024", "2023"]) and \
               any(kw in title for kw in ["本科", "一本", "二本", "常规批", "一段", "普通批"]):
                key = f"{prov_name}_{art['id']}"
                all_articles[key] = {"province": prov_name, **art}
                print(f"  ⭐ {title[:50]}")
        
        time.sleep(0.5)
    
    print(f"\n共找到{len(all_articles)}篇目标文章")
    
    # 保存文章列表
    with open(os.path.join(DATA_DIR, "articles.json"), "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    # 从每篇文章提取图片URL
    img_map = {}
    for key, art in all_articles.items():
        imgs = fetch_article_images(s, art["url"])
        if imgs:
            img_map[key] = {"province": art["province"], "title": art["title"], "images": imgs}
            print(f"  {key}: {len(imgs)}张图片")
        time.sleep(0.5)
    
    with open(os.path.join(DATA_DIR, "image_map.json"), "w", encoding="utf-8") as f:
        json.dump(img_map, f, ensure_ascii=False, indent=2)
    
    # 统计
    total_imgs = sum(len(v["images"]) for v in img_map.values())
    print(f"\n总计: {len(img_map)}篇文章, {total_imgs}张图片")
    
    # 下载所有图片
    downloaded = 0
    for key, info in img_map.items():
        prov = info["province"]
        for i, img_url in enumerate(info["images"]):
            ext = ".jpg"
            if ".png" in img_url:
                ext = ".png"
            fname = f"{prov}_{key.split('_')[-1]}_{i}{ext}"
            fpath = os.path.join(IMG_DIR, fname)
            if os.path.exists(fpath):
                continue
            try:
                r = s.get(img_url, timeout=15)
                if r.status_code == 200 and len(r.content) > 5000:
                    with open(fpath, "wb") as f:
                        f.write(r.content)
                    downloaded += 1
            except:
                pass
            time.sleep(0.3)
    
    print(f"\n下载完成: {downloaded}张新图片")


if __name__ == "__main__":
    main()
