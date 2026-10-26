#!/usr/bin/env python3
"""
Playwright + 百度学术 文献检索脚本 v2.0
用于 academic-paper-generator 技能的第1.5步

V2 新增：
  - 方案A：搜索结果页直接解析作者+期刊+年份+卷期+页码
  - 方案B：点击"引用"按钮获取GB/T 7714格式完整引用
  - 方案C：进入详情页兜底

依赖: pip install playwright (已安装)
Chrome: C:/Program Files/Google/Chrome/Application/chrome.exe
百度账号: 19302537562 / qwert12345

🔴 必须 headless=False —— 百度对headless有强反爬
🔴 搜索间隔 > 30秒 —— 同IP高频请求触发风控

用法:
    python playwright_baidu_scholar.py "员工激励 工作积极性"
    python playwright_baidu_scholar.py "消费结构升级" --max 15 --json
"""

import os
import sys
import time
import re
import json
import argparse
from urllib.parse import quote

os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = "C:/Program Files/Google/Chrome/Application/chrome.exe"
from playwright.sync_api import sync_playwright

CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
BAIDU_USERNAME = "19302537562"
BAIDU_PASSWORD = "qwert12345"


# ──────────────────────────────────────────────
# 方案A：从搜索结果页摘要行解析元数据
# ──────────────────────────────────────────────

def parse_source_line(text):
    """
    解析百度学术摘要行，格式示例：
      "张三, 李四, 王五 - 管理世界, 2022, 38(5): 112-125."
      "Zhang San, Li Si - Journal of Management, 2022, 38(5): 112-125."
    返回: {authors, journal, year, volume, issue, pages} 或 {}
    """
    result = {}
    
    # 模式1: "作者 - 期刊, 年份, 卷(期): 页码"
    m = re.match(
        r'(.+?)\s*[-–—]\s*'
        r'(.+?)[,，]\s*'
        r'(\d{4})'
        r'(?:[,，]\s*(\d+))?'            # 可选卷号
        r'(?:\((\d+)\))?'                 # 可选期号（括号内）
        r'(?:[,，:：]\s*(\d+[-–—]\d+|\d+))?'  # 可选页码
        r'[.。]?\s*$',
        text.strip()
    )
    
    if m:
        result['authors'] = m.group(1).strip()
        result['journal'] = m.group(2).strip()
        result['year'] = m.group(3)
        result['volume'] = m.group(4) or ''
        result['issue'] = m.group(5) or ''
        result['pages'] = m.group(6) or ''
        return result
    
    # 模式2: 只有"期刊, 年份, 卷(期): 页码"（无作者分隔符）
    m = re.match(
        r'(.+?)[,，]\s*'
        r'(\d{4})'
        r'(?:[,，]\s*(\d+))?'
        r'(?:\((\d+)\))?'
        r'(?:[,，:：]\s*(\d+[-–—]\d+|\d+))?',
        text.strip()
    )
    if m and any(kw in text for kw in ['学报','期刊','大学','学院','研究','科学','经济','管理']):
        result['journal'] = m.group(1).strip()
        result['year'] = m.group(2)
        result['volume'] = m.group(3) or ''
        result['issue'] = m.group(4) or ''
        result['pages'] = m.group(5) or ''
        return result
    
    return {}


# ──────────────────────────────────────────────
# 方案B：从GB/T 7714引用文本解析
# ──────────────────────────────────────────────

def parse_citation_text(text):
    """
    解析GB/T 7714格式引用:
      "[1] 张三, 李四. 论文标题[J]. 管理世界, 2022, 38(5): 112-125."
    返回: 6项元数据字典
    """
    result = {}
    
    # 去掉序号 [1] 等
    text = re.sub(r'^\[\d+\]\s*', '', text).strip()
    
    # 按 ". " 或 ".  " 分割
    # 格式: 作者. 标题[J]. 期刊, 年份, 卷(期): 页码.
    
    # 提取作者（第一个"."之前）
    m = re.match(r'(.+?)\.\s', text)
    if m:
        result['authors'] = m.group(1).strip()
    
    # 提取标题（在"[J]"或"[D]"等之前）
    m = re.search(r'\.\s+(.+?)\[(J|D|M|C|N|R|S|P|A|Z|EB|DB)\]\s*\.\s*', text)
    if m:
        result['title'] = m.group(1).strip()
    
    # 提取期刊+卷期页码（最后一个[J].之后）
    m = re.search(r'\[J\]\s*\.\s*(.+)$', text)
    if m:
        source = m.group(1).strip().rstrip('.')
        parsed = parse_source_line(source)
        result.update(parsed)
    
    return result


# ──────────────────────────────────────────────
# 核心：搜索 + 提取
# ──────────────────────────────────────────────

def handle_captcha(page, context_desc):
    """检测并处理验证码"""
    body = page.evaluate("() => document.body.innerText")
    if '验证' in body[:600]:
        print(f"[!] ⚠️ {context_desc}需要验证码，请在浏览器中手动完成...")
        print("[!] 完成后按回车继续（或按Ctrl+C取消）...")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print("[!] 无法交互，跳过")
            return False
        time.sleep(2)
        return True
    return False


