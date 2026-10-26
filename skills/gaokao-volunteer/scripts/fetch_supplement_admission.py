#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高考征集志愿（补录）数据采集脚本 v1.1
=========================================
采集全国31省 2023-2025 年征集志愿（补录）投档数据。

数据来源：
1. dxsbb.com（大学生必备网）- 通过 so.dxsbb.com (Google CSE) 搜索"征集志愿"页面
   - 搜索接口: https://so.dxsbb.com/cse/search?q={keyword}&s=17035947201502151521
   - 已知大批页面以图片形式存储数据（需人工标注）
2. 各省教育考试院官网 - 每年7-8月发布征集志愿投档线PDF

数据字段：
  - province: 省份
  - year: 年份 (2023/2024/2025)
  - category: 科类 (物理类/历史类/理科/文科/综合)
  - school_name: 院校名称
  - school_code: 院校代码
  - batch: 批次 (本科批/专科批/本科一批等)
  - round: 征集轮次 (第一次征集/第二次征集)
  - plan_count: 计划数 (缺额人数)
  - actual_count: 投档数 (实际投档人数)
  - min_score: 投档最低分
  - source: 数据来源 (dxsbb/考试院)
  - source_url: 数据来源URL

输出文件：
  - supplement_data/supplement_admission_known.json (已知页面手动标注数据)
  - supplement_data/supplement_admission_search.json (搜索发现的新页面)
  - supplement_data/supplement_admission_all.json   (全量合并)
  - supplement_data/supplement_admission_index.json (索引文件)

用法：
  python fetch_supplement_admission.py --search "关键词"     # 搜索发现新页面
  python fetch_supplement_admission.py --known              # 采集已知页面
  python fetch_supplement_admission.py --all                # 全量采集
  python fetch_supplement_admission.py --index              # 生成索引
"""

import json
import re
import os
import sys
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime

# ===== 配置 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'supplement_data'))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}
REQUEST_DELAY = 2.0  # 秒

# ===== 已知的征集志愿数据页面（手动标注） =====
# 格式: {"id": 标识, "url": "页面URL", "province": "省份", "year": 年份,
#        "batch": "批次", "round": "征集轮次",
#        "category": "科类(可选)", "has_html_table": true/false}
#
# 这些页面需要逐一确认是否为HTML表格格式(true)还是图片格式(false)
KNOWN_PAGES = [
    # === 2024年征集志愿 ===
    {"id": "hn_2024_ys_bk_lq", "url": "https://www.dxsbb.com/news/53102.html",
     "province": "湖南", "year": 2024, "batch": "本科提前批艺术类",
     "round": "征集志愿", "category": "艺术类", "has_html_table": False},

    {"id": "jx_2024_ty_bk", "url": "https://www.dxsbb.com/news/110731.html",
     "province": "江西", "year": 2024, "batch": "本科批",
     "round": "征集志愿", "category": "体育类", "has_html_table": False},

    {"id": "gd_2024_ty_bkzk", "url": "https://www.dxsbb.com/news/110712.html",
     "province": "广东", "year": 2024, "batch": "本科批+专科批",
     "round": "征集志愿", "category": "体育类", "has_html_table": False},

    {"id": "ln_2022_wl_bk1", "url": "https://www.dxsbb.com/news/119690.html",
     "province": "辽宁", "year": 2022, "batch": "本科批",
     "round": "第一次征集志愿", "category": "物理类", "has_html_table": False},

    {"id": "hain_2019_lg_bkA", "url": "https://www.dxsbb.com/news/57494.html",
     "province": "海南", "year": 2019, "batch": "本科A批",
     "round": "征集志愿", "category": "理科", "has_html_table": True},

    # === 2025年数据(山东常规批有征集轮次) ===
    {"id": "sd_2025_cg1", "url": "https://www.dxsbb.com/news/147455.html",
     "province": "山东", "year": 2025, "batch": "常规批",
     "round": "第1次征集", "category": "综合", "has_html_table": False},

    {"id": "sd_2025_cg2", "url": "https://www.dxsbb.com/news/147455.html",
     "province": "山东", "year": 2025, "batch": "常规批",
     "round": "第2次征集", "category": "综合", "has_html_table": False},

    {"id": "sd_2025_cg3", "url": "https://www.dxsbb.com/news/147455.html",
     "province": "山东", "year": 2025, "batch": "常规批",
     "round": "第3次征集", "category": "综合", "has_html_table": False},

    # 更多页面待添加...
]


def fetch_url(url, timeout=30):
    """使用 urllib 获取页面内容"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.URLError as _ssl_err:
            # Retry with SSL verification disabled (for so.dxsbb.com cert mismatch)
            import ssl as _ssl_mod
            _ctx = _ssl_mod.create_default_context()
            _ctx.check_hostname = False
            _ctx.verify_mode = _ssl_mod.CERT_NONE
            resp = urllib.request.urlopen(req, timeout=timeout, context=_ctx)
        html = resp.read().decode('utf-8', 'ignore')
        return html
    except Exception as e:
        print(f"  [ERROR] 请求失败: {url}")
        print(f"    {e}")
        return None


