#!/usr/bin/env python3
"""
磁盘垃圾扫描脚本 - scan_disk.py
扫描指定路径，找出老文件、大文件、临时文件等垃圾候选项
输出 JSON 格式供 SKILL.md 工作流使用
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# ============ 配置 ============

# 默认扫描排除的目录（系统关键路径）
EXCLUDED_DIRS = {
    "Windows", "$Windows.~BT", "$Windows.~WS", "$Recycle.Bin",
    "System Volume Information", "ProgramData", "Program Files",
    "Program Files (x86)", "Microsoft", "AppData",
}

# 垃圾文件扩展名
JUNK_EXTENSIONS = {
    ".tmp", ".temp", ".log", ".bak", ".old", ".chk",
    ".gid", ".dmp", ".err", ".last", "~",
    ".crdownload", ".part", ".download",
    ".swp", ".swo", ".wlx", ".wlk",
}

# 缓存/临时目录关键词
CACHE_DIR_KEYWORDS = {
    "cache", "Cache", "CACHE", "temp", "Temp", "TEMP",
    "tmp", "Tmp", "log", "Log", "LOG",
    "__pycache__", "node_modules", ".cache",
    "Thumbs", "thumbnails",
}

# 大文件阈值（默认 100MB）
LARGE_FILE_THRESHOLD_MB = 100

# 老文件阈值（默认 180 天）
OLD_FILE_THRESHOLD_DAYS = 180


def should_skip_dir(dirname: str, exclude_keywords: list = None) -> bool:
    """判断是否跳过此目录"""
    if dirname in EXCLUDED_DIRS:
        return True
    for kw in CACHE_DIR_KEYWORDS:
        if kw in dirname:
            return True
    # 用户指定的排除关键词
    if exclude_keywords:
        for kw in exclude_keywords:
            if kw.lower() in dirname.lower():
                return True
    return False


def is_junk_file(filepath: Path, exclude_keywords: list = None) -> bool:
    """判断文件是否是垃圾文件"""
    name = filepath.name
    ext = filepath.suffix.lower()
    full_path = str(filepath)

    # 排除关键词匹配
    if exclude_keywords:
        for kw in exclude_keywords:
            if kw.lower() in full_path.lower():
                return False  # 命中的排除项，不算垃圾，跳过

    # 扩展名匹配
    if ext in JUNK_EXTENSIONS:
        return True

    # 文件名模式：以 ~ 开头或 ~$ 开头（Office 临时文件）
    if name.startswith("~") or name.startswith("~$"):
        return True

    # Thumbs.db
    if name.lower() == "thumbs.db":
        return True

    # desktop.ini
    if name.lower() == "desktop.ini":
        return True

    # .DS_Store (macOS残留)
    if name == ".DS_Store":
        return True

    return False


def format_size(size_bytes: int) -> str:
    """将字节数转为人类可读格式"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}PB"


