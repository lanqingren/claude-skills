#!/usr/bin/env python3
"""Generate travel marketing prompt bundles from product links or IDs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import importlib
import json
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable


SPRINGTOUR_BASE = "https://m.springtour.com"
DEFAULT_CTA = "扫码查看详细行程"
SKILL_DIR = Path(__file__).resolve().parents[1]
PRODUCT_LINK_QR_OUTPUT = "product_link_qr.png"
PRODUCT_IMAGE_LIMIT = 3
PRODUCT_IMAGE_PREFIX = "product_image"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class NeedTextFallbackError(RuntimeError):
    """Raised when URL parsing cannot produce usable product text and should request manual text input."""

PLATFORM_DISPLAY_NAMES = {
    "ctrip.com": "携程",
    "trip.com": "Trip.com",
    "qunar.com": "去哪儿",
    "fliggy.com": "飞猪",
    "tuniu.com": "途牛",
    "ly.com": "同程",
    "tongcheng.com": "同程",
    "mafengwo.cn": "马蜂窝",
    "springtour.com": "春秋旅游",
}


def normalized_host(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def is_springtour_url(url: str) -> bool:
    host = normalized_host(url)
    return host.endswith("springtour.com")


def infer_platform_name(url: str | None) -> str:
    if not url:
        return "旅游平台"
    host = normalized_host(url)
    for domain, display in PLATFORM_DISPLAY_NAMES.items():
        if host.endswith(domain):
            return display
    if not host:
        return "旅游平台"
    root = host.split(".")[0]
    if not root:
        return "旅游平台"
    return root.capitalize()


def build_text_fallback_request(url: str | None, reason: str = "") -> str:
    lines = [
        "当前链接未能稳定提取到可用产品正文。",
        "你不用按固定模板写，直接把你手头已有的一段产品介绍文本粘贴给我就行（长短都可以）。",
    ]
    if reason:
        lines.append(f"原因：{reason}")
    if url:
        lines.append(f"链接：{url}")
    lines.extend(
        [
            "",
            "建议你直接贴这些任意内容（有多少贴多少）：",
            "",
            "- 产品标题/线路名",
            "- 价格或促销句子",
            "- 行程亮点、酒店、景点介绍",
            "- 你认为重要的任何文案片段",
            "",
            "如果是命令行使用：可把这段文本保存为 `product.md`，再用 `--text-file product.md` 继续。",
        ]
    )
    return "\n".join(lines)


def ensure_qrcode_package() -> Any:
    """Return qrcode module, installing it if this business terminal lacks it."""
    try:
        import qrcode

        return qrcode
    except ImportError:
        print("未检测到 qrcode，正在安装 qrcode[pil] 以生成产品链接二维码...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "qrcode[pil]"], check=True)
        importlib.invalidate_caches()
        import qrcode

        return qrcode


TEMPLATE_NAMES = {
    "1": "朋友圈旅游产品海报",
    "2": "小红书旅游产品封面",
    "3": "旅游产品介绍长图",
    "4": "社群推广文案+配图",
    "5": "爆款小红书旅游笔记",
    "6": "高转化旅游产品销售页",
    "7": "旅行社销售朋友圈文案",
    "8": "旅游产品短视频脚本",
}
TEMPLATE_MENU_OPTIONS = [*TEMPLATE_NAMES.values(), "全部"]

def normalize_template_key(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).lower()


TEMPLATE_ALIASES = {normalize_template_key(key): key for key in TEMPLATE_NAMES}
TEMPLATE_ALIASES.update({normalize_template_key(name): key for key, name in TEMPLATE_NAMES.items()})
TEMPLATE_ALIASES.update(
    {
        normalize_template_key("社群推广文案 + 配图"): "4",
    }
)


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {
        "User-Agent": "Mozilla/5.0 TripCuePromptGenerator/1.0",
        "Accept": "application/json,text/plain,*/*",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8", "ignore").strip()
    if not raw.startswith("{"):
        raise ValueError(f"Non-JSON response from {url}")
    return json.loads(raw)


def strip_html(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def money(value: Any) -> str:
    try:
        n = int(float(str(value).replace(",", "")))
        return f"￥{n:,}起/人"
    except Exception:
        s = str(value or "").strip()
        if not s:
            return ""
        s = s if s.startswith("￥") else f"￥{s}"
        return s if "起/人" in s else f"{s}起/人"


def weekday_zh(date_str: str) -> str:
    names = "一二三四五六日"
    try:
        d = dt.date.fromisoformat(date_str[:10])
        return f"周{names[d.weekday()]}"
    except Exception:
        return ""


def parse_days_nights(text: str) -> tuple[str, str]:
    m = re.search(r"(\d+)\s*日\s*(\d+)\s*晚", text)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"(\d+)\s*日", text)
    if m:
        return m.group(1), ""
    return "", ""


def extract_numeric_product_id(text: str) -> str:
    m = re.search(r"productId=(\d+)", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{5,})\b", text)
    if m:
        return m.group(1)
    return ""


def build_product_id(url: str | None, product_id: str | None = None) -> str:
    if product_id:
        return str(product_id).strip()
    if url:
        numeric = extract_numeric_product_id(url)
        if numeric:
            return numeric
        host = normalized_host(url) or "link"
        short_host = re.sub(r"[^a-z0-9]+", "", host)[:10] or "link"
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
        return f"{short_host}_{digest}"
    return "manual"


def product_page_url(product_id: str, url: str | None = None) -> str:
    if url:
        return url.strip()
    if product_id and product_id != "manual" and product_id.isdigit():
        return f"{SPRINGTOUR_BASE}/page/product/index?productId={product_id}"
    return ""


def infer_destination_from_title(title: str) -> str:
    value = re.sub(r"\d+\s*日.*$", "", title).strip()
    value = re.sub(r"(自由行|跟团游|半自助|私家团|一地游).*$", "", value).strip()
    return value.strip(" -_·｜|●+")


def split_title(name: str) -> tuple[str, str, str]:
    raw = strip_html(name)
    if not raw:
        return "旅游产品", "", ""
    title_part = re.split(r"[｜|●]", raw, maxsplit=1)[0].strip() or raw
    title = re.split(r"[+]", title_part, maxsplit=1)[0].strip() or title_part
    dest_parts = []
    if "+" in title_part:
        for part in title_part.split("+")[1:]:
            clean = strip_html(part).strip()
            if clean:
                dest_parts.append(clean)
    if not dest_parts:
        inferred = infer_destination_from_title(title)
        if inferred and inferred != title:
            dest_parts.append(inferred)
    dest = " + ".join(dest_parts[:6])
    subtitle = dest.replace(" + ", " · ") if dest else ""
    return title, dest, subtitle


def take_lines(text: str, limit: int = 8) -> list[str]:
    chunks = []
    for line in re.split(r"[\n；;]+", strip_html(text)):
        line = line.strip(" -•\t")
        if line:
            chunks.append(line)
    return chunks[:limit]


def text_lines(text: str) -> list[str]:
    out = []
    for line in strip_html(text).splitlines():
        line = line.strip(" -•\t")
        if line and line not in out:
            out.append(line)
    return out


def unique_preserve(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def looks_like_image_url(value: str) -> bool:
    lower = value.lower()
    if lower.startswith("data:image/"):
        return False
    if not (lower.startswith("http://") or lower.startswith("https://") or lower.startswith("//") or lower.startswith("/")):
        return False
    if any(ext in lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".avif"]):
        return True
    return any(token in lower for token in ["/image", "/img", "pic.", "dimg", "tripcdn", "ctrip"])


def extract_payload_text_and_images(payload: Any) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    images: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
            return
        if isinstance(node, list):
            for value in node:
                walk(value)
            return
        if not isinstance(node, str):
            return
        value = strip_html(node).strip()
        if not value:
            return
        if looks_like_image_url(value):
            images.append(value)
            return
        if 2 <= len(value) <= 120 and re.search(r"[\u4e00-\u9fff￥¥]", value):
            texts.append(value)

    walk(payload)
    return unique_preserve(texts), unique_preserve(images)


def product_from_network_payloads(product_id: str, body_text: str, dom_images: list[str], payloads: list[Any]) -> dict[str, Any] | None:
    text_parts = text_lines(body_text)
    image_urls = list(dom_images or [])
    for payload in payloads:
        texts, images = extract_payload_text_and_images(payload)
        text_parts.extend(texts)
        image_urls.extend(images)
    text_parts = unique_preserve(text_parts)[:300]
    image_urls = unique_preserve(image_urls)[:40]
    if len(text_parts) < 3 and not image_urls:
        return None
    merged_text = "\n".join(text_parts)
    product = product_from_text(product_id, merged_text, image_urls)
    title = (product.get("title") or "").strip()
    if not title or title in {"旅游", "Ctrip.com", "携程旅行网"}:
        product["title"] = f"旅游产品 {product_id}"
        product["raw_name"] = product["title"]
    return product


def detect_unreadable_page_reason(body_text: str, payloads: list[Any]) -> str:
    clean = strip_html(body_text)
    texts: list[str] = []
    for payload in payloads[:10]:
        extracted, _images = extract_payload_text_and_images(payload)
        texts.extend(extracted[:40])
    combined = "\n".join(unique_preserve(texts)[:120])
    anti_tokens = [
        "加载错误",
        "请稍后再试",
        "验证",
        "验证码",
        "访问频繁",
        "风控",
        "robot",
        "spider",
        "anti",
        "forbidden",
    ]
    probe = f"{clean}\n{combined}".lower()
    if any(token.lower() in probe for token in anti_tokens):
        return "疑似触发平台风控/反爬，页面只返回壳层或错误提示。"
    if len(clean) < 120:
        return "页面正文过少，未提取到可用产品信息。"
    return "页面可访问，但未解析到可用产品字段。"


def pick_product_title(text: str) -> str:
    lines = text_lines(text)
    title_markers = ["自由行", "跟团游", "半自助", "私家团", "一地游", "日", "晚", "●"]
    skip_words = ["首页", "客服", "收藏", "分享", "登录", "注册", "预订须知"]
    for line in lines:
        if any(word in line for word in skip_words):
            continue
        if len(line) > 8 and any(marker in line for marker in title_markers):
            return line
    return lines[0] if lines else "旅游产品"


def extract_price_from_text(text: str) -> str:
    lines = text_lines(text)
    preferred = [line for line in lines if any(token in line for token in ["￥", "¥"]) and any(token in line for token in ["起", "价格", "成人", "总价"])]
    candidates = preferred or [line for line in lines if any(token in line for token in ["￥", "¥"])]
    for line in candidates:
        m = re.search(r"[￥¥]\s*([\d,]+)(?:\.\d+)?", line)
        if m:
            return money(m.group(1))
    return ""


def extract_highlights_from_text(text: str, raw_title: str, limit: int = 10) -> list[str]:
    skip_words = ["首页", "客服", "收藏", "分享", "登录", "注册", "产品编号", "预订须知", "费用说明"]
    highlights = []
    for line in text_lines(text):
        if line == raw_title or len(line) > 80 or any(word in line for word in skip_words):
            continue
        if any(token in line for token in ["酒店", "市场", "早去晚回", "自由行", "精选", "升级", "体验", "含", "近", "宿", "美食", "景点", "航班"]):
            highlights.append(line)
        if len(highlights) >= limit:
            break
    return unique_preserve(highlights)[:limit]


def ensure_python_playwright(install: bool = True) -> tuple[Any, type[Exception], type[Exception]]:
    """Return Playwright sync helpers, installing Python Playwright if needed."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        return sync_playwright, PlaywrightTimeoutError, PlaywrightError
    except ImportError as exc:
        if not install:
            raise RuntimeError("未安装 Python Playwright；请先安装后再读取页面。") from exc
        print("未检测到 Python Playwright，正在安装 playwright...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "playwright"], check=True)
        importlib.invalidate_caches()
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        return sync_playwright, PlaywrightTimeoutError, PlaywrightError


def install_playwright_chromium() -> None:
    print("正在安装 Playwright Chromium 浏览器...", file=sys.stderr)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


def launch_chromium(playwright: Any, install: bool, playwright_error: type[Exception]) -> Any:
    try:
        return playwright.chromium.launch(headless=True)
    except playwright_error as exc:
        message = str(exc)
        if not install or ("Executable doesn't exist" not in message and "playwright install" not in message):
            raise
        install_playwright_chromium()
        return playwright.chromium.launch(headless=True)


def is_usable_page_text(text: str, product_id: str) -> bool:
    clean = strip_html(text)
    if len(clean) < 120:
        return False
    markers = ["产品", "行程", "价格", "出发", "目的地", "酒店", "景点", "交通", "签证", "包含"]
    score = sum(1 for marker in markers if marker in clean)
    if product_id and product_id.isdigit() and product_id in clean:
        score += 1
    return score >= 2


def fetch_product_with_playwright(
    product_id: str,
    url: str | None = None,
    install: bool = True,
    timeout_ms: int = 35000,
    allow_springtour_api_capture: bool = True,
) -> dict[str, Any]:
    """Open a product page in a real browser and extract product data from network/DOM."""
    sync_playwright, playwright_timeout, playwright_error = ensure_python_playwright(install)
    target_url = url or f"{SPRINGTOUR_BASE}/page/product/index?productId={product_id}"
    captured: dict[str, Any] = {"detail": {}, "summary": {}, "daily": {}, "desc": {}}
    body_text = ""
    dom_images: list[str] = []
    generic_payloads: list[Any] = []
    network_image_urls: list[str] = []

    def capture_response(response: Any) -> None:
        response_url = response.url
        lower_url = response_url.lower()
        try:
            resource_type = response.request.resource_type
        except Exception:
            resource_type = ""
        if resource_type == "image" and len(network_image_urls) < 200:
            network_image_urls.append(response_url)
        data: Any = None
        try:
            headers = response.headers or {}
            content_type = str(headers.get("content-type", "")).lower()
        except Exception:
            content_type = ""
        should_read_json = "application/json" in content_type or any(token in lower_url for token in ["graphql", "restapi", "soa2", "product"])
        if should_read_json:
            try:
                data = response.json()
            except Exception:
                data = None
        if data is not None and len(generic_payloads) < 40:
            generic_payloads.append(data)
        if not allow_springtour_api_capture or not product_id.isdigit() or data is None:
            return
        if "gettourproduct" in lower_url and isinstance(data, dict) and data.get("Data"):
            captured["detail"] = data["Data"]
        elif "dailydesc" in lower_url and isinstance(data, dict) and data.get("data"):
            captured["daily"] = data["data"]
        elif f"/product/web/product/{product_id}".lower() in lower_url and isinstance(data, dict) and data.get("data"):
            captured["summary"] = data["data"]
        elif "getproductdescinfo" in lower_url and isinstance(data, dict):
            captured["desc"] = data

    with sync_playwright() as pw:
        browser = launch_chromium(pw, install, playwright_error)
        try:
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                has_touch=True,
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                locale="zh-CN",
            )
            page = context.new_page()
            page.on("response", capture_response)
            page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except playwright_timeout:
                pass
            for _ in range(5):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(500)
            try:
                body_text = page.locator("body").inner_text(timeout=5000)
            except Exception:
                body_text = ""
            try:
                dom_images = page.eval_on_selector_all(
                    "img",
                    """
                    imgs => imgs
                        .map(img => img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || img.getAttribute('lazy-src') || img.getAttribute('data-lazy-src') || '')
                        .filter(Boolean)
                    """,
                )
            except Exception:
                dom_images = []
            try:
                next_data_text = page.locator("#__NEXT_DATA__").inner_text(timeout=1000).strip()
                if next_data_text.startswith("{"):
                    generic_payloads.append(json.loads(next_data_text))
            except Exception:
                pass
        finally:
            browser.close()

    if is_usable_page_text(body_text, product_id):
        all_images = unique_preserve([*dom_images, *network_image_urls])
        product = product_from_text(product_id, body_text, all_images)
        if captured["detail"] or captured["summary"] or captured["daily"]:
            product = merge_product_data(product, normalize_product(product_id, captured["detail"], captured["summary"], captured["daily"], captured["desc"]))
        return product
    if captured["detail"] or captured["summary"] or captured["daily"]:
        product = normalize_product(product_id, captured["detail"], captured["summary"], captured["daily"], captured["desc"])
        product["pictures"] = unique_preserve([*(product.get("pictures") or []), *dom_images, *network_image_urls])[:40]
        return product
    fallback_product = product_from_network_payloads(product_id, body_text, [*dom_images, *network_image_urls], generic_payloads)
    if fallback_product:
        return fallback_product
    reason = detect_unreadable_page_reason(body_text, generic_payloads)
    raise NeedTextFallbackError(reason)


