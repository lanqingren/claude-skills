#!/usr/bin/env python3
"""OCR提取上海和天津投档分数线数据"""
import os, sys, json, re, time
from rapidocr_onnxruntime import RapidOCR

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
OCR_DIR = os.path.join(DATA_DIR, "ocr_images")
OUTPUT_DIR = os.path.join(DATA_DIR, "province_v9")

engine = RapidOCR()

def ocr_image(img_path):
    """OCR单张图片，返回识别到的行列表"""
    result, elapse = engine(img_path)
    if not result:
        return []
    lines = []
    for item in result:
        # item = [bbox, text, score]
        text = item[1].strip()
        if text:
            lines.append(text)
    return lines

def parse_shanghai_line(line):
    """解析上海投档表格行 - 格式: 院校代码 专业组 院校名称 ... 最低分 位次"""
    # 上海是3+3模式，分数+位次
    parts = re.split(r'[\s,，]+', line.strip())
    parts = [p for p in parts if p]
    if len(parts) < 3:
        return None
    
    # Try to find score and section from the end
    numbers = []
    for p in reversed(parts):
        p_clean = p.replace(',', '').replace('，', '')
        if re.match(r'^-?\d+$', p_clean):
            numbers.insert(0, int(p_clean))
    
    if len(numbers) < 2:
        return None
    
    score = None
    section = None
    # Last number is usually section (位次), second to last is score
    if len(numbers) >= 2:
        section = numbers[-1]
        score = numbers[-2]
    
    # School name = everything that's not a number
    name_parts = [p for p in parts if not re.match(r'^-?\d+$', p.replace(',', '').replace('，', ''))]
    name = ' '.join(name_parts) if name_parts else ''
    
    if score and section and name:
        return {'name': name, 'score': score, 'section': section}
    return None

def parse_tianjin_line(line):
    """解析天津投档表格行 - 格式类似"""
    parts = re.split(r'[\s,，]+', line.strip())
    parts = [p for p in parts if p]
    if len(parts) < 3:
        return None
    
    numbers = []
    for p in reversed(parts):
        p_clean = p.replace(',', '').replace('，', '')
        if re.match(r'^-?\d+$', p_clean):
            numbers.insert(0, int(p_clean))
    
    if len(numbers) < 2:
        return None
    
    score = numbers[-2] if len(numbers) >= 2 else None
    section = numbers[-1] if len(numbers) >= 1 else None
    
    name_parts = [p for p in parts if not re.match(r'^-?\d+$', p.replace(',', '').replace('，', ''))]
    name = ' '.join(name_parts) if name_parts else ''
    
    if score and section and name:
        return {'name': name, 'score': score, 'section': section}
    return None

def process_province(prefix, year, parser_func):
    """处理一个省的所有图片"""
    records = []
    files = sorted([f for f in os.listdir(OCR_DIR) if f.startswith(prefix) and f'{year}' in f])
    print(f"\n=== {prefix} {year}: {len(files)} images ===")
    
    for fname in files:
        img_path = os.path.join(OCR_DIR, fname)
        print(f"  OCR: {fname}...", end='', flush=True)
        lines = ocr_image(img_path)
        print(f" {len(lines)} lines")
        
        for line in lines:
            rec = parser_func(line)
            if rec:
                records.append(rec)
    
    # Deduplicate by school name
    seen = {}
    for r in records:
        name = r['name']
        if name not in seen:
            seen[name] = r
        else:
            # Keep the one with lower score (min admission score)
            if r['score'] < seen[name]['score']:
                seen[name] = r
    
    print(f"  Total raw: {len(records)}, unique: {len(seen)}")
    return list(seen.values())

# Process Shanghai
print("Processing Shanghai...")
sh_2023 = process_province('shanghai', '2023', parse_shanghai_line)
sh_2024 = process_province('shanghai', '2024', parse_shanghai_line)

# Process Tianjin
print("\nProcessing Tianjin...")
tj_2023 = process_province('tianjin', '2023', parse_tianjin_line)
tj_2024 = process_province('tianjin', '2024', parse_tianjin_line)

# Save
results = {
    '上海': {'2023': sh_2023, '2024': sh_2024},
    '天津': {'2023': tj_2023, '2024': tj_2024},
}

for province, years_data in results.items():
    # Save per-year data
    for year, records in years_data.items():
        if records:
            outfile = os.path.join(OUTPUT_DIR, f'{province}_ocr_{year}.json')
            with open(outfile, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            print(f"Saved {province} {year}: {len(records)} records -> {outfile}")

# Print summary
print("\n=== OCR Summary ===")
for province, years_data in results.items():
    for year, records in years_data.items():
        print(f"  {province} {year}: {len(records)} schools")
