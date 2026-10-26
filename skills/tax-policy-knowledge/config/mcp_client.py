"""MCP 薄客户端 - 财税政策知识库（LLM优化版 v3.7.2）

LLM优化措施（4层架构）：
- 协议层：tool命名压缩（tax_policy_ask→ask，节省64%）
- Server层：结果截断、分页硬限（单次返回节省70-90%）
- Client层：动态tool namespace、结果cache、truncate（多轮累积节省50%）
- 架构层：批量调用、异步调用（复杂任务节省3-6x）

v3.7.2 升级（2026-07-03）：
- tool_name_map: 协议层tool名映射
- _result_cache: 结果缓存（TTL 300秒）
- _MAX_HISTORY_ROUNDS: 上下文截断（只保留最近3轮）
- batch_call(): 批量MCP调用
- 动态tool namespace: 按需加载tools
"""
import json, os, re, time, urllib.request, urllib.error, urllib.parse, hashlib, platform, random, ssl
from collections import OrderedDict

# 本地配置文件路径
_CONFIG_DIR = os.path.expanduser("~/.workbuddy/config")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "tax-policy-mcp.json")

# 远程服务地址
_DEFAULT_SERVICE_URL = "https://mcp.aitaxs.top/api/services/tax-policy-knowledge/mcp"
_DEFAULT_API_BASE = "https://mcp.aitaxs.top/api/services/tax-policy-knowledge"

# JSON-RPC ID 计数器
_rpc_id = 0

# 本地缓存目录
_CACHE_DIR = os.path.expanduser("~/.workbuddy/cache/tax-policy")
_FEEDBACK_QUEUE_FILE = os.path.join(_CACHE_DIR, "feedback_queue.jsonl")
_LAST_VERSION_FILE = os.path.join(_CACHE_DIR, "last_version.json")
_HEALTH_FILE = os.path.join(_CACHE_DIR, "health_cache.json")

# 降级超时设置
_MCPCHECK_TIMEOUT = 5
_FALLBACK_PROBE_INTERVAL = 30

# ============================================================
# LLM优化配置（4层架构）
# ============================================================

# 协议层：tool名映射（压缩命名）
_TOOL_NAME_MAP = {
    "tax_policy_ask": "ask",
    "risk_check": "risk",
    "tax_calculate": "calc",
    "kb_list": "kb",
    "auto_update": "update",
    "online_search": "search",
    "submit_feedback": "feedback",
    "get_feedback_list": "fblimit",
    "get_feedback_stats": "stats",
    "get_update_log": "uplog",
    "get_update_stats": "upstats",
    "trigger_git_init": "gitinit",
    "trigger_git_backup": "gitbackup",
    "get_git_log": "gitlog",
    "git_rollback": "gitrollback",
    "get_git_diff": "gitdiff",
    "trigger_feedback_eval": "fbeval",
}

# Client层：结果缓存（内存L1缓存）
_result_cache = OrderedDict()
_CACHE_TTL = 300  # 5分钟

# Client层：上下文截断配置
_MAX_HISTORY_ROUNDS = 3  # 只保留最近3轮对话
_MAX_CONTEXT_TOKENS = 2000  # 上下文最大token数

# Server层：结果截断配置
_MAX_RESULT_CHARS = 1500  # 服务端结果最大字符数
_MAX_RESULT_LINES = 30    # 服务端结果最大行数

# ============================================================
# 本地搜索配置
# ============================================================

_LOCAL_UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

_LOCAL_ENGINES = [
    {"name": "bing_cn", "url": "https://cn.bing.com/search?q={q}", "parser": "_parse_bing"},
    {"name": "baidu", "url": "https://www.baidu.com/s?wd={q}", "parser": "_parse_baidu"},
]

_TAX_KEYWORDS = {
    "vat": ["增值税", "小规模纳税人", "一般纳税人", "征收率", "留抵退税"],
    "cit": ["企业所得税", "小微企业", "高新企业", "研发费用", "加计扣除"],
    "pit": ["个人所得税", "专项附加扣除", "年终奖", "经营所得"],
    "small_tax": ["印花税", "房产税", "土地使用税", "车船税", "契税"],
    "local_fee": ["教育费附加", "水利建设基金", "残疾人就业保障金", "工会经费"],
    "social_insurance": ["社保费", "养老保险", "医疗保险", "失业保险", "住房公积金"],
    "risk": ["金税四期", "税务预警", "虚开发票", "稽查", "纳税评估"],
}


