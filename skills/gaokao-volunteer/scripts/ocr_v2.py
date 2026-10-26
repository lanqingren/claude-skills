#!/usr/bin/env python
"""用RapidOCR从投档线图片中批量提取数据（按bbox坐标分行解析）。"""
import json, os, re, sys, time, traceback
from pathlib import Path
import urllib.request, ssl

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data")
HTML_DIR = DATA_DIR / "dxsbb_html"
IMG_DIR  = DATA_DIR / "dxsbb_images"
V9_DIR   = DATA_DIR / "province_v9"
IMG_DIR.mkdir(parents=True, exist_ok=True)

os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def get_content_images(html_path):
    """提取dxsbb页面中的数据图片"""
    html = open(html_path, encoding='utf-8', errors='replace').read()
    imgs = re.findall(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>', html)
    # 只要2020年以后上传的infoImg（排除logo/广告/学校图标）
    data_urls = []
    seen = set()
    for u in imgs:
        if 'img.dxsbb.com/upFiles/infoImg/' not in u:
            continue
        if '/school/' in u:
            continue
        if u in seen:
            continue
        # 排除旧广告图片（2016-2019年上传的）
        if re.search(r'/(201[6-9])', u):
            continue
        seen.add(u)
        data_urls.append(u)
    return data_urls

def download_image(url, save_path):
    if save_path.exists() and save_path.stat().st_size > 5000:
        return True
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.dxsbb.com/',
        })
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
            save_path.write_bytes(resp.read())
        return save_path.stat().st_size > 5000
    except Exception as e:
        print(f"    下载失败: {e}")
        return False

_ocr_engine = None
def get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine

def ocr_and_extract(img_path):
    """OCR一张图片，按行分组后提取学校和分数。
    
    投档线表格典型结构：
    院校代码 | 院校名称 | 投档分/调档线 | [同分排序子列]
    
    用bbox的Y坐标将OCR结果分到不同行。
    """
    ocr = get_ocr()
    result, _ = ocr(str(img_path))
    if not result:
        return []
    
    # 将OCR结果转为 [(center_y, center_x, text, conf), ...]
    items = []
    for item in result:
        bbox = item[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        text = item[1]
        conf = item[2]
        
        # 计算中心坐标
        ys = [p[1] for p in bbox]
        xs = [p[0] for p in bbox]
        cy = sum(ys) / len(ys)
        cx = sum(xs) / len(xs)
        
        items.append((cy, cx, text, conf))
    
    # 按Y坐标排序后聚类成行
    items.sort(key=lambda x: (x[0], x[1]))
    
    rows = []
    current_row = []
    current_y = None
    y_threshold = 15  # Y坐标差异小于15像素认为是同一行
    
    for cy, cx, text, conf in items:
        if current_y is None or abs(cy - current_y) <= y_threshold:
            current_row.append((cx, text, conf))
            current_y = cy if current_y is None else (current_y + cy) / 2
        else:
            if current_row:
                current_row.sort(key=lambda x: x[0])
                rows.append(current_row)
            current_row = [(cx, text, conf)]
            current_y = cy
    if current_row:
        rows.append(current_row)
    
    # 从每行提取学校和分数
    records = []
    for row in rows:
        texts = [t for _, t, _ in row]
        joined = ' '.join(texts)
        
        # 跳过表头行
        if any(k in joined for k in ['院校', '代号', '代码', '名称', '投档', '调档', '分数', '最低', '位次', '计划', '备注', '序号', '类别', '说明', '注:']):
            continue
        
        # 策略1：找包含"大学"/"学院"等的文本作为学校名，其后的3位数字作为分数
        school = None
        score = None
        
        for i, (cx, text, conf) in enumerate(row):
            if school is None and any(k in text for k in ['大学', '学院', '学校', '分校', '校区']):
                school = text.strip()
                # 在后续列找分数
                for j in range(i+1, len(row)):
                    num_text = row[j][1].strip()
                    # 提取数字
                    nums = re.findall(r'(\d{3})', num_text)
                    if nums:
                        try:
                            val = int(nums[0])
                            if 200 <= val <= 750:
                                score = val
                                break
                        except:
                            pass
        
        # 策略2：如果没找到，尝试从合并文本中提取
        if school is None:
            # 匹配 "学校名+3位数字" 或 "学校名 数字"
            m = re.search(r'([\u4e00-\u9fa5]{2,}(?:大学|学院|学校|分校)).*?(\d{3})', joined)
            if m:
                school = m.group(1)
                try:
                    score = int(m.group(2))
                    if not (200 <= score <= 750):
                        score = None
                except:
                    score = None
        
        if school and score:
            # 清理学校名
            school = re.sub(r'\d+', '', school).strip()
            if len(school) >= 2:
                records.append((school, score))
    
    return records


def process_province(province, html_configs):
    """
    html_configs: [(html_filename, year, category, batch)]
    """
    print(f"\n{'='*50}")
    print(f"OCR: {province}")
    print(f"{'='*50}")
    
    all_records = []
    
    for html_name, year, category, batch in html_configs:
        html_path = HTML_DIR / html_name
        if not html_path.exists():
            print(f"  ⚠️ {html_name} 不存在")
            continue
        
        img_urls = get_content_images(html_path)
        if not img_urls:
            print(f"  ⚠️ {html_name} 无数据图片")
            continue
        
        print(f"  📄 {html_name}: {len(img_urls)} 张图片")
        
        page_records = []
        for idx, url in enumerate(img_urls):
            ext = url.rsplit('.', 1)[-1].split('?')[0]
            safe_name = re.sub(r'[^\w]', '_', html_name.replace('.html', ''))
            img_path = IMG_DIR / f"{province}_{safe_name}_{idx}.{ext}"
            
            if not download_image(url, img_path):
                continue
            
            records = ocr_and_extract(img_path)
            page_records.extend(records)
            
            if (idx + 1) % 5 == 0 or idx == len(img_urls) - 1:
                print(f"    图片 {idx+1}/{len(img_urls)}: 累计 {len(page_records)} 条")
        
        for school, score in page_records:
            all_records.append({
                'province': province,
                'year': year,
                'category': category,
                'batch': batch,
                'school': school,
                'score': score,
                'rank': None,
            })
        
        print(f"  📊 {html_name}: {len(page_records)} 条")
    
    out_path = V9_DIR / f"{province}_v9.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    stats = {}
    for r in all_records:
        key = f"{r['year']}_{r['category']}"
        stats[key] = stats.get(key, 0) + 1
    print(f"  💾 {len(all_records)} 条 → {out_path.name}")
    print(f"  📈 {stats}")
    
    return len(all_records)


# ─── 省份配置 ───
PROVINCE_CONFIG = {
    "四川": [
        ("四川_2023理科一本.html", "2023", "理科", "一本"),
        ("四川_2023文科一本.html", "2023", "文科", "一本"),
        ("四川_2024理科一本.html", "2024", "理科", "一本"),
        ("四川_2024文科一本.html", "2024", "文科", "一本"),
    ],
    "重庆": [
        ("重庆_2023物理.html", "2023", "物理", "本科"),
        ("重庆_2023历史.html", "2023", "历史", "本科"),
        ("重庆_2024物理.html", "2024", "物理", "本科"),
        ("重庆_2024历史.html", "2024", "历史", "本科"),
    ],
    "湖北": [
        ("湖北_2023物理.html", "2023", "物理", "本科"),
        ("湖北_2023历史.html", "2023", "历史", "本科"),
        ("湖北_2024物理.html", "2024", "物理", "本科"),
        ("湖北_2024历史.html", "2024", "历史", "本科"),
    ],
    "福建": [
        ("福建_2023物理.html", "2023", "物理", "本科"),
        ("福建_2023历史.html", "2023", "历史", "本科"),
        ("福建_2024物理.html", "2024", "物理", "本科"),
        ("福建_2024历史.html", "2024", "历史", "本科"),
    ],
    "云南": [
        ("云南_2023理科一本.html", "2023", "理科", "一本"),
        ("云南_2023文科一本.html", "2023", "文科", "一本"),
        ("云南_2024理科一本.html", "2024", "理科", "一本"),
        ("云南_2024文科一本.html", "2024", "文科", "一本"),
    ],
    "新疆": [
        ("新疆_2023理科一本.html", "2023", "理科", "一本"),
        ("新疆_2023文科一本.html", "2023", "文科", "一本"),
        ("新疆_2024理科一本.html", "2024", "理科", "一本"),
        ("新疆_2024文科一本.html", "2024", "文科", "一本"),
    ],
    "宁夏": [
        ("宁夏_2023理科一本.html", "2023", "理科", "一本"),
        ("宁夏_2023文科一本.html", "2023", "文科", "一本"),
        ("宁夏_2024理科一本.html", "2024", "理科", "一本"),
        ("宁夏_2024文科一本.html", "2024", "文科", "一本"),
    ],
}

if __name__ == '__main__':
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['四川', '重庆', '湖北', '福建']
    
    total = 0
    for prov in targets:
        if prov not in PROVINCE_CONFIG:
            print(f"未知省份: {prov}")
            continue
        try:
            n = process_province(prov, PROVINCE_CONFIG[prov])
            total += n
        except Exception as e:
            print(f"  ❌ {prov} 出错: {e}")
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"🎉 完成！共 {total} 条")
