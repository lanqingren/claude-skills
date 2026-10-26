#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片生成工具脚本
支持：无参考图生成（generate）、有参考图生成/编辑（edit）、下载图片（download）
"""

import os
import sys
import base64
import argparse
import requests

# API 端点
GENERATE_URL = "https://n.lconai.com/v1/images/generations"
EDIT_URL     = "https://n.lconai.com/v1/images/edits"
REQUEST_TIMEOUT = 600  # 请求超时（秒）


def get_token() -> str:
    token = os.environ.get("WEDA_API_KEY", "")
    if not token:
        print("错误：未设置环境变量 WEDA_API_KEY", file=sys.stderr)
        sys.exit(1)
    return token


def base_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json; charset=utf-8",
    }


# ─── 保存工具 ──────────────────────────────────────────────────────────────────

def save_from_url(url: str, output_dir: str, index: int = 0) -> str:
    """从 URL 下载图片，保存到 output_dir，返回保存路径。"""
    os.makedirs(output_dir, exist_ok=True)
    # 尝试从 URL 提取文件名，否则按序号命名
    name = url.split("?")[0].rstrip("/").split("/")[-1]
    if not name or "." not in name:
        name = f"image_{index}.png"
    save_path = os.path.join(output_dir, name)
    with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"图片已保存：{save_path}")
    return save_path


def save_from_b64(b64: str, output_dir: str, index: int = 0, fmt: str = "png") -> str:
    """将 base64 编码的图片数据保存到 output_dir，返回保存路径。"""
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f"image_{index}.{fmt}")
    with open(save_path, "wb") as f:
        f.write(base64.b64decode(b64))
    print(f"图片已保存：{save_path}")
    return save_path


def save_results(data: list, output_dir: str, fmt: str = "png") -> list[str]:
    """从响应 data 列表中保存所有图片，返回保存路径列表。"""
    paths = []
    for i, item in enumerate(data):
        if item.get("url"):
            paths.append(save_from_url(item["url"], output_dir, i))
        elif item.get("b64_json"):
            paths.append(save_from_b64(item["b64_json"], output_dir, i, fmt))
        else:
            print(f"警告：第 {i} 张图片无 url 或 b64_json 字段", file=sys.stderr)
    return paths


# ─── 1. 无参考图生成 ────────────────────────────────────────────────────────────

def generate_image(
    prompt: str,
    model: str = "gpt-image-2",
    n: int = 1,
    size: str | None = None,
    quality: str | None = None,
    fmt: str | None = None,
    output_dir: str = ".",
) -> dict:
    """调用生成接口（无参考图），返回完整响应 JSON。"""
    token = get_token()
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "response_format": "url",
    }
    if size:
        payload["size"] = size
    if quality:
        payload["quality"] = quality
    if fmt:
        payload["format"] = fmt

    resp = requests.post(
        GENERATE_URL,
        headers={**base_headers(token), "Content-Type": "application/json; charset=utf-8"},
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    result = resp.json()

    data = result.get("data", [])
    save_results(data, output_dir, fmt or "png")
    return result


# ─── 2. 有参考图生成/编辑 ───────────────────────────────────────────────────────

def edit_image(
    prompt: str,
    images: list[str],
    model: str = "gpt-image-2",
    mask: str | None = None,
    n: int = 1,
    size: str | None = None,
    quality: str | None = None,
    output_dir: str = ".",
) -> dict:
    """调用编辑接口（有参考图，multipart），返回完整响应 JSON。"""
    token = get_token()
    data_fields: dict = {
        "prompt": prompt,
        "model": model,
        "n": str(n),
        "response_format": "url",
    }
    if size:
        data_fields["size"] = size
    if quality:
        data_fields["quality"] = quality

    opened: list = []
    files: list = []
    try:
        for img_path in images:
            f = open(img_path, "rb")
            opened.append(f)
            files.append(("image", f))
        if mask:
            f = open(mask, "rb")
            opened.append(f)
            files.append(("mask", f))

        resp = requests.post(
            EDIT_URL,
            headers=base_headers(token),
            data=data_fields,
            files=files,
            timeout=REQUEST_TIMEOUT,
        )
    finally:
        for f in opened:
            f.close()

    resp.raise_for_status()
    result = resp.json()

    img_data = result.get("data", [])
    save_results(img_data, output_dir)
    return result


# ─── 3. 下载图片 ────────────────────────────────────────────────────────────────

def download_image(url: str, save_path: str) -> str:
    """将 url 下载到 save_path（目录或完整路径），返回最终保存路径。"""
    if os.path.isdir(save_path):
        name = url.split("?")[0].rstrip("/").split("/")[-1]
        if not name or "." not in name:
            name = "image.png"
        save_path = os.path.join(save_path, name)
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    print(f"开始下载：{url}")
    with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"图片已保存：{save_path}")
    return save_path


# ─── CLI ────────────────────────────────────────────────────────────────────────

def cmd_generate(args: argparse.Namespace) -> None:
    import json
    result = generate_image(
        prompt=args.prompt,
        model=args.model,
        n=args.n,
        size=args.size,
        quality=args.quality,
        fmt=args.format,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_edit(args: argparse.Namespace) -> None:
    import json
    result = edit_image(
        prompt=args.prompt,
        images=args.image,
        model=args.model,
        mask=args.mask,
        n=args.n,
        size=args.size,
        quality=args.quality,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_download(args: argparse.Namespace) -> None:
    download_image(args.url, args.output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="图片生成工具 — 无参考图生成、有参考图编辑、下载图片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── generate（无参考图）──
    p_gen = sub.add_parser("generate", help="无参考图生成图片（JSON 请求）")
    p_gen.add_argument("--prompt", required=True, help="文本提示词")
    p_gen.add_argument("--model", default="gpt-image-2", help="模型名称，默认 gpt-image-2")
    p_gen.add_argument("--n", type=int, default=1, help="生成数量，1~10，默认 1")
    p_gen.add_argument("--size", default=None, help="尺寸，如 1024x1024、1536x1024")
    p_gen.add_argument("--quality", default=None, choices=["low", "medium", "high"], help="质量")
    p_gen.add_argument("--format", default=None, dest="format", choices=["jpeg", "png", "webp"], help="图片格式")
    p_gen.add_argument("--output-dir", default=".", dest="output_dir", help="保存目录，默认当前目录")
    p_gen.set_defaults(func=cmd_generate)

    # ── edit（有参考图）──
    p_edit = sub.add_parser("edit", help="有参考图生成/编辑图片（multipart 请求）")
    p_edit.add_argument("--prompt", required=True, help="文本提示词")
    p_edit.add_argument("--image", action="append", required=True, metavar="PATH", help="参考图片路径，可多次指定")
    p_edit.add_argument("--model", default="gpt-image-2", help="模型名称，默认 gpt-image-2")
    p_edit.add_argument("--mask", default=None, metavar="PATH", help="掩码图片路径（PNG）")
    p_edit.add_argument("--n", type=int, default=1, help="生成数量，1~10，默认 1")
    p_edit.add_argument("--size", default=None, help="尺寸，如 1024x1024、auto")
    p_edit.add_argument("--quality", default=None, choices=["low", "medium", "high", "auto"], help="质量")
    p_edit.add_argument("--output-dir", default=".", dest="output_dir", help="保存目录，默认当前目录")
    p_edit.set_defaults(func=cmd_edit)

    # ── download ──
    p_dl = sub.add_parser("download", help="下载图片到本地")
    p_dl.add_argument("--url", required=True, help="图片下载 URL")
    p_dl.add_argument("--output", required=True, metavar="PATH", help="保存路径（目录或完整文件名）")
    p_dl.set_defaults(func=cmd_download)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
