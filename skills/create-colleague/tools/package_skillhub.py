#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


INCLUDE_PATHS = [
    "SKILL.md",
    "README.md",
    "README_EN.md",
    "INSTALL.md",
    "requirements.txt",
    "SKILLHUB_UPLOAD.md",
    "prompts",
    "tools",
]
EXCLUDE_NAMES = {
    "__pycache__",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
}


def iter_files(root: Path):
    for relative in INCLUDE_PATHS:
        path = root / relative
        if not path.exists():
            continue
        if path.is_file():
            yield path
            continue
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in EXCLUDE_NAMES for part in file_path.parts):
                continue
            if file_path.suffix in EXCLUDE_SUFFIXES:
                continue
            yield file_path


def build_zip(output_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in iter_files(root):
            archive.write(file_path, file_path.relative_to(root))


def read_skill_version(root: Path) -> str:
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8-sig")
    match = re.search(r'^version:\s*"([^"]+)"', skill_text, flags=re.MULTILINE)
    if not match:
        raise ValueError("Unable to find version in SKILL.md")
    return match.group(1)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    version = read_skill_version(root)
    parser = argparse.ArgumentParser(
        description="Create a SkillHub-ready zip with SKILL.md at the archive root."
    )
    parser.add_argument(
        "--output",
        default=f"../dist/create-colleague-skillhub-v{version}.zip",
        help="Output zip path, relative to this script or absolute.",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (script_dir / output_path).resolve()

    build_zip(output_path)
    print(f"Created SkillHub package: {output_path}")


if __name__ == "__main__":
    main()
