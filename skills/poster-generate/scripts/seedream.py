#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""海报生成器 - 使用豆包 Seedream API（文生图 / 图生图，参考图与官方 `image` 数组一致）"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DOUBAO_MODEL = "doubao-seedream-4-5-251128"
MAX_REF_IMAGES = 3
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 与文档常见限制一致

_EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

SIZES = {
    "2k": {
        "1:1": "2048x2048", "4:3": "2304x1728", "3:4": "1728x2304",
        "16:9": "2848x1600", "9:16": "1600x2848", "3:2": "2496x1664",
        "2:3": "1664x2496", "21:9": "3136x1344",
    },
    "4k": {
        "1:1": "4096x4096", "3:4": "3520x4704", "4:3": "4704x3520",
        "16:9": "5504x3040", "9:16": "3040x5504", "2:3": "3328x4992",
        "3:2": "4992x3328", "21:9": "6240x2656",
    },
}


def _local_path_to_data_url(path: str) -> str:
    if not os.path.isfile(path):
        print(f"错误：参考图不是有效文件：{path}")
        sys.exit(1)
    size = os.path.getsize(path)
    if size > MAX_IMAGE_BYTES:
        print(f"错误：单张参考图超过 {MAX_IMAGE_BYTES // (1024 * 1024)}MB：{path}")
        sys.exit(1)
    ext = os.path.splitext(path)[1].lower()
    mime = _EXT_TO_MIME.get(ext)
    if not mime:
        print(f"错误：不支持的图片扩展名 {ext!r}，请使用：{', '.join(sorted(_EXT_TO_MIME))}")
        sys.exit(1)
    with open(path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def generate_image(
    prompt,
    output_path=None,
    resolution="2k",
    ratio="3:4",
    ref_image_paths=None,
):
    """使用豆包 Seedream API 生成图片。ref_image_paths 为本地路径列表，将编码为 data URL 填入 image 数组。"""
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        print("错误：需要 ARK_API_KEY 环境变量")
        sys.exit(1)

    ref_image_paths = ref_image_paths or []
    if len(ref_image_paths) > MAX_REF_IMAGES:
        print(f"错误：参考图最多 {MAX_REF_IMAGES} 张，当前 {len(ref_image_paths)} 张")
        sys.exit(1)

    size = SIZES.get(resolution.lower(), SIZES["2k"]).get(ratio, SIZES["2k"]["3:4"])

    print(f"分辨率：{resolution.upper()} | 比例：{ratio} | 尺寸：{size}")
    if ref_image_paths:
        print(f"图生图：{len(ref_image_paths)} 张本地参考图")
    print(f"提示词：{prompt[:80]}..." if len(prompt) > 80 else f"提示词：{prompt}")
    print("生成中...\n")

    try:
        payload = {
            "model": DOUBAO_MODEL,
            "prompt": prompt,
            "size": size,
            "watermark": False,
            "sequential_image_generation": "auto"
        }
        if ref_image_paths:
            payload["image"] = [_local_path_to_data_url(p) for p in ref_image_paths]


        req = urllib.request.Request(
            DOUBAO_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        image_url = result.get("data", [{}])[0].get("url")
        if not image_url:
            print(f"响应格式无效：{result}")
            return None

        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_" for c in prompt[:15])
            output_path = f"output/poster-{safe_name}-{timestamp}.png"

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        urllib.request.urlretrieve(image_url, output_path)
        print(f"已保存：{output_path}")
        return output_path

    except urllib.error.HTTPError as e:
        print(f"HTTP 错误：{e.code}")
        try:
            body = e.read().decode("utf-8", errors="replace")
            if body:
                print(body)
        except OSError:
            pass
        return None
    except Exception as e:
        print(f"错误：{e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="海报生成器",
        epilog="示例：python3 seedream.py --prompt 赛博朋克城市 --resolution 2k --ratio 3:4"
    )
    parser.add_argument("--prompt", required=True, help="图片描述提示词")
    parser.add_argument("--resolution", default="2k", choices=["2k", "4k"], help="分辨率")
    parser.add_argument("--ratio", default="3:4", help="宽高比")
    parser.add_argument(
        "--image",
        action="append",
        dest="ref_images",
        default=None,
        metavar="PATH",
        help=f"参考图（本地文件），可重复，最多 {MAX_REF_IMAGES} 张",
    )
    parser.add_argument("--output", help="输出文件路径")

    args = parser.parse_args()
    ref = args.ref_images
    if ref is not None and len(ref) > MAX_REF_IMAGES:
        print(f"错误：--image 最多使用 {MAX_REF_IMAGES} 次")
        sys.exit(1)

    out = generate_image(
        args.prompt,
        args.output,
        args.resolution,
        args.ratio,
        ref_image_paths=ref,
    )
    if not out:
        sys.exit(1)


if __name__ == "__main__":
    main()