def fetch_product_from_api(product_id: str) -> dict[str, Any]:
    detail = {}
    summary = {}
    daily = {}
    desc = {}
    errors: list[str] = []

    try:
        resp = request_json(f"{SPRINGTOUR_BASE}/site/tour/GetTourProduct", "POST", {"ProductId": int(product_id)})
        if resp.get("Data"):
            detail = resp["Data"]
    except Exception as exc:
        errors.append(f"GetTourProduct: {exc}")

    try:
        resp = request_json(f"{SPRINGTOUR_BASE}/product/web/product/{product_id}")
        if resp.get("data"):
            summary = resp["data"]
    except Exception as exc:
        errors.append(f"product summary: {exc}")

    try:
        resp = request_json(f"{SPRINGTOUR_BASE}/product/web/product/dailydesc/{product_id}")
        if resp.get("data"):
            daily = resp["data"]
    except Exception as exc:
        errors.append(f"daily desc: {exc}")

    try:
        resp = request_json(f"{SPRINGTOUR_BASE}/site/product/GetProductDescInfo/{product_id}", "POST", {})
        if resp:
            desc = resp
    except Exception as exc:
        errors.append(f"desc info: {exc}")

    if not detail and not summary and not daily:
        raise RuntimeError("接口读取失败或没有可用产品内容：" + " | ".join(errors))
    return normalize_product(product_id, detail, summary, daily, desc)


