"""Render packaging_plan.json as the human-readable packaging_plan.md table.

Usage:
    python helpers/render_packaging_plan.py <edit/packaging_plan.json>
    python helpers/render_packaging_plan.py <edit/packaging_plan.json> -o <edit/packaging_plan.md>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def fmt_seconds(value: Any) -> str:
    return f"{float(value):.3f}"


def fmt_text(value: Any) -> str:
    if isinstance(value, list):
        return " / ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def escape_cell(value: Any) -> str:
    text = fmt_text(value)
    return text.replace("|", "\\|").replace("\n", "<br>")


def time_range(segment: dict[str, Any]) -> str:
    if segment.get("时间") is not None:
        return str(segment["时间"])
    if segment.get("start") is not None and segment.get("end") is not None:
        return f"{fmt_seconds(segment['start'])}-{fmt_seconds(segment['end'])}"
    return ""


def packaging_instruction(segment: dict[str, Any]) -> Any:
    return segment.get("包装指令", segment.get("内容", segment.get("画面文字", segment.get("on_screen_text", ""))))


def screen_mode(segment: dict[str, Any]) -> Any:
    return segment.get("画面模式", segment.get("组件", segment.get("component", "")))


def packaging_design(segment: dict[str, Any]) -> str:
    if segment.get("包装设计") is not None:
        return fmt_text(segment["包装设计"])
    if segment.get("动画与布局") is not None:
        return fmt_text(segment["动画与布局"])
    layout = fmt_text(segment.get("layout", ""))
    animation = fmt_text(segment.get("animation", ""))
    return f"{layout}<br>{animation}" if layout and animation else layout or animation


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# 全片包装节奏",
        "",
        "| 时间 | 包装指令 | 画面模式 | 包装设计 |",
        "|---|---|---|---|",
    ]

    for segment in plan.get("segments", []):
        when = escape_cell(time_range(segment))
        instruction = escape_cell(packaging_instruction(segment))
        mode = escape_cell(screen_mode(segment))
        design = escape_cell(packaging_design(segment))
        lines.append(f"| {when} | {instruction} | {mode} | {design} |")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render packaging_plan.json to packaging_plan.md")
    parser.add_argument("plan", type=Path, help="Path to packaging_plan.json")
    parser.add_argument("-o", "--output", type=Path, help="Output markdown path")
    args = parser.parse_args()

    plan_path = args.plan
    out_path = args.output or plan_path.with_suffix(".md")
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    out_path.write_text(render_markdown(plan), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
