#!/usr/bin/env python3
"""分割上海2024超长图片，逐块OCR"""
import os, re, json
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

OCR_DIR = r"D:\GitHub\hermescn\data\gaokao-data\ocr_images"
CACHE_DIR = r"D:\GitHub\hermescn\data\gaokao-data\province_v9"
SLICE_HEIGHT = 1100  # 每块高度

engine = RapidOCR()

def ocr_tall_image(fp):
    """分割大图后OCR"""
    img = Image.open(fp)
    w, h = img.size
    
    if h <= SLICE_HEIGHT * 1.5:
        result, _ = engine(fp)
        return [r[1].strip() for r in result] if result else []
    
    # 分割
    all_texts = []
    pieces = (h + SLICE_HEIGHT - 1) // SLICE_HEIGHT
    overlap = 100  # 重叠区避免截断行
    for i in range(pieces):
        top = max(0, i * SLICE_HEIGHT - overlap)
        bottom = min(h, (i + 1) * SLICE_HEIGHT + overlap)
        cropped = img.crop((0, top, w, bottom))
        
        # 临时文件
        tmp = f"/tmp/sh_slice_{i}.png"
        cropped.save(tmp)
        
        result, _ = engine(tmp)
        if result:
            all_texts.extend([r[1].strip() for r in result])
        os.remove(tmp)
    
    return all_texts

def parse_shanghai(texts):
    """解析上海投档线格式"""
    records = []
    i = 0
    while i < len(texts):
        t = texts[i]
        # 模式1: 5位数代码 → 中文名(含括号) → 3位数分数
        if re.match(r'^\d{4,5}$', t):
            # 找下一个中文名
            for j in range(i + 1, min(i + 3, len(texts))):
                next_t = texts[j]
                cn = sum(1 for c in next_t if '\u4e00' <= c <= '\u9fff')
                if cn >= 2:
                    # 找分数
                    for k in range(j + 1, min(j + 5, len(texts))):
                        score_text = texts[k]
                        scores = re.findall(r'(\d{3})', score_text)
                        if scores:
                            score = int(scores[0])
                            if 390 <= score <= 620:  # 上海分数范围
                                # 清理校名
                                name = re.sub(r'\(\d+\)', '', next_t).strip()
                                name = re.sub(r'（\d+）', '', name).strip()
                                if name:
                                    records.append({'name': name, 'score': score, 'category': '综合'})
                                i = k
                                break
                    break
        i += 1
    return records

# 处理2024
print("=== 上海2024 OCR (分块) ===")
all_records_2024 = []
for i in range(1, 9):
    for ext in ['png', 'jpg']:
        fp = os.path.join(OCR_DIR, f'shanghai_2024_{i}.{ext}')
        if not os.path.exists(fp): continue
        
        img = Image.open(fp)
        print(f'  shanghai_2024_{i}: {img.size[0]}x{img.size[1]} → ', end='', flush=True)
        
        texts = ocr_tall_image(fp)
        records = parse_shanghai(texts)
        all_records_2024.extend(records)
        print(f'{len(texts)} blocks, {len(records)} records')

# 去重
seen = {}
for r in all_records_2024:
    n = r['name'].strip()
    if n not in seen or r['score'] < seen[n]['score']:
        seen[n] = r

print(f'\n2024 unique: {len(seen)}')
with open(os.path.join(CACHE_DIR, 'ocr_cache_shanghai_2024.json'), 'w', encoding='utf-8') as f:
    json.dump(list(seen.values()), f, ensure_ascii=False, indent=2)

# 检查与2023重叠
with open(os.path.join(CACHE_DIR, 'ocr_cache_shanghai_2023.json')) as f:
    s2023 = {r['name']: r['score'] for r in json.load(f)}
overlap = set(seen.keys()) & set(s2023.keys())
print(f'2023-2024 overlap: {len(overlap)} schools')
