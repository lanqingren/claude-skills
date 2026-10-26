#!/usr/bin/env python3
"""下载福建/安徽/江西/贵州的投档数据图片"""
import re, os, urllib.request, ssl

DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
OCR_DIR = os.path.join(DATA_DIR, "ocr_images")
os.makedirs(OCR_DIR, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

targets = [
    ('福建_2023物理.html', 'fujian_2023_wuli'),
    ('福建_2023历史.html', 'fujian_2023_lishi'),
    ('福建_2024物理.html', 'fujian_2024_wuli'),
    ('福建_2024历史.html', 'fujian_2024_lishi'),
    ('安徽_2024物理.html', 'anhui_2024_wuli'),
    ('安徽_2024历史.html', 'anhui_2024_lishi'),
    ('江西_2024物理.html', 'jiangxi_2024_wuli'),
    ('江西_2024历史.html', 'jiangxi_2024_lishi'),
    ('贵州_2024物理.html', 'guizhou_2024_wuli'),
    ('贵州_2024历史.html', 'guizhou_2024_lishi'),
]

total = 0
for htmlfile, prefix in targets:
    fp = os.path.join(DATA_DIR, 'dxsbb_html', htmlfile)
    if not os.path.exists(fp):
        print(f'{htmlfile}: not found')
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        html = f.read()
    pattern = r'src=["\'](https://img\.dxsbb\.com/[^"\']+\.(?:png|jpg|jpeg))'
    imgs = re.findall(pattern, html)
    data_imgs = sorted(set(i for i in imgs if '2016' not in i and 'logo' not in i and 'school/' not in i))
    print(f'{prefix}: {len(data_imgs)} images', flush=True)
    
    for i, url in enumerate(data_imgs):
        ext = 'png' if url.endswith('.png') else 'jpg'
        fname = f'{prefix}_{i+1}.{ext}'
        fpath = os.path.join(OCR_DIR, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
            total += 1
            continue
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                with open(fpath, 'wb') as out:
                    out.write(resp.read())
            if os.path.getsize(fpath) > 1000:
                total += 1
                print(f'  ✅ {fname}', flush=True)
            else:
                os.remove(fpath)
        except Exception as e:
            print(f'  FAIL {fname}: {e}', flush=True)

print(f'\nTotal valid images downloaded: {total}')
