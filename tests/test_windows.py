# -*- coding: utf-8 -*-
"""Windows 适配层测试（macOS 上整体跳过）。

覆盖：netstat/CIM 解析、cmd 引号、PPID 树（含环）、PEB cwd、
PID 存活判定、Windows 命令生成、锚点进程的真实启停生命周期。
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import server


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipIf(not server.IS_WIN, "Windows 适配层专属测试")
class WindowsParsingTests(unittest.TestCase):
    def test_netstat_parse(self):
        text = (
            "\n"
            "Active Connections\n\n"
            "  Proto  Local Address          Foreign Address        State           PID\n"
            "  TCP    0.0.0.0:9600           0.0.0.0:0              LISTENING       1234\n"
            "  TCP    127.0.0.1:8899         0.0.0.0:0              LISTENING       5678\n"
            "  TCP    [::1]:8765             [::]:0                 LISTENING       9012\n"
            "  TCP    127.0.0.1:54321        127.0.0.1:0            ESTABLISHED     3456\n"
            "  TCP    0.0.0.0:9601           0.0.0.0:0              LISTENING       abc\n"
        )
        found = server._parse_netstat_output(text)
        self.assertEqual(found[(1234, 9600)], {"0.0.0.0"})
        self.assertEqual(found[(5678, 8899)], {"127.0.0.1"})
        self.assertEqual(found[(9012, 8765)], {"::1"})
        self.assertNotIn((3456, 54321), found)  # 非 LISTENING 跳过
        self.assertNotIn((None, 9601), found)   # 非数字 PID 跳过

    def test_cim_json_parse(self):
        text = json.dumps([
            {"ProcessId": 1, "ParentProcessId": 0, "Name": "System",
             "ExecutablePath": None, "CommandLine": None,
             "CreationDate": "20250401090000.000000+480", "WorkingSetSize": 0,
             "UserModeTime": 0, "KernelModeTime": 0},
            {"ProcessId": 42, "ParentProcessId": 1, "Name": "python.exe",
             "ExecutablePath": "C:\\py\\python.exe", "CommandLine": "python -m http.server",
             "CreationDate": "2025-04-01T09:00:00Z", "WorkingSetSize": 1048576,
             "UserModeTime": 1562500000, "KernelModeTime": 312500000},
        ])
        table = server._parse_win_process_table_json(text)
        self.assertEqual(table[1]["ppid"], 0)
        self.assertEqual(table[42]["args"], "python -m http.server")
        self.assertEqual(table[42]["exe"], "C:\\py\\python.exe")
        self.assertEqual(table[42]["utime"], 1562500000)
        self.assertEqual(table[42]["ktime"], 312500000)
        self.assertEqual(server._parse_win_process_table_json(""), {})
        self.assertEqual(server._parse_win_process_table_json("not json"), {})

    def test_win_cpu_percent(self):
        # 1s 用户 + 1s 内核 / 2s 窗口 / 4 核 → 25.0
        self.assertEqual(
            server._win_cpu_percent(
                {"utime": 0, "ktime": 0},
                {"utime": 1e7, "ktime": 1e7}, 2.0, 4),
            25.0)
        # 单核满载 → 100.0；超限截断到 100
        self.assertEqual(
            server._win_cpu_percent(
                {"utime": 0, "ktime": 0},
                {"utime": 2e7, "ktime": 0}, 2.0, 1),
            100.0)
        self.assertEqual(
            server._win_cpu_percent(
                {"utime": 0, "ktime": 0},
                {"utime": 1e8, "ktime": 0}, 1.0, 1),
            100.0)
        # 计数器回退 / 时间窗无效 / 字段缺失 → 0
        self.assertEqual(
            server._win_cpu_percent(
                {"utime": 5e7, "ktime": 0},
                {"utime": 1e7, "ktime": 0}, 2.0, 4),
            0.0)
        self.assertEqual(
            server._win_cpu_percent(
                {"utime": 0, "ktime": 0},
                {"utime": 1e7, "ktime": 0}, 0.0, 4),
            0.0)
        self.assertEqual(
            server._win_cpu_percent(
                {"utime": None, "ktime": None},
                {"utime": 1e7, "ktime": 1e7}, 2.0, 4),
            0.0)

    def test_pgid_members_map_windows_roots(self):
        table = {
            1: {"ppid": 0}, 2: {"ppid": 1}, 3: {"ppid": 2}, 9: {"ppid": 0},
        }
        with mock.patch.object(server, "_win_process_table",
                               return_value=table) as fetch:
            # 只为受管锚点建树：条目数与 roots 一致，而非全系统每 pid 一棵
            self.assertEqual(server.pgid_members_map({1}),
                             {1: [1, 2, 3]})
            self.assertEqual(server.pgid_members_map({1, 9}),
                             {1: [1, 2, 3], 9: [9]})
            # 锚点已退出（不在表中）仍有条目：孤儿后代按 PPID 挂在锚点上
            self.assertEqual(server.pgid_members_map({77}), {77: [77]})
            # None 保持全量
            full = server.pgid_members_map()
            self.assertEqual(set(full), {1, 2, 3, 9})
            fetch.assert_called_with(fresh=False)

    def test_win_quote(self):
        self.assertEqual(server._win_quote("C:\\my dir\\job.py"),
                         '"C:\\my dir\\job.py"')
        self.assertEqual(server._win_quote('say "hi"'),
                         '"say ""hi"""')

    def test_win_parse_creation(self):
        from datetime import datetime, timedelta, timezone
        # PS 5.1 ConvertTo-Json 的实际输出（epoch 毫秒，JSON 转义 \/）
        self.assertAlmostEqual(
            server._win_parse_creation("/Date(1743498000123)/"),
            1743498000.123, places=3)
        self.assertAlmostEqual(
            server._win_parse_creation("\\/Date(1743498000123)\\/"),
            1743498000.123, places=3)
        # ISO 8601（PS 7 / 显式字符串）
        expected_utc = datetime(2025, 4, 1, 9, 0, 0,
                                tzinfo=timezone.utc).timestamp()
        self.assertAlmostEqual(
            server._win_parse_creation("2025-04-01T09:00:00Z"),
            expected_utc, places=3)
        self.assertAlmostEqual(
            server._win_parse_creation("2025-04-01T17:00:00+08:00"),
            expected_utc, places=3)
        # DMTF：时区后缀单位是分钟（+480 = UTC+8），不得依赖本机时区
        expected_cn = datetime(
            2025, 4, 1, 9, 0, 0,
            tzinfo=timezone(timedelta(minutes=480))).timestamp()
        self.assertAlmostEqual(
            server._win_parse_creation("20250401090000.123456+480"),
            expected_cn + 0.123456, places=3)
        self.assertAlmostEqual(
            server._win_parse_creation("20250401090000+000"),
            expected_utc, places=3)
        self.assertIsNone(server._win_parse_creation(""))
        self.assertIsNone(server._win_parse_creation(None))
        self.assertIsNone(server._win_parse_creation("garbage"))
        self.assertIsNone(server._win_parse_creation("\\/Date(abc)\\/"))

    def test_win_tree_of_with_cycle(self):
        table = {
            1: {"ppid": 0}, 2: {"ppid": 1}, 3: {"ppid": 2},
            4: {"ppid": 3}, 5: {"ppid": 4},  # 5→4→3→2→1 正常链
            6: {"ppid": 7}, 7: {"ppid": 6},  # 环
        }
        tree = server._win_tree_of(1, table)
        self.assertEqual(tree[0], 1)
        self.assertEqual(set(tree), {1, 2, 3, 4, 5})
        cyclic = server._win_tree_of(6, table)
        self.assertEqual(set(cyclic), {6, 7})

    def test_win_command_for_script(self):
        cases = [
            ("C:\\path\\job.py", "py", 'py -3 -- "C:\\path\\job.py"'),
            ("C:\\path\\job.py", None, 'python -- "C:\\path\\job.py"'),
            ("C:\\path\\run.bat", None, '"C:\\path\\run.bat"'),
            ("C:\\path\\run.cmd", None, '"C:\\path\\run.cmd"'),
            ("C:\\path\\job.ps1", None,
             'powershell -NoProfile -ExecutionPolicy Bypass -File "C:\\path\\job.ps1"'),
            ("C:\\path\\job.sh", "bash", 'bash -- "C:\\path\\job.sh"'),
            ("C:\\path\\job.sh", None, '"C:\\path\\job.sh"'),
        ]
        for path, which_result, expected in cases:
            with self.subTest(path=path, which=which_result):
                def fake_which(name, which_result=which_result):
                    return which_result if which_result is not None else None
                with mock.patch.object(server.shutil, "which",
                                       side_effect=fake_which):
                    self.assertEqual(server.command_for_script(path), expected)