def fetch_product(
    product_id: str,
    url: str | None = None,
    source_mode: str = "browser-first",
    install_playwright: bool = True,
    timeout_ms: int = 35000,
) -> dict[str, Any]:
    errors: list[str] = []
    springtour_source = bool(product_id.isdigit() and (is_springtour_url(url) if url else True))
    if source_mode == "api-only" and not springtour_source:
        raise SystemExit("非春秋链接不支持 api-only，请使用 --source-mode browser-first。")
    if source_mode == "browser-first":
        try:
            product = fetch_product_with_playwright(
                product_id,
                url=url,
                install=install_playwright,
                timeout_ms=timeout_ms,
                allow_springtour_api_capture=springtour_source,
            )
            if url and not product.get("platform"):
                product["platform"] = infer_platform_name(url)
            return product
        except NeedTextFallbackError as exc:
            errors.append(f"Playwright: {exc}")
            if springtour_source:
                print(f"Playwright DOM 提取不足，改用接口兜底：{exc}", file=sys.stderr)
            else:
                raise SystemExit(build_text_fallback_request(url, str(exc))) from exc
        except Exception as exc:
            errors.append(f"Playwright: {exc}")
            if springtour_source:
                print(f"Playwright DOM 提取失败，改用接口兜底：{exc}", file=sys.stderr)
            else:
                raise SystemExit(build_text_fallback_request(url, "浏览器读取失败或页面结构变化。")) from exc

    if not springtour_source:
        raise SystemExit(build_text_fallback_request(url, "当前链接不支持接口兜底。"))
    try:
        product = fetch_product_from_api(product_id)
        if url and not product.get("platform"):
            product["platform"] = infer_platform_name(url)
        return product
    except Exception as exc:
        errors.append(f"API: {exc}")
        raise SystemExit(build_text_fallback_request(url, "浏览器与接口均未取到可用内容。")) from exc


