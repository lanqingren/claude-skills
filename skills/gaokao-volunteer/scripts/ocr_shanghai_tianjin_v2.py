#!/usr/bin/env python3
"""OCR提取上海和天津投档分数线数据 v2 - 从单元格重构表格行"""
import os, sys, json, re
from rapidocr_onnxruntime import RapidOCR

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
OCR_DIR = os.path.join(DATA_DIR, "ocr_images")
OUTPUT_DIR = os.path.join(DATA_DIR, "province_v9")

engine = RapidOCR()

def ocr_image_cells(img_path):
    """OCR单张图片，返回单元格列表 [(bbox, text, score)]"""
    result, _ = engine(img_path)
    return result or []

def is_chinese_text(s):
    """判断是否主要是中文文本（学校名称）"""
    cn = sum(1 for c in s if '\u4e00' <= c <= '\u9fff')
    return cn >= 2 and not s.replace('.','').replace('-','').isdigit()

def is_number(s):
    """判断是否是纯数字"""
    s = s.replace(',', '').replace('，', '').strip()
    return bool(re.match(r'^-?\d+$', s))

def extract_tianjin(img_path):
    """提取天津数据：序号 代码 院校名称 总分 语文 数学 外语"""
    cells = ocr_image_cells(img_path)
    records = []
    texts = [c[1].strip() for c in cells]
    
    # Find data rows: Chinese school name followed by score (3-digit)
    i = 0
    while i < len(texts):
        text = texts[i]
        if is_chinese_text(text) and len(text) >= 4:  # School name
            # Check if next item is a score
            score = None
            for j in range(i+1, min(i+4, len(texts))):
                if is_number(texts[j]):
                    val = int(texts[j].replace(',', ''))
                    if 400 <= val <= 750:  # Valid score range for Tianjin
                        score = val
                        break
            
            if score:
                name = text
                # Clean up name
                name = re.sub(r'^[\d\s]+', '', name).strip()
                if len(name) >= 4:  # Valid school name
                    records.append({'name': name, 'score': score})
                    i = j + 1
                    continue
        i += 1
    
    return records

def extract_shanghai(img_path):
    """提取上海数据：院校专业组代码 院校专业组名称 投档线(3-digit score) ..."""
    cells = ocr_image_cells(img_path)
    records = []
    texts = [c[1].strip() for c in cells]
    
    # Shanghai scores are typically 400-580 (总分660)
    i = 0
    while i < len(texts):
        text = texts[i]
        if is_chinese_text(text) and len(text) >= 4:
            # Check if next item is a score
            score = None
            for j in range(i+1, min(i+4, len(texts))):
                if is_number(texts[j]):
                    val = int(texts[j].replace(',', ''))
                    if 350 <= val <= 660:  # Valid score range for Shanghai
                        score = val
                        break
            
            if score:
                name = text
                name = re.sub(r'^[\d\s]+', '', name).strip()
                if len(name) >= 4:
                    records.append({'name': name, 'score': score})
                    i = j + 1
                    continue
        i += 1
    
    return records

def process_province(prefix, year, extractor):
    """处理一个省的所有图片"""
    all_records = []
    files = sorted([f for f in os.listdir(OCR_DIR) if f.startswith(prefix) and year in f and f.endswith('.png')])
    print(f"\n=== {prefix} {year}: {len(files)} images ===")
    
    for fname in files:
        img_path = os.path.join(OCR_DIR, fname)
        print(f"  {fname}...", end='', flush=True)
        records = extractor(img_path)
        print(f" {len(records)} schools")
        all_records.extend(records)
    
    # Deduplicate
    seen = {}
    for r in all_records:
        name = r['name']
        if name not in seen:
            seen[name] = r
        elif r['score'] < seen[name]['score']:
            seen[name] = r
    
    print(f"  Total: {len(all_records)} raw -> {len(seen)} unique")
    return list(seen.values())

# Process all
print("RapidOCR engine ready")

sh_2023 = process_province('shanghai', '2023', extract_shanghai)
sh_2024 = process_province('shanghai', '2024', extract_shanghai)
tj_2023 = process_province('tianjin', '2023', extract_tianjin)
tj_2024 = process_province('tianjin', '2024', extract_tianjin)

# Save
for province, year, records in [('上海','2023',sh_2023), ('上海','2024',sh_2024), 
                                  ('天津','2023',tj_2023), ('天津','2024',tj_2024)]:
    if records:
        outfile = os.path.join(OUTPUT_DIR, f'{province}_ocr_{year}.json')
        with open(outfile, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        # Print samples
        print(f"\n{province} {year} sample (first 5):")
        for r in records[:5]:
            print(f"  {r['name']}: {r['score']}")
    else:
        print(f"\n{province} {year}: NO DATA EXTRACTED")

print("\n=== Final Summary ===")
print(f"上海 2023: {len(sh_2023)}, 2024: {len(sh_2024)}")
print(f"天津 2023: {len(tj_2023)}, 2024: {len(tj_2024)}")