def is_zhishi_page(url):
    """判断是否为知乎/知道类非数据页面（应跳过）"""
    skip_domains = ['zhidao.baidu.com', 'zhihu.com', 'wenku.baidu.com']
    return any(d in url for d in skip_domains)


def parse_supplement_table(html_text, page_info):
    """
    从 HTML 表格中解析征集志愿数据。
    针对 dxsbb 上常见的表格格式：
    - 科类 | 院校代码 | 院校名称 | 计划数 | 投档数 | 投档最低分
    """
    records = []
    
    # 查找可能包含数据的表格
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html_text, re.DOTALL | re.IGNORECASE)
    
    for table_html in tables:
        # 提取行
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
        if len(rows) < 2:
            continue
        
        # 分析第一行是否为表头
        first_cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', rows[0], re.DOTALL)
        header_text = ' '.join(re.sub(r'<[^>]+>', '', c).strip() for c in first_cells)
        
        # 判断是否为数据表（含院校名称/计划数等关键词）
        data_keywords = ['院校', '计划', '投档', '分数', '代码', '科类']
        is_data_table = any(k in header_text for k in data_keywords)
        if not is_data_table:
            continue
        
        # 从第一行推断各列含义
        col_map = {}
        for i, cell in enumerate(first_cells):
            text = re.sub(r'<[^>]+>', '', cell).strip()
            if any(k in text for k in ['科类', '类别']):
                col_map['category'] = i
            elif any(k in text for k in ['代码', '代号']):
                col_map['school_code'] = i
            elif any(k in text for k in ['院校名称', '学校名称', '院校']):
                col_map['school_name'] = i
            elif any(k in text for k in ['计划数', '缺额', '计划']):
                col_map['plan_count'] = i
            elif any(k in text for k in ['投档数', '投档人数']):
                col_map['actual_count'] = i
            elif any(k in text for k in ['投档最低分', '最低分', '投档线']):
                col_map['min_score'] = i
            elif any(k in text for k in ['位次', '投档位次']):
                col_map['rank'] = i
        
        if 'school_name' not in col_map and 'school_code' not in col_map:
            continue  # 没有院校信息，不是数据表
        
        # 解析数据行
        for row_html in rows[1:]:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            
            if len(cells) < 2:
                continue
            
            record = {}
            record['province'] = page_info['province']
            record['year'] = page_info['year']
            record['batch'] = page_info['batch']
            record['round'] = page_info['round']
            if page_info.get('category'):
                record['category'] = page_info['category']
            if 'category' in col_map:
                record['category'] = cells[col_map['category']]
            if 'school_code' in col_map:
                record['school_code'] = cells[col_map['school_code']]
            if 'school_name' in col_map:
                record['school_name'] = cells[col_map['school_name']]
            if 'plan_count' in col_map:
                val = cells[col_map['plan_count']]
                record['plan_count'] = int(re.sub(r'[^\d]', '', val)) if re.search(r'\d', val) else val
            if 'actual_count' in col_map:
                val = cells[col_map['actual_count']]
                record['actual_count'] = int(re.sub(r'[^\d]', '', val)) if re.search(r'\d', val) else val
            if 'min_score' in col_map:
                record['min_score'] = cells[col_map['min_score']]
            if 'rank' in col_map:
                record['rank'] = cells[col_map['rank']]
            
            record['source'] = 'dxsbb'
            record['source_url'] = page_info['url']
            
            if record.get('school_name') and len(record['school_name']) > 1:
                records.append(record)
    
    return records