def extract_papers_from_results(page, max_results):
    """
    方案A：从搜索结果页提取论文元数据。
    百度学术搜索结果典型DOM结构：
      <div> 标题 </div>
      <div> 作者1, 作者2 - 期刊名, 年份, 卷(期): 页码 </div>
      <div> 被引: X | 来源: 知网 </div>
    """
    papers = []
    
    # JS提取：找所有包含"作者-期刊-年份"模式的文本块
    raw_items = page.evaluate("""
        () => {
            const items = [];
            document.querySelectorAll('div, p, span').forEach(el => {
                const text = el.textContent.trim();
                // 匹配: "作者 - 期刊, 年份" 或 "期刊, 年份, 卷(期): 页码"
                if (text.length > 20 && text.length < 500 &&
                    /\\d{4}/.test(text) &&
                    /(学报|期刊|大学|学院|研究|科学|经济|管理|论坛|探索|理论|实践)/.test(text)) {
                    // 去重（同一文本块只保留一次）
                    if (!items.some(i => i.text === text)) {
                        items.push({
                            text: text,
                            html: el.outerHTML.substring(0, 300)
                        });
                    }
                }
            });
            return items.slice(0, 20);
        }
    """)
    
    # 解析每条
    for item in raw_items:
        text = item['text']
        parsed = parse_source_line(text)
        if parsed and ('journal' in parsed or 'authors' in parsed):
            paper = {
                'title': '',
                'authors': parsed.get('authors', ''),
                'journal': parsed.get('journal', ''),
                'year': parsed.get('year', ''),
                'volume': parsed.get('volume', ''),
                'issue': parsed.get('issue', ''),
                'pages': parsed.get('pages', ''),
                'source': '百度学术-搜索结果页',
                'verified': False
            }
            papers.append(paper)
    
    return papers[:max_results]


def extract_via_cite_button(page, paper_index):
    """
    方案B：点击第 paper_index 个结果的"引用"按钮，获取GB/T 7714引用。
    返回解析后的元数据，或 {}。
    """
    try:
        # 找引用按钮——百度学术通常是文字"引用"或图标
        cite_btns = page.locator('text=引用').all()
        if not cite_btns:
            cite_btns = page.locator('[class*="cite"], [class*="quote"], [class*="ref"]').all()
        
        if paper_index < len(cite_btns):
            cite_btns[paper_index].click()
            time.sleep(1.5)
            
            # 获取弹出的引用文本
            cite_popup = page.locator('[class*="cite"], [class*="quotation"], [class*="popup"], .dialog').first
            if cite_popup.is_visible(timeout=3000):
                cite_text = cite_popup.inner_text()
                parsed = parse_citation_text(cite_text)
                if parsed:
                    parsed['verified'] = True
                    parsed['source'] = '百度学术-GB/T7714引用'
                    return parsed
            
            # 关闭弹窗
            page.keyboard.press('Escape')
            time.sleep(0.5)
    except Exception as e:
        pass
    
    return {}


def search_baidu_scholar(keyword, max_results=10, use_cite_fallback=True):
    """主函数：搜索百度学术，提取完整文献元数据"""
    papers = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 🔴 必须非headless
            executable_path=CHROME_PATH,
            args=['--no-sandbox', '--disable-gpu', '--disable-blink-features=AutomationControlled']
        )
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # 阶段0：搜索
        search_url = f"https://xueshu.baidu.com/s?wd={quote(keyword)}"
        print(f"[*] 搜索: {keyword}")
        page.goto(search_url, timeout=25000)
        time.sleep(5)
        
        if handle_captcha(page, "百度学术"):
            pass
        
        # 阶段1：方案A——从搜索结果页直接提取
        print("[*] 方案A：搜索结果页直接解析...")
        papers = extract_papers_from_results(page, max_results)
        
        # 也提取标题（独立搜索）
        titles = page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('h3 a, a.title, .sc_content a.title').forEach(el => {
                    const text = el.textContent.trim();
                    if (text.length > 10 && text.length < 200) results.push(text);
                });
                return results;
            }
        """)
        
        # 将标题匹配到papers
        for i, paper in enumerate(papers):
            if i < len(titles):
                paper['title'] = titles[i].strip()
        
        # 阶段2：方案B——元数据不完整的，点击"引用"按钮
        incomplete = [i for i, p in enumerate(papers) if not p['journal'] or not p['year']]
        if incomplete and use_cite_fallback:
            print(f"[*] 方案B：{len(incomplete)}篇元数据不完整，尝试点击引用按钮...")
            for idx in incomplete:
                cited = extract_via_cite_button(page, idx)
                if cited:
                    papers[idx].update(cited)
                    print(f"  [✓] 第{idx+1}篇：引用提取成功")
                else:
                    print(f"  [✗] 第{idx+1}篇：引用提取失败")
        
        browser.close()
    
    return papers


def main():
    parser = argparse.ArgumentParser(description='百度学术文献检索 v2.0')
    parser.add_argument('keyword', help='搜索关键词')
    parser.add_argument('--max', type=int, default=10, help='最大结果数 (默认10)')
    parser.add_argument('--json', action='store_true', help='输出JSON')
    parser.add_argument('--no-cite', action='store_true', help='跳过引用按钮fallback')
    args = parser.parse_args()
    
    papers = search_baidu_scholar(
        args.keyword,
        max_results=args.max,
        use_cite_fallback=not args.no_cite
    )
    
    if args.json:
        print(json.dumps(papers, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"检索结果：{len(papers)} 篇 | 关键词：{args.keyword}")
        print(f"{'='*60}")
        for i, p in enumerate(papers):
            complete = all([p.get('authors'), p.get('journal'), p.get('year')])
            status = "✅完整" if complete else "⚠️缺元数据"
            print(f"\n[{i+1}] {status}")
            print(f"    标题: {p.get('title', '(未提取)')[:100]}")
            print(f"    作者: {p.get('authors', '?')}")
            print(f"    期刊: {p.get('journal', '?')} | {p.get('year', '?')}年 "
                  f"卷{p.get('volume','?')}({p.get('issue','?')}): {p.get('pages','?')}")
            print(f"    来源: {p.get('source', '?')}")


if __name__ == '__main__':
    main()