def normalize_product(product_id: str, detail: dict[str, Any], summary: dict[str, Any], daily: dict[str, Any], desc: dict[str, Any]) -> dict[str, Any]:
    raw_name = detail.get("Name") or summary.get("product_name") or f"产品 {product_id}"
    title, dest, subtitle = split_title(raw_name)
    schedules = []
    for item in detail.get("SchedulePrices") or []:
        date = str(item.get("ScheduleDate", ""))[:10]
        price = money(item.get("Price"))
        schedules.append(
            {
                "date": date,
                "weekday": weekday_zh(date),
                "price": price,
                "inventory": item.get("RemainInventory"),
            }
        )

    recommend_lines = take_lines(detail.get("Recommend"), 10)
    title_bits = [p.strip(" +｜|●") for p in re.split(r"[+｜|●]", raw_name) if p.strip()]
    highlights = []
    for line in recommend_lines + title_bits[1:] + (summary.get("tag_themes") or []):
        clean = strip_html(line)
        if clean and clean not in highlights and len(clean) < 80:
            highlights.append(clean)
    highlights = highlights[:10]

    itinerary = []
    segments = detail.get("ProductSegmentDescriptions") or []
    if segments:
        for seg in segments[:20]:
            itinerary.append(
                {
                    "day": seg.get("Days") or seg.get("Day") or len(itinerary) + 1,
                    "title": strip_html(seg.get("Title") or ""),
                    "description": strip_html(seg.get("Description") or "")[:350],
                }
            )
    for item in daily.get("daily_description_list") or []:
        if len(itinerary) >= 20:
            break
        itinerary.append(
            {
                "day": item.get("day") or len(itinerary) + 1,
                "title": item.get("city_name") or "",
                "description": strip_html(item.get("description") or "")[:350],
            }
        )

    pictures = []
    for pic in detail.get("Pictures") or []:
        url = pic.get("Url")
        if url:
            pictures.append(url)
    for day in daily.get("daily_description_list") or []:
        for pic in day.get("picture_list") or []:
            url = pic.get("pic_url")
            if url and url not in pictures:
                pictures.append(url)

    favorable = take_lines(detail.get("FavorableInfo"), 6)
    if not favorable:
        favorable = ["早订优惠以实际产品页为准"]

    included = []
    excluded = []
    for item in detail.get("ChargeDescriptions") or []:
        title_text = strip_html(item.get("Title"))
        body = strip_html(item.get("Descripiton") or item.get("Description"))
        target = excluded if "不含" in title_text else included
        if body:
            target.append(f"{title_text}：{body}" if title_text else body)

    parsed_days, parsed_nights = parse_days_nights(raw_name)
    days = detail.get("Days") or daily.get("days") or parsed_days
    nights = detail.get("NightDays")
    if nights is None or nights == "":
        nights = parsed_nights
    if days and nights not in (None, ""):
        days_text = f"{days}日{nights}晚"
    elif days:
        days_text = f"{days}日"
    else:
        days_text = "行程天数以产品页为准"

    return {
        "product_id": product_id,
        "raw_name": strip_html(raw_name),
        "title": title,
        "destination": dest or subtitle or "目的地以产品页为准",
        "subtitle": subtitle or dest,
        "platform": "旅游平台",
        "origin": (detail.get("City") or {}).get("Name") or "上海",
        "days": days_text,
        "min_price": money(detail.get("MinPrice") or detail.get("CurrentChannel", {}).get("Price")),
        "schedules": schedules,
        "highlights": highlights,
        "favorable": favorable,
        "itinerary": itinerary,
        "included": included[:8],
        "excluded": excluded[:6],
        "pictures": pictures[:12],
        "output_product_images": [],
        "product_url": "",
        "output_qr_image": "",
        "phone": "",
        "wechat": "",
        "store": "",
        "cta": "",
        "use_qr": False,
        "use_background": False,
    }


def product_from_text(product_id: str, text: str, pictures: list[str] | None = None) -> dict[str, Any]:
    raw_title = pick_product_title(text).lstrip("# ").strip()
    title, dest, subtitle = split_title(raw_title)
    parsed_days, parsed_nights = parse_days_nights(raw_title)
    if parsed_days and parsed_nights:
        days_text = f"{parsed_days}日{parsed_nights}晚"
    elif parsed_days:
        days_text = f"{parsed_days}日"
    else:
        days_text = "行程天数以用户粘贴内容为准"
    return {
        "product_id": product_id,
        "raw_name": raw_title,
        "title": title[:28],
        "destination": dest or "目的地以用户粘贴内容为准",
        "subtitle": subtitle,
        "platform": "旅游平台",
        "origin": "上海",
        "days": days_text,
        "min_price": extract_price_from_text(text),
        "schedules": [],
        "highlights": extract_highlights_from_text(text, raw_title, 10),
        "favorable": [],
        "itinerary": [],
        "included": [],
        "excluded": [],
        "pictures": unique_preserve(pictures or [])[:12],
        "output_product_images": [],
        "product_url": "",
        "output_qr_image": "",
        "phone": "",
        "wechat": "",
        "store": "",
        "cta": "",
        "use_qr": False,
        "use_background": False,
    }