def search_dxsbb(query):
    """
    通过 dxsbb Google CSE 搜索
    返回 [(url, title), ...]
    """
    results = []
    encoded = urllib.parse.quote(query)
    search_url = f"https://so.dxsbb.com/cse/search?q={encoded}&s=17035947201502151521"
    
    print(f"[搜索] {query}")
    html = fetch_url(search_url, timeout=30)
    if not html:
        return results
    
    # 提取搜索结果中的链接（去重）
    seen = set()
    for m in re.finditer(r'<a[^>]*href="(https?://www\.dxsbb\.com/news/(\d+)\.html)"[^>]*>(.*?)</a>', html, re.DOTALL):
        url = m.group(1)
        title = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        if url not in seen:
            seen.add(url)
            results.append((url, title))
    
    print(f"  找到 {len(results)} 个链接")
    for u, t in results[:10]:
        print(f"    [{t[:60]}]")
        print(f"    {u}")
    
    return results


def fetch_known_pages():
    """采集已知标注的征集志愿页面"""
    all_records = []
    
    for page in KNOWN_PAGES:
        if page.get('has_html_table') != True:
            print(f"[跳过] {page['id']} - {page['url']} (图片格式，无法自动解析)")
            continue
        
        print(f"\n[采集] {page['id']} ({page['province']}{page['year']}{page['batch']})")
        print(f"  URL: {page['url']}")
        
        html = fetch_url(page['url'])
        if not html:
            continue
        
        records = parse_supplement_table(html, page)
        print(f"  解析到 {len(records)} 条记录")
        all_records.extend(records)
        
        time.sleep(REQUEST_DELAY)
    
    return all_records


def search_and_discover(queries=None):
    """
    搜索发现新页面，返回发现的页面信息
    """
    if queries is None:
        queries = [
            "征集志愿 投档分数线 2025",
            "征集志愿 投档分数线 2024",
            "征集志愿 投档分数线 2023",
            "第一次征集志愿 投档最低分",
            "第二次征集志愿 投档最低分 2024",
            "本科批 征集志愿 投档线 2024",
            "专科批 征集志愿 投档线 2024",
            "补录 投档分数线 2024",
            "征集志愿 计划数 投档数",
        ]
    
    all_pages = []  # [(url, title), ...]
    seen = set()
    
    for query in queries:
        pages = search_dxsbb(query)
        for url, title in pages:
            if url not in seen:
                seen.add(url)
                all_pages.append((url, title))
        time.sleep(1)
    
    return all_pages


