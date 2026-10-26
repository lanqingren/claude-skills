#!/usr/bin/env python
"""用PaddleOCR从投档线图片中批量提取数据。"""
import json, os, re, sys, time, traceback
from pathlib import Path
import urllib.request, ssl

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data")
HTML_DIR = DATA_DIR / "dxsbb_html"
IMG_DIR  = DATA_DIR / "dxsbb_images"
V9_DIR   = DATA_DIR / "province_v9"
IMG_DIR.mkdir(parents=True, exist_ok=True)

# 关闭代理
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ─── 从HTML提取内容图片URL ───
def get_content_images(html_path):
    """提取dxsbb页面中的数据图片（排除logo/广告）"""
    html = open(html_path, encoding='utf-8', errors='replace').read()
    # 匹配 img.dxsbb.com 域名的数据图片
    pattern = r'src="(https://img\.dxsbb\.com/upFiles/infoImg/[^"]+)"'
    urls = re.findall(pattern, html)
    # 排除 logo 和 infoImg/school/ (学校logo)
    data_urls = [u for u in urls if '/school/' not in u and 'logo' not in u.lower()]
    return data_urls

# ─── 下载图片 ───
def download_image(url, save_path):
    if save_path.exists() and save_path.stat().st_size > 5000:
        return True
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://www.dxsbb.com/',
        })
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
            data = resp.read()
            save_path.write_bytes(data)
            return len(data) > 5000
    except Exception as e:
        print(f"    下载失败 {url}: {e}")
        return False

# ─── PaddleOCR ───
_ocr = None
def get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        try:
            # v3.x API
            _ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        except TypeError:
            # v2.x API fallback
            _ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
    return _ocr

def ocr_image(img_path):
    """OCR一张图片，返回 [(text, confidence), ...]"""
    ocr = get_ocr()
    try:
        result = ocr.ocr(str(img_path), cls=True)
    except Exception as e:
        print(f"    OCR失败 {img_path.name}: {e}")
        return []
    
    lines = []
    if result and result[0]:
        for item in result[0]:
            if item and len(item) >= 2:
                text = item[1][0] if isinstance(item[1], (list, tuple)) else str(item[1])
                conf = item[1][1] if isinstance(item[1], (list, tuple)) and len(item[1]) > 1 else 0.5
                lines.append((text.strip(), conf))
    return lines


def parse_ocr_lines(lines):
    """从OCR文本行中提取学校名和分数。
    投档线表格的典型OCR结果：每行包含学校名 + 分数（数字）
    """
    records = []
    for text, conf in lines:
        if conf < 0.5:
            continue
        # 跳过表头行
        if any(k in text for k in ['院校', '代号', '代码', '名称', '投档', '分数', '最低', '位次', '计划']):
            continue
        # 匹配 "学校名 + 分数" 的模式
        # 常见格式：清华大学695 / 北京大学 698 / 0001北京大学685
        # 尝试提取末尾的数字作为分数
        m = re.match(r'^(.+?)(\d{3})\s*$', text.strip())
        if m:
            school = m.group(1).strip()
            score = int(m.group(2))
            if 200 <= score <= 750 and len(school) >= 2:
                if any(k in school for k in ['大学', '学院', '学校', '分校']):
                    records.append((school, score))
                    continue
        
        # 尝试 "学校名   分数" 中间有空格的情况
        parts = text.split()
        if len(parts) >= 2:
            # 最后一部分是分数
            try:
                score = int(parts[-1])
                school = ' '.join(parts[:-1]).strip()
                if 200 <= score <= 750 and len(school) >= 2:
                    if any(k in school for k in ['大学', '学院', '学校', '分校']):
                        records.append((school, score))
                        continue
            except:
                pass
    
    return records


# ─── 处理一个省份 ───
def process_province_images(province, html_files):
    """
    html_files: [(html_filename, year, category, batch)]
    """
    print(f"\n{'='*50}")
    print(f"OCR处理: {province}")
    print(f"{'='*50}")
    
    all_records = []
    
    for html_name, year, category, batch in html_files:
        html_path = HTML_DIR / html_name
        if not html_path.exists():
            print(f"  ⚠️ {html_name} 不存在，跳过")
            continue
        
        # 获取数据图片URL
        img_urls = get_content_images(html_path)
        if not img_urls:
            print(f"  ⚠️ {html_name} 无数据图片")
            continue
        
        print(f"  📄 {html_name}: {len(img_urls)} 张图片")
        
        province_records = []
        for i, url in enumerate(img_urls):
            # 下载图片
            ext = url.rsplit('.', 1)[-1].split('?')[0]
            img_name = f"{province}_{html_name.replace('.html','')}_{i}.{ext}"
            img_path = IMG_DIR / img_name
            
            if not download_image(url, img_path):
                continue
            
            # OCR
            lines = ocr_image(img_path)
            parsed = parse_ocr_lines(lines)
            province_records.extend(parsed)
            print(f"    图片 {i+1}/{len(img_urls)}: {len(lines)} 行 → {len(parsed)} 条记录")
        
        # 保存
        for school, score in province_records:
            all_records.append({
                'province': province,
                'year': year,
                'category': category,
                'batch': batch,
                'school': school,
                'score': score,
                'rank': None,
            })
        
        print(f"  📊 {html_name}: 共 {len(province_records)} 条")
    
    # 写入
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


if __name__ == '__main__':
    # 要处理的省份（按重要性排序）
    # 格式: province -> [(html_file, year, category, batch)]
    
    # 选择要处理的省份（通过命令行参数或默认全部）
    target_provinces = sys.argv[1:] if len(sys.argv) > 1 else [
        '四川', '湖北', '重庆', '福建',
    ]
    
    PROVINCE_CONFIG = {
        "四川": [
            ("四川_2023理科一本.html", "2023", "理科", "一本"),
            ("四川_2023文科一本.html", "2023", "文科", "一本"),
            ("四川_2024理科一本.html", "2024", "理科", "一本"),
            ("四川_2024文科一本.html", "2024", "文科", "一本"),
            ("四川_2023理科二本.html", "2023", "理科", "二本"),
            ("四川_2023文科二本.html", "2023", "文科", "二本"),
            ("四川_2024理科二本.html", "2024", "理科", "二本"),
            ("四川_2024文科二本.html", "2024", "文科", "二本"),
        ],
        "湖北": [
            ("湖北_2023物理.html", "2023", "物理", "本科"),
            ("湖北_2023历史.html", "2023", "历史", "本科"),
            ("湖北_2024物理.html", "2024", "物理", "本科"),
            ("湖北_2024历史.html", "2024", "历史", "本科"),
        ],
        "重庆": [
            ("重庆_2023物理.html", "2023", "物理", "本科"),
            ("重庆_2023历史.html", "2023", "历史", "本科"),
            ("重庆_2024物理.html", "2024", "物理", "本科"),
            ("重庆_2024历史.html", "2024", "历史", "本科"),
        ],
        "福建": [
            ("福建_2023物理.html", "2023", "物理", "本科"),
            ("福建_2023历史.html", "2023", "历史", "本科"),
            ("福建_2024物理.html", "2024", "物理", "本科"),
            ("福建_2024历史.html", "2024", "历史", "本科"),
        ],
    }
    
    total = 0
    for prov in target_provinces:
        if prov not in PROVINCE_CONFIG:
            print(f"未知省份: {prov}")
            continue
        try:
            n = process_province_images(prov, PROVINCE_CONFIG[prov])
            total += n
        except Exception as e:
            print(f"  ❌ {prov} 出错: {e}")
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"🎉 OCR完成！共 {total} 条记录")
    print(f"{'='*50}")
