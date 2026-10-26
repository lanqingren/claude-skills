#!/usr/bin/env python3
"""
下载指定图片到本地保存地址
用法: python download_image.py <image_url> <save_path>
示例: python download_image.py https://example.com/image.png C:/Downloads/image.png
"""

import sys
import os
import urllib.request
import urllib.error


def download_image(url: str, save_path: str) -> None:
    # 确保目标目录存在
    save_dir = os.path.dirname(os.path.abspath(save_path))
    os.makedirs(save_dir, exist_ok=True)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read()
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code} - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: {e.reason}", file=sys.stderr)
        sys.exit(1)

    with open(save_path, "wb") as f:
        f.write(data)

    size_kb = len(data) / 1024
    print(f"OK: saved to {os.path.abspath(save_path)} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python download_image.py <image_url> <save_path>", file=sys.stderr)
        print("Example: python download_image.py https://example.com/img.png C:/Downloads/img.png", file=sys.stderr)
        sys.exit(1)

    download_image(sys.argv[1], sys.argv[2])
