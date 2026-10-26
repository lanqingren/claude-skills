#!/usr/bin/env python3
"""交付自动归档：删_tmp/ → 打包zip → 移到归档目录"""
import os, sys, shutil, zipfile
from pathlib import Path

ARCHIVE_DIR = Path("C:/Users/Lein/Desktop/LW迭代库/项目")

def archive(project_dir: str):
    project = Path(project_dir).resolve()
    if not project.exists():
        print(f"❌ 项目目录不存在: {project}")
        sys.exit(1)
    
    # 1. 删除 _tmp/
    tmp = project / "_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
        print(f"🗑️  已删除 _tmp/")
    
    # 2. 打包
    zip_path = project.parent / f"{project.name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in project.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(project.parent))
    print(f"📦 已打包: {zip_path.name} ({zip_path.stat().st_size/1024/1024:.1f}MB)")
    
    # 3. 移动到归档目录
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE_DIR / zip_path.name
    if dest.exists():
        dest.unlink()
    shutil.move(str(zip_path), str(dest))
    print(f"📁 已归档到: {dest}")
    
    # 4. 清理项目目录
    shutil.rmtree(project)
    print(f"🧹 已清理项目目录")
    print(f"✅ 交付归档完成")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python archive_project.py <项目目录路径>")
        sys.exit(1)
    archive(sys.argv[1])
