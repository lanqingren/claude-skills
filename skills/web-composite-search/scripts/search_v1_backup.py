#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web复合搜索 - 智能多引擎聚合搜索工具 (修复版 v1.2.0)
专为国内网络优化，零Google依赖
修复内容: 反爬策略、引擎更新、解析器增强
"""

import re
import json
import time
import hashlib
import urllib.parse
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
import math

import requests
from bs4 import BeautifulSoup

# ============ User-Agent 轮换池 ============
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

def get_random_ua():
    """获取随机User-Agent"""
    return random.choice(USER_AGENTS)


# ============ 搜索引擎配置 ============
ENGINES = {
    # 国内通用
    "baidu": {
        "name": "百度",
        "type": "general",
        "base_url": "https://www.baidu.com/s",
        "params": {"wd": "{query}", "tn": "baidu", "ie": "utf-8", "rn": "20"},
        "advanced_syntax": True,
        "weight": 0.85,
        "timeout": 5,
        "request_interval": 1.5,  # 请求间隔1.5秒
        "retry_count": 2,
        "headers": {
            "Referer": "https://www.baidu.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    },
    "sogou": {
        "name": "搜狗",
        "type": "general",
        "base_url": "https://www.sogou.com/web",
        "params": {"query": "{query}", "page": "1", "ie": "utf8"},
        "advanced_syntax": True,
        "weight": 0.8,
        "timeout": 5,
        "request_interval": 1.0,
    },
    "sogou_wechat": {
        "name": "搜狗微信",
        "type": "social",
        "base_url": "https://weixin.sogou.com/weixin",
        "params": {"type": "2", "query": "{query}", "page": "1"},
        "advanced_syntax": False,
        "weight": 0.9,
        "timeout": 5,
        "request_interval": 1.0,
    },
    "bing_cn": {
        "name": "必应中文",
        "type": "general",
        "base_url": "https://cn.bing.com/search",
        "params": {"q": "{query}", "setmkt": "zh-cn", "count": "20"},
        "advanced_syntax": True,
        "weight": 0.8,
        "timeout": 5,
    },
    # 学术搜索 (修复版)
    "bing_academic": {
        "name": "必应学术",
        "type": "academic",
        "base_url": "https://cn.bing.com/academic/search",
        "params": {"q": "{query}"},
        "advanced_syntax": True,
        "weight": 0.9,
        "timeout": 8,
    },
    "arxiv": {
        "name": "ArXiv",
        "type": "academic",
        "base_url": "https://arxiv.org/search",
        "params": {"query": "{query}", "searchtype": "all", "size": "20"},
        "advanced_syntax": False,
        "weight": 0.95,
        "timeout": 15,  # 增加超时到15秒
        "retry_count": 3,
    },
    "pubmed": {
        "name": "PubMed",
        "type": "academic",
        "base_url": "https://pubmed.ncbi.nlm.nih.gov/",
        "params": {"term": "{query}"},
        "advanced_syntax": True,
        "weight": 0.9,
        "timeout": 8,
        "note": "生物医学文献，国内直连",
    },
    # 财经投资 (添加备用)
    "eastmoney": {
        "name": "东方财富",
        "type": "finance",
        "base_url": "https://search.eastmoney.com/search/web",
        "params": {"q": "{query}", "page": "1"},
        "advanced_syntax": False,
        "weight": 0.9,
        "timeout": 5,
        "selectors": {
            "container": [".search-result-item", ".news-item", ".article-box", ".result"],
            "title": ["h3 a", ".title a", "h2 a", "a"],
            "snippet": ["p.description", ".summary", ".content", "p"],
        }
    },
    "xueqiu": {
        "name": "雪球",
        "type": "finance",
        "base_url": "https://xueqiu.com/k",
        "params": {"q": "{query}"},
        "advanced_syntax": False,
        "weight": 0.85,
        "timeout": 5,
        "note": "投资社区，国内可用",
    },
    # 技术社区 (移除Stack Overflow和掘金，保留GitHub)
    "github": {
        "name": "GitHub",
        "type": "tech",
        "base_url": "https://github.com/search",
        "params": {"q": "{query}", "type": "repositories"},
        "advanced_syntax": True,
        "weight": 0.85,
        "timeout": 8,
    },
    "csdn": {
        "name": "CSDN",
        "type": "tech",
        "base_url": "https://so.csdn.net/so/search",
        "params": {"q": "{query}", "t": "article"},
        "advanced_syntax": False,
        "weight": 0.7,
        "timeout": 5,
        "note": "代码资源，国内稳定",
    },
    # 国际引擎 (移除Yandex)
    "bing_intl": {
        "name": "必应国际",
        "type": "general_intl",
        "base_url": "https://www.bing.com/search",
        "params": {"q": "{query}", "setmkt": "en-us", "count": "20", "setlang": "en"},
        "advanced_syntax": True,
        "weight": 1.0,
        "timeout": 8,
    },
    "ddg": {
        "name": "DuckDuckGo",
        "type": "privacy",
        "base_url": "https://lite.duckduckgo.com/lite/",
        "params": {"q": "{query}", "kl": "cn-zh"},
        "advanced_syntax": True,
        "weight": 0.8,
        "timeout": 8,
    },
    "brave": {
        "name": "Brave Search",
        "type": "privacy",
        "base_url": "https://search.brave.com/search",
        "params": {"q": "{query}", "source": "web"},
        "advanced_syntax": True,
        "weight": 0.85,
        "timeout": 6,
    },
    "qwant": {
        "name": "Qwant",
        "type": "privacy",
        "base_url": "https://www.qwant.com/",
        "params": {"q": "{query}", "t": "web"},
        "advanced_syntax": True,
        "weight": 0.8,
        "timeout": 6,
    },
}

# ============ 意图路由规则 (移除失效引擎) ============
ROUTING_RULES = [
    {
        "id": "advanced_syntax",
        "condition": r"(site:\S+|filetype:\S+|\"[^\"]+\"|\-\S+|intitle:\S+|inurl:\S+)",
        "priority": 100,
        "engines": ["bing_intl", "baidu", "sogou"],  # 移除yandex, 360
        "intent": "advanced",
    },
    {
        "id": "academic",
        "keywords": ["论文", "文献", "doi", "被引", "期刊", "conference", "arxiv", "pubmed", "博士", "硕士", "学位论文"],
        "priority": 90,
        "engines": ["bing_academic", "arxiv", "pubmed"],  # 替换为可用学术引擎
        "intent": "academic",
    },
    {
        "id": "tech",
        "keywords": ["github", "code", "programming", "error", "bug", "debug", "python", "java", "javascript", "报错", "代码", "编程"],
        "priority": 85,
        "engines": ["github", "csdn", "bing_intl"],  # 移除stackoverflow, juejin
        "intent": "tech",
    },
    {
        "id": "finance",
        "keywords": ["股票", "基金", "财报", "市值", "行情", "ticker", "earning", "nasdaq", "沪深", "港股", "美股", "a股", "可转债"],
        "priority": 80,
        "engines": ["eastmoney", "xueqiu", "bing_intl"],
        "intent": "finance",
    },
    {
        "id": "social",
        "keywords": ["微信公众号", "公众号", "推文"],
        "priority": 75,
        "engines": ["sogou_wechat", "sogou"],  # 移除zhihu
        "intent": "social",
    },
    {
        "id": "default",
        "priority": 0,
        "engines": ["baidu", "sogou", "bing_cn", "bing_intl"],  # 移除360
        "intent": "general",
    },
]


@dataclass
class SearchResult:
    """搜索结果数据类"""
    title: str
    url: str
    snippet: str
    source_engine: str
    source_type: str
    rank: int = 0
    confidence_score: float = 0.0
    duplicate_of: Optional[str] = None
    is_verified_source: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "rank": self.rank,
            "title": self.title,
            "url": self.url,
            "display_url": self._get_display_url(),
            "source_engine": self.source_engine,
            "source_type": self.source_type,
            "snippet": self.snippet,
            "confidence_score": round(self.confidence_score, 3),
            "duplicate_of": self.duplicate_of,
            "is_verified_source": self.is_verified_source,
        }
    
    def _get_display_url(self) -> str:
        """获取显示URL"""
        try:
            parsed = urlparse(self.url)
            return f"{parsed.netloc}{parsed.path[:30]}..." if len(parsed.path) > 30 else parsed.netloc + parsed.path
        except:
            return self.url[:50]


class CompositeSearch:
    """复合搜索引擎主类 (修复版)"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.session = requests.Session()
        self.results_per_engine = self.config.get("results_per_engine", 20)
        self.max_concurrent = self.config.get("max_concurrent_engines", 5)
        self.default_max_results = self.config.get("default_max_results", 10)
        self.last_request_time = {}  # 记录上次请求时间
        
    def _get_headers(self, engine_id: str) -> Dict:
        """获取引擎特定的请求头"""
        engine = ENGINES.get(engine_id, {})
        headers = {
            "User-Agent": get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Cache-Control": "max-age=0",
        }
        
        # 合并引擎特定headers
        if "headers" in engine:
            headers.update(engine["headers"])
        
        return headers
    
    def _apply_rate_limit(self, engine_id: str):
        """应用请求速率限制"""
        engine = ENGINES.get(engine_id, {})
        interval = engine.get("request_interval", 0.5)
        
        last_time = self.last_request_time.get(engine_id, 0)
        elapsed = time.time() - last_time
        
        if elapsed < interval:
            sleep_time = interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time[engine_id] = time.time()
    
    def detect_intent(self, query: str, intent_hint: Optional[str] = None) -> Tuple[str, List[str]]:
        """检测查询意图并返回推荐引擎"""
        if intent_hint:
            for rule in ROUTING_RULES:
                if rule.get("intent") == intent_hint:
                    return intent_hint, rule["engines"]
        
        # 检查高级语法
        advanced_pattern = r"(site:\S+|filetype:\S+|\"[^\"]+\"|\-\S+|intitle:\S+|inurl:\S+)"
        if re.search(advanced_pattern, query, re.IGNORECASE):
            return "advanced", ["bing_intl", "baidu", "sogou"]
        
        # 按优先级检查关键词
        sorted_rules = sorted(ROUTING_RULES, key=lambda x: x.get("priority", 0), reverse=True)
        for rule in sorted_rules:
            if rule["id"] == "default":
                continue
            if "keywords" in rule:
                if any(kw in query.lower() for kw in rule["keywords"]):
                    return rule["intent"], rule["engines"]
        
        # 默认
        return "general", ROUTING_RULES[-1]["engines"]
    
    def _search_engine(self, engine_id: str, query: str) -> List[SearchResult]:
        """执行单个搜索引擎查询 (带重试)"""
        engine = ENGINES.get(engine_id)
        if not engine:
            return []
        
        retry_count = engine.get("retry_count", 1)
        
        for attempt in range(retry_count):
            try:
                # 应用速率限制
                self._apply_rate_limit(engine_id)
                
                # 构建请求URL
                params = {k: v.format(query=query) if "{query}" in v else v 
                         for k, v in engine["params"].items()}
                
                # 获取请求头
                headers = self._get_headers(engine_id)
                
                timeout = engine.get("timeout", 5)
                response = self.session.get(
                    engine["base_url"],
                    params=params,
                    headers=headers,
                    timeout=(3, timeout),  # (连接超时, 读取超时)
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # 解析结果
                results = self._parse_results(engine_id, response.text, engine)
                return results[:self.results_per_engine]
                
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    time.sleep(wait_time)
                    continue
                print(f"[{engine_id}] 搜索失败 (重试{retry_count}次): {e}")
                return []
        
        return []
    
    def _parse_results(self, engine_id: str, html: str, engine: Dict) -> List[SearchResult]:
        """解析搜索结果HTML"""
        results = []
        soup = BeautifulSoup(html, 'lxml')
        
        if engine_id == "baidu":
            results = self._parse_baidu(soup, engine)
        elif engine_id == "sogou":
            results = self._parse_sogou(soup, engine)
        elif engine_id == "sogou_wechat":
            results = self._parse_sogou_wechat(soup, engine)
        elif engine_id.startswith("bing"):
            results = self._parse_bing(soup, engine)
        elif engine_id == "ddg":
            results = self._parse_ddg(soup, engine)
        elif engine_id == "github":
            results = self._parse_github(soup, engine)
        elif engine_id == "arxiv":
            results = self._parse_arxiv(soup, engine)
        elif engine_id == "pubmed":
            results = self._parse_pubmed(soup, engine)
        elif engine_id == "eastmoney":
            results = self._parse_eastmoney(soup, engine)
        elif engine_id == "csdn":
            results = self._parse_csdn(soup, engine)
        elif engine_id == "brave":
            results = self._parse_brave(soup, engine)
        elif engine_id == "qwant":
            results = self._parse_qwant(soup, engine)
        
        return results
    
    def _safe_select(self, soup, selectors: List[str]) -> Optional:
        """多选择器备选安全选择"""
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem
        return None
    
    def _safe_select_all(self, soup, selectors: List[str]) -> List:
        """多选择器备选安全选择所有"""
        for selector in selectors:
            elems = soup.select(selector)
            if elems:
                return elems
        return []
    
    def _parse_baidu(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析百度搜索结果 (增强版)"""
        results = []
        # 多选择器备选
        containers = self._safe_select_all(soup, [
            '.result',
            '.c-container',
            '.content-left_8ZsG .result',
            '[tpl]'
        ])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['h3 a', '.t a', '.title_3T-31', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                # 获取摘要
                snippet_elem = self._safe_select(container, [
                    '.content-right_8Zs40',
                    '.c-abstract',
                    '.content-right',
                    '.abstract',
                    'span[class*="content"]'
                ])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_sogou(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析搜狗搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['.vrwrap', '.result', '.search-result'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['h3 a', '.vr-title a', 'h2 a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_elem = self._safe_select(container, ['.str-text', '.vr-content', '.abstract', 'p'])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_sogou_wechat(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析搜狗微信搜索结果"""
        results = []
        containers = self._safe_select_all(soup, [
            '.wx-news-list li',
            '.news-list li',
            '.weui_media_box',
            '.txt-box'
        ])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, [
                    'h3 a', '.weui_media_title', 'a[class*="title"]', 'h4 a'
                ])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                if url.startswith('/'):
                    url = 'https://weixin.sogou.com' + url
                
                snippet_elem = self._safe_select(container, [
                    'p', '.weui_media_desc', '[class*="summary"]', '.txt-info'
                ])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_bing(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析必应搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['.b_algo', 'li.b_algo', '.result'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['h2 a', 'h3 a', 'h1 a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_elem = self._safe_select(container, [
                    '.b_caption p',
                    'p[class*="snippet"]',
                    '.b_snippet',
                    'p'
                ])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_ddg(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析DuckDuckGo搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['.result', '.web-result', '.links_main'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['.result__title a', 'h2 a', 'h3 a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_elem = self._safe_select(container, [
                    '.result__snippet',
                    '.result__body',
                    '.links_main .result__snippet'
                ])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_github(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析GitHub搜索结果"""
        results = []
        containers = self._safe_select_all(soup, [
            '.repo-list-item',
            '[data-testid="results-list"] > div',
            '.Box-sc-g0xbh4-0'
        ])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['h3 a', '.search-title a', 'a[href*="/"]'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                href = title_elem.get('href', '')
                url = urljoin("https://github.com", href) if not href.startswith('http') else href
                
                snippet_elem = self._safe_select(container, ['.mb-1', '.search-match', 'p', '[class*="description"]'])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_arxiv(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析ArXiv搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['li.arxiv-result', '.result', '.search-result'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['p.title a', 'h3 a', '.title a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                if url.startswith('/'):
                    url = 'https://arxiv.org' + url
                
                snippet_elem = self._safe_select(container, ['p.abstract', '.abstract', '.snippet'])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_pubmed(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析PubMed搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['.docsum-content', '.result', 'article'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['a.docsum-title', 'h3 a', '.title a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                if url.startswith('/'):
                    url = 'https://pubmed.ncbi.nlm.nih.gov' + url
                
                snippet_elem = self._safe_select(container, ['.full-authors', '.abstract', '.summary'])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_eastmoney(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析东方财富搜索结果 (多选择器备选)"""
        results = []
        # 使用引擎配置中的选择器
        selectors = engine.get("selectors", {})
        container_selectors = selectors.get("container", [".search-result-item", ".news-item", ".result"])
        containers = self._safe_select_all(soup, container_selectors)
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_selectors = selectors.get("title", ["h3 a", ".title a", "h2 a", "a"])
                title_elem = self._safe_select(container, title_selectors)
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_selectors = selectors.get("snippet", ["p.description", ".summary", ".content", "p"])
                snippet_elem = self._safe_select(container, snippet_selectors)
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_csdn(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析CSDN搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['.search-list-item', '.result', 'article'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['h3 a', '.title a', 'h2 a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_elem = self._safe_select(container, ['.content', '.abstract', '.summary', 'p'])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_brave(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析Brave搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['.snippet', '.result', 'article'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['h2 a', 'h3 a', '.title a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_elem = self._safe_select(container, ['.snippet-description', '.description', 'p'])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _parse_qwant(self, soup: BeautifulSoup, engine: Dict) -> List[SearchResult]:
        """解析Qwant搜索结果"""
        results = []
        containers = self._safe_select_all(soup, ['.result', '.web-result', 'article'])
        
        for idx, container in enumerate(containers[:self.results_per_engine], 1):
            try:
                title_elem = self._safe_select(container, ['h3 a', 'h2 a', '.title a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                snippet_elem = self._safe_select(container, ['.result__snippet', '.description', 'p'])
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source_engine=engine["name"],
                    source_type=engine["type"],
                    rank=idx,
                    confidence_score=engine["weight"] * (1 / math.log2(idx + 2))
                ))
            except Exception:
                continue
        
        return results
    
    def _deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """去重算法"""
        seen_urls = set()
        seen_titles = {}
        unique_results = []
        
        for result in results:
            # URL规范化去重
            canonical_url = self._canonicalize_url(result.url)
            if canonical_url in seen_urls:
                continue
            
            # 标题相似度去重
            title_normalized = result.title.lower().strip()
            is_duplicate = False
            for existing_title, existing_url in seen_titles.items():
                if self._title_similarity(title_normalized, existing_title) > 0.85:
                    result.duplicate_of = existing_url
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_urls.add(canonical_url)
                seen_titles[title_normalized] = result.url
                unique_results.append(result)
        
        return unique_results
    
    def _canonicalize_url(self, url: str) -> str:
        """URL规范化"""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower().replace('www.', '')
            path = parsed.path.rstrip('/')
            return f"{netloc}{path}"
        except:
            return url
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """计算标题相似度"""
        set1 = set(title1.split())
        set2 = set(title2.split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def search(self, query: str, intent_hint: Optional[str] = None, 
               max_results: Optional[int] = None) -> Dict:
        """执行复合搜索"""
        start_time = time.time()
        max_results = max_results or self.default_max_results
        
        # 检测意图和选择引擎
        detected_intent, engines = self.detect_intent(query, intent_hint)
        
        print(f"[分析] 查询意图: {detected_intent}")
        print(f"[分析] 选用引擎: {', '.join(engines)}")
        
        # 并发执行搜索
        all_results = []
        failed_engines = []
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            future_to_engine = {
                executor.submit(self._search_engine, engine_id, query): engine_id 
                for engine_id in engines if engine_id in ENGINES
            }
            
            for future in as_completed(future_to_engine):
                engine_id = future_to_engine[future]
                try:
                    results = future.result(timeout=20)  # 增加超时到20秒
                    if results:
                        all_results.extend(results)
                        print(f"[成功] {engine_id}: 获取 {len(results)} 条结果")
                    else:
                        failed_engines.append(engine_id)
                        print(f"[警告] {engine_id}: 无结果")
                except Exception as e:
                    failed_engines.append(engine_id)
                    print(f"[失败] {engine_id}: {e}")
        
        # 去重
        unique_results = self._deduplicate(all_results)
        
        # 按置信度排序
        unique_results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # 重新排名
        for idx, result in enumerate(unique_results, 1):
            result.rank = idx
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return {
            "query_analysis": {
                "original_query": query,
                "detected_intent": detected_intent,
                "engines_selected": engines,
                "engines_failed": failed_engines,
                "execution_time_ms": execution_time,
                "is_advanced_syntax": detected_intent == "advanced",
            },
            "aggregated_results": [r.to_dict() for r in unique_results[:max_results]],
            "metadata": {
                "total_fetched": len(all_results),
                "after_deduplication": len(unique_results),
                "fallback_used": len(failed_engines) > 0,
                "china_optimized": True,
            }
        }


def main():
    """命令行入口"""
    import argparse
    import sys
    import io
    
    # 设置Windows控制台UTF-8编码
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(description="web复合搜索 - 智能多引擎聚合搜索工具 (修复版)")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--intent", "-i", choices=["academic", "tech", "finance", "social", "privacy", "advanced", "general"],
                       help="搜索意图提示")
    parser.add_argument("--max-results", "-n", type=int, default=10, help="最大返回结果数")
    parser.add_argument("--json", "-j", action="store_true", help="输出JSON格式")
    parser.add_argument("--output", "-o", help="输出结果到文件")
    
    args = parser.parse_args()
    
    searcher = CompositeSearch()
    results = searcher.search(args.query, args.intent, args.max_results)
    
    # 构建输出内容
    if args.json:
        output = json.dumps(results, ensure_ascii=False, indent=2)
    else:
        lines = []
        lines.append("\n" + "="*60)
        lines.append(f"搜索: {results['query_analysis']['original_query']}")
        lines.append(f"意图: {results['query_analysis']['detected_intent']}")
        lines.append(f"用时: {results['query_analysis']['execution_time_ms']}ms")
        lines.append(f"去重前/后: {results['metadata']['total_fetched']}/{results['metadata']['after_deduplication']}")
        lines.append("="*60 + "\n")
        
        for r in results["aggregated_results"]:
            lines.append(f"{r['rank']}. {r['title']}")
            lines.append(f"   来源: {r['source_engine']} | 置信度: {r['confidence_score']}")
            lines.append(f"   {r['url']}")
            snippet = r['snippet'][:150] if r['snippet'] else ""
            lines.append(f"   {snippet}...")
            lines.append("")
        output = "\n".join(lines)
    
    # 输出到文件或控制台
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"结果已保存到: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
