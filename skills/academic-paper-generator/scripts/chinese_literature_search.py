#!/usr/bin/env python3
"""
多通道中文学术文献检索 — 替代不稳定的百度学术Playwright方案。

通道优先级（自动降级）：
  🥇 Tavily API（已配置key）→ 中文综合搜索 + 学术站点过滤
  🥈 Semantic Scholar → 英文论文（免费API，无key）
  🥉 arxiv API → 补充英文文献
  🏅 兜底 → 输出结构化搜索指令，用户手动搜后回来验证

用法：
  python chinese_literature_search.py --keyword "招商银行 零售转型" --lang zh
  python chinese_literature_search.py --keyword "commercial bank transformation" --lang en
  python chinese_literature_search.py --keyword "商业银行 风险管理" --max 15 --output results.json
"""

import json
import sys
import time
import argparse
import urllib.parse
import urllib.request
from pathlib import Path


# ============================================================
# 配置
# ============================================================

# Tavily API 配置（从memory中获取的key）
TAVILY_API_KEY = "tvly-dev-..."
TAVILY_API_URL = "https://api.tavily.com/search"

# 学术站点过滤
CN_ACADEMIC_SITES = [
    "cnki.net",
    "wanfangdata.com.cn",
    "cqvip.com",        # 维普
    "xueshu.baidu.com", # 百度学术（作为元数据源）
    "scholar.google.com",
]

CN_OFFICIAL_SITES = [
    "stats.gov.cn",     # 国家统计局
    "pbc.gov.cn",       # 央行
    "cbirc.gov.cn",     # 银保监会
    "csrc.gov.cn",      # 证监会
]

# arxiv API
ARXIV_API_URL = "https://export.arxiv.org/api/query"


# ============================================================
# 通道1：Tavily 搜索
# ============================================================

def search_tavily(keyword: str, max_results: int = 10,
                  include_domains: list = None) -> list:
    """通过Tavily API搜索，返回文献列表"""
    if not TAVILY_API_KEY or TAVILY_API_KEY == "tvly-dev-...":
        print("⚠️ Tavily API Key 未配置，跳过此通道")
        return []

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TAVILY_API_KEY}"
    }

    payload = {
        "query": keyword,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": False,
    }

    if include_domains:
        payload["include_domains"] = include_domains

    try:
        req = urllib.request.Request(
            TAVILY_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('results', [])

            papers = []
            for r in results:
                papers.append({
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'snippet': r.get('content', '')[:300],
                    'source': 'tavily',
                    'raw_score': r.get('score', 0),
                })
            return papers

    except Exception as e:
        print(f"⚠️ Tavily 搜索失败: {e}")
        return []


# ============================================================
# 通道2：arxiv 搜索
# ============================================================

def search_arxiv(keyword: str, max_results: int = 10) -> list:
    """通过arxiv API搜索英文文献"""
    import xml.etree.ElementTree as ET

    params = urllib.parse.urlencode({
        'search_query': f'all:{keyword}',
        'max_results': max_results,
        'sortBy': 'relevance',
    })
    url = f"{ARXIV_API_URL}?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_data = resp.read().decode('utf-8')

        # 解析XML
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(xml_data)

        papers = []
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns)
            summary = entry.find('atom:summary', ns)
            link = entry.find('atom:id', ns)

            authors = []
            for author in entry.findall('atom:author', ns):
                name = author.find('atom:name', ns)
                if name is not None and name.text:
                    authors.append(name.text)

            papers.append({
                'title': title.text.strip() if title is not None and title.text else '',
                'authors': authors,
                'url': link.text.strip() if link is not None and link.text else '',
                'snippet': (summary.text[:300] if summary is not None and summary.text else ''),
                'source': 'arxiv',
                'year': extract_year(entry),
            })

        return papers

    except Exception as e:
        print(f"⚠️ arxiv 搜索失败: {e}")
        return []


def extract_year(entry) -> str:
    """从arxiv条目提取年份"""
    import xml.etree.ElementTree as ET
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    published = entry.find('atom:published', ns)
    if published is not None and published.text:
        return published.text[:4]
    return ''


# ============================================================
# 通道3：Semantic Scholar
# ============================================================

