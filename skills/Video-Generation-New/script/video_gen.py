#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频生成工具脚本
支持：提交任务、单次查询状态、轮询查询状态、下载视频
"""

import os
import sys
import time
import argparse
import requests

# API 基础配置
CREATE_URL = "https://n.lconai.com/v1/videos"
QUERY_URL  = "https://n.lconai.com/v1/video/query"
REQUEST_TIMEOUT = 600  # 请求超时（秒）


def get_token() -> str:
    token = os.environ.get("WEDA_API_KEY", "")
    if not token:
        print("错误：未设置环境变量 WEDA_API_KEY", file=sys.stderr)
        sys.exit(1)
    return token


def headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json; charset=utf-8",
    }


# ─── 1. 提交任务 ────────────────────────────────────────────────────────────────

def create_task(
    prompt: str,
    model: str = "grok-imagine-video-1.5-preview",
    seconds: int | None = None,
    size: str | None = None,
    input_reference: str | None = None,
    video: str | None = None,
) -> dict:
    """提交视频生成任务，返回完整响应 JSON。"""
    token = get_token()
    data = {"model": model, "prompt": prompt}
    if seconds is not None:
        data["seconds"] = str(seconds)
    if size:
        data["size"] = size

    files: dict = {}
    opened: list = []
    try:
        if input_reference:
            f = open(input_reference, "rb")
            opened.append(f)
            files["input_reference"] = f
        if video:
            f = open(video, "rb")
            opened.append(f)
            files["video"] = f

        resp = requests.post(
            CREATE_URL,
            headers=headers(token),
            data=data,
            files=files if files else None,
            timeout=REQUEST_TIMEOUT,
        )
    finally:
        for f in opened:
            f.close()

    resp.raise_for_status()
    result = resp.json()
    print(f"任务已提交，ID：{result.get('id')}")
    return result


# ─── 2. 单次查询状态 ────────────────────────────────────────────────────────────

def query_task(task_id: str) -> dict:
    """单次查询任务状态，返回完整响应 JSON。"""
    token = get_token()
    resp = requests.get(
        QUERY_URL,
        headers=headers(token),
        params={"id": task_id},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ─── 3. 轮询查询状态 ────────────────────────────────────────────────────────────

def poll_task(task_id: str, interval: float = 3.0, timeout: float = 600.0) -> dict:
    """
    轮询查询任务状态，直到 completed/failed 或超时。
    - interval：轮询间隔（秒），默认 3
    - timeout ：最长等待时间（秒），默认 600
    超时后抛出 TimeoutError；如需继续等待，可再次调用本函数或使用 query_task。
    """
    deadline = time.time() + timeout
    while True:
        result = query_task(task_id)
        status = result.get("status", "")
        progress = result.get("progress", "")
        print(f"任务状态：{status}  进度：{progress}")

        if status == "completed":
            return result
        if status in ("failed", "error"):
            print(f"任务失败：{result}", file=sys.stderr)
            sys.exit(1)

        if time.time() >= deadline:
            raise TimeoutError(
                f"轮询超时（{timeout}s），任务 {task_id} 尚未完成。"
                " 可重新运行 query 或 poll 命令继续等待。"
            )
        time.sleep(interval)


# ─── 4. 下载视频 ────────────────────────────────────────────────────────────────

def download_video(video_url: str, save_path: str) -> str:
    """
    将 video_url 下载到 save_path（支持目录或完整文件路径）。
    返回最终保存路径。
    """
    if os.path.isdir(save_path):
        filename = video_url.split("?")[0].rstrip("/").split("/")[-1]
        save_path = os.path.join(save_path, filename)

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    print(f"开始下载：{video_url}")
    with requests.get(video_url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

    print(f"视频已保存：{save_path}")
    return save_path


# ─── CLI ────────────────────────────────────────────────────────────────────────

def cmd_create(args: argparse.Namespace) -> None:
    result = create_task(
        prompt=args.prompt,
        model=args.model,
        seconds=args.seconds,
        size=args.size,
        input_reference=args.input_reference,
        video=args.video,
    )
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_query(args: argparse.Namespace) -> None:
    import json
    result = query_task(args.id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_poll(args: argparse.Namespace) -> None:
    import json
    try:
        result = poll_task(args.id, interval=args.interval, timeout=args.timeout)
    except TimeoutError as e:
        print(f"警告：{e}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.download and result.get("video_url"):
        download_video(result["video_url"], args.download)


def cmd_download(args: argparse.Namespace) -> None:
    download_video(args.url, args.output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="视频生成工具 — 提交任务、查询状态、下载视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── create ──
    p_create = sub.add_parser("create", help="提交视频生成任务")
    p_create.add_argument("--prompt", required=True, help="视频文本提示词")
    p_create.add_argument("--model", default="grok-imagine-video-1.5", help="模型名称")
    p_create.add_argument("--seconds", type=int, default=None, help="视频时长（秒，最大15）")
    p_create.add_argument("--size", default=None, help="分辨率，如 1280x720")
    p_create.add_argument("--input-reference", dest="input_reference", default=None, help="参考图片本地路径")
    p_create.add_argument("--video", default=None, help="参考视频本地路径")
    p_create.set_defaults(func=cmd_create)

    # ── query ──
    p_query = sub.add_parser("query", help="单次查询任务状态")
    p_query.add_argument("--id", required=True, help="任务 ID")
    p_query.set_defaults(func=cmd_query)

    # ── poll ──
    p_poll = sub.add_parser("poll", help="轮询任务状态直到完成或超时")
    p_poll.add_argument("--id", required=True, help="任务 ID")
    p_poll.add_argument("--interval", type=float, default=3.0, help="轮询间隔（秒），默认 3")
    p_poll.add_argument("--timeout", type=float, default=600.0, help="最长等待时间（秒），默认 600")
    p_poll.add_argument("--download", default=None, metavar="PATH", help="完成后自动下载到指定路径")
    p_poll.set_defaults(func=cmd_poll)

    # ── download ──
    p_dl = sub.add_parser("download", help="下载视频到本地")
    p_dl.add_argument("--url", required=True, help="视频下载 URL")
    p_dl.add_argument("--output", required=True, metavar="PATH", help="保存路径（目录或完整文件名）")
    p_dl.set_defaults(func=cmd_download)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
