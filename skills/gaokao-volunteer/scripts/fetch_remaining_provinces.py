#!/usr/bin/env python
"""批量下载并提取剩余省份的投档线数据（16省）。"""
import json, os, re, sys, time, traceback
from pathlib import Path
import urllib.request, ssl

# ─── 配置 ───
DATA_DIR = Path(r"D:\GitHub\hermescn\data\gaokao-data")
HTML_DIR = DATA_DIR / "dxsbb_html"
V9_DIR   = DATA_DIR / "province_v9"
HTML_DIR.mkdir(parents=True, exist_ok=True)
V9_DIR.mkdir(parents=True, exist_ok=True)

# 关闭代理
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# ─── 待下载省份（只取本科批，2023+2024配对）───
ARTICLES = {
    # 老高考（2023+2024都是文/理）
    "四川": [
        ("2023理科一本", "https://www.dxsbb.com/news/144146.html", "2023", "理科", "一本"),
        ("2023文科一本", "https://www.dxsbb.com/news/144151.html", "2023", "文科", "一本"),
        ("2023理科二本", "https://www.dxsbb.com/news/144156.html", "2023", "理科", "二本"),
        ("2023文科二本", "https://www.dxsbb.com/news/144163.html", "2023", "文科", "二本"),
        ("2024理科一本", "https://www.dxsbb.com/news/147483.html", "2024", "理科", "一本"),
        ("2024文科一本", "https://www.dxsbb.com/news/147480.html", "2024", "文科", "一本"),
        ("2024理科二本", "https://www.dxsbb.com/news/147491.html", "2024", "理科", "二本"),
        ("2024文科二本", "https://www.dxsbb.com/news/147489.html", "2024", "文科", "二本"),
    ],
    "云南": [
        ("2023理科一本", "https://www.dxsbb.com/news/144234.html", "2023", "理科", "一本"),
        ("2023文科一本", "https://www.dxsbb.com/news/144233.html", "2023", "文科", "一本"),
        ("2023理科二本", "https://www.dxsbb.com/news/144236.html", "2023", "理科", "二本"),
        ("2023文科二本", "https://www.dxsbb.com/news/144235.html", "2023", "文科", "二本"),
        ("2024理科一本", "https://www.dxsbb.com/news/147555.html", "2024", "理科", "一本"),
        ("2024文科一本", "https://www.dxsbb.com/news/147548.html", "2024", "文科", "一本"),
        ("2024理科二本", "https://www.dxsbb.com/news/147559.html", "2024", "理科", "二本"),
        ("2024文科二本", "https://www.dxsbb.com/news/147558.html", "2024", "文科", "二本"),
    ],
    "新疆": [
        ("2023理科一本", "https://www.dxsbb.com/news/144219.html", "2023", "理科", "一本"),
        ("2023文科一本", "https://www.dxsbb.com/news/144220.html", "2023", "文科", "一本"),
        ("2023理科二本", "https://www.dxsbb.com/news/144221.html", "2023", "理科", "二本"),
        ("2023文科二本", "https://www.dxsbb.com/news/144222.html", "2023", "文科", "二本"),
        ("2024理科一本", "https://www.dxsbb.com/news/147544.html", "2024", "理科", "一本"),
        ("2024文科一本", "https://www.dxsbb.com/news/147545.html", "2024", "文科", "一本"),
        ("2024理科二本", "https://www.dxsbb.com/news/147546.html", "2024", "理科", "二本"),
        ("2024文科二本", "https://www.dxsbb.com/news/147547.html", "2024", "文科", "二本"),
    ],
    "宁夏": [
        ("2023理科一本", "https://www.dxsbb.com/news/144226.html", "2023", "理科", "一本"),
        ("2023文科一本", "https://www.dxsbb.com/news/144227.html", "2023", "文科", "一本"),
        ("2023理科二本", "https://www.dxsbb.com/news/144229.html", "2023", "理科", "二本"),
        ("2023文科二本", "https://www.dxsbb.com/news/144230.html", "2023", "文科", "二本"),
        ("2024理科一本", "https://www.dxsbb.com/news/147550.html", "2024", "理科", "一本"),
        ("2024文科一本", "https://www.dxsbb.com/news/147551.html", "2024", "文科", "一本"),
        ("2024理科二本", "https://www.dxsbb.com/news/147553.html", "2024", "理科", "二本"),
        ("2024文科二本", "https://www.dxsbb.com/news/147554.html", "2024", "文科", "二本"),
    ],
    # 新高考（2023+2024都是物/历）
    "福建": [
        ("2023历史", "https://www.dxsbb.com/news/144245.html", "2023", "历史", "本科"),
        ("2023物理", "https://www.dxsbb.com/news/144246.html", "2023", "物理", "本科"),
        ("2024历史", "https://www.dxsbb.com/news/147524.html", "2024", "历史", "本科"),
        ("2024物理", "https://www.dxsbb.com/news/147521.html", "2024", "物理", "本科"),
    ],
    "湖北": [
        ("2023历史", "https://www.dxsbb.com/news/144205.html", "2023", "历史", "本科"),
        ("2023物理", "https://www.dxsbb.com/news/144204.html", "2023", "物理", "本科"),
        ("2024历史", "https://www.dxsbb.com/news/147537.html", "2024", "历史", "本科"),
        ("2024物理", "https://www.dxsbb.com/news/147535.html", "2024", "物理", "本科"),
    ],
    "江苏": [
        ("2023历史", "https://www.dxsbb.com/news/137511.html", "2023", "历史", "本科"),
        ("2023物理", "https://www.dxsbb.com/news/137510.html", "2023", "物理", "本科"),
        ("2024历史", "https://www.dxsbb.com/news/147502.html", "2024", "历史", "本科"),
        ("2024物理", "https://www.dxsbb.com/news/147503.html", "2024", "物理", "本科"),
    ],
    "重庆": [
        ("2023历史", "https://www.dxsbb.com/news/144189.html", "2023", "历史", "本科"),
        ("2023物理", "https://www.dxsbb.com/news/144188.html", "2023", "物理", "本科"),
        ("2024历史", "https://www.dxsbb.com/news/147510.html", "2024", "历史", "本科"),
        ("2024物理", "https://www.dxsbb.com/news/147508.html", "2024", "物理", "本科"),
    ],
    # 3+3 新高考（不分文理/物历）
    "北京": [
        ("2023本科", "https://www.dxsbb.com/news/137611.html", "2023", "综合", "本科"),
        ("2024本科", "https://www.dxsbb.com/news/147452.html", "2024", "综合", "本科"),
    ],
    "天津": [
        ("2023本科A", "https://www.dxsbb.com/news/144121.html", "2023", "综合", "本科A"),
        ("2024本科A", "https://www.dxsbb.com/news/147450.html", "2024", "综合", "本科A"),
    ],
    "上海": [
        ("2023本科", "https://www.dxsbb.com/news/144122.html", "2023", "综合", "本科"),
        ("2024本科", "https://www.dxsbb.com/news/147457.html", "2024", "综合", "本科"),
    ],
    "海南": [
        ("2023本科", "https://www.dxsbb.com/news/144137.html", "2023", "综合", "本科"),
        ("2024本科", "https://www.dxsbb.com/news/147455.html", "2024", "综合", "本科"),
    ],
    # 过渡省份（2023文/理 → 2024物/历）—— 只取2024数据做单年参考
    "安徽": [
        ("2024物理", "https://www.dxsbb.com/news/147467.html", "2024", "物理", "本科"),
        ("2024历史", "https://www.dxsbb.com/news/147470.html", "2024", "历史", "本科"),
    ],
    "贵州": [
        ("2024物理", "https://www.dxsbb.com/news/147473.html", "2024", "物理", "本科"),
        ("2024历史", "https://www.dxsbb.com/news/147469.html", "2024", "历史", "本科"),
    ],
    "江西": [
        ("2024物理", "https://www.dxsbb.com/news/147511.html", "2024", "物理", "本科"),
        ("2024历史", "https://www.dxsbb.com/news/147509.html", "2024", "历史", "本科"),
    ],
}


