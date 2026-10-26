"""Automated test package for the console project."""
import functools
import os
import tempfile


@functools.lru_cache(maxsize=1)
def windows_symlink_available():
    """Windows 非管理员且未开启开发者模式时 os.symlink 抛 WinError 1314；
    CI 以管理员运行可以创建，本地普通终端不行。依赖符号链接的测试用它跳过。"""
    if os.name != "nt":
        return True
    try:
        with tempfile.TemporaryDirectory() as td:
            os.symlink(os.path.join(td, "missing"), os.path.join(td, "link"))
        return True
    except OSError:
        return False