def scan_path(root_path: str,
              old_days: int = OLD_FILE_THRESHOLD_DAYS,
              large_mb: float = LARGE_FILE_THRESHOLD_MB,
              max_depth: int = 5,
              quick_mode: bool = False,
              exclude_keywords: list = None) -> dict:
    """
    扫描指定路径，返回垃圾候选项
    """
    root = Path(root_path)
    if not root.exists():
        return {"error": f"路径不存在: {root_path}"}

    now = time.time()
    old_threshold = now - (old_days * 86400)
    large_threshold = large_mb * 1024 * 1024

    # 结果收集
    old_files = []       # 老文件
    large_files = []     # 大文件
    junk_files = []      # 垃圾扩展名文件
    cache_dirs = []      # 缓存目录
    empty_dirs = []      # 空目录

    # 限制扫描数量（快速模式更少）
    max_files = 5000 if quick_mode else 50000
    scanned = 0

    try:
        for dirpath, dirnames, filenames in os.walk(root):
            # 深度控制
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth >= max_depth:
                dirnames.clear()
                continue

            # 过滤要跳过的目录（原地修改影响 os.walk 行为）
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d, exclude_keywords)]

            # 检查是否为缓存目录本身
            dir_name = Path(dirpath).name
            is_cache_dir = any(kw in dir_name for kw in CACHE_DIR_KEYWORDS)

            if is_cache_dir:
                try:
                    dir_size = sum(
                        f.stat().st_size for f in Path(dirpath).rglob("*") if f.is_file()
                    )
                    dir_mtime = os.path.getmtime(dirpath)
                    dir_age_days = int((now - dir_mtime) / 86400)
                    cache_dirs.append({
                        "path": dirpath,
                        "size": dir_size,
                        "size_human": format_size(dir_size),
                        "age_days": dir_age_days,
                    })
                    # 跳过缓存目录内部扫描
                    dirnames.clear()
                    continue
                except (PermissionError, OSError):
                    pass

            # 检查空目录
            if not filenames and not dirnames:
                empty_dirs.append({
                    "path": dirpath,
                })

            for fname in filenames:
                scanned += 1
                if scanned > max_files:
                    break

                fpath = Path(dirpath) / fname
                try:
                    stat = fpath.stat()
                except (PermissionError, OSError, FileNotFoundError):
                    continue

                fsize = stat.st_size
                fmtime = stat.st_mtime
                age_days = int((now - fmtime) / 86400)

                file_info = {
                    "path": str(fpath),
                    "size": fsize,
                    "size_human": format_size(fsize),
                    "age_days": age_days,
                    "modified": datetime.fromtimestamp(fmtime).strftime("%Y-%m-%d %H:%M"),
                }

                # 垃圾扩展名文件（排除关键词命中的不算垃圾）
                if is_junk_file(fpath, exclude_keywords):
                    junk_files.append(file_info)
                    continue  # 已归为垃圾，不再重复归类

                # 老文件
                if fmtime < old_threshold:
                    old_files.append(file_info)

                # 大文件
                if fsize > large_threshold:
                    large_files.append(file_info)

            if scanned > max_files:
                break

    except PermissionError:
        pass

    # 排序：按大小降序
    old_files.sort(key=lambda x: x["size"], reverse=True)
    large_files.sort(key=lambda x: x["size"], reverse=True)
    junk_files.sort(key=lambda x: x["size"], reverse=True)
    cache_dirs.sort(key=lambda x: x["size"], reverse=True)

    # 汇总统计
    total_old_size = sum(f["size"] for f in old_files)
    total_large_size = sum(f["size"] for f in large_files)
    total_junk_size = sum(f["size"] for f in junk_files)
    total_cache_size = sum(d["size"] for d in cache_dirs)
    total_potential = total_old_size + total_large_size + total_junk_size + total_cache_size

    result = {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_path": str(root),
        "scan_params": {
            "old_days": old_days,
            "large_mb": large_mb,
            "max_depth": max_depth,
            "quick_mode": quick_mode,
        },
        "summary": {
            "scanned_files": scanned,
            "old_files_count": len(old_files),
            "large_files_count": len(large_files),
            "junk_files_count": len(junk_files),
            "cache_dirs_count": len(cache_dirs),
            "empty_dirs_count": len(empty_dirs),
            "total_potential_savings": format_size(total_potential),
        },
        "old_files": old_files[:100],       # 最多列100个
        "large_files": large_files[:50],     # 最多列50个
        "junk_files": junk_files[:100],      # 最多列100个
        "cache_dirs": cache_dirs[:30],       # 最多列30个
        "empty_dirs": empty_dirs[:50],       # 最多列50个
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="磁盘垃圾扫描工具")
    parser.add_argument("path", help="要扫描的根路径")
    parser.add_argument("--old-days", type=int, default=OLD_FILE_THRESHOLD_DAYS,
                        help=f"老文件天数阈值（默认{OLD_FILE_THRESHOLD_DAYS}天）")
    parser.add_argument("--large-mb", type=float, default=LARGE_FILE_THRESHOLD_MB,
                        help=f"大文件MB阈值（默认{LARGE_FILE_THRESHOLD_MB}MB）")
    parser.add_argument("--max-depth", type=int, default=5,
                        help="最大扫描深度（默认5）")
    parser.add_argument("--quick", action="store_true",
                        help="快速模式（扫描更少文件）")
    parser.add_argument("--exclude", default=None,
                        help="排除关键词，逗号分隔，如 'hfish,WPS,test'")
    parser.add_argument("--output", "-o", default=None,
                        help="输出JSON文件路径（默认stdout）")

    args = parser.parse_args()

    # 解析排除关键词
    exclude_keywords = None
    if args.exclude:
        exclude_keywords = [kw.strip() for kw in args.exclude.split(",") if kw.strip()]

    result = scan_path(
        args.path,
        old_days=args.old_days,
        large_mb=args.large_mb,
        max_depth=args.max_depth,
        quick_mode=args.quick,
        exclude_keywords=exclude_keywords,
    )

    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"扫描结果已保存到: {args.output}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
