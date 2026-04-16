# coding: utf-8

"""
PyInstaller 运行时启动器。

目的：
1) 修正工作目录，使得代码里的 `QIcon("resource/shoko.png")` 能正常找到资源；
2) 把打包进来的 `gif/magick.exe` 目录加入 `PATH`，让 `shutil.which("magick")` 命中。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sticker_maker.application import main


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _base_dir() -> Path:
    # PyInstaller onefile/onedir 解包后的根目录
    if _is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    # 开发运行时：resource 位于 app/resource，因此工作目录切到 app/
    return Path(__file__).resolve().parent


def _prepare_runtime() -> None:
    base_dir = _base_dir()
    os.chdir(base_dir)

    # 让 ffmpeg/magick 可通过 shutil.which(...) 被找到
    # 1) 首选项目内的 resource/exe（你目前的 exe 放在这里）
    exe_dir = base_dir / "resource" / "exe"
    if exe_dir.is_dir():
        os.environ["PATH"] = f"{exe_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    # 2) 兼容：如果你同时保留了 gif/magick.exe，则也加入 PATH
    gif_dir = base_dir / "gif" if _is_frozen() else Path(__file__).resolve().parent.parent / "gif"
    if gif_dir.is_dir():
        os.environ["PATH"] = f"{gif_dir}{os.pathsep}{os.environ.get('PATH', '')}"


def run() -> int:
    _prepare_runtime()
    return main()


if __name__ == "__main__":
    raise SystemExit(run())