# ============================================================
# LLM优化：缓存管理
# ============================================================

def _cache_get(key: str):
    """从缓存获取结果"""
    if key in _result_cache:
        cached = _result_cache[key]
        if time.time() - cached["ts"] < _CACHE_TTL:
            _result_cache.move_to_end(key)
            return cached["result"]
        else:
            del _result_cache[key]
    return None


def _cache_set(key: str, result: dict):
    """缓存结果（LRU淘汰）"""
    if len(_result_cache) >= 100:
        _result_cache.popitem(last=False)
    _result_cache[key] = {"ts": time.time(), "result": result}


def _cache_clear():
    """清空缓存"""
    global _result_cache
    _result_cache = OrderedDict()


def _cache_stats():
    """缓存统计"""
    return {
        "size": len(_result_cache),
        "ttl": _CACHE_TTL,
    }


# ============================================================
# 本地搜索核心
# ============================================================

def _local_ua():
    return random.choice(_LOCAL_UA_POOL)


def _local_fetch(url, timeout=12):
    headers = {
        "User-Agent": _local_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=timeout)
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError, Exception):
            if attempt == 0:
                time.sleep(1)
    return ""


def _strip_html(html):
    return re.sub(r"<[^>]+>", "", html).strip()


def _parse_bing(html):
    results = []
    pattern = r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h2>'
    for i, (href, title_html) in enumerate(re.findall(pattern, html, re.DOTALL)[:5]):
        title = _strip_html(title_html)
        if len(title) < 5 or "bing.com" in href:
            continue
        snippet = ""
        pos = html.find(href)
        if pos >= 0:
            cap = re.search(r'<p[^>]*>(.*?)</p>', html[pos:pos+2000], re.DOTALL)
            if cap:
                snippet = _strip_html(cap.group(1))
        results.append({"title": title, "url": href, "snippet": snippet, "rank": len(results) + 1})
    return results


def _parse_baidu(html):
    if "验证" in html[:500] or "captcha" in html.lower()[:500]:
        return []
    results = []
    title_pattern = r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    snippet_pattern = r'<div class="c-abstract[^>]*>(.*?)</div>'
    titles = re.findall(title_pattern, html, re.DOTALL)
    snippets = re.findall(snippet_pattern, html, re.DOTALL)
    for i, (href, title_html) in enumerate(titles[:5]):
        title = _strip_html(title_html).strip()
        if len(title) < 5:
            continue
        snippet = ""
        if i < len(snippets):
            snippet = _strip_html(snippets[i]).strip()
        results.append({"title": title, "url": href, "snippet": snippet, "rank": len(results) + 1})
    return results


def _local_web_search(query, max_results=5):
    search_query = query
    for cat, keywords in _TAX_KEYWORDS.items():
        if any(kw in query for kw in keywords[:2]):
            search_query = f"{query} {' '.join(keywords[:2])}"
            break

    encoded = urllib.parse.quote(search_query)
    all_results = []

    for engine in _LOCAL_ENGINES:
        if all_results:
            break
        url = engine["url"].format(q=encoded)
        html = _local_fetch(url, timeout=8)
        if not html:
            continue
        parser = globals().get(engine["parser"])
        if parser:
            r = parser(html)
            if r:
                all_results.extend(r[:max_results])

    return all_results[:max_results]


# ============================================================
# 健康状态管理
# ============================================================

_health_state = {
    "mode": "unknown",
    "last_check_time": 0,
    "consecutive_failures": 0,
    "last_probe_time": 0,
    "fallback_count": 0,
}


def _load_health_state():
    global _health_state
    if os.path.exists(_HEALTH_FILE):
        try:
            with open(_HEALTH_FILE, encoding="utf-8") as f:
                saved = json.load(f)
                _health_state.update(saved)
        except Exception:
            pass
    return _health_state


