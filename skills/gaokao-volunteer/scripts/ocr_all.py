#!/usr/bin/env python3
"""单独OCR所有缺失省份的图片，结果存入缓存"""
import os, sys, json, glob, re
from rapidocr_onnxruntime import RapidOCR

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
OCR_DIR = os.path.join(DATA_DIR, "ocr_images")
V9_DIR = os.path.join(DATA_DIR, "province_v9")

engine = RapidOCR()

# All prefixes to process
PREFIXES = [
    'shanghai_2023', 'shanghai_2024',
    'tianjin_2023', 'tianjin_2024',
    'fujian_2023_wuli', 'fujian_2023_lishi',
    'fujian_2024_wuli', 'fujian_2024_lishi',
    'anhui_2024_wuli', 'anhui_2024_lishi',
    'jiangxi_2024_wuli', 'jiangxi_2024_lishi',
    'guizhou_2024_wuli', 'guizhou_2024_lishi',
]

def is_school_name(text):
    cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return cn >= 2 and len(text) >= 4

def is_score(s):
    s = s.replace(',', '').replace('，', '')
    return bool(re.match(r'^-?\d+$', s))

NOISE = ['分以上','分及以','注：','投档','院校','名称','序号','合计','公示','选考',
         '外语','语文','数学','本科线','代码','序号','性质','办学']

def ocr_prefix(prefix):
    cache_file = os.path.join(V9_DIR, f'ocr_cache_{prefix}.json')
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 10:
        print(f'  ⏭️ {prefix}: cached')
        return
    
    files = sorted(glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.png')) +
                   glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.jpg')))
    print(f'  📷 {prefix}: {len(files)} images', flush=True)
    
    records = []
    for fp in files:
        result, _ = engine(fp)
        if not result:
            continue
        texts = [c[1].strip() for c in result]
        
        i = 0
        while i < len(texts):
            text = texts[i]
            if is_school_name(text):
                for j in range(i+1, min(i+4, len(texts))):
                    num = texts[j].replace(',', '').replace('，', '')
                    if is_score(num):
                        val = int(num)
                        if 200 <= val <= 750:
                            name = re.sub(r'[\(（][\dQ\d]+[\)）]', '', text).strip()
                            name = re.sub(r'^[\d\s]+', '', name).strip()
                            if any(x in name for x in NOISE):
                                break
                            if len(name) >= 4:
                                records.append({'name': name, 'score': val})
                                i = j + 1
                                break
                else:
                    i += 1
                continue
            i += 1
    
    # Deduplicate
    seen = {}
    for r in records:
        if r['name'] not in seen or r['score'] < seen[r['name']]['score']:
            seen[r['name']] = r
    unique = list(seen.values())
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f'  ✅ {prefix}: {len(unique)} schools → {os.path.basename(cache_file)}', flush=True)

for prefix in PREFIXES:
    ocr_prefix(prefix)

print('\nAll OCR processing done!')
