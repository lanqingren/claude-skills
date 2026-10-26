#!/usr/bin/env python3
"""
文献检索智能路由调度器 v1.0
================================
根据研究领域自动选择最优检索通道：

  中国金融/社科/政策 → 🥇 cnki（浏览器自动化） → 🥈 arxiv（兜底）
  国际通用/技术/方法论 → 🥇 arxiv → 🥈 OpenAlex（元数据补全） → 🥉 cnki（补充中文视角）
  混合/不确定 → 三通道并行 → 去重合并

用法：
  python literature_router.py --keyword "商业银行 零售转型"
  python literature_router.py --keyword "deep learning image recognition" --domain tech
  python literature_router.py --keyword "乡村振兴 基层治理" --output results.json
"""

import json, re, time, urllib.request, urllib.parse, urllib.error
import argparse, sys
from pathlib import Path
from datetime import datetime


# ============================================================
# 领域分类器
# ============================================================

CN_SPECIFIC_SIGNALS = [
    # 中国金融/经济
    '银行', '商业银行', '央行', '利率', '存款', '贷款', '货币政策', '金融监管',
    '招商银行', '工商银行', '建设银行', '农业银行', '中国银行', '交通银行',
    '股份制银行', '城商行', '农商行', '零售转型', '对公业务', '中间业务',
    '理财', '信托', '保险', '证券', '资本市场', '注册制', '科创板',
    '沪港通', '深港通', '债券通', '熊猫债', '点心债',

    # 中国政策/治理
    '乡村振兴', '精准扶贫', '共同富裕', '双碳', '碳中和',
    '一带一路', '供给侧改革', '国企改革', '混合所有制',
    '新型城镇化', '户籍改革', '土地流转', '三权分置',
    '基层治理', '社区治理', '网格化', '放管服',
    '数字经济', '平台经济', '反垄断', '数据要素',

    # 中国特色领域
    '中医', '中药', '针灸', '推拿',
    '双减', '学区房', '高考改革', '职业教育',
    '大湾区', '长三角', '京津冀', '成渝',
    '雄安', '海南自贸港', '粤港澳',

    # 中国公司/品牌
    '华为', '腾讯', '阿里', '字节', '百度', '京东', '美团',
    '比亚迪', '宁德时代', '小米', '大疆',
]

TECH_SIGNALS = [
    # 通用技术
    'deep learning', 'machine learning', 'neural network', 'transformer',
    'reinforcement learning', 'gan', 'cnn', 'rnn', 'lstm', 'bert', 'gpt',
    'algorithm', 'optimization', 'complexity', 'throughput',
    'image recognition', 'nlp', 'computer vision', 'speech recognition',

    # 方法/模型
    'regression', 'classification', 'clustering', 'pca', 'svm',
    'random forest', 'xgboost', 'gradient boosting', 'time series',

    # 工程/系统
    'distributed system', 'kubernetes', 'docker', 'microservice',
    'database', 'blockchain', 'iot', '5g', 'cloud computing',
    'compiler', 'operating system', 'fpga', 'asic',
]


def classify_domain(keyword: str) -> dict:
    """
    分类研究领域
    返回: {domain, confidence, reason}
    """
    kw_lower = keyword.lower()

    cn_score = sum(1 for sig in CN_SPECIFIC_SIGNALS if sig in keyword)
    tech_score = sum(1 for sig in TECH_SIGNALS if sig in kw_lower)

    # 同时包含中英文信号 → 混合
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', keyword))
    has_english = bool(re.search(r'[a-zA-Z]{3,}', keyword))

    if cn_score >= 2 and tech_score == 0:
        return {'domain': 'cn_specific', 'confidence': 0.9,
                'reason': f'检测到{cn_score}个中国特有信号词'}
    elif tech_score >= 2 and cn_score == 0:
        return {'domain': 'tech_universal', 'confidence': 0.9,
                'reason': f'检测到{tech_score}个通用技术信号词'}
    elif cn_score >= 1 and tech_score >= 1:
        return {'domain': 'mixed', 'confidence': 0.7,
                'reason': f'同时含中国({cn_score})和技术({tech_score})信号'}
    elif has_chinese and not has_english:
        return {'domain': 'cn_specific', 'confidence': 0.5,
                'reason': '纯中文关键词，默认中国特有方向'}
    elif has_english and not has_chinese:
        return {'domain': 'tech_universal', 'confidence': 0.5,
                'reason': '纯英文关键词，默认国际通用方向'}
    else:
        return {'domain': 'mixed', 'confidence': 0.3,
                'reason': '无法明确分类，走混合通道'}


