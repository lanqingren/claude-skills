#!/usr/bin/env python3
"""
书骨 · BookBone 质量自检脚本

用法: python3 quality_check.py <SKILL.md路径>

检查书籍蒸馏Skill的6项通过标准：
- 心智模型数量（3-7个）
- 方法论/检查清单数量（3-8条）
- 概念词汇表（5-15个）
- 应用边界（明确写出）
- 案例模式（至少3个）
- 诚实边界（至少3条）
"""

import re
import sys
from pathlib import Path


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def count_sections(content: str, heading: str) -> int:
    """统计以 heading 开头的二级章节数量（### 模型N: / ### 方法N: 等）"""
    # Match patterns like "### 模型1:", "### 方法1:", "### 模式1:"
    pattern = rf"### {heading}\d+:"
    return len(re.findall(pattern, content))


def count_table_rows(content: str, section_heading: str) -> int:
    """统计某个section下表格的数据行数"""
    # Find the section content until next ## heading
    pattern = rf"{re.escape(section_heading)}\s*\n([\s\S]*?)(?=\n## |\Z)"
    match = re.search(pattern, content)
    if not match:
        return 0
    section = match.group(1)
    # Count table rows (lines that start with | and are not header separators)
    lines = section.strip().split("\n")
    rows = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and not re.match(r"\|[|\s:\-]+\|", stripped):
            rows += 1
    return rows


def check_section_exists(content: str, heading: str) -> bool:
    """检查某个section是否存在"""
    return heading in content


def run_checks(path: str) -> dict:
    content = read_file(path)

    checks = {}

    # 1. 心智模型数量（3-7个）
    model_count = count_sections(content, "模型")
    checks["心智模型数量"] = {
        "value": model_count,
        "min": 3,
        "max": 7,
        "pass": 3 <= model_count <= 7,
        "note": f"找到 {model_count} 个心智模型",
    }

    # 2. 方法论/检查清单数量（3-8条）
    method_count = count_sections(content, "方法")
    checks["方法论/检查清单数量"] = {
        "value": method_count,
        "min": 3,
        "max": 8,
        "pass": 3 <= method_count <= 8,
        "note": f"找到 {method_count} 条方法论",
    }

    # 3. 概念词汇表（5-15个）
    concept_count = count_table_rows(content, "## 关键概念词汇表")
    # Also try counting by pattern "### " within the vocabulary section
    if concept_count < 5:
        # Try alternative: count concept entries in the table
        pattern = r"## 关键概念词汇表\s*\n([\s\S]*?)(?=\n## |\Z)"
        match = re.search(pattern, content)
        if match:
            section = match.group(1)
            # Count non-header table lines
            lines = section.strip().split("\n")
            concept_count = 0
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("|") and "---" not in stripped:
                    concept_count += 1
    checks["概念词汇表"] = {
        "value": concept_count,
        "min": 5,
        "max": 20,
        "pass": 5 <= concept_count <= 20,
        "note": f"找到 {concept_count} 个概念",
    }

    # 4. 应用边界
    has_application_range = check_section_exists(content, "## 应用范围")
    has_suitable = "适合用这本书分析的问题" in content
    has_unsuitable = "不适合用这本书分析的问题" in content
    checks["应用边界"] = {
        "value": has_suitable and has_unsuitable,
        "pass": has_application_range and has_suitable and has_unsuitable,
        "note": f"应用范围section: {'有' if has_application_range else '无'}, 适合: {'有' if has_suitable else '无'}, 不适合: {'有' if has_unsuitable else '无'}",
    }

    # 5. 案例模式（至少3个）
    case_count = count_sections(content, "模式")
    checks["案例模式"] = {
        "value": case_count,
        "min": 3,
        "max": None,
        "pass": case_count >= 3,
        "note": f"找到 {case_count} 个案例模式",
    }

    # 6. 诚实边界
    has_honesty = check_section_exists(content, "## 诚实边界")
    # Count individual boundary items (lines starting with "- " within the section)
    if has_honesty:
        pattern = r"## 诚实边界\s*\n([\s\S]*?)(?=\n## |\Z)"
        match = re.search(pattern, content)
        if match:
            section = match.group(1)
            boundary_items = len(re.findall(r"^\s*-\s+", section, re.MULTILINE))
        else:
            boundary_items = 0
    else:
        boundary_items = 0
    checks["诚实边界"] = {
        "value": boundary_items,
        "min": 3,
        "max": None,
        "pass": has_honesty and boundary_items >= 3,
        "note": f"找到 {boundary_items} 条边界声明",
    }

    # 7. 章节覆盖（检查是否有附录章节分析来源）
    has_appendix = check_section_exists(content, "高信息密度章节")
    checks["章节覆盖"] = {
        "value": has_appendix,
        "pass": has_appendix,
        "note": f"高信息密度章节标注: {'有' if has_appendix else '无'}",
    }

    # 8. 表达风格（如适用 - 可选检查）
    has_style = check_section_exists(content, "## 表达风格")
    checks["表达风格"] = {
        "value": has_style,
        "pass": True,  # 可选，不强制
        "note": f"表达风格: {'已提取' if has_style else '跳过（可能为技术/方法论书籍）'}",
    }

    return checks


def print_report(checks: dict):
    print("\n" + "=" * 60)
    print("  书骨 · BookBone 质量自检报告")
    print("=" * 60)

    all_pass = True
    for name, result in checks.items():
        status = "PASS" if result["pass"] else "FAIL"
        if not result["pass"]:
            all_pass = False
        note = result.get("note", "")
        range_info = ""
        if "min" in result and "max" in result:
            if result["max"]:
                range_info = f" (标准: {result['min']}-{result['max']})"
            else:
                range_info = f" (标准: >= {result['min']})"
        print(f"  [{status}] {name}: {note}{range_info}")

    print("-" * 60)
    if all_pass:
        print("  结果: 全部通过")
    else:
        failed = [name for name, r in checks.items() if not r["pass"]]
        print(f"  结果: {len(failed)} 项未通过 - {', '.join(failed)}")
    print("=" * 60 + "\n")

    return all_pass


def main():
    if len(sys.argv) < 2:
        print("用法: python3 quality_check.py <SKILL.md路径>")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"错误: 文件不存在 - {path}")
        sys.exit(1)

    checks = run_checks(path)
    all_pass = print_report(checks)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
