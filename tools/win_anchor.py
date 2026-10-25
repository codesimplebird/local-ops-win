#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Windows 受控进程锚点（总控台专用，仅 Windows 使用）。

由 server.py 的 _start_app_windows 拉起：argv[1] 是本次启动的随机标记
（console-run:<token>），argv[2] 是用户在启动台保存的命令字符串。

行为等价于 macOS 端的外层 bash 包装：
1. 把用户命令写入临时 .cmd 批处理文件，再以 ``cmd /d /c`` 执行
   （cmd 对含引号命令行的解析规则与 POSIX 完全不同，批处理文件是
   唯一能原样执行任意命令的稳妥通道）；文件以系统区域编码写入，
   与 cmd 的解析一致；
2. 直接子进程退出后继续等到整棵进程树清空再退出（对应 bash 的 ``wait``），
   因此“脚本把服务放后台后自己退出”的场景下锚点仍是受控身份锚；
3. 以直接子进程的退出码退出，供总控台记录任务成功/失败。

总控台自身重启不影响本锚点：锚点独立存活，受控身份由命令行标记 +
PPID 后代树识别（Windows 子进程在父进程退出后仍保留原 PPID）。
"""

import ctypes
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

CREATE_NO_WINDOW = 0x08000000
POLL_SEC = 2.0
TH32CS_SNAPPROCESS = 0x00000002


def _batch_file(command):
    """写入临时 .cmd 文件，返回其路径。调用方负责删除。

    必须用 ANSI 代码页（mbcs）写入：cmd 解析 .cmd 文件永远走系统
    ANSI/OEM 代码页（中文系统为 GBK）。Python 开启 UTF-8 模式时
    locale.getpreferredencoding 返回 UTF-8，写出的中文路径会被 cmd
    读成乱码并报 exit 9009（命令未找到）。
    """
    fd, path = tempfile.mkstemp(prefix="console-", suffix=".cmd")
    with os.fdopen(fd, "w", encoding="mbcs", errors="replace",
                   newline="\r\n") as f:
        f.write("@echo off\r\n")
        f.write(command + "\r\n")
        f.write("exit /b %errorlevel%\r\n")
    return path


class _ProcessEntry32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_kernel32.Process32FirstW.restype = wintypes.BOOL
_kernel32.Process32FirstW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W)]
_kernel32.Process32NextW.restype = wintypes.BOOL
_kernel32.Process32NextW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(_ProcessEntry32W)]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

_INVALID_HANDLE = wintypes.HANDLE(-1).value


def _snapshot_children():
    """CreateToolhelp32Snapshot → {ppid: [pid, ...]}；失败返回 None。

    与 PowerShell CIM 等价的 pid/ppid 信息，但零子进程、毫秒级完成；
    每个运行中应用的锚点每 2 秒轮询一次，起 PowerShell 会成倍放大开销。
    """
    snap = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == _INVALID_HANDLE:
        return None
    entry = _ProcessEntry32W()
    entry.dwSize = ctypes.sizeof(_ProcessEntry32W)
    children = {}
    try:
        ok = _kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            pid = entry.th32ProcessID
            ppid = entry.th32ParentProcessID
            if pid > 0 and ppid > 0:
                children.setdefault(ppid, []).append(pid)
            ok = _kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        _kernel32.CloseHandle(snap)
    return children


def _live_descendants(root_pid):
    """root 是否有存活后代（沿 PPID 链完整遍历，含隔代）。

    children 按 PPID 值索引、不关心中间层是否存活，因此只要链上有存活的
    直接子进程，整条链（含隔代后代）都能找到。中间层全部死亡后链断裂、
    更深的孤儿不再可见——这是 Windows PPID 树与 macOS 进程组的已知差异，
    服务端受控识别（managed_pids）同为 PPID 树口径，两侧一致。
    快照查询失败时保守认为仍在运行。
    """
    children = _snapshot_children()
    if children is None:
        return True  # 查询失败时保守认为仍在运行
    stack = list(children.get(root_pid, []))
    seen = set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children.get(pid, []))
    return bool(seen)


def run(marker, command):
    """以锚点身份执行用户命令，返回退出码（供 server.py frozen 模式内联调用）。"""
    batch = _batch_file(command)
    try:
        proc = subprocess.Popen(
            ["cmd", "/d", "/c", batch],
            creationflags=CREATE_NO_WINDOW)
    except OSError:
        return 1
    try:
        code = proc.wait()
        try:
            while _live_descendants(proc.pid):
                time.sleep(POLL_SEC)
        except KeyboardInterrupt:
            pass
        return code if isinstance(code, int) else 1
    finally:
        try:
            os.remove(batch)
        except OSError:
            pass


def main():
    if len(sys.argv) < 3:
        return 1
    return run(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    sys.exit(main())
