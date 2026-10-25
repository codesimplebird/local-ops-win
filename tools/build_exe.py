#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyInstaller onedir 打包：产出免 Python 安装的总控台独立目录 + zip。

布局策略：onedir 产物 exe 之外，把 VERSION、static/、tools/win_anchor.py、
licenses/ 与 README.md 直接铺设在 exe 同目录（与源码树同构）。运行时
BASE_DIR = exe 目录，静态资源/锚点脚本按源码树的相对位置寻址，不需要
_MEIPASS 数据寻址；win_anchor 保持与开发形态同一份文件（单一事实来源）。

运行时代码仍是纯 Python 标准库；PyInstaller 只是构建期依赖
（requirements-dev.txt），不违反零第三方运行时依赖的约束。
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
EXE_NAME = "Console"
LAYOUT_ITEMS = (
    "VERSION",
    "README.md",
    "static",
    "licenses",
)


def fail(message: str) -> None:
    raise SystemExit(message)


def read_version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        fail("无法读取 VERSION：%s" % exc)


def run_pyinstaller(dist: Path) -> Path:
    icon = ROOT / "static" / "assets" / "favicon.ico"
    if not icon.is_file():
        icon = ROOT / "static" / "assets" / "favicon-32.png"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onedir", "--noconsole",
        "--name", EXE_NAME,
        "--icon", str(icon),
        "--distpath", str(dist),
        "--workpath", str(ROOT / "build" / "exe"),
        "--specpath", str(ROOT / "build" / "exe"),
        str(ROOT / "server.py"),
    ]
    print("运行 PyInstaller …")
    result = subprocess.run(args, cwd=str(ROOT))
    if result.returncode != 0:
        fail("PyInstaller 构建失败（exit %d）" % result.returncode)
    app_dir = dist / EXE_NAME
    exe = app_dir / ("%s.exe" % EXE_NAME)
    if not exe.is_file():
        fail("未找到构建产物：%s" % exe)
    return app_dir


def install_layout(app_dir: Path) -> None:
    """把运行期资源铺设到 exe 同目录（与源码树同构）。"""
    for name in LAYOUT_ITEMS:
        source = ROOT / name
        target = app_dir / name
        if not source.exists():
            fail("打包资源缺失：%s" % source)
        if target.exists():
            shutil.rmtree(target) if source.is_dir() else target.unlink()
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    anchor = app_dir / "tools" / "win_anchor.py"
    anchor.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "tools" / "win_anchor.py", anchor)
    for required in (app_dir / "VERSION",
                     app_dir / "static" / "index.html",
                     app_dir / "static" / "app.js",
                     anchor):
        if not required.is_file():
            fail("布局校验失败：%s" % required)


def zip_dir(app_dir: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(app_dir.rglob("*")):
            zf.write(path, path.relative_to(app_dir.parent))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="构建总控台 Windows 独立发行包（PyInstaller onedir）")
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        fail("未安装 PyInstaller：pip install -r requirements-dev.txt")

    version = read_version()
    app_dir = run_pyinstaller(args.dist)
    install_layout(app_dir)

    output = args.dist / ("Console-win64-%s.zip" % version)
    zip_dir(app_dir, output)
    checksum = sha256(output)
    (output.with_suffix(output.suffix + ".sha256")).write_text(
        "%s  %s\n" % (checksum, output.name), encoding="utf-8", newline="\n")
    print("已生成 %s" % output)
    print("SHA-256 %s" % checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