def download(url, save_path):
    """下载HTML页面"""
    if save_path.exists() and save_path.stat().st_size > 1000:
        return True
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
            raw = resp.read()
            # 尝试常见编码
            for enc in ('utf-8', 'gbk', 'gb2312'):
                try:
                    text = raw.decode(enc)
                    break
                except:
                    continue
            else:
                text = raw.decode('utf-8', errors='replace')
            save_path.write_text(text, encoding='utf-8')
            return True
    except Exception as e:
        print(f"  ❌ 下载失败 {url}: {e}")
        return False


def extract_table_data(html_text):
    """从HTML中提取所有table的数据行"""
    from html.parser import HTMLParser
    
    tables = []
    current_table = None
    current_row = None
    current_cell = None
    in_table = False
    in_row = False
    in_cell = False
    skip_tag = False  # 跳过script/style内的内容
    
    class TableParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tables = []
            self.current_table = None
            self.current_row = None
            self.current_cell = None
            self.in_table = False
            self.in_row = False
            self.in_cell = False
            self.skip_depth = 0
            
        def handle_starttag(self, tag, attrs):
            if tag in ('script', 'style'):
                self.skip_depth += 1
            elif tag == 'table':
                self.in_table = True
                self.current_table = []
            elif tag == 'tr' and self.in_table:
                self.in_row = True
                self.current_row = []
            elif tag in ('td', 'th') and self.in_row:
                self.in_cell = True
                self.current_cell = []
                
        def handle_endtag(self, tag):
            if tag in ('script', 'style'):
                self.skip_depth = max(0, self.skip_depth - 1)
            elif tag == 'table' and self.in_table:
                if self.current_table and len(self.current_table) > 1:
                    self.tables.append(self.current_table)
                self.in_table = False
                self.current_table = None
            elif tag == 'tr' and self.in_row:
                if self.current_row:
                    self.current_table.append(self.current_row)
                self.in_row = False
                self.current_row = None
            elif tag in ('td', 'th') and self.in_cell:
                text = ''.join(self.current_cell).strip()
                text = re.sub(r'&nbsp;', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                self.current_row.append(text)
                self.in_cell = False
                self.current_cell = None
                
        def handle_data(self, data):
            if self.skip_depth > 0:
                return
            if self.in_cell:
                self.current_cell.append(data)
    
    parser = TableParser()
    try:
        parser.feed(html_text)
    except:
        pass
    return parser.tables


def identify_columns(header_row, table_data):
    """识别表格列：返回 {col_idx: 'school'/'score'/'rank'/'plan'/'code'}"""
    col_map = {}
    for i, h in enumerate(header_row):
        h_lower = h.lower().strip()
        # 学校
        if any(k in h for k in ['院校名称', '学校名称', '院校', '高校', '大学', '学校']):
            if 'school' not in col_map.values():
                col_map[i] = 'school'
        # 分数
        elif any(k in h for k in ['投档分', '录取分', '最低分', '投档线', '分数线', '最低', '分数']):
            if i not in col_map:
                col_map[i] = 'score'
        # 位次/排位
        elif any(k in h for k in ['最低位次', '位次', '排位', '排名', '最低排', '累计人数']):
            if i not in col_map:
                col_map[i] = 'rank'
        # 计划数
        elif any(k in h for k in ['计划数', '计划', '招生计划']):
            if i not in col_map:
                col_map[i] = 'plan'
        # 院校代号/代码
        elif any(k in h for k in ['院校代号', '院校代码', '学校代码', '代号', '代码']):
            if i not in col_map:
                col_map[i] = 'code'
        # 专业
        elif any(k in h for k in ['专业代号', '专业名称', '专业']):
            if i not in col_map:
                col_map[i] = 'major'
    
    # 如果表头没识别出school，用数据推断
    if 'school' not in col_map.values() and len(table_data) > 2:
        for i in range(min(len(header_row), 10)):
            if i in col_map:
                continue
            # 检查该列是否包含大学/学院/学校关键词
            school_count = 0
            for row in table_data[:50]:
                if i < len(row) and any(k in row[i] for k in ['大学', '学院', '学校', '分校']):
                    school_count += 1
            if school_count > 5:
                col_map[i] = 'school'
                break
    
    # 如果没识别出score，用数据推断
    if 'score' not in col_map.values() and len(table_data) > 2:
        for i in range(min(len(header_row), 15)):
            if i in col_map:
                continue
            # 检查该列是否主要是数字（在300-750范围内）
            num_count = 0
            for row in table_data[:100]:
                if i < len(row):
                    val = row[i].replace(' ', '').replace('&nbsp;', '')
                    try:
                        num = float(val)
                        if 200 <= num <= 800:
                            num_count += 1
                    except:
                        pass
            if num_count > 20:
                col_map[i] = 'score'
                break
    
    return col_map


def find_header_row(tables):
    """在所有table中找到包含关键列名的表头行"""
    keywords = ['院校名称', '学校名称', '投档分', '录取分', '最低分', '投档线', '分数线']
    best_table = None
    best_row_idx = -1
    best_score = 0
    
    for table in tables:
        for idx, row in enumerate(table[:5]):  # 表头通常在前5行
            score = sum(1 for kw in keywords if any(kw in cell for cell in row))
            if score > best_score:
                best_score = score
                best_table = table
                best_row_idx = idx
    
    return best_table, best_row_idx


def parse_score(val):
    """解析分数值"""
    if not val:
        return None
    val = val.strip().replace(' ', '').replace('&nbsp;', '')
    # 提取第一个数字
    m = re.search(r'(\d+\.?\d*)', val)
    if m:
        try:
            num = float(m.group(1))
            if 100 <= num <= 800:
                return int(num) if num == int(num) else num
        except:
            pass
    return None


def parse_rank(val):
    """解析位次"""
    if not val:
        return None
    val = val.strip().replace(' ', '').replace('&nbsp;', '').replace(',', '')
    m = re.search(r'(\d+)', val)
    if m:
        try:
            num = int(m.group(1))
            if 10 < num < 5000000:
                return num
        except:
            pass
    return None


def process_province(province, articles):
    """处理一个省份：下载→提取→保存"""
    print(f"\n{'='*60}")
    print(f"处理: {province} ({len(articles)} pages)")
    print(f"{'='*60}")
    
    all_records = []
    
    for label, url, year, category, batch in articles:
        html_path = HTML_DIR / f"{province}_{label}.html"
        
        # 下载
        if not html_path.exists() or html_path.stat().st_size < 1000:
            print(f"  ⬇️ 下载 {label}...")
            if not download(url, html_path):
                continue
            time.sleep(1.5)  # 礼貌延迟
        else:
            print(f"  ✅ 已缓存 {label}")
        
        # 提取
        html_text = html_path.read_text(encoding='utf-8', errors='replace')
        tables = extract_table_data(html_text)
        
        if not tables:
            print(f"  ⚠️ 无表格数据")
            continue
        
        table, header_idx = find_header_row(tables)
        if not table or header_idx < 0:
            print(f"  ⚠️ 未找到表头")
            continue
        
        header_row = table[header_idx]
        data_rows = table[header_idx+1:]
        col_map = identify_columns(header_row, data_rows)
        
        school_col = None
        score_col = None
        rank_col = None
        for c, t in col_map.items():
            if t == 'school': school_col = c
            elif t == 'score': score_col = c
            elif t == 'rank': rank_col = c
        
        if school_col is None or score_col is None:
            print(f"  ⚠️ 列识别失败 (school={school_col}, score={score_col}), header={header_row[:8]}")
            continue
        
        count = 0
        for row in data_rows:
            if school_col >= len(row) or score_col >= len(row):
                continue
            school = row[school_col].strip()
            if not school or len(school) < 2:
                continue
            # 跳过非学校行
            if school in ('合计', '注:', '备注', '说明'):
                continue
            
            score = parse_score(row[score_col])
            if score is None or score < 100:
                continue
            
            rank = None
            if rank_col is not None and rank_col < len(row):
                rank = parse_rank(row[rank_col])
            
            all_records.append({
                'province': province,
                'year': year,
                'category': category,
                'batch': batch,
                'school': school,
                'score': score,
                'rank': rank,
            })
            count += 1
        
        print(f"  📊 {label}: {count} 条记录 (school col={school_col}, score col={score_col}, rank col={rank_col})")
    
    # 保存
    out_path = V9_DIR / f"{province}_v9.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    # 统计
    years = {}
    cats = {}
    for r in all_records:
        yk = f"{r['year']}_{r['category']}"
        years[yk] = years.get(yk, 0) + 1
        cats[r['category']] = cats.get(r['category'], 0) + 1
    
    print(f"  💾 保存 {len(all_records)} 条 → {out_path.name}")
    print(f"  📈 年份/科类分布: {dict(years)}")
    
    return len(all_records)


# ─── 主程序 ───
total = 0
success = 0
for province, articles in ARTICLES.items():
    try:
        n = process_province(province, articles)
        if n > 0:
            total += n
            success += 1
    except Exception as e:
        print(f"  ❌ {province} 出错: {e}")
        traceback.print_exc()

print(f"\n{'='*60}")
print(f"🎉 全部完成！{success}/{len(ARTICLES)} 省成功，共 {total} 条记录")
print(f"{'='*60}")