# ============================================================
# 通道1：arxiv API
# ============================================================

def channel_arxiv(keyword: str, max_results: int = 10) -> list:
    """arxiv API 搜索"""
    import xml.etree.ElementTree as ET
    try:
        encoded = urllib.parse.quote(keyword)
        url = f"https://export.arxiv.org/api/query?search_query=all:{encoded}&max_results={max_results}&sortBy=relevance"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_data = resp.read().decode('utf-8')

        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(xml_data)
        papers = []
        for entry in root.findall('atom:entry', ns):
            title_el = entry.find('atom:title', ns)
            published_el = entry.find('atom:published', ns)
            id_el = entry.find('atom:id', ns)

            authors = []
            for author in entry.findall('atom:author', ns):
                name = author.find('atom:name', ns)
                if name is not None and name.text:
                    authors.append(name.text)

            papers.append({
                'title': title_el.text.strip() if title_el is not None and title_el.text else '',
                'authors': authors,
                'year': published_el.text[:4] if published_el is not None and published_el.text else '',
                'journal': 'arXiv',
                'url': id_el.text.strip() if id_el is not None and id_el.text else '',
                'doi': '',
                'cited': 0,
                'source': 'arxiv',
            })
        return papers
    except Exception as e:
        print(f"  ⚠️ arxiv 通道异常: {e}")
        return []


# ============================================================
# 通道2：OpenAlex API（cnki-scholar 后端）
# ============================================================

def channel_openalex(keyword: str, max_results: int = 10) -> list:
    """OpenAlex API 搜索"""
    try:
        encoded = urllib.parse.quote(keyword)
        url = f"https://api.openalex.org/works?search={encoded}&per_page={max_results}&sort=cited_by_count:desc"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Hermes-LiteratureRouter/1.0')
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        papers = []
        for r in data.get('results', []):
            title = r.get('title', '')
            authors = [a.get('author', {}).get('display_name', '')
                      for a in r.get('authorships', [])]
            year = r.get('publication_year', '')
            doi = r.get('doi', '')
            cited = r.get('cited_by_count', 0)
            source = r.get('primary_location', {}) or {}
            journal = (source.get('source', {}) or {}).get('display_name', '')

            papers.append({
                'title': title,
                'authors': authors,
                'year': year,
                'journal': journal,
                'url': f"https://doi.org/{doi}" if doi else '',
                'doi': doi,
                'cited': cited,
                'source': 'openalex',
            })
        return papers
    except Exception as e:
        print(f"  ⚠️ OpenAlex 通道异常: {e}")
        return []


# ============================================================
# 通道3：cnki 浏览器自动化（占位——需用户配合）
# ============================================================

def channel_cnki_browser(keyword: str) -> list:
    """
    CNKI 浏览器自动化通道
    当前返回手动搜索指南（因为需要实际浏览器交互）
    """
    return []  # 浏览器自动化在此脚本中不可用，由上层 skill 调用 cnki-unified 处理


# ============================================================
# 去重与排序
# ============================================================

def deduplicate(papers: list) -> list:
    """按标题前60字符去重"""
    seen = set()
    unique = []
    for p in papers:
        key = p['title'].lower().strip()[:60]
        if key and key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def format_citation(p: dict, index: int) -> str:
    """格式化为引用条目"""
    authors = p.get('authors', [])
    author_str = ', '.join(authors[:3])
    if len(authors) > 3:
        author_str += ' 等'

    parts = [f"[{index}] {author_str}. {p['title']}"]
    if p.get('journal'):
        parts.append(f"[J]. {p['journal']}")
    if p.get('year'):
        parts.append(f", {p['year']}")
    parts.append(f"  [{p.get('source', '')}]")

    if p.get('doi'):
        parts.append(f"\n    DOI: {p['doi']}")
    if p.get('url') and 'arxiv' in p.get('url', ''):
        parts.append(f"\n    {p['url']}")

    return ''.join(parts)


# ============================================================
# 路由引擎
# ============================================================