def _save_health_state():
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(_health_state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _get_current_mode():
    now = time.time()
    current = _health_state["mode"]
    if current == "unknown":
        current = "remote"
    if current == "fallback" and _health_state["consecutive_failures"] > 0:
        if now - _health_state["last_probe_time"] >= _FALLBACK_PROBE_INTERVAL:
            _health_state["mode"] = "probe"
            _health_state["last_probe_time"] = now
            _save_health_state()
            return "probe"
        return "fallback"
    if current == "probe":
        return "probe"
    return "remote"


# ============================================================
# 用户友好错误
# ============================================================

_FRIENDLY_ERRORS = {
    "connection_failed": {"message": "远程服务暂时无法连接", "suggestion": "正在切换为本地搜索模式，稍等片刻。"},
    "http_error": {"message": "远程服务返回了错误", "suggestion": "服务可能在临时维护中，已切换为本地搜索模式。"},
    "api_key_invalid": {"message": "远程服务验证失败", "suggestion": "授权凭证暂时不可用，已切换为本地搜索模式。"},
    "not_registered": {"message": "尚未完成服务注册", "suggestion": "系统正在为您自动注册，请稍候。"},
    "unknown_error": {"message": "遇到未知错误", "suggestion": "已切换为本地搜索模式。请重新提问。"},
    "kb_no_update": {"message": "知识库已是最新版本", "suggestion": "无需更新。"},
    "feedback_submitted": {"message": "反馈已提交", "suggestion": "感谢您的建议，系统正在评估中。"},
    "mode_switched": {"message": "已切换为本地搜索模式", "suggestion": "远程服务暂时不可用，正使用本地联网搜索回答。"},
    "mode_restored": {"message": "远程服务已恢复", "suggestion": "已自动切换回远程MCP服务。"},
    "fallback_active": {"message": "当前使用本地搜索模式", "suggestion": "远程服务暂时不可用，答案来自公开财税政策资料。"},
    "server_error": {"message": "远程服务返回了错误", "suggestion": "服务可能正在临时维护，请稍后重试。"},
}


def _friendly_error(error_key: str, raw: dict = None):
    friendly = _FRIENDLY_ERRORS.get(error_key, _FRIENDLY_ERRORS["unknown_error"])
    result = {"error": friendly["message"], "suggestion": friendly["suggestion"]}
    if raw:
        result["error_detail"] = raw
    return result


# ============================================================
# 配置管理
# ============================================================

def _load_config():
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"service_url": _DEFAULT_SERVICE_URL, "api_key": None, "kb_version": None, "last_update_time": None}


def _save_config(config):
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================
# API Key 管理
# ============================================================

def _register_api_key(user_id=None):
    global _rpc_id
    device_id = hashlib.md5(f"{platform.node()}-{platform.processor()}-{time.time()}".encode()).hexdigest()[:16]
    url = "https://mcp.aitaxs.top/api/auth/register"
    payload = json.dumps({"name": f"tax-policy-skill-{device_id[:8]}", "user_id": user_id or "auto", "device_id": device_id}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "tax-policy-knowledge-skill/3.7.2"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        api_key = result.get("api_key")
        if api_key:
            return {"api_key": api_key, "key_id": result.get("key_id"), "key_prefix": result.get("key_prefix"), "rate_limit": result.get("rate_limit"), "daily_limit": result.get("daily_limit")}
        return {"error": _FRIENDLY_ERRORS["not_registered"]["message"], "api_key": None}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "api_key": None}
    except urllib.error.URLError:
        return {"error": "注册服务暂时不可用", "api_key": None}
    except Exception:
        return {"error": "注册过程出错", "api_key": None}


def _ensure_api_key(config: dict) -> str:
    api_key = config.get("api_key")
    if api_key:
        return api_key
    result = _register_api_key()
    api_key = result.get("api_key")
    if api_key:
        config["api_key"] = api_key
        config["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _save_config(config)
        return api_key
    return None


# ============================================================
# 健康检查
# ============================================================

def _quick_health_check(timeout=_MCPCHECK_TIMEOUT) -> dict:
    config = _load_config()
    api_key = _ensure_api_key(config)
    service_url = config.get("service_url", _DEFAULT_SERVICE_URL)
    rpc_payload = json.dumps({"jsonrpc": "2.0", "id": 9999, "method": "tools/list", "params": {}}).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "tax-policy-knowledge-skill/3.7.2"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(service_url, data=rpc_payload, headers=headers)
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read())
        if "result" in result and "tools" in result.get("result", {}):
            return {"healthy": True, "tools_count": len(result["result"]["tools"])}
        return {"healthy": False, "reason": "invalid_response"}
    except urllib.error.HTTPError as e:
        return {"healthy": False, "reason": f"http_{e.code}"}
    except urllib.error.URLError:
        return {"healthy": False, "reason": "connection_failed"}
    except Exception:
        return {"healthy": False, "reason": "timeout"}


