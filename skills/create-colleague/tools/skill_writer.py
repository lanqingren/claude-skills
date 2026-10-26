#!/usr/bin/env python3
"""
Skill 文件写入器

负责将生成的 work.md、persona.md 写入到正确的目录结构，
并生成 meta.json 和完整的 SKILL.md。

用法：
    python3 skill_writer.py --action create --slug zhangsan --meta meta.json \
        --work work_content.md --persona persona_content.md \
        --base-dir ./colleagues

    python3 skill_writer.py --action update --slug zhangsan \
        --work-patch work_patch.md --persona-patch persona_patch.md \
        --base-dir ./colleagues

    python3 skill_writer.py --action list --base-dir ./colleagues
"""

from __future__ import annotations

import json
import shutil
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


SKILL_MD_TEMPLATE = """\
---
name: colleague_{slug}
description: {name}，{identity}
user-invocable: true
---

# {name}

{identity}

---

## PART A：工作能力

{work_content}

---

## PART B：人物性格

{persona_content}

---

## 运行规则

接收到任何任务或问题时：

1. **先由 PART B 判断**：你会不会接这个任务？用什么态度接？
2. **再由 PART A 执行**：用你的技术能力和工作方法完成任务
3. **输出时保持 PART B 的表达风格**：你说话的方式、用词习惯、句式

**PART B 的 Layer 0 规则永远优先，任何情况下不得违背。**
"""


def read_utf8_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json_file(path: Path) -> dict:
    return json.loads(read_utf8_text(path))


def slugify(name: str) -> str:
    """
    将姓名转为 slug。
    优先尝试 pypinyin（如已安装），否则 fallback 到简单处理。
    """
    # 尝试用 pypinyin 转拼音
    try:
        from pypinyin import lazy_pinyin
        parts = lazy_pinyin(name)
        slug = "_".join(parts)
    except ImportError:
        # fallback：保留 ASCII 字母数字，中文直接去掉
        import unicodedata
        result = []
        for char in name.lower():
            cat = unicodedata.category(char)
            if char.isascii() and (char.isalnum() or char in ("-", "_")):
                result.append(char)
            elif char == " ":
                result.append("_")
            # 中文字符跳过（无 pypinyin 时无法转换）
        slug = "".join(result)

    # 清理：去掉连续下划线，首尾下划线
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug if slug else "colleague"


