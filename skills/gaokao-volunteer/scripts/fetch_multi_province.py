#!/usr/bin/env python3
"""
多省份高考投档数据批量下载器
================================
从 gaokao.cn (EOL) API 批量下载各省份的院校录取分数线数据。
支持多年份、多省份、多科类。

数据源：api.eol.cn/gkcx/api/
"""

import requests
import json
import time
import os
from pathlib import Path

DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data\multi_province")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 省份ID映射 (gaokao.cn API使用)
PROVINCES = {
    11: "北京", 12: "天津", 13: "河北", 14: "山西", 15: "内蒙古",
    21: "辽宁", 22: "吉林", 23: "黑龙江", 31: "上海", 32: "江苏",
    33: "浙江", 34: "安徽", 35: "福建", 36: "江西", 37: "山东",
    41: "河南", 42: "湖北", 43: "湖南", 44: "广东", 45: "广西",
    46: "海南", 50: "重庆", 51: "四川", 52: "贵州", 53: "云南",
    54: "西藏", 61: "陕西", 62: "甘肃", 63: "青海", 64: "宁夏", 65: "新疆",
}

# 重点下载的省份（按用户要求 + 人口大省）
TARGET_PROVINCES = {
    44: "广东",
    11: "北京",
    31: "上海",
    42: "湖北",
    51: "四川",
    52: "贵州",
    32: "江苏",
    33: "浙江",
    37: "山东",
    41: "河南",
}

BASE_URL = "https://api.eol.cn/gkcx/api/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.gaokao.cn/',
    'Accept': 'application/json, text/plain, */*',
}

# 关闭系统代理（Clash代理会导致国内API卡死）
SESSION = requests.Session()
SESSION.trust_env = False


def fetch_province_scores(province_id, year, page=1, size=20, score_type=None):
    """
    获取某省某年的院校录取分数线
    type: 1=本科一批, 2=本科二批, 3=专科, etc.
    """
    params = {
        'access_token': '',
        'signsafe': '',
        'uri': 'apidata/api/gk/score/province',
        'province_id': str(province_id),
        'year': str(year),
        'page': str(page),
        'size': str(size),
    }
    if score_type:
        params['type'] = str(score_type)

    try:
        r = SESSION.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data
    except Exception as e:
        return {"error": str(e)}


def fetch_all_pages(province_id, year, max_pages=100, size=20, delay=0.5):
    """分页获取所有数据"""
    all_items = []
    for page in range(1, max_pages + 1):
        data = fetch_province_scores(province_id, year, page, size)
        
        if "error" in data:
            print(f"    ❌ 第{page}页失败: {data['error']}")
            break
        
        code = data.get("code")
        if code and code != "0000":
            print(f"    ⚠️ API返回: code={code} msg={data.get('message','')}")
            break
        
        items = data.get("data", {}).get("item", [])
        num_found = data.get("data", {}).get("numFound")
        
        if not items:
            break
        
        all_items.extend(items)
        print(f"    第{page}页: {len(items)}条 (累计 {len(all_items)})")
        
        if num_found and len(all_items) >= int(num_found):
            break
        if len(items) < size:
            break
        
        time.sleep(delay)
    
    return all_items


def download_province(province_id, province_name, years):
    """下载某省多年数据"""
    print(f"\n{'='*60}")
    print(f"📍 {province_name} (ID:{province_id})")
    print(f"{'='*60}")
    
    for year in years:
        filepath = DATA_DIR / f"{province_name}_{year}_admission.json"
        if filepath.exists():
            print(f"  {year}: 已存在，跳过")
            continue
        
        print(f"\n  📥 下载 {province_name} {year}年投档数据...")
        items = fetch_all_pages(province_id, year)
        
        if items:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 保存 {len(items)} 条 → {filepath.name}")
            
            # 简单统计
            scores = [int(i['min']) for i in items if str(i.get('min','')).isdigit()]
            ranks = [int(i['min_section']) for i in items if str(i.get('min_section','')).isdigit()]
            print(f"     分数范围: {min(scores)}~{max(scores) if scores else 'N/A'}")
            if ranks:
                print(f"     位次范围: {min(ranks)}~{max(ranks)}")
        else:
            print(f"  ❌ {year}年无数据")
        
        time.sleep(1)  # 省间冷却


def main():
    years = [2023, 2024]  # 2025年API可能还没数据
    
    print(f"🎯 目标省份: {', '.join(TARGET_PROVINCES.values())}")
    print(f"📅 年份: {years}")
    print(f"📁 输出目录: {DATA_DIR}")
    
    for pid, pname in TARGET_PROVINCES.items():
        download_province(pid, pname, years)
    
    # 最终统计
    print(f"\n{'='*60}")
    print(f"📊 下载完成统计")
    print(f"{'='*60}")
    files = list(DATA_DIR.glob("*.json"))
    total_records = 0
    for f in sorted(files):
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        records = len(data) if isinstance(data, list) else 0
        total_records += records
        print(f"  {f.name}: {records} 条")
    print(f"\n  总计: {len(files)} 文件, {total_records} 条记录")


if __name__ == "__main__":
    main()