@unittest.skipIf(not server.IS_WIN, "Windows 适配层专属测试")
class WinProcTableCacheTests(unittest.TestCase):
    """进程表 TTL 缓存：单飞复用、失败不缓存、fresh 直通。"""

    def setUp(self):
        self._saved = dict(server._WIN_TABLE_CACHE)
        server._WIN_TABLE_CACHE.update(
            {"mono": 0.0, "table": None, "prev": None, "prev_mono": 0.0})

    def tearDown(self):
        server._WIN_TABLE_CACHE.clear()
        server._WIN_TABLE_CACHE.update(self._saved)

    @staticmethod
    def _cim_text(pid=42):
        return json.dumps([{
            "ProcessId": pid, "ParentProcessId": 1, "Name": "python.exe",
            "ExecutablePath": "C:\\py\\python.exe", "CommandLine": "python app.py",
            "CreationDate": "/Date(1743498000000)/", "WorkingSetSize": 1024,
            "UserModeTime": 0, "KernelModeTime": 0}])

    def test_ttl_cache_single_flight(self):
        with mock.patch.object(server, "_win_powershell",
                               return_value=self._cim_text()) as ps:
            first = server._win_process_table()
            second = server._win_process_table()
            self.assertEqual(ps.call_count, 1)
            self.assertIs(first, second)
            # fresh 直通缓存（写路径校验用）
            server._win_process_table(fresh=True)
            self.assertEqual(ps.call_count, 2)

    def test_failed_fetch_not_cached(self):
        replies = iter(["", self._cim_text()])
        with mock.patch.object(server, "_win_powershell",
                               side_effect=lambda *a, **k: next(replies)) as ps:
            self.assertEqual(server._win_process_table(), {})
            # 失败结果不落缓存：下一次普通调用重新查询并拿到数据
            table = server._win_process_table()
            self.assertEqual(ps.call_count, 2)
            self.assertIn(42, table)

    def test_history_keeps_previous_snapshot(self):
        replies = iter([self._cim_text(42), self._cim_text(43)])
        with mock.patch.object(server, "_win_powershell",
                               side_effect=lambda *a, **k: next(replies)):
            self.assertIsNone(server._win_table_history()[0])
            server._win_process_table()
            prev, _ = server._win_table_history()
            self.assertIsNone(prev)  # 首次成功没有历史
            server._win_process_table(fresh=True)
            prev, dt = server._win_table_history()
            self.assertIn(42, prev)
            self.assertGreaterEqual(dt, 0.0)