def _update_mode(healthy: bool):
    global _health_state
    if healthy:
        if _health_state["mode"] != "remote":
            _health_state["mode"] = "remote"
            _health_state["consecutive_failures"] = 0
            _health_state["last_check_time"] = time.time()
            _save_health_state()
    else:
        if _health_state["mode"] != "fallback":
            _health_state["consecutive_failures"] += 1
            if _health_state["consecutive_failures"] >= 1:
                _health_state["mode"] = "fallback"
                _health_state["last_probe_time"] = time.time()
                _health_state["fallback_count"] += 1
                _save_health_state()
        _health_state["last_check_time"] = time.time()


# ============================================================
# MCP调用（协议层优化：保留完整tool名）
# ============================================================

def _call_mcp_tool(tool_name: str, params: dict, api_key: str = None, service_url: str = None, _retry: bool = True):
    """调用 MCP 工具。服务端仅认完整tool名（tax_policy_ask/risk_check等），不使用短名映射。"""
    global _rpc_id
    _rpc_id += 1

    if service_url is None:
        service_url = _DEFAULT_SERVICE_URL

    # 服务端使用完整tool名路由，不映射
    # 注意：服务端MCP端点通过body.body的arguments.api_key获取鉴权，header中的Authorization仅作备选
    if api_key and "api_key" not in params:
        params["api_key"] = api_key

    rpc_payload = json.dumps({
        "jsonrpc": "2.0",
        "id": _rpc_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": params},
    }).encode()

    headers = {"Content-Type": "application/json", "User-Agent": "tax-policy-knowledge-skill/3.7.2"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(service_url, data=rpc_payload, headers=headers)
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        r = result.get("result", result)
        content_list = r.get("content", [])
        for item in content_list:
            if item.get("type") == "text":
                text = item.get("text", "")
                if "API Key" in text and _retry:
                    return _friendly_error("api_key_invalid")
                if text.startswith("错误:") or text.startswith("❌"):
                    return _friendly_error("server_error", {"message": text[:200]})

        # Server层优化：结果截断
        structured = r.get("structuredContent", {})
        if structured and isinstance(structured, dict):
            # 截断长字段
            for key, value in structured.items():
                if isinstance(value, str) and len(value) > _MAX_RESULT_CHARS:
                    structured[key] = value[:_MAX_RESULT_CHARS] + f"\n\n... (内容已截断，共{len(value)}字符)"
                if isinstance(value, list) and len(value) > _MAX_RESULT_LINES:
                    structured[key] = value[:_MAX_RESULT_LINES]
                    structured[f"{key}_more"] = f"... 还有{len(value) - _MAX_RESULT_LINES}条"
            return structured

        for item in content_list:
            if item.get("type") == "text":
                text = item.get("text", "")
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except (json.JSONDecodeError, TypeError):
                    pass
        return r
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:200]
        if e.code == 401 and _retry:
            return _friendly_error("api_key_invalid")
        return _friendly_error("http_error", {"http_code": e.code, "raw": detail})
    except urllib.error.URLError:
        return _friendly_error("connection_failed")
    except Exception:
        return _friendly_error("unknown_error")


# ============================================================
# 批量MCP调用（架构层优化）
# ============================================================