def route_and_search(keyword: str, domain_hint: str = None,
                     max_results: int = 10, verbose: bool = True) -> dict:
    """
    智能路由主函数
    """
    # 1. 领域分类
    if domain_hint:
        classification = {'domain': domain_hint, 'confidence': 1.0,
                         'reason': '用户指定'}
    else:
        classification = classify_domain(keyword)

    if verbose:
        print(f"  🧭 领域判定: {classification['domain']} "
              f"(置信度{classification['confidence']:.0%}) — {classification['reason']}")

    # 2. 根据领域选择通道
    all_papers = []
    channels_used = []

    if classification['domain'] == 'cn_specific':
        # 中国特有 → cnki优先，arxiv兜底
        if verbose:
            print("  📡 路由: cnki（主） → arxiv（兜底）")

        # 先试 arxiv（异步可行），cnki 需浏览器交互留到上层
        arxiv_results = channel_arxiv(keyword, max_results)
        all_papers.extend(arxiv_results)
        channels_used.append('arxiv')

        # cnki 浏览器通道标记为待补充
        if verbose:
            print(f"  ⚠️ cnki 浏览器通道需用户配合，当前仅 arxiv 结果")

    elif classification['domain'] == 'tech_universal':
        # 国际通用 → arxiv优先，OpenAlex补元数据
        if verbose:
            print("  📡 路由: arxiv（主） → OpenAlex（元数据补全）")

        arxiv_results = channel_arxiv(keyword, max_results)
        all_papers.extend(arxiv_results)
        channels_used.append('arxiv')

        oa_results = channel_openalex(keyword, max_results)
        all_papers.extend(oa_results)
        channels_used.append('openalex')

    else:  # mixed
        # 混合 → 三通道并行
        if verbose:
            print("  📡 路由: arxiv ∥ OpenAlex（并行，cnki待补充）")

        arxiv_results = channel_arxiv(keyword, max_results)
        all_papers.extend(arxiv_results)
        channels_used.append('arxiv')

        oa_results = channel_openalex(keyword, max_results)
        all_papers.extend(oa_results)
        channels_used.append('openalex')

    # 3. 去重
    unique = deduplicate(all_papers)

    if verbose:
        print(f"  📊 各通道合计: {len(all_papers)}条 → 去重后: {len(unique)}条")
        print(f"  🏷️  使用通道: {', '.join(channels_used)}")

    return {
        'keyword': keyword,
        'classification': classification,
        'channels_used': channels_used,
        'total': len(unique),
        'papers': unique,
        'cnki_pending': classification['domain'] == 'cn_specific',
    }


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='文献检索智能路由调度器')
    parser.add_argument('--keyword', required=True, help='搜索关键词')
    parser.add_argument('--domain', help='手动指定领域: cn_specific / tech_universal / mixed')
    parser.add_argument('--max', type=int, default=10, dest='max_results', help='最大结果数')
    parser.add_argument('--output', help='输出JSON文件路径')
    parser.add_argument('--format', default='text', choices=['text', 'json', 'ref'],
                       help='输出格式')
    args = parser.parse_args()

    print(f'{"="*60}')
    print(f'  文献检索智能路由')
    print(f'  关键词: {args.keyword}')
    print(f'{"="*60}')

    start = time.time()
    result = route_and_search(args.keyword, args.domain, args.max_results)
    elapsed = time.time() - start

    if args.format == 'json' or args.output:
        output_data = {
            'keyword': result['keyword'],
            'classification': result['classification'],
            'channels_used': result['channels_used'],
            'total': result['total'],
            'cnki_pending': result['cnki_pending'],
            'papers': result['papers'],
            'elapsed': round(elapsed, 2),
        }
        if args.output:
            Path(args.output).write_text(
                json.dumps(output_data, ensure_ascii=False, indent=2),
                encoding='utf-8')
            print(f'\n  ✅ 结果已保存: {args.output}')
        else:
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
    elif args.format == 'ref':
        for i, p in enumerate(result['papers'][:args.max_results], 1):
            print(format_citation(p, i))
    else:
        print(f"\n  📋 前{min(5, result['total'])}条结果:")
        for i, p in enumerate(result['papers'][:5], 1):
            print(f"  [{i}] {p['title'][:80]}")
            if p.get('authors'):
                print(f"      作者: {', '.join(p['authors'][:3])}")
            if p.get('year'):
                print(f"      年份: {p['year']}  |  来源: {p['source']}  |  被引: {p.get('cited', 0)}")

    if result.get('cnki_pending'):
        encoded = urllib.parse.quote(result['keyword'])
        print(f"""
  ⚠️  CNKI 浏览器通道待补充。请手动在知网搜索：
      https://kns.cnki.net/kns8s/search?classid=YSTT4HG0&kw={encoded}
      搜索后将 标题+作者+期刊+年份 粘贴回来，自动补全引用。
""")

    print(f'\n  ⏱️  总耗时: {elapsed:.1f}s')


if __name__ == '__main__':
    main()
