#!/usr/bin/env python3
"""
垃圾清理执行脚本 - delete_trash.py
读取垃圾桶.md，解析其中的文件路径，逐个删除（移到回收站）
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Windows 回收站支持
try:
    import ctypes
    HAS_CTYPES = True
except ImportError:
    HAS_CTYPES = False


def send_to_recycle_bin(filepath: str) -> dict:
    """将文件移到回收站（Windows）"""
    result = {"path": filepath, "status": "unknown", "message": ""}

    if not os.path.exists(filepath):
        result["status"] = "not_found"
        result["message"] = "文件不存在，可能已被删除"
        return result

    try:
        # Windows: 使用 SHFileOperation 移到回收站
        if sys.platform == "win32" and HAS_CTYPES:
            # 使用 ctypes 调用 SHFileOperationW
            from ctypes import wintypes

            class SHFILEOPSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("wFunc", wintypes.UINT),
                    ("pFrom", ctypes.c_wchar_p),
                    ("pTo", ctypes.c_wchar_p),
                    ("fFlags", wintypes.WORD),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", wintypes.LPVOID),
                    ("lpszProgressTitle", ctypes.c_wchar_p),
                ]

            FO_DELETE = 3
            FOF_ALLOWUNDO = 0x40
            FOF_NOCONFIRMATION = 0x10
            FOF_SILENT = 0x04

            fileop = SHFILEOPSTRUCT()
            fileop.hwnd = 0
            fileop.wFunc = FO_DELETE
            # pFrom 需要双 \0 结尾
            fileop.pFrom = filepath + "\0\0"
            fileop.pTo = None
            fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
            fileop.fAnyOperationsAborted = False
            fileop.hNameMappings = None
            fileop.lpszProgressTitle = None

            ret = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
            if ret == 0:
                result["status"] = "recycled"
                result["message"] = "已移到回收站"
            else:
                # 回收站失败，尝试直接删除
                result["status"] = "recycle_failed"
                result["message"] = f"移到回收站失败(错误码{ret})，跳过"
        else:
            # 非 Windows：直接删除
            if os.path.isdir(filepath):
                import shutil
                shutil.rmtree(filepath)
            else:
                os.remove(filepath)
            result["status"] = "deleted"
            result["message"] = "已直接删除"
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def delete_file_directly(filepath: str) -> dict:
    """直接删除文件（不经过回收站）"""
    result = {"path": filepath, "status": "unknown", "message": ""}

    if not os.path.exists(filepath):
        result["status"] = "not_found"
        result["message"] = "文件不存在，可能已被删除"
        return result

    try:
        if os.path.isdir(filepath):
            import shutil
            shutil.rmtree(filepath)
        else:
            os.remove(filepath)
        result["status"] = "deleted"
        result["message"] = "已删除"
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)

    return result


def parse_trash_md(md_path: str) -> list:
    """解析垃圾桶.md，提取所有文件路径"""
    paths = []
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    for line in content.split("\n"):
        line = line.strip()
        # 匹配行内包含路径的行（以 - 开头的列表项，或包含盘符的行）
        # 路径格式：C:\xxx 或 \\xxx 或 /xxx
        # 从 markdown 行中提取路径
        import re
        # 匹配 Windows 绝对路径
        win_paths = re.findall(r'[A-Za-z]:\\[^\s\]"\'\`|<>]+', line)
        for p in win_paths:
            # 清理尾部标点
            p = p.rstrip(".,;:)]}\"'")
            if p not in paths:
                paths.append(p)

    return paths


def main():
    parser = argparse.ArgumentParser(description="垃圾清理执行工具")
    parser.add_argument("trash_md", help="垃圾桶.md 文件路径")
    parser.add_argument("--no-recycle", action="store_true",
                        help="直接删除而非移到回收站")
    parser.add_argument("--dry-run", action="store_true",
                        help="只列出要删除的文件，不实际删除")
    parser.add_argument("--output", "-o", default=None,
                        help="输出结果JSON路径")

    args = parser.parse_args()

    if not os.path.exists(args.trash_md):
        print(f"错误: 垃圾桶文件不存在: {args.trash_md}")
        sys.exit(1)

    paths = parse_trash_md(args.trash_md)
    if not paths:
        print("垃圾桶.md 中未找到有效路径")
        sys.exit(0)

    print(f"找到 {len(paths)} 个待清理路径")

    results = []
    delete_fn = delete_file_directly if args.no_recycle else send_to_recycle_bin

    for i, p in enumerate(paths):
        if args.dry_run:
            exists = "✓" if os.path.exists(p) else "✗"
            print(f"  [{exists}] {p}")
            results.append({"path": p, "status": "dry_run", "exists": os.path.exists(p)})
        else:
            r = delete_fn(p)
            results.append(r)
            status_icon = {
                "recycled": "♻️",
                "deleted": "🗑️",
                "not_found": "⚠️",
                "error": "❌",
                "recycle_failed": "⚠️",
            }.get(r["status"], "?")
            print(f"  {status_icon} {r['status']}: {p}")
            if r["message"]:
                print(f"      {r['message']}")

    # 汇总
    success = sum(1 for r in results if r["status"] in ("recycled", "deleted", "not_found"))
    failed = sum(1 for r in results if r["status"] in ("error", "recycle_failed"))

    summary = {
        "total": len(results),
        "success": success,
        "failed": failed,
        "results": results,
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")

    print(f"\n清理完成: 成功 {success}/{len(results)}, 失败 {failed}")


if __name__ == "__main__":
    main()