def run_search_mode():
    """搜索模式：发现新页面"""
    pages = search_and_discover()
    
    # 保存搜索结果
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_pages": len(pages),
        "pages": [{"url": u, "title": t} for u, t in pages]
    }
    outpath = os.path.join(OUTPUT_DIR, 'supplement_admission_search.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n发现 {len(pages)} 个页面")
    print(f"已保存到: {outpath}")
    
    # 输出可用于 KNOWN_PAGES 的 YAML 块
    print("\n--- 以下可追加到 KNOWN_PAGES ---")
    for url, title in pages:
        # 尝试从标题提取省份和年份
        prov_match = re.search(r'(湖南|湖北|广东|广西|山东|山西|河南|河北|江苏|浙江|安徽|福建|江西|四川|贵州|云南|陕西|甘肃|青海|海南|辽宁|吉林|黑龙江|北京|上海|天津|重庆|新疆|宁夏|内蒙古|西藏)', title)
        year_match = re.search(r'(202[0-9])', title)
        province = prov_match.group(1) if prov_match else "?"
        year = int(year_match.group(1)) if year_match else 0
        page_id = province + "_" + str(year) + "_" + url.split("/")[-1].split(".")[0]
        print('    {"id": "' + page_id + '",')
        print(f'     "url": "{url}",')
        print(f'     "province": "{province}", "year": {year},')
        print(f'     "batch": "?", "round": "征集志愿",')
        print(f'     "has_html_table": False}},')


def run_known_mode():
    """采集已知页面模式"""
    records = fetch_known_pages()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    outpath = os.path.join(OUTPUT_DIR, 'supplement_admission_known.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    print(f"\n共采集 {len(records)} 条记录")
    print(f"已保存到: {outpath}")
    
    return records


def generate_index():
    """生成数据索引"""
    index = {
        "version": "1.1",
        "generated_at": datetime.now().isoformat(),
        "description": "高考征集志愿（补录）数据索引",
        "data_files": [],
        "summary": {"total_records": 0}
    }
    
    if os.path.exists(OUTPUT_DIR):
        for f in sorted(os.listdir(OUTPUT_DIR)):
            if f.endswith('.json') and f != 'supplement_admission_index.json':
                fp = os.path.join(OUTPUT_DIR, f)
                try:
                    with open(fp, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                    if isinstance(data, list):
                        index['data_files'].append({
                            "filename": f,
                            "record_count": len(data),
                            "size_bytes": os.path.getsize(fp)
                        })
                        index['summary']['total_records'] += len(data)
                    elif isinstance(data, dict):
                        index['data_files'].append({
                            "filename": f,
                            "type": data.get('description', 'metadata'),
                            "size_bytes": os.path.getsize(fp)
                        })
                except Exception as e:
                    print(f"  [WARN] {f}: {e}")
    
    idx_path = os.path.join(OUTPUT_DIR, 'supplement_admission_index.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"索引已生成: {idx_path}")
    print(f"数据文件数: {len(index['data_files'])}")
    print(f"总记录数: {index['summary'].get('total_records', 'N/A')}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='高考征集志愿数据采集 v1.1')
    parser.add_argument('--search', action='store_true', help='搜索发现新页面')
    parser.add_argument('--known', action='store_true', help='采集已知标注页面')
    parser.add_argument('--all', action='store_true', help='全量采集（搜索+已知）')
    parser.add_argument('--index', action='store_true', help='生成数据索引')
    parser.add_argument('--query', type=str, help='自定义搜索词（与--search搭配）')
    
    args = parser.parse_args()
    
    if args.index:
        generate_index()
    elif args.search:
        if args.query:
            pages = search_dxsbb(args.query)
            for url, title in pages:
                print(f"{url}\t{title}")
        else:
            run_search_mode()
    elif args.known:
        run_known_mode()
    elif args.all:
        print("Phase 1: 搜索发现新页面...")
        run_search_mode()
        print("\nPhase 2: 采集已知页面...")
        run_known_mode()
        print("\nPhase 3: 生成索引...")
        generate_index()
    else:
        parser.print_help()
        print("\n常用命令:")
        print("  python fetch_supplement_admission.py --search        # 搜索发现新页面")
        print("  python fetch_supplement_admission.py --known         # 采集已知页面")
        page_id = province + "_" + str(year) + "_" + url.split("/")[-1].split(".")[0]
        print('    {"id": "' + page_id + '",')