def validate_slug(slug: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", slug):
        raise ValueError(
            "Invalid slug. Use only lowercase letters, numbers, hyphens, and underscores."
        )
    return slug


def resolve_skill_dir(base_dir: Path, slug: str) -> Path:
    resolved_base = base_dir.expanduser().resolve()
    skill_dir = (resolved_base / validate_slug(slug)).resolve()
    skill_dir.relative_to(resolved_base)
    return skill_dir


def build_identity_string(meta: dict) -> str:
    """从 meta 构建身份描述字符串"""
    profile = meta.get("profile", {})
    parts = []

    company = profile.get("company", "")
    level = profile.get("level", "")
    role = profile.get("role", "")

    if company:
        parts.append(company)
    if level:
        parts.append(level)
    if role:
        parts.append(role)

    identity = " ".join(parts) if parts else "同事"

    mbti = profile.get("mbti", "")
    if mbti:
        identity += f"，MBTI {mbti}"

    return identity


def create_skill(
    base_dir: Path,
    slug: str,
    meta: dict,
    work_content: str,
    persona_content: str,
) -> Path:
    """创建新的同事 Skill 目录结构"""

    skill_dir = resolve_skill_dir(base_dir, slug)
    skill_dir.mkdir(parents=True, exist_ok=True)

    # 创建子目录
    (skill_dir / "versions").mkdir(exist_ok=True)
    (skill_dir / "knowledge" / "docs").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "messages").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "emails").mkdir(parents=True, exist_ok=True)

    # 写入 work.md
    (skill_dir / "work.md").write_text(work_content, encoding="utf-8")

    # 写入 persona.md
    (skill_dir / "persona.md").write_text(persona_content, encoding="utf-8")

    # 生成并写入 SKILL.md
    name = meta.get("name", slug)
    identity = build_identity_string(meta)

    skill_md = SKILL_MD_TEMPLATE.format(
        slug=slug,
        name=name,
        identity=identity,
        work_content=work_content,
        persona_content=persona_content,
    )
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 写入 work-only skill
    work_only = (
        f"---\nname: colleague_{slug}_work\n"
        f"description: {name} 的工作能力（仅 Work，无 Persona）\n"
        f"user-invocable: true\n---\n\n{work_content}\n"
    )
    (skill_dir / "work_skill.md").write_text(work_only, encoding="utf-8")

    # 写入 persona-only skill
    persona_only = (
        f"---\nname: colleague_{slug}_persona\n"
        f"description: {name} 的人物性格（仅 Persona，无工作能力）\n"
        f"user-invocable: true\n---\n\n{persona_content}\n"
    )
    (skill_dir / "persona_skill.md").write_text(persona_only, encoding="utf-8")

    # 写入 meta.json
    now = datetime.now(timezone.utc).isoformat()
    meta["slug"] = slug
    meta.setdefault("created_at", now)
    meta["updated_at"] = now
    meta["version"] = "v1"
    meta.setdefault("corrections_count", 0)

    (skill_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return skill_dir


def update_skill(
    skill_dir: Path,
    work_patch: Optional[str] = None,
    persona_patch: Optional[str] = None,
    correction: Optional[dict] = None,
) -> str:
    """更新现有 Skill，先存档当前版本，再写入更新"""

    meta_path = skill_dir / "meta.json"
    meta = read_json_file(meta_path)

    current_version = meta.get("version", "v1")
    try:
        version_num = int(current_version.lstrip("v").split("_")[0]) + 1
    except ValueError:
        version_num = 2
    new_version = f"v{version_num}"

    # 存档当前版本
    version_dir = skill_dir / "versions" / current_version
    version_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("SKILL.md", "work.md", "persona.md"):
        src = skill_dir / fname
        if src.exists():
            shutil.copy2(src, version_dir / fname)

    # 应用 work patch
    if work_patch:
        current_work = read_utf8_text(skill_dir / "work.md")
        new_work = current_work + "\n\n" + work_patch
        (skill_dir / "work.md").write_text(new_work, encoding="utf-8")

    # 应用 persona patch 或 correction
    if persona_patch or correction:
        current_persona = read_utf8_text(skill_dir / "persona.md")

        if correction:
            correction_line = (
                f"\n- [{correction.get('scene', '通用')}] "
                f"不应该 {correction['wrong']}，应该 {correction['correct']}"
            )
            target = "## Correction 记录"
            if target in current_persona:
                insert_pos = current_persona.index(target) + len(target)
                # 跳过紧跟的空行和"暂无"占位行
                rest = current_persona[insert_pos:]
                skip = "\n\n（暂无记录）"
                if rest.startswith(skip):
                    rest = rest[len(skip):]
                new_persona = current_persona[:insert_pos] + correction_line + rest
            else:
                new_persona = (
                    current_persona
                    + f"\n\n## Correction 记录\n{correction_line}\n"
                )
            meta["corrections_count"] = meta.get("corrections_count", 0) + 1
        else:
            new_persona = current_persona + "\n\n" + persona_patch

        (skill_dir / "persona.md").write_text(new_persona, encoding="utf-8")

    # 重新生成 SKILL.md
    work_content = read_utf8_text(skill_dir / "work.md")
    persona_content = read_utf8_text(skill_dir / "persona.md")
    name = meta.get("name", skill_dir.name)
    identity = build_identity_string(meta)

    skill_md = SKILL_MD_TEMPLATE.format(
        slug=skill_dir.name,
        name=name,
        identity=identity,
        work_content=work_content,
        persona_content=persona_content,
    )
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # 更新 meta
    meta["version"] = new_version
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return new_version


def list_colleagues(base_dir: Path) -> list:
    """列出所有已创建的同事 Skill"""
    colleagues = []

    if not base_dir.exists():
        return colleagues

    for skill_dir in sorted(base_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        meta_path = skill_dir / "meta.json"
        if not meta_path.exists():
            continue

        try:
            meta = read_json_file(meta_path)
        except Exception:
            continue

        colleagues.append({
            "slug": meta.get("slug", skill_dir.name),
            "name": meta.get("name", skill_dir.name),
            "identity": build_identity_string(meta),
            "version": meta.get("version", "v1"),
            "updated_at": meta.get("updated_at", ""),
            "corrections_count": meta.get("corrections_count", 0),
        })

    return colleagues


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill 文件写入器")
    parser.add_argument("--action", required=True, choices=["create", "update", "list"])
    parser.add_argument("--slug", help="同事 slug（用于目录名）")
    parser.add_argument("--name", help="同事姓名")
    parser.add_argument("--meta", help="meta.json 文件路径")
    parser.add_argument("--work", help="work.md 内容文件路径")
    parser.add_argument("--persona", help="persona.md 内容文件路径")
    parser.add_argument("--work-patch", help="work.md 增量更新内容文件路径")
    parser.add_argument("--persona-patch", help="persona.md 增量更新内容文件路径")
    parser.add_argument(
        "--base-dir",
        default="./colleagues",
        help="同事 Skill 根目录（默认：./colleagues）",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()

    if args.action == "list":
        colleagues = list_colleagues(base_dir)
        if not colleagues:
            print("暂无已创建的同事 Skill")
        else:
            print(f"已创建 {len(colleagues)} 个同事 Skill：\n")
            for c in colleagues:
                updated = c["updated_at"][:10] if c["updated_at"] else "未知"
                print(f"  [{c['slug']}]  {c['name']} — {c['identity']}")
                print(f"    版本: {c['version']}  纠正次数: {c['corrections_count']}  更新: {updated}")
                print()

    elif args.action == "create":
        if not args.slug and not args.name:
            print("错误：create 操作需要 --slug 或 --name", file=sys.stderr)
            sys.exit(1)

        meta: dict = {}
        if args.meta:
            meta = read_json_file(Path(args.meta))
        if args.name:
            meta["name"] = args.name

        try:
            slug = validate_slug(args.slug) if args.slug else slugify(meta.get("name", "colleague"))
        except ValueError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            sys.exit(1)

        work_content = ""
        if args.work:
            work_content = read_utf8_text(Path(args.work))

        persona_content = ""
        if args.persona:
            persona_content = read_utf8_text(Path(args.persona))

        skill_dir = create_skill(base_dir, slug, meta, work_content, persona_content)
        print(f"✅ Skill 已创建：{skill_dir}")
        print(f"   触发词：/{slug}")

    elif args.action == "update":
        if not args.slug:
            print("错误：update 操作需要 --slug", file=sys.stderr)
            sys.exit(1)

        try:
            skill_dir = resolve_skill_dir(base_dir, args.slug)
        except ValueError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            sys.exit(1)
        if not skill_dir.exists():
            print(f"错误：找不到 Skill 目录 {skill_dir}", file=sys.stderr)
            sys.exit(1)

        work_patch = read_utf8_text(Path(args.work_patch)) if args.work_patch else None
        persona_patch = read_utf8_text(Path(args.persona_patch)) if args.persona_patch else None

        new_version = update_skill(skill_dir, work_patch, persona_patch)
        print(f"✅ Skill 已更新到 {new_version}：{skill_dir}")


if __name__ == "__main__":
    main()
