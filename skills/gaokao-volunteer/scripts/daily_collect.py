#!/usr/bin/env python3
"""
高考志愿数据每日采集脚本
============================
每天凌晨运行，从多个数据源采集全国各省2023-2025年投档数据。

数据源优先级：
1. dxsbb.com（院校投档线汇总，最全面）
2. 贵州省考试院 raw_2024.json（已有2024年31省数据）
3. 阳光高考/掌上高考 API（当前不可用，保留接口）
4. 各省考试院官网（备用）

使用方法：
  python daily_collect.py                  # 全量采集
  python daily_collect.py --source dxsbb   # 只从dxsbb采集
  python daily_collect.py --source eol     # 只从EOL采集
  python daily_collect.py --province 贵州   # 只采集贵州
  python daily_collect.py --year 2025       # 只采集2025年
  python daily_collect.py --dry-run         # 试跑，不保存
"""
import requests, re, os, sys, json, time, argparse, hashlib
from datetime import datetime

# ========== 配置 ==========
DATA_DIR = r"D:\GitHub\hermescn\data\gaokao-data"
CLASSIFIED_PATH = os.path.join(DATA_DIR, "province_classified.json")
RAW_2024_PATH = os.path.join(DATA_DIR, "raw_2024.json")
COLLECT_LOG = os.path.join(DATA_DIR, "collect_log.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

os.makedirs(BACKUP_DIR, exist_ok=True)

session = requests.Session()
session.trust_env = False
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# dxsbb.com 已知2025年URL ID映射
DXSBB_KNOWN_URLS = {
    # 2025年
    '北京_2025_本科': 'https://www.dxsbb.com/news/149119.html',
    '北京_2025_专科': 'https://www.dxsbb.com/news/149120.html',
    '上海_2025': 'https://www.dxsbb.com/news/149121.html',
    '浙江_2025_一段': 'https://www.dxsbb.com/news/149123.html',
    '浙江_2025_二段': 'https://www.dxsbb.com/news/149124.html',
    '山东_2025_1': 'https://www.dxsbb.com/news/149125.html',
    '山东_2025_2': 'https://www.dxsbb.com/news/149126.html',
    '山东_2025_3': 'https://www.dxsbb.com/news/149127.html',
    '河北_2025_物理': 'https://www.dxsbb.com/news/149128.html',
    '河北_2025_历史': 'https://www.dxsbb.com/news/149129.html',
}

# EOL API 地址（可能限流）
EOL_BASE = "https://www.eol.cn/eol/api"

# ========== 工具函数 ==========

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    return line

def load_classified():
    if os.path.exists(CLASSIFIED_PATH):
        with open(CLASSIFIED_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_classified(data):
    # 先备份
    if os.path.exists(CLASSIFIED_PATH):
        backup_name = f"province_classified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        os.rename(CLASSIFIED_PATH, backup_path)
        log(f"  已备份原文件 → {backup_path}")
    
    with open(CLASSIFIED_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  已保存 {CLASSIFIED_PATH}")

def load_collect_log():
    if os.path.exists(COLLECT_LOG):
        with open(COLLECT_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'runs': [], 'total_collected': 0, 'source_stats': {}}

def save_collect_log(log_data):
    with open(COLLECT_LOG, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

def count_pairs(classified):
    return sum(len(p.get('pairs', {})) for p in classified.values())

def get_existing_keys(classified):
    """获取已有的所有key集合，用于去重"""
    keys = set()
    for prov, pdata in classified.items():
        for key in pdata.get('pairs', {}):
            keys.add(f"{prov}|{key}")
    return keys

# ========== 数据源1: dxsbb.com ==========

def fetch_dxsbb_page(url, max_retries=3):
    """获取dxsbb.com页面，带重试"""
    for attempt in range(max_retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                # 处理编码
                if r.encoding and r.encoding.lower() in ('gbk', 'gb2312', 'iso-8859-1'):
                    r.encoding = 'utf-8'
                return r.text
            elif r.status_code == 404:
                return None
            else:
                log(f"  HTTP {r.status_code} for {url}, retry {attempt+1}")
        except Exception as e:
            log(f"  Error fetching {url}: {e}, retry {attempt+1}")
        time.sleep(2)
    return None

def parse_dxsbb_table(html, province, year):
    """解析dxsbb.com页面中的表格数据"""
    from html.parser import HTMLParser
    
    records = []
    
    # 简单表格解析
    table_match = re.search(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table_match:
        # 尝试其他格式
        table_match = re.search(r'<table[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
    
    if not table_match:
        return records
    
    table_html = table_match.group(1)
    
    # 提取所有行
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
    
    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        if len(cells) < 3:
            continue
        
        # 清理HTML标签
        clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        
        # 尝试提取学校名称和分数
        record = extract_school_score(clean_cells, province, year)
        if record:
            records.append(record)
    
    return records

def extract_school_score(cells, province, year):
    """从表格单元格提取学校+分数"""
    # dxsbb.com的表格格式因省份而异
    # 通用策略：找含"大学"或"学院"的单元格作为学校名，找数字作为分数
    
    school = None
    score = None
    rank = None
    category = None  # 理科/文科/物理/历史/综合
    
    for i, cell in enumerate(cells):
        # 学校名
        if not school and ('大学' in cell or '学院' in cell or '职业' in cell):
            school = cell
            # 尝试提取代码+名称格式（如"A422山东大学"）
            code_match = re.match(r'([A-Z]\d+)(.+)', school)
            if code_match:
                school = code_match.group(2)
        
        # 分数（400-750之间的数字）
        if score is None:
            nums = re.findall(r'\b(\d{3})\b', cell)
            for n in nums:
                val = int(n)
                if 300 <= val <= 750:
                    score = val
                    break
        
        # 位次
        if rank is None:
            rank_match = re.search(r'(\d{4,6})', cell)
            if rank_match:
                val = int(rank_match.group(1))
                if 1 <= val <= 100000:
                    rank = val
        
        # 科类
        if not category:
            if '理' in cell or '物理' in cell:
                category = '理科' if '理' in cell and '物理' not in cell else '物理'
            elif '文' in cell or '历史' in cell:
                category = '文科' if '文' in cell and '历史' not in cell else '历史'
            elif '综合' in cell:
                category = '综合'
    
    if school and score:
        return {
            'school': school,
            'score': score,
            'rank': rank,
            'year': year,
            'category': category or '未知',
            'source': 'dxsbb',
        }
    
    return None

def collect_dxsbb_known(province_filter=None, dry_run=False):
    """从已知dxsbb URL采集"""
    collected = 0
    new_records = []
    existing_keys = set()
    
    classified = load_classified()
    if not dry_run:
        existing_keys = get_existing_keys(classified)
    
    log("=== 采集 dxsbb.com 已知URL ===")
    
    for label, url in DXSBB_KNOWN_URLS.items():
        parts = label.split('_')
        province = parts[0]
        year = int(parts[1])
        
        if province_filter and province != province_filter:
            continue
        
        log(f"  获取 {label}: {url}")
        html = fetch_dxsbb_page(url)
        if not html:
            log(f"  ❌ 无法获取 {label}")
            continue
        
        records = parse_dxsbb_table(html, province, year)
        log(f"  解析到 {len(records)} 条记录")
        
        for rec in records:
            school = rec['school']
            cat = rec['category']
            key = f"{school}|{year}|{cat}"
            full_key = f"{province}|{key}"
            
            if full_key in existing_keys:
                continue
            
            new_records.append({
                'province': province,
                'key': key,
                'score': rec['score'],
                'rank': rec['rank'],
                'school': school,
                'category': cat,
            })
        
        time.sleep(0.5)
    
    log(f"  dxsbb已知URL: 新增 {len(new_records)} 条")
    return new_records

def discover_dxsbb_new_urls(start_id=140000, end_id=160000, step=1):
    """搜索dxsbb.com新的URL（扩展范围）"""
    log(f"=== 搜索 dxsbb.com 新URL ({start_id}-{end_id}) ===")
    new_urls = {}
    
    for uid in range(start_id, end_id, step):
        url = f"https://www.dxsbb.com/news/{uid}.html"
        try:
            r = session.head(url, headers=HEADERS, timeout=5, allow_redirects=False)
            if r.status_code in (200, 301, 302):
                # 获取页面标题
                r2 = session.get(url, headers=HEADERS, timeout=10)
                title_match = re.search(r'<title>(.*?)</title>', r2.text)
                title = title_match.group(1) if title_match else ''
                
                if '投档' in title or '分数线' in title or '录取' in title:
                    new_urls[uid] = {'url': url, 'title': title}
                    log(f"  ✅ {uid}: {title}")
        except:
            pass
        
        if uid % 100 == 0:
            log(f"  进度: {uid}/{end_id}, 发现 {len(new_urls)} 个")
            time.sleep(0.5)
    
    log(f"  搜索完成: 发现 {len(new_urls)} 个新URL")
    return new_urls

# ========== 数据源2: EOL ==========

def collect_eol_province(province_id, year=2025, province_name='', dry_run=False):
    """从EOL API采集某省某年数据"""
    url = f"{EOL_BASE}/schoolprovince"
    params = {
        'province_id': province_id,
        'year': year,
        'page': 1,
        'size': 100,
    }
    
    collected = 0
    page = 1
    
    while True:
        params['page'] = page
        try:
            r = session.get(url, params=params, headers={
                **HEADERS,
                'Referer': f'https://www.eol.cn/eol/api',
            }, timeout=15)
            
            if r.status_code != 200:
                break
            
            data = r.json()
            
            # EOL限流检查
            if data.get('code') == 1069:
                log(f"  ⚠️ EOL限流 (code 1069)，停止采集")
                break
            
            items = data.get('data', {}).get('items', [])
            if not items:
                break
            
            for item in items:
                school = item.get('name', '')
                score = item.get('min', 0)
                rank = item.get('min_section')
                cat = item.get('local_type_name', '未知')
                local_prov = item.get('local_province_name', '')
                
                if school and score and int(score) > 0:
                    collected += 1
            
            total_pages = data.get('data', {}).get('total_page', 1)
            if page >= total_pages:
                break
            page += 1
            time.sleep(0.3)
            
        except Exception as e:
            log(f"  EOL API error: {e}")
            break
    
    return collected

def collect_eol_all(province_filter=None, year=2025, dry_run=False):
    """从EOL采集所有省份"""
    log(f"=== 采集 EOL API ({year}年) ===")
    
    # 省份ID映射（EOL的province_id）
    PROVINCE_IDS = {
        '北京': 1, '天津': 2, '河北': 3, '山西': 4, '内蒙古': 5,
        '辽宁': 6, '吉林': 7, '黑龙江': 8, '上海': 9, '江苏': 10,
        '浙江': 11, '安徽': 12, '福建': 13, '江西': 14, '山东': 15,
        '河南': 16, '湖北': 17, '湖南': 18, '广东': 19, '广西': 20,
        '海南': 21, '重庆': 22, '四川': 23, '贵州': 24, '云南': 25,
        '西藏': 26, '陕西': 27, '甘肃': 28, '青海': 29, '宁夏': 30,
        '新疆': 31,
    }
    
    total = 0
    for prov, pid in PROVINCE_IDS.items():
        if province_filter and prov != province_filter:
            continue
        log(f"  {prov} (id={pid})...")
        n = collect_eol_province(pid, year, prov, dry_run)
        total += n
        log(f"   获取 {n} 条")
    
    log(f"  EOL合计: {total} 条")
    return total

# ========== 数据源3: raw_2024.json 深度挖掘 ==========

def collect_from_raw2024(province_filter=None, dry_run=False):
    """从raw_2024.json提取更多数据"""
    if not os.path.exists(RAW_2024_PATH):
        log("  raw_2024.json 不存在，跳过")
        return []
    
    log("=== 从 raw_2024.json 提取数据 ===")
    
    with open(RAW_2024_PATH, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    classified = load_classified()
    existing_keys = get_existing_keys(classified) if not dry_run else set()
    
    new_records = []
    
    for item in raw:
        prov = item.get('province_name', '')
        if not prov:
            continue
        if province_filter and prov != province_filter:
            continue
        
        school = item.get('name', '')
        score = item.get('min', 0)
        rank = item.get('min_section')
        cat = item.get('local_type_name', '物理')
        year = 2024
        
        if school and score and int(score) > 0:
            key = f"{school}|{year}|{cat}"
            full_key = f"{prov}|{key}"
            
            if full_key in existing_keys:
                continue
            
            new_records.append({
                'province': prov,
                'key': key,
                'score': int(score),
                'rank': int(rank) if rank else None,
                'school': school,
                'category': cat,
            })
    
    log(f"  raw_2024.json: 新增 {len(new_records)} 条")
    return new_records

# ========== 数据整合 ==========

def integrate_new_records(new_records, dry_run=False):
    """将新记录整合到province_classified.json"""
    if not new_records:
        return 0
    
    classified = load_classified()
    integrated = 0
    
    for rec in new_records:
        prov = rec['province']
        if prov not in classified:
            classified[prov] = {'pairs': {}}
        
        pdata = classified[prov]
        if 'pairs' not in pdata:
            pdata['pairs'] = {}
        
        key = rec['key']
        if key in pdata['pairs']:
            continue
        
        pdata['pairs'][key] = {
            'score': rec['score'],
            'rank': rec.get('rank'),
        }
        integrated += 1
    
    if not dry_run and integrated > 0:
        save_classified(classified)
    
    return integrated

# ========== 回测 ==========

def run_backtest(dry_run=False):
    """运行回测（IQR自适应阈值，与backtest_by_cat_v2.py一致）"""
    log("=== 运行回测（IQR自适应阈值） ===")
    
    classified = load_classified()
    prov_cat_offsets = {}
    
    for prov, pdata in classified.items():
        pairs = pdata.get('pairs', {})
        school_cat_years = {}
        
        for key, val in pairs.items():
            parts = key.split('|')
            if len(parts) >= 3:
                school, year_str, cat = parts[0], parts[1], parts[2]
                score = val.get('score') if isinstance(val, dict) else val
                if score:
                    try:
                        k = (school, cat)
                        if k not in school_cat_years:
                            school_cat_years[k] = {}
                        school_cat_years[k][int(year_str)] = int(score)
                    except:
                        continue
        
        for (school, cat), years in school_cat_years.items():
            yr_list = sorted(years.keys())
            for i in range(len(yr_list) - 1):
                y1, y2 = yr_list[i], yr_list[i+1]
                offset = years[y2] - years[y1]
                prov_cat_offsets.setdefault(prov, {}).setdefault(cat, []).append(offset)
    
    # 计算每个省份+科类的IQR自适应阈值
    prov_results = {}
    total_c_hits = total_c_total = 0
    total_w_hits = total_w_total = 0
    total_b_hits = total_b_total = 0
    
    for prov in sorted(prov_cat_offsets.keys()):
        for cat in sorted(prov_cat_offsets[prov].keys()):
            offsets = prov_cat_offsets[prov][cat]
            if len(offsets) < 3:
                continue
            
            n = len(offsets)
            sorted_off = sorted(offsets)
            q1 = sorted_off[n // 4]
            q3 = sorted_off[3 * n // 4]
            iqr = q3 - q1
            median = sorted_off[n // 2]
            
            # IQR自适应阈值
            # 冲：分数大幅上涨 → offset > c_thresh → 说明院校分数线涨幅超过预期，可以冲
            # 保：分数大幅下跌 → offset < b_thresh → 说明院校分数线跌幅大，可以保
            # 稳：在两者之间
            c_thresh = q3 + 1.5 * iqr  # 冲的阈值（分数涨幅上限）
            b_thresh = q1 - 1.5 * iqr  # 保的阈值（分数跌幅下限）
            
            # 命中率 = 偏移量在阈值范围内的比例
            # 冲命中：offset <= c_thresh（分数没涨太多，位次在冲的范围内）
            # 保命中：offset >= b_thresh（分数没跌太多，位次在保的范围内）
            c_hits = sum(1 for o in offsets if o <= c_thresh)
            b_hits = sum(1 for o in offsets if o >= b_thresh)
            w_hits = n - c_hits - b_hits  # 注意：c_hits和b_hits有重叠部分
            # 修正：稳 = 既在c_thresh以下又在b_thresh以上
            w_hits = sum(1 for o in offsets if b_thresh <= o <= c_thresh)
            
            c_rate = c_hits / n * 100
            w_rate = w_hits / n * 100
            b_rate = b_hits / n * 100
            
            prov_results.setdefault(prov, {})[cat] = {
                'pairs': n, 'C': round(c_rate, 1), 'W': round(w_rate, 1), 'B': round(b_rate, 1),
                'median': median, 'iqr': iqr,
            }
            
            total_c_hits += c_hits
            total_c_total += n
            total_w_hits += w_hits
            total_w_total += n
            total_b_hits += b_hits
            total_b_total += n
    
    nat_c = total_c_hits / total_c_total * 100 if total_c_total else 0
    nat_w = total_w_hits / total_w_total * 100 if total_w_total else 0
    nat_b = total_b_hits / total_b_total * 100 if total_b_total else 0
    
    log(f"  全国汇总: {total_c_total}对, C={nat_c:.1f}%, W={nat_w:.1f}%, B={nat_b:.1f}%")
    
    for prov in sorted(prov_results.keys()):
        cats = prov_results[prov]
        for cat in sorted(cats.keys()):
            r = cats[cat]
            log(f"  {prov} {cat}: {r['pairs']}对, C={r['C']}%, W={r['W']}%, B={r['B']}%")
    
    return {
        'national': {'pairs': total_c_total, 'C': round(nat_c, 1), 'W': round(nat_w, 1), 'B': round(nat_b, 1)},
        'provinces': prov_results,
    }

# ========== 报告 ==========

def generate_report(bt_result, new_count, source_stats):
    """生成采集报告"""
    report = {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'new_records': new_count,
        'source_stats': source_stats,
        'backtest': bt_result,
        'total_records': count_pairs(load_classified()),
    }
    
    log("\n" + "="*60)
    log("📊 采集报告")
    log("="*60)
    log(f"  新增数据: {new_count} 条")
    log(f"  总数据量: {report['total_records']} 条")
    log(f"  数据源统计: {json.dumps(source_stats, ensure_ascii=False)}")
    
    nat = bt_result['national']
    log(f"  回测结果: {nat['pairs']}对, C={nat['C']}%, W={nat['W']}%, B={nat['B']}%")
    
    # 保存报告
    report_dir = os.path.join(DATA_DIR, "collect_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"  报告已保存: {report_file}")
    
    return report

# ========== 主流程 ==========

def main():
    parser = argparse.ArgumentParser(description='高考志愿数据每日采集')
    parser.add_argument('--source', choices=['dxsbb', 'eol', 'raw2024', 'all'], default='all',
                        help='数据源选择 (默认: all)')
    parser.add_argument('--province', type=str, default=None,
                        help='只采集指定省份 (如: 贵州)')
    parser.add_argument('--year', type=int, default=None,
                        help='只采集指定年份 (如: 2025)')
    parser.add_argument('--discover', action='store_true',
                        help='搜索dxsbb.com新URL')
    parser.add_argument('--dry-run', action='store_true',
                        help='试跑，不保存数据')
    parser.add_argument('--backtest-only', action='store_true',
                        help='只做回测，不采集')
    args = parser.parse_args()
    
    log("="*60)
    log("🎓 高考志愿数据每日采集")
    log("="*60)
    
    if args.dry_run:
        log("  ⚠️ DRY RUN 模式，不会保存数据")
    
    if args.backtest_only:
        bt = run_backtest(args.dry_run)
        generate_report(bt, 0, {})
        return
    
    all_new = []
    source_stats = {}
    
    # 1. dxsbb.com 已知URL
    if args.source in ('dxsbb', 'all'):
        dxsbb_new = collect_dxsbb_known(args.province, args.dry_run)
        all_new.extend(dxsbb_new)
        source_stats['dxsbb_known'] = len(dxsbb_new)
    
    # 2. EOL API
    if args.source in ('eol', 'all'):
        year = args.year or 2025
        eol_count = collect_eol_all(args.province, year, args.dry_run)
        source_stats['eol'] = eol_count
    
    # 3. raw_2024.json
    if args.source in ('raw2024', 'all'):
        raw_new = collect_from_raw2024(args.province, args.dry_run)
        all_new.extend(raw_new)
        source_stats['raw2024'] = len(raw_new)
    
    # 4. 整合
    integrated = integrate_new_records(all_new, args.dry_run)
    log(f"\n=== 整合完成: {integrated} 条新增 ===")
    
    # 5. 回测
    bt = run_backtest(args.dry_run)
    
    # 6. 报告
    report = generate_report(bt, integrated, source_stats)
    
    # 7. 更新采集日志
    log_data = load_collect_log()
    log_data['runs'].append({
        'time': report['time'],
        'new_records': integrated,
        'total_records': report['total_records'],
        'backtest': bt['national'],
        'source_stats': source_stats,
    })
    log_data['total_collected'] += integrated
    for src, cnt in source_stats.items():
        log_data['source_stats'][src] = log_data['source_stats'].get(src, 0) + cnt
    save_collect_log(log_data)
    
    log("\n✅ 采集完成！")

if __name__ == '__main__':
    main()