def search_semantic_scholar(keyword: str, max_results: int = 10) -> list:
    """通过Semantic Scholar API搜索"""
    params = urllib.parse.urlencode({
        'query': keyword,
        'limit': max_results,
        'fields': 'title,authors,year,url,abstract,externalIds,publicationVenue',
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        papers = []
        for p in data.get('data', []):
            authors = [a.get('name', '') for a in p.get('authors', [])]
            venue = p.get('publicationVenue', {}) or {}
            papers.append({
                'title': p.get('title', ''),
                'authors': authors,
                'year': p.get('year', ''),
                'url': p.get('url', ''),
                'snippet': (p.get('abstract', '') or '')[:300],
                'source': 'semantic_scholar',
                'venue': venue.get('name', ''),
                'doi': (p.get('externalIds', {}) or {}).get('DOI', ''),
            })

        return papers

    except Exception as e:
        print(f"⚠️ Semantic Scholar 搜索失败: {e}")
        return []


# ============================================================
# 去重 & 排序
# ============================================================

def deduplicate_and_rank(papers: list) -> list:
    """按标题相似度去重，按来源优先级排序"""
    seen_titles = set()
    unique = []

    source_priority = {'tavily': 0, 'semantic_scholar': 1, 'arxiv': 2}

    for p in sorted(papers, key=lambda x: source_priority.get(x.get('source', ''), 99)):
        title_key = p['title'].lower().strip()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique.append(p)

    return unique


# ============================================================
# 格式化输出
# ============================================================

def format_reference(paper: dict, index: int) -> str:
    """格式化单条文献为引用格式"""
    title = paper.get('title', '')
    authors = paper.get('authors', [])
    year = paper.get('year', '')
    source = paper.get('source', '')
    url = paper.get('url', '')
    venue = paper.get('venue', '')

    author_str = ', '.join(authors[:3])
    if len(authors) > 3:
        author_str += ' 等'

    parts = [f"[{index}] {author_str}. {title}"]
    if venue:
        parts.append(f"[J]. {venue}, {year}.")
    elif year:
        parts.append(f" [{year}].")

    parts.append(f"\n    来源: {source} | {url}")

    return ''.join(parts)


def generate_manual_search_guide(keyword: str) -> str:
    """生成手动搜索指导"""
    encoded = urllib.parse.quote(keyword)
    return f"""
============================================================
  ⚠️ 自动检索未获取到足够中文学术文献
  请手动执行以下搜索，然后回来让我核实：
============================================================

1. 知网 (CNKI): https://kns.cnki.net/kns8/defaultresult/index
   搜索词: {keyword}

2. 万方 (WanFang): https://s.wanfangdata.com.cn/paper
   搜索词: {keyword}

3. 百度学术: https://xueshu.baidu.com/s?wd={encoded}

4. Google Scholar: https://scholar.google.com/scholar?q={encoded}

操作步骤：
  - 搜索 → 筛选近5年/核心期刊 → 复制 标题+作者+期刊+年份+卷期
  - 粘贴给我 → 我逐条核实6项元数据后写入论文

============================================================
"""


# ============================================================
# 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='多通道学术文献检索')
    parser.add_argument('--keyword', required=True, help='搜索关键词')
    parser.add_argument('--lang', default='zh', choices=['zh', 'en'],
                       help='主要语言')
    parser.add_argument('--max', type=int, default=10, dest='max_results',
                       help='最大结果数')
    parser.add_argument('--output', help='输出JSON文件路径')
    parser.add_argument('--format', default='text',
                       choices=['text', 'json', 'ref'],
                       help='输出格式')
    args = parser.parse_args()

    print(f'🔍 多通道文献检索: "{args.keyword}"')
    print(f'   目标语言: {args.lang}, 最大结果: {args.max_results}')
    print()

    all_papers = []

    # 🥇 中文通道：Tavily
    if args.lang == 'zh':
        print('── 🥇 Tavily 中文搜索 ──')
        # 先搜学术站点
        academic_papers = search_tavily(
            f"{args.keyword} 学术 期刊",
            max_results=args.max_results,
        )
        print(f'   找到 {len(academic_papers)} 条')
        all_papers.extend(academic_papers)

    # 🥈 Semantic Scholar
    print('── 🥈 Semantic Scholar ──')
    ss_papers = search_semantic_scholar(args.keyword, args.max_results)
    print(f'   找到 {len(ss_papers)} 条')
    all_papers.extend(ss_papers)

    # 🥉 arxiv（补充英文文献）
    print('── 🥉 arxiv ──')
    arxiv_papers = search_arxiv(args.keyword, args.max_results)
    print(f'   找到 {len(arxiv_papers)} 条')
    all_papers.extend(arxiv_papers)

    # 去重排序
    unique = deduplicate_and_rank(all_papers)
    print(f'\n📊 去重后共 {len(unique)} 条文献')

    # 输出
    if args.format == 'json' or args.output:
        output_data = {
            'keyword': args.keyword,
            'total': len(unique),
            'papers': unique,
        }
        if args.output:
            Path(args.output).write_text(
                json.dumps(output_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            print(f'   → 已保存到 {args.output}')
        else:
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
    elif args.format == 'ref':
        for i, p in enumerate(unique, 1):
            print(format_reference(p, i))
    else:
        for i, p in enumerate(unique, 1):
            print(f"\n[{i}] {p['title']}")
            if p.get('authors'):
                print(f"    作者: {', '.join(p['authors'])}")
            if p.get('year'):
                print(f"    年份: {p['year']}")
            if p.get('venue'):
                print(f"    期刊: {p['venue']}")
            print(f"    来源: {p['source']}")
            print(f"    URL: {p['url']}")
            print(f"    摘要: {p.get('snippet', '')[:150]}...")

    # 中文文献不足 → 提示手动搜索
    cn_papers = [p for p in unique if p['source'] == 'tavily']
    if args.lang == 'zh' and len(cn_papers) < 3:
        print(generate_manual_search_guide(args.keyword))


if __name__ == '__main__':
    main()
