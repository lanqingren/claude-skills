#!/usr/bin/env python3
"""只OCR福建2023数据（物理+历史）"""
import os, glob, re, json
from rapidocr_onnxruntime import RapidOCR

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
OCR_DIR = os.path.join(DATA_DIR, "ocr_images")
V9_DIR = os.path.join(DATA_DIR, "province_v9")

engine = RapidOCR()

NOISE = ['分以上','分及以','注：','投档','院校','名称','序号','合计','公示','选考',
         '外语','语文','数学','本科线','代码','性质','办学']

def is_school(text):
    cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return cn >= 2 and len(text) >= 4

def ocr_prefix(prefix):
    cache = os.path.join(V9_DIR, f'ocr_cache_{prefix}.json')
    if os.path.exists(cache) and os.path.getsize(cache) > 10:
        with open(cache, 'r') as f:
            d = json.load(f)
        if d:
            print(f'  ⏭️ {prefix}: cached ({len(d)})', flush=True)
            return d

    files = sorted(glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.png')) +
                   glob.glob(os.path.join(OCR_DIR, f'{prefix}_*.jpg')))
    print(f'  📷 {prefix}: {len(files)} images', flush=True)

    records = []
    for idx, fp in enumerate(files):
        result, _ = engine(fp)
        if not result:
            continue
        texts = [c[1].strip() for c in result]
        i = 0
        while i < len(texts):
            text = texts[i]
            if is_school(text):
                for j in range(i+1, min(i+4, len(texts))):
                    num = texts[j].replace(',', '').replace('，', '')
                    if re.match(r'^-?\d+$', num):
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
        if (idx + 1) % 5 == 0:
            print(f'    {prefix}: {idx+1}/{len(files)} done ({len(records)} records)', flush=True)

    seen = {}
    for r in records:
        if r['name'] not in seen or r['score'] < seen[r['name']]['score']:
            seen[r['name']] = r
    unique = list(seen.values())
    with open(cache, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f'  ✅ {prefix}: {len(unique)} schools', flush=True)
    return unique

print('=== 福建 2023 物理 ===', flush=True)
ocr_prefix('fujian_2023_wuli')
print('=== 福建 2023 历史 ===', flush=True)
ocr_prefix('fujian_2023_lishi')
print('=== Done! ===', flush=True)