def merge_product_data(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Keep Playwright DOM text as primary, fill only missing structured fields."""
    merged = dict(primary)
    for key in ["min_price", "origin"]:
        if not merged.get(key) and secondary.get(key):
            merged[key] = secondary[key]
    if str(merged.get("days", "")).startswith("行程天数") and secondary.get("days"):
        merged["days"] = secondary["days"]
    for key in ["schedules", "favorable", "itinerary", "included", "excluded"]:
        if not merged.get(key) and secondary.get(key):
            merged[key] = secondary[key]
    merged["highlights"] = unique_preserve([*(merged.get("highlights") or []), *(secondary.get("highlights") or [])])[:10]
    merged["pictures"] = unique_preserve([*(merged.get("pictures") or []), *(secondary.get("pictures") or [])])[:12]
    return merged


def apply_supplement_options(product: dict[str, Any], args: argparse.Namespace, template_ids: list[str]) -> dict[str, Any]:
    """Apply user answers for information that is not present in the product link."""
    if args.contact_mode == "custom":
        product["phone"] = args.phone or ""
        product["wechat"] = args.wechat or ""
        product["store"] = args.store or ""
        product["cta"] = args.cta or ("咨询了解详细行程" if any([args.phone, args.wechat, args.store]) else "")
    else:
        product["phone"] = ""
        product["wechat"] = ""
        product["store"] = ""
        product["cta"] = args.cta or ""

    product["use_qr"] = args.qr_mode == "use"
    product["use_background"] = args.background_mode == "use"
    product["include_product_images"] = args.product_images_mode == "auto"
    product["include_link_qr"] = args.link_qr_mode == "auto"
    if (product["use_qr"] or product["include_link_qr"]) and not product["cta"]:
        product["cta"] = DEFAULT_CTA
    return product


def fmt_list(items: list[str], empty: str = "") -> str:
    text = "\n".join(f"- {x}" for x in items if x)
    if text:
        return text
    return f"- {empty}" if empty else ""


def fmt_schedules(p: dict[str, Any]) -> str:
    if not p["schedules"]:
        return ""
    return "\n".join(f"{s['date']} {s['weekday']} {s['price']}" for s in p["schedules"][:8])


def fmt_itinerary(p: dict[str, Any], limit: int = 12) -> str:
    if not p["itinerary"]:
        return ""
    lines = []
    for day in p["itinerary"][:limit]:
        title = day["title"] or "行程安排"
        desc = day["description"].replace("\n", " ")
        lines.append(f"Day {day['day']} {title}：{desc[:160]}")
    return "\n".join(lines)


def contact_text(p: dict[str, Any]) -> str:
    parts = []
    if p.get("phone"):
        parts.append(f"咨询电话 {p['phone']}")
    if p.get("wechat"):
        parts.append(f"客服微信 {p['wechat']}")
    if p.get("store"):
        parts.append(f"门店名称 {p['store']}")
    if p.get("cta"):
        parts.append(p["cta"])
    return "；".join(parts)


def contact_area_label(p: dict[str, Any]) -> str:
    if any([p.get("phone"), p.get("wechat"), p.get("store")]):
        return "咨询信息"
    if p.get("cta"):
        return "报名引导"
    return ""


def common_product_block(p: dict[str, Any]) -> str:
    lines = [
        f"产品名称：{p['title']}",
        f"目的地：{p['destination']}",
        f"产品编号：{p['product_id']}",
    ]
    if p.get("origin"):
        lines.append(f"出发地：{p['origin']}")
    if p.get("days"):
        lines.append(f"天数：{p['days']}")
    if p.get("min_price"):
        lines.append(f"价格：{p['min_price']}")
    schedules = fmt_schedules(p)
    if schedules:
        lines.extend(["出发日期：", schedules])
    highlights = fmt_list(p["highlights"])
    if highlights:
        lines.extend(["核心卖点：", highlights])
    favorable = fmt_list(p["favorable"])
    if favorable:
        lines.extend(["早订/优惠：", favorable])
    contact = contact_text(p)
    if contact:
        lines.append(f"报名信息：{contact}")
    return "\n".join(lines)


def qr_asset_name(p: dict[str, Any]) -> str:
    if p.get("output_qr_image"):
        return p["output_qr_image"]
    if p.get("use_qr"):
        return "二维码 PNG"
    return ""


def qr_asset_label(p: dict[str, Any]) -> str:
    if p.get("output_qr_image"):
        return f"产品链接二维码 {p['output_qr_image']}"
    if p.get("use_qr"):
        return "我提供的二维码 PNG"
    return ""


def asset_rules(p: dict[str, Any]) -> str:
    rules = []
    if p.get("output_product_images"):
        rules.append(f"本次产出会随附产品图 {asset_name_text(p['output_product_images'])}，可作为背景图、主视觉底图或拼贴素材使用，优先使用真实产品图建立目的地氛围。")
    if p.get("output_qr_image"):
        rules.append(f"本次产出会随附产品链接二维码 {p['output_qr_image']}，请嵌入底部报名/咨询区域，二维码保持标准正方形 1:1，不要拉伸、倾斜、裁切或做透视变形。")
    if p.get("use_qr"):
        rules.append("我会提供二维码 PNG，请嵌入底部报名/咨询区域，二维码保持标准正方形 1:1，不要拉伸、倾斜、裁切或做透视变形。")
    if p.get("use_background"):
        rules.append("我会提供背景图或主视觉素材，请按画面需要作为背景、主视觉底图或拼贴素材使用，优先保证旅行氛围、画面质感和文字可读性。")
    if not rules:
        return ""
    return "【素材使用要求】\n" + "\n".join(f"{i}. {rule}" for i, rule in enumerate(rules, start=1))


def visual_source_text(p: dict[str, Any]) -> str:
    product_images = p.get("output_product_images") or []
    if product_images and p.get("use_background"):
        return f"优先使用随附产品图 {asset_name_text(product_images)}，也可结合我提供的背景图/主视觉素材作为背景、主视觉底图或拼贴素材；画面可加入古城、湖区、宫殿、街景、地标、地图线、机票、相机、行李箱等旅行元素。"
    if product_images:
        return f"优先使用随附产品图 {asset_name_text(product_images)} 作为真实产品主视觉、背景底图或拼贴素材；画面可加入古城、湖区、宫殿、街景、地标、地图线、机票、相机、行李箱等旅行元素。"
    if p.get("use_background"):
        return "使用我提供的背景图/主视觉素材或产品目的地代表性风景作为主视觉，可结合古城、湖区、宫殿、街景、地标、地图线、机票、相机、行李箱等旅行元素。"
    return "使用产品目的地代表性风景作为主视觉，可结合古城、湖区、宫殿、街景、地标、地图线、机票、相机、行李箱等旅行元素。"


def picture_text_lines(p: dict[str, Any]) -> str:
    lines = [f"主标题：{p['title']}"]
    if p.get("subtitle") or p.get("destination"):
        lines.append(f"副标题：{p['subtitle'] or p['destination']}")
    if p.get("min_price"):
        lines.append(f"价格：{p['min_price']}")
    if p.get("cta"):
        lines.append(f"报名引导：{p['cta']}")
    return "\n".join(lines)


def layout_rules(p: dict[str, Any]) -> str:
    platform = p.get("platform") or "旅游平台"
    rules = []
    rules.append(f"顶部放清晰品牌文字“{platform}”和产品编号 {p['product_id']}。")
    rules.append("主标题必须大而清晰。")
    focus = []
    if p.get("min_price"):
        focus.append("价格")
    if p.get("days"):
        focus.append("天数")
    if p.get("origin"):
        focus.append("出发地")
    if p.get("schedules"):
        focus.append("班期")
    if focus:
        rules.append(f"{'、'.join(focus)}要醒目但不吵。")
    if p.get("highlights"):
        rules.append("核心卖点用图标化标签展示。")
    bottom = []
    contact_label = contact_area_label(p)
    if contact_label:
        bottom.append(contact_label)
    qr_label = qr_asset_label(p)
    if qr_label:
        bottom.append(qr_label)
    if bottom:
        rules.append(f"底部放{'和'.join(bottom)}。")
    return "\n".join(f"{i}. {rule}" for i, rule in enumerate(rules, start=1))


def negative_rules(p: dict[str, Any]) -> str:
    rules = []
    if qr_asset_name(p):
        rules.append("不要凭空生成新的二维码；只使用随附或用户提供的二维码 PNG，或保留正方形占位框。")
    rules.extend([
        "不要把国家、城市、价格、日期、产品编号写错。",
        "不要让文字互相遮挡。",
    ])
    return "\n".join(rules)


def section(title: str, body: str) -> str:
    body = body.strip()
    if not body:
        return ""
    return f"\n【{title}】\n{body}"


def price_instruction(p: dict[str, Any]) -> str:
    if p.get("min_price"):
        return f"价格统一写成“{p['min_price']}”。"
    return "如未提供价格，不要编造价格，也不要出现价格占位描述。"


def asset_short_phrase(p: dict[str, Any]) -> str:
    parts = []
    if p.get("output_product_images"):
        parts.append(f"产品图 {asset_name_text(p['output_product_images'])}")
    qr_label = qr_asset_label(p)
    if qr_label:
        parts.append(qr_label)
    if p.get("use_background"):
        parts.append("背景图/主视觉素材")
    return "、".join(parts)


def image_prompt(p: dict[str, Any], scene: str, ratio: str, style: str) -> str:
    platform = p.get("platform") or "旅游平台"
    return f"""请生成一张高质量移动端旅游营销海报。

【使用场景】
{scene}

【产品信息】
{common_product_block(p)}

【画面比例】
{ratio}

【视觉风格】
{style}
画面要体现目的地吸引力、产品品质感、平台可信感和清晰成交信息。

【主视觉】
{visual_source_text(p)}

【画面文字】
{picture_text_lines(p)}

【版式要求】
{layout_rules(p)}

{asset_rules(p)}

【负面要求】
{negative_rules(p)}

【品牌一致性】
图片里的品牌词统一使用“{platform}”，不要出现其他平台 logo 或品牌字样。"""


def render_1(p: dict[str, Any]) -> str:
    return image_prompt(p, "微信朋友圈竖版产品海报", "9:16 竖版", "高质感旅行杂志风 + 轻营销海报风")


def render_2(p: dict[str, Any]) -> str:
    return image_prompt(p, "小红书旅游产品封面", "3:4 竖版", "小红书种草风、清新旅行杂志风、可爱但不幼稚")


def render_3(p: dict[str, Any]) -> str:
    itinerary = fmt_itinerary(p)
    structure = [
        "首屏：目的地大视觉 + 产品名称 + 核心卖点。",
        "卖点区：用 4-6 个卡片展示产品亮点。",
    ]
    if itinerary:
        structure.append("行程区：按 Day 1 / Day 2 / Day 3 的形式展示每日安排。")
    structure.append("体验区：展示景点、美食、住宿、交通亮点。")
    if p.get("min_price") or p.get("schedules") or p.get("favorable"):
        structure.append("价格/班期区：突出已提供的价格、出发日期或优惠信息。")
    bottom = []
    if contact_text(p):
        bottom.append("联系方式")
    if qr_asset_name(p):
        bottom.append("二维码")
    if bottom:
        structure.append(f"结尾区：放置{'和'.join(bottom)}。")
    structure_text = "\n".join(f"{i}. {item}" for i, item in enumerate(structure, start=1))
    return f"""你是一位旅游产品详情页设计师。请制作一张旅游产品介绍长图。

【产品信息】
{common_product_block(p)}
{section('每日安排摘要', itinerary)}

【内容结构】
{structure_text}

【画面比例】
9:20 或更长竖版长图。

{asset_rules(p)}

【输出要求】
生成完整的旅游产品介绍长图，适合销售转发和客户咨询使用。"""


def render_4(p: dict[str, Any]) -> str:
    output_items = [
        "社群短文案：150 字以内。",
        "社群长文案：300-500 字。",
        "朋友圈文案：旅行顾问真实口吻。",
        "小红书标题：生成 10 个。",
        "海报文案：主标题、副标题、3 个卖点标签、底部行动号召。",
    ]
    if asset_short_phrase(p):
        output_items.append(f"配图 Prompt：按已选择素材要求使用 {asset_short_phrase(p)}。")
    else:
        output_items.append("配图 Prompt：使用目的地代表性风景与旅行元素，不要提及未提供的素材。")
    output_text = "\n".join(f"{i}. {item}" for i, item in enumerate(output_items, start=1))
    return f"""你是一位旅行社社群运营专家。请生成适合微信群/企业微信社群发布的推广内容。

【产品信息】
{common_product_block(p)}

【输出内容】
{output_text}

【文案风格】
轻松、有画面感、有购买理由，不要生硬广告腔。{price_instruction(p)}"""


def render_5(p: dict[str, Any]) -> str:
    itinerary = fmt_itinerary(p, 8)
    title_bits = ["目的地", "天数", "省心", "出片"]
    if p.get("min_price"):
        title_bits.append("价格")
    ending = "结尾引导收藏或咨询。" if contact_text(p) or p.get("cta") else "结尾引导收藏，不要出现未提供的咨询方式。"
    return f"""你是一位小红书旅游博主兼旅行社营销策划。请写一篇旅游产品种草笔记。

【产品信息】
{common_product_block(p)}
{section('经典行程', itinerary)}

【标题要求】
生成 5 个标题，突出{('、').join(title_bits)}。

【正文结构】
1. 强吸引力开头。
2. 说明目的地为什么值得去。
3. 清单式介绍行程亮点。
4. 展示适合人群。
5. 说明产品优势。
6. {ending}

【输出格式】
标题：
正文：
话题标签：
评论区引导语："""


def render_6(p: dict[str, Any]) -> str:
    included = fmt_list(p["included"])
    itinerary = fmt_itinerary(p, 10)
    structure = [
        "吸引眼球的主标题。",
        "一句话说明最大价值。",
        "3-5 个核心卖点。",
        "为什么这个时间适合去。",
    ]
    if itinerary:
        structure.append("行程体验亮点。")
    if included:
        structure.append("费用包含亮点。")
    structure.append("适合人群。")
    if contact_text(p) or p.get("cta"):
        structure.append("报名行动号召。")
    structure_text = "\n".join(f"{i}. {item}" for i, item in enumerate(structure, start=1))
    return f"""你是一位旅行社产品营销专家。请写一份高转化旅游产品销售页文案。

【产品信息】
{common_product_block(p)}
{section('费用包含', included)}
{section('每日安排摘要', itinerary)}

【文案结构】
{structure_text}

【文案要求】
{price_instruction(p)}专业但不生硬。"""


def render_7(p: dict[str, Any]) -> str:
    ending = "每条最后加一句自然咨询引导。" if contact_text(p) or p.get("cta") else "每条最后加一句自然收藏/了解引导，不要出现未提供的咨询方式。"
    price_line = f"价格统一写成“{p['min_price']}”。" if p.get("min_price") else "不要编造价格。"
    return f"""你是一位有经验的旅行顾问。请写 10 条适合朋友圈发布的旅游产品文案。

【产品信息】
{common_product_block(p)}

【文案要求】
1. 语气像真实旅行顾问，不要太广告。
2. 每条控制在 80-150 字。
3. 每条角度不同：种草型、稀缺型、价格型、亲子/家庭型、闺蜜型、爸妈型、高品质型、懒人省心型、节假日型、老客推荐型。
4. {ending}
5. {price_line}

【输出格式】
按 1-10 编号输出。"""


def render_8(p: dict[str, Any]) -> str:
    itinerary = fmt_itinerary(p, 8)
    steps = [
        "前 3 秒强钩子。",
        "目的地氛围画面。",
        "3-5 个核心景点快闪。",
        "产品卖点展示。",
    ]
    if p.get("min_price") or p.get("schedules"):
        steps.append("价格/出发日期露出。")
    if contact_text(p) or p.get("cta"):
        steps.append("结尾引导咨询。")
    steps_text = "\n".join(f"{i}. {item}" for i, item in enumerate(steps, start=1))
    return f"""你是一位旅游短视频编导。请生成一条 30-45 秒旅游产品短视频脚本。

【产品信息】
{common_product_block(p)}
{section('核心景点/行程', itinerary)}

【脚本结构】
{steps_text}

【输出内容】
分镜脚本、画面内容、旁白文案、屏幕字幕、背景音乐建议、封面标题建议。"""


RENDERERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "1": render_1,
    "2": render_2,
    "3": render_3,
    "4": render_4,
    "5": render_5,
    "6": render_6,
    "7": render_7,
    "8": render_8,
}


def parse_templates(value: str) -> list[str]:
    value = value.strip()
    try:
        parsed = json.loads(value)
    except Exception:
        parsed = None
    if isinstance(parsed, list):
        value = "，".join(str(item) for item in parsed if str(item).strip())
    if normalize_template_key(value) in {"all", "全部", "全部生成"}:
        return list(TEMPLATE_NAMES)
    out = []
    for part in re.split(r"[,，;；、|｜\n]+", value.strip()):
        if not part:
            continue
        key = normalize_template_key(part)
        if key in {"all", "全部", "全部生成"}:
            return list(TEMPLATE_NAMES)
        tid = TEMPLATE_ALIASES.get(key)
        if not tid:
            raise SystemExit(f"未知模板名称：{part}。请使用 --list-templates 查看可选模板名称。")
        out.append(tid)
    return out or ["1"]


def safe_name(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\\s]+", "_", value.strip())
    return value.strip("_")[:40] or "product"


def asset_name_text(names: list[str]) -> str:
    return "、".join(names)


def normalize_asset_url(url: str, base_url: str = "") -> str:
    value = strip_html(url).strip()
    if not value:
        return ""
    lower = value.lower()
    if lower.startswith(("data:", "javascript:", "blob:")):
        return ""
    if value.startswith("//"):
        value = "https:" + value
    elif value.startswith("/"):
        value = urllib.parse.urljoin(base_url or SPRINGTOUR_BASE, value)
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in {"http", "https"}:
        return ""
    if not parts.netloc:
        return ""
    path = urllib.parse.quote(parts.path, safe="/%")
    query = urllib.parse.quote(parts.query, safe="=&%:/?,+-_.")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def image_extension(url: str, content_type: str = "") -> str:
    ctype = content_type.split(";")[0].strip().lower()
    if ctype in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[ctype]
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix == ".jpeg":
        return ".jpg"
    if suffix in IMAGE_EXTENSIONS:
        return suffix
    return ".jpg"


def unique_urls(urls: list[str], base_url: str = "") -> list[str]:
    seen = set()
    out = []
    for url in urls:
        normalized = normalize_asset_url(url, base_url=base_url)
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def download_image(url: str, referer: str = "") -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 TripCuePromptGenerator/1.0",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": referer or (SPRINGTOUR_BASE + "/"),
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def copy_product_images(product: dict[str, Any], out_dir: Path) -> list[tuple[str, str]]:
    product["output_product_images"] = []
    if not product.get("include_product_images"):
        return []
    assets: list[tuple[str, str]] = []
    referer = product.get("product_url") or ""
    for url in unique_urls(product.get("pictures") or [], base_url=referer):
        if len(assets) >= PRODUCT_IMAGE_LIMIT:
            break
        try:
            data, content_type = download_image(url, referer=referer)
        except Exception as exc:
            print(f"产品图下载失败，已跳过：{url} ({exc})", file=sys.stderr)
            continue
        if not data:
            continue
        ext = image_extension(url, content_type)
        filename = f"{PRODUCT_IMAGE_PREFIX}_{len(assets) + 1:02d}{ext}"
        (out_dir / filename).write_bytes(data)
        assets.append((f"产品图 {len(assets) + 1}", filename))
    product["output_product_images"] = [filename for _label, filename in assets]
    return assets


def create_link_qr(product: dict[str, Any], out_dir: Path) -> list[tuple[str, str]]:
    product["output_qr_image"] = ""
    if not product.get("include_link_qr") or not product.get("product_url"):
        return []
    qrcode = ensure_qrcode_package()
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=14,
        border=4,
    )
    qr.add_data(product["product_url"])
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    target = out_dir / PRODUCT_LINK_QR_OUTPUT
    img.save(target)
    product["output_qr_image"] = PRODUCT_LINK_QR_OUTPUT
    return [("产品链接二维码", PRODUCT_LINK_QR_OUTPUT)]


def copy_output_assets(product: dict[str, Any], out_dir: Path) -> list[tuple[str, str]]:
    assets: list[tuple[str, str]] = []
    assets.extend(create_link_qr(product, out_dir))
    assets.extend(copy_product_images(product, out_dir))
    return assets


def cleanup_generated_files(out_dir: Path) -> None:
    """Remove old generated artifacts so reruns keep the simplified bundle shape."""
    patterns = [
        "??_*_Prompt.txt",
        "??_*_Prompt.md",
        "00_总索引_一键复制.txt",
        PRODUCT_LINK_QR_OUTPUT,
        f"{PRODUCT_IMAGE_PREFIX}_*.*",
    ]
    for pattern in patterns:
        for path in out_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def write_bundle(product: dict[str, Any], template_ids: list[str], output_root: Path) -> Path:
    out_dir = output_root / f"{product['product_id']}_{safe_name(product['title'])}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cleanup_generated_files(out_dir)
    output_assets = copy_output_assets(product, out_dir)

    written = []
    for tid in template_ids:
        content = RENDERERS[tid](product).strip() + "\n"
        content = re.sub(r"\n{3,}", "\n\n", content)
        base = f"{int(tid):02d}_{TEMPLATE_NAMES[tid]}_Prompt"
        written.append((tid, base, content))

    md_index = [f"# {product['title']} Prompt 总索引（可直接复制）", ""]
    md_index.extend([f"以下为 {len(written)} 套已填入产品数据的 Prompt。", ""])
    if output_assets:
        md_index.extend(["## 随附标准素材", ""])
        for label, asset in output_assets:
            md_index.append(f"- {label}：`{asset}`")
        md_index.append("")
    for i, (_tid, base, content) in enumerate(written, start=1):
        md_index.extend([f"## {i}. {base}", "", "```text", content.rstrip(), "```", ""])
    (out_dir / "00_总索引_一键复制.md").write_text("\n".join(md_index), encoding="utf-8")

    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Travel product URL from SpringTour/Ctrip/Trip.com etc.")
    parser.add_argument("--product-id", help="Product ID when URL is unavailable")
    parser.add_argument("--text-file", help="Fallback Atlas/product Markdown file, used only after Playwright/API parsing fails")
    parser.add_argument("--source-mode", choices=["browser-first", "api-only"], default="browser-first", help="Use Playwright browser extraction first, or skip browser and use APIs only")
    parser.add_argument("--no-install-playwright", action="store_true", help="Do not auto-install Python Playwright or Chromium when missing")
    parser.add_argument("--playwright-timeout-ms", type=int, default=35000, help="Playwright navigation timeout in milliseconds")
    parser.add_argument("--templates", default="朋友圈旅游产品海报", help="Template names, comma-separated, or 全部")
    parser.add_argument("--output-root", default="./旅游营销Prompt模板/产品生成", help="Output root directory")
    parser.add_argument("--list-templates", action="store_true", help="List template menu and exit")
    parser.add_argument("--contact-mode", choices=["omit", "custom"], default="omit", help="How to handle contact info missing from the product link")
    parser.add_argument("--phone", default="", help="Custom phone number")
    parser.add_argument("--wechat", default="", help="Custom WeChat ID")
    parser.add_argument("--store", default="", help="Custom store name")
    parser.add_argument("--cta", default="", help="Optional call-to-action text")
    parser.add_argument("--qr-mode", choices=["use", "omit"], default="omit", help="Whether the user will provide a QR code PNG")
    parser.add_argument("--link-qr-mode", choices=["auto", "omit"], default="auto", help="Generate a square QR PNG from the product URL or canonical product page URL")
    parser.add_argument("--background-mode", choices=["use", "omit"], default="omit", help="Whether the user will provide a background or hero visual asset")
    parser.add_argument("--product-images-mode", choices=["auto", "omit"], default="auto", help="Download and include up to 3 product images from the product link when available")
    args = parser.parse_args()

    if args.list_templates:
        for name in TEMPLATE_MENU_OPTIONS:
            print(name)
        return

    if not (args.product_id or args.url or args.text_file):
        raise SystemExit(
            "我可以帮你把旅游产品信息生成营销 Prompt。\n"
            "你可以任选一种输入：\n"
            "1) 直接给产品链接（携程/春秋/Trip.com 等）\n"
            "2) 直接贴一段产品介绍文本（不需要固定格式）\n"
            "3) 给一个产品 ID（仅数字）\n"
            "如果你现在只是想先了解我能做什么，也可以直接说你的目标（例如：做朋友圈海报文案、小红书封面、销售页）。"
        )
    if args.product_id and not args.url and not str(args.product_id).isdigit() and not args.text_file:
        raise SystemExit("当仅使用 --product-id 时，请提供纯数字 ID；或改为直接传入 --url。")

    product_id = build_product_id(args.url, args.product_id)
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
        product = product_from_text(product_id, text)
    else:
        product = fetch_product(
            product_id,
            url=args.url,
            source_mode=args.source_mode,
            install_playwright=not args.no_install_playwright,
            timeout_ms=args.playwright_timeout_ms,
        )
    product["platform"] = infer_platform_name(args.url)
    product["product_url"] = product_page_url(product_id, args.url)
    template_ids = parse_templates(args.templates)
    product = apply_supplement_options(product, args, template_ids)
    out_dir = write_bundle(product, template_ids, Path(args.output_root))
    print(out_dir)


if __name__ == "__main__":
    main()