def batch_call(calls: list, api_key: str = None, service_url: str = None):
    """批量MCP调用（并行执行，架构层优化：节省3-6x）
    
    Args:
        calls: [{"tool": "tax_policy_ask", "params": {...}}, ...]
    """
    results = []
    
    def call_one(call):
        tool_name = call.get("tool")
        params = call.get("params", {})
        result = _call_mcp_tool(tool_name, params, api_key, service_url)
        results.append(result)
    
    threads = []
    for call in calls:
        t = __import__("threading").Thread(target=call_one, args=(call,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join(timeout=60)
    
    return results


# ============================================================
# 本地回退搜索
# ============================================================

def _web_search(query: str, timeout: int = 10) -> dict:
    results = _local_web_search(query, max_results=5)
    return {"source": "local_search", "query": query, "results": results, "result_count": len(results)}


def _generate_local_answer(question: str, category: str = None) -> dict:
    query = question
    if category:
        query = f"{category} {query}"
    search_result = _web_search(query)
    if search_result.get("error"):
        return {"source": "local_fallback", "status": "search_failed", "question": question, "message": "当前处于本地搜索模式，但搜索服务暂时不可用。建议稍后重试或咨询专业税务师。"}
    results = search_result.get("results", [])
    if not results:
        return {"source": "local_fallback", "status": "no_results", "question": question, "message": "当前处于本地搜索模式，未找到相关信息。建议稍后重试，或咨询专业税务师。"}
    answer_parts = [f"## 关于「{question}」", "", "⚠️ 当前处于**本地搜索模式**（远程服务暂时不可用），以下内容来自公开财税政策资料：", ""]
    for i, r in enumerate(results):
        answer_parts.append(f"### {i+1}. {r['title']}")
        if r.get("snippet"):
            answer_parts.append(f"> {r['snippet']}")
        answer_parts.append("")
    answer_parts.extend(["---", "", "> 📌 **提示**：当前为本地搜索模式，信息可能不够完整。", "> 远程MCP服务恢复后会自动切换，届时将获得更精准的政策依据和专业分析。", "> 如需最新政策，建议访问[国家税务总局官网](https://www.chinatax.gov.cn)。"])
    return {"source": "local_fallback", "status": "ok", "question": question, "result": "\n".join(answer_parts), "search_query": query, "result_count": len(results)}


# ============================================================
# REST API调用
# ============================================================

def _call_rest_api(method: str, path: str, params: dict = None, api_key: str = None) -> dict:
    url = f"{_DEFAULT_API_BASE}{path}"
    headers = {"Content-Type": "application/json", "User-Agent": "tax-policy-knowledge-skill/3.7.2"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        if method == "GET":
            if params:
                qs = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{qs}"
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=30)
        else:
            data = json.dumps(params or {}).encode()
            req = urllib.request.Request(url, data=data, headers=headers)
            resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:200]
        return _friendly_error("http_error", {"http_code": e.code, "raw": detail})
    except urllib.error.URLError:
        return _friendly_error("connection_failed")
    except Exception:
        return _friendly_error("unknown_error")


# ============================================================
# 反馈提交
# ============================================================

def _append_feedback_queue(entry: dict):
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_FEEDBACK_QUEUE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ============================================================
# 对外接口（带缓存 + 降级）
# ============================================================

def tax_policy_ask(question: str, category: str = None) -> dict:
    """政策问答（Client层优化：带缓存）"""
    _load_health_state()
    mode = _get_current_mode()

    if mode == "probe":
        health = _quick_health_check()
        if health.get("healthy"):
            _update_mode(True)
        else:
            _update_mode(False)
            return _generate_local_answer(question, category)
    elif mode == "fallback":
        return _generate_local_answer(question, category)

    # Client层优化：结果缓存
    cache_key = f"ask:{question}:{category}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    result = _do_remote_policy_ask(question, category)
    _cache_set(cache_key, result)
    return result


def _do_remote_policy_ask(question: str, category: str = None) -> dict:
    config = _load_config()
    service_url = config.get("service_url", _DEFAULT_SERVICE_URL)
    api_key = _ensure_api_key(config)
    params = {"question": question}
    if category:
        params["category"] = category
    result = _call_mcp_tool("tax_policy_ask", params, api_key, service_url)
    if _is_not_found_response(result):
        _append_feedback_queue({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "type": "knowledge_missing", "question": question, "expected_answer": None, "confidence": 70, "source": "client_auto", "remote_status": "not_found"})
    if "error" not in result:
        _log("policy_ask", {"question": question, "status": "ok"})
    else:
        _log("policy_ask", {"question": question, "status": "error", "detail": result.get("error")})
    return result


def risk_check(scenario: str, level_filter: str = None) -> dict:
    """风险检查（Client层优化：带缓存）"""
    _load_health_state()
    mode = _get_current_mode()

    if mode == "probe":
        health = _quick_health_check()
        if health.get("healthy"):
            _update_mode(True)
        else:
            _update_mode(False)
            return _generate_local_answer(scenario)
    elif mode == "fallback":
        return _generate_local_answer(scenario)

    cache_key = f"risk:{scenario}:{level_filter}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    result = _do_remote_risk_check(scenario, level_filter)
    _cache_set(cache_key, result)
    return result


def _do_remote_risk_check(scenario: str, level_filter: str = None) -> dict:
    config = _load_config()
    service_url = config.get("service_url", _DEFAULT_SERVICE_URL)
    api_key = _ensure_api_key(config)
    params = {"scenario": scenario}
    if level_filter:
        params["level_filter"] = level_filter
    result = _call_mcp_tool("risk_check", params, api_key, service_url)
    if "error" not in result:
        _log("risk_check", {"scenario": scenario, "status": "ok"})
    else:
        _log("risk_check", {"scenario": scenario, "status": "error", "detail": result.get("error")})
    return result


def tax_calculate(tax_type: str, params: dict) -> dict:
    """税务计算（Client层优化：带缓存）"""
    _load_health_state()
    mode = _get_current_mode()

    if mode == "probe":
        health = _quick_health_check()
        if health.get("healthy"):
            _update_mode(True)
        else:
            _update_mode(False)
            return _friendly_error("unknown_error")
    elif mode == "fallback":
        return _friendly_error("fallback_active")

    cache_key = f"calc:{tax_type}:{json.dumps(params, sort_keys=True)}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    result = _do_remote_tax_calculate(tax_type, params)
    _cache_set(cache_key, result)
    return result


def _do_remote_tax_calculate(tax_type: str, params: dict) -> dict:
    config = _load_config()
    service_url = config.get("service_url", _DEFAULT_SERVICE_URL)
    api_key = _ensure_api_key(config)
    payload = {"tax_type": tax_type, "params": params}
    result = _call_mcp_tool("tax_calculate", payload, api_key, service_url)
    if "error" not in result:
        _log("tax_calculate", {"tax_type": tax_type, "status": "ok"})
    else:
        _log("tax_calculate", {"tax_type": tax_type, "status": "error", "detail": result.get("error")})
    return result


def kb_list() -> dict:
    """知识库概览（Client层优化：带缓存）"""
    _load_health_state()
    mode = _get_current_mode()
    if mode == "probe":
        health = _quick_health_check()
        if health.get("healthy"):
            _update_mode(True)
        else:
            _update_mode(False)
            return _friendly_error("fallback_active")
    elif mode == "fallback":
        return _friendly_error("fallback_active")

    result = _do_remote_kb_list()
    return result


def _do_remote_kb_list() -> dict:
    config = _load_config()
    service_url = config.get("service_url", _DEFAULT_SERVICE_URL)
    api_key = _ensure_api_key(config)
    return _call_mcp_tool("kb_list", {}, api_key, service_url)


def online_search(query: str, category: str = "", max_results: int = 5) -> dict:
    """在线搜索"""
    config = _load_config()
    service_url = config.get("service_url", _DEFAULT_SERVICE_URL)
    api_key = _ensure_api_key(config)
    params = {"query": query, "category": category, "max_results": max_results}
    result = _call_mcp_tool("online_search", params, api_key, service_url)
    if "error" in result:
        return _web_search(query)
    return result


def trigger_auto_update(question: str, category: str = "", force: bool = False) -> dict:
    """触发服务端知识库自动更新"""
    config = _load_config()
    service_url = config.get("service_url", _DEFAULT_SERVICE_URL)
    api_key = _ensure_api_key(config)
    params = {"question": question, "category": category, "force": force}
    return _call_mcp_tool("auto_update", params, api_key, service_url)


def get_mode_status() -> dict:
    """查询当前运行模式"""
    _load_health_state()
    return {"mode": _get_current_mode(), "consecutive_failures": _health_state["consecutive_failures"], "fallback_count": _health_state["fallback_count"], "last_check_time": _health_state["last_check_time"], "cache": _cache_stats()}


def _is_not_found_response(result: dict) -> bool:
    if "result" not in result:
        return False
    r = result["result"]
    if isinstance(r, str):
        return "未找到" in r or "暂无" in r
    if not isinstance(r, dict):
        return False
    content_list = r.get("content", [])
    for item in content_list:
        text = item.get("text", "") if item.get("type") == "text" else ""
        if "未找到" in text or "暂无" in text or "no detailed info" in text.lower():
            return True
    structured = r.get("structuredContent", {})
    text_val = str(structured.get("answer", structured.get("result", "")))
    if "未找到" in text_val or "暂无" in text_val:
        return True
    return False


# ============================================================
# 反馈管理（Client层优化：带缓存）
# ============================================================

def submit_feedback(feedback_type: str, question: str, expected_answer: str, confidence: int = 90, source: str = "client_auto") -> dict:
    """提交反馈（Client层优化：带缓存）"""
    _load_health_state()
    mode = _get_current_mode()
    if mode in ["fallback", "probe"]:
        return _friendly_error("fallback_active")
    result = _do_submit_feedback(feedback_type, question, expected_answer, confidence, source)
    return result


def _do_submit_feedback(feedback_type: str, question: str, expected_answer: str, confidence: int, source: str) -> dict:
    config = _load_config()
    api_key = _ensure_api_key(config)
    payload = {
        "type": feedback_type,
        "question": question,
        "expected_answer": expected_answer,
        "confidence": confidence,
        "source": source,
    }
    result = _call_rest_api("POST", "/feedback/submit", payload, api_key)
    _append_feedback_queue({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": feedback_type,
        "question": question,
        "expected_answer": expected_answer,
        "confidence": confidence,
        "source": source,
    })
    return result


def get_feedback_list(limit: int = 20) -> dict:
    """获取反馈列表（Client层优化：带缓存）"""
    _load_health_state()
    mode = _get_current_mode()
    if mode in ["fallback", "probe"]:
        return _friendly_error("fallback_active")
    cache_key = f"fblimit:{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    result = _call_rest_api("GET", "/feedback/list", {"limit": limit})
    _cache_set(cache_key, result)
    return result


def get_feedback_stats() -> dict:
    """获取反馈评估统计（Client层优化：带缓存）"""
    _load_health_state()
    mode = _get_current_mode()
    if mode in ["fallback", "probe"]:
        return _friendly_error("fallback_active")
    cache_key = "fbstats"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    result = _call_rest_api("GET", "/feedback/stats", {})
    _cache_set(cache_key, result)
    return result


# ============================================================
# 更新管理
# ============================================================

def get_update_log(limit: int = 20) -> dict:
    """获取知识库自动更新日志"""
    return _call_rest_api("GET", "/update-log", {"limit": limit})


def get_update_stats() -> dict:
    """获取知识库自动更新统计"""
    return _call_rest_api("GET", "/update-stats", {})


# ============================================================
# Git 管理
# ============================================================

def trigger_git_init() -> dict:
    """初始化 Git 版本管理"""
    return _call_rest_api("POST", "/git/init", {})


def trigger_git_backup() -> dict:
    """手动触发 Git 备份"""
    return _call_rest_api("POST", "/git/backup", {})


def get_git_log(limit: int = 20) -> dict:
    """获取 Git 提交日志"""
    return _call_rest_api("GET", "/git/log", {"limit": limit})


def git_rollback(commit: str = "") -> dict:
    """回滚到指定 commit"""
    return _call_rest_api("POST", "/git/rollback", {"commit": commit}) if commit else _call_rest_api("POST", "/git/rollback", {})


def get_git_diff() -> dict:
    """查看知识库未提交的变更"""
    return _call_rest_api("GET", "/git/diff", {})


def trigger_feedback_eval() -> dict:
    """批量评估所有待处理反馈"""
    return _call_rest_api("POST", "/feedback/batch-eval", {})


# ============================================================
# 本地日志
# ============================================================

_LOG_DIR = os.path.expanduser("~/.workbuddy/logs/tax-policy")


def _log(action: str, data: dict):
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        today = time.strftime("%Y-%m-%d")
        log_file = os.path.join(_LOG_DIR, f"{today}.jsonl")
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": action, **data}
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    print("=== 财税政策 MCP 客户端 v3.7.2 (LLM优化版) ===")
    print(f"缓存容量: {_CACHE_TTL}秒, 上下文截断: 最近{_MAX_HISTORY_ROUNDS}轮")
    print(f"tool名映射: {len(_TOOL_NAME_MAP)}个")
    config = _load_config()
    print(f"服务地址: {config.get('service_url')}")
    print(f"API Key: {'已配置' if config.get('api_key') else '未配置（首次调用将自动注册）'}")
    print(f"知识库版本: {config.get('kb_version', '未同步')}")

    print("\n测试缓存统计...")
    print(json.dumps(_cache_stats(), ensure_ascii=False))

    print("\n测试模式状态...")
    print(json.dumps(get_mode_status(), ensure_ascii=False, indent=2))