@unittest.skipIf(not server.IS_WIN, "Windows 适配层专属测试")
class WindowsProcessTests(unittest.TestCase):
    def test_pid_alive_detects_exit(self):
        proc = subprocess.Popen([sys.executable, "-c",
                                 "import time; time.sleep(30)"])
        try:
            self.assertTrue(server.pid_alive(proc.pid))
            proc.kill()
            proc.wait()
            deadline = time.time() + 3
            while time.time() < deadline and server.pid_alive(proc.pid):
                time.sleep(0.05)
            self.assertFalse(server.pid_alive(proc.pid))
        finally:
            if proc.poll() is None:
                proc.kill()

    def test_instance_lock_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "lock")
            first = server.acquire_instance_lock(path)
            second = server.acquire_instance_lock(path)
            self.assertIsNotNone(first)
            self.assertIsNone(second)
            server.release_instance_lock(first)
            third = server.acquire_instance_lock(path)
            self.assertIsNotNone(third)
            server.release_instance_lock(third)

    def test_win_cwd_reads_own_directory(self):
        cwd = server._win_cwd(server.SELF_PID)
        self.assertIsNotNone(cwd)
        self.assertEqual(os.path.realpath(cwd), os.path.realpath(os.getcwd()))

    def _config_with_app(self, directory, app):
        path = os.path.join(directory, "config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({**server.Config.DEFAULT, "apps": [app]}, f)
        return server.Config(path)

    def test_task_exit_code_survives_cmd_wrapper(self):
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.object(server, "LOGS_DIR", td):
            app = {**server.Config.APP_DEFAULT, "id": "win000001",
                   "kind": "task", "cwd": td,
                   "command": "python -c \"import sys; sys.exit(130)\""}
            ok, error, proc, _, _ = server.start_app(app)
            self.assertTrue(ok, error)
            try:
                self.assertEqual(proc.wait(timeout=20), 130)
            finally:
                if server.pid_alive(proc.pid):
                    server.stop_pid_tree(proc.pid)

    def test_service_lifecycle_managed_stop(self):
        port = _free_port()
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.object(server, "LOGS_DIR", td):
            base = {**server.Config.APP_DEFAULT, "id": "win000002",
                    "name": "Service", "cwd": td,
                    "command": "python -m http.server %d" % port}
            cfg = self._config_with_app(td, base)
            ok, error, proc, pgid, token = server.start_app(base)
            self.assertTrue(ok, error)
            server.persist_started_app(cfg, base["id"], proc, pgid, token)
            tracked = server.find_app(cfg.snapshot(), base["id"])
            try:
                deadline = time.time() + 10
                managed = []
                while time.time() < deadline and not managed:
                    time.sleep(0.3)
                    managed = server.managed_pids(tracked)
                self.assertTrue(managed, "受管进程未被识别")
                # token 校验：锚点命令行应带本次启动的随机标记
                snap = server.ps_snapshot({proc.pid})
                self.assertIn("console-run:" + token,
                              snap.get(proc.pid, {}).get("args", ""))
                # 受管身份与端口监听是独立事件：进程表缓存让身份识别明显
                # 变快，服务 bind 完成需要再等一等（轮询而非立即断言）
                listening = False
                deadline = time.time() + 10
                while time.time() < deadline and not listening:
                    time.sleep(0.3)
                    listening = port in {p for _, p in server.scan_listeners()}
                self.assertTrue(listening, "服务未在配置端口上监听")
                stopped, error = server.stop_app_and_clear(
                    cfg, tracked, timeout=10)
                self.assertTrue(stopped, error)
                self.assertFalse(server.pid_alive(proc.pid))
                self.assertNotIn(port, {p for _, p in server.scan_listeners()})
            finally:
                if server.pid_alive(proc.pid):
                    server.stop_pid_tree(proc.pid)
                # 等端口释放（子进程退出）再让 TemporaryDirectory 清理，
                # 避免子进程仍以 td 为工作目录/持有日志句柄时 rmdir 报
                # WinError 145（目录不是空的）
                deadline = time.time() + 5
                while time.time() < deadline:
                    if not server.pid_alive(proc.pid) and \
                            port not in {p for _, p in server.scan_listeners()}:
                        break
                    time.sleep(0.2)

    def test_win_launch_env_keeps_path_and_token(self):
        env = server.build_launch_env("win-secret", {"PATH": "C:\\bin"})
        self.assertEqual(env["PATH"], "C:\\bin")
        self.assertEqual(env[server.RUN_TOKEN_ENV], "win-secret")

    def test_redirect_console_output_with_closed_std_handles(self):
        """pythonw/隐藏窗口启动时 fd 1/2 可能无效：重定向不得崩溃，
        且后续输出必须落到 console.log（回归 --launcher OSError 9）。"""
        logs = tempfile.mkdtemp(prefix="console-logs-")
        saved_logs_dir = server.LOGS_DIR
        saved_fds = (os.dup(1), os.dup(2))
        try:
            server.LOGS_DIR = logs
            os.close(1)
            os.close(2)
            server.redirect_console_output()
            print("probe-stdout")
            sys.stderr.write("probe-stderr\n")
            sys.stderr.flush()
        finally:
            os.dup2(saved_fds[0], 1)
            os.dup2(saved_fds[1], 2)
            os.close(saved_fds[0])
            os.close(saved_fds[1])
            server.LOGS_DIR = saved_logs_dir
        with open(os.path.join(logs, "console.log"),
                  encoding="utf-8", errors="replace") as f:
            text = f.read()
        self.assertIn("probe-stdout", text)
        self.assertIn("probe-stderr", text)


if __name__ == "__main__":
    unittest.main()
