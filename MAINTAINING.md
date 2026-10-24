# 维护指南(Windows 社区版)

本仓库是 [laogou717/local-ops](https://github.com/laogou717/local-ops) 的 Windows 社区衍生版,基线为 [dontpanic1/local-ops](https://github.com/dontpanic1/local-ops) 的 `windows-support` 分支(上游 PR #2)。MIT 许可证,版权归原项目及贡献者所有。

## Remote 布局

| Remote | 指向 | 用途 |
| --- | --- | --- |
| `origin` | laogou717/local-ops | 上游,定期合并同步 |
| `dontpanic` | dontpanic1/local-ops | Windows 适配原始来源,仅追溯用 |

本仓库自己的长期分支是 `main`。

## 本机环境

- Python 3.12+(仅标准库,无第三方依赖)。要求 3.12 是因为代码使用了 `datetime.fromisoformat` 对 7 位小数秒等较新解析能力。
- 本机注意:系统 PATH 里的 `python` 曾是 Microsoft Store 占位符,`C:\Python313` 是残缺安装(只剩 dll),`py` 启动器注册表指向它。实际可用解释器通过 uv 安装在 `~/.local/bin/python3.12.exe`,并已复制出 `~/.local/bin/python.exe` shim 保证 `python` 可用。若日后重装 Python,删掉该 shim 避免遮蔽。
- Git Bash 中 `python` 已可用;cmd/PowerShell 用 `C:\Users\14834\.local\bin\python3.12.exe`。

## 日常命令

```bash
cd /c/dev/local-ops-win
python server.py                 # 启动,自动开浏览器 http://127.0.0.1:9600
python -m unittest discover -s tests -p "test_*.py"   # 全量测试(约 35s)
python tools/check_project.py    # 项目检查(含前端 JS 语法检查,需 node)
```

## 同步上游

```bash
git fetch origin
git log --oneline HEAD..origin/main    # 预览新提交
git merge origin/main
```

已知冲突热点与解决约定:

1. **server.py 项目识别区**(detect_project):上游以 `python3` 为基准加生态支持(poetry 等),本分支有 Windows 的 `python`/`python3` 适配与 uv 支持。合并时融合到同一选择链,当前优先级:`uv.lock` > `poetry.lock` > 系统解释器;变量沿用本分支的 `py_base`/`py_prefix`/`py_module`。
2. **README.md**:保留本仓库顶部的衍生版声明和双平台说明;上游把使用细节迁往 Wiki,本仓库保留完整章节便于离线查阅(章节内容以上游 Wiki 为准做同步)。
3. **CHANGELOG.md**:两边的 Added 条目都保留。

合并后必须跑全量测试再提交。上游测试若新增对命令前缀的断言,注意它默认 `python3`;本分支 Windows 路径产生 `python`,相关测试已按平台分支,合并时保持。

## 测试基线

- 全量 176 个测试,本机预期:**0 失败、13 跳过、3 个 ERROR**。
- 3 个 ERROR 全部是符号链接测试(`test_symlink_*`):创建符号链接需要开发者模式或管理员特权,普通环境必然失败,属环境限制而非代码缺陷。开启系统"开发者模式"后可归零。
- `tests/test_windows.py` 是 Windows 专属测试(解析器纯函数 + 真实进程生命周期);涉及 Windows 的改动必须在这里补回归测试。

## 已修复的 Windows 专属问题(改动时别回退)

1. **`--launcher` 崩溃(OSError 9)**:`redirect_console_output` 在标准句柄缺失(pythonw、隐藏窗口启动)时,`os.open` 会占用刚腾空的 fd 1/2,`dup2` 变自别名空操作、`finally` 误关标准句柄。现先 dup 两次腾挪到高位,并对 `msvcrt.setmode(1/2)` 加守卫;`sys.stdout` 为 None 时重建输出流。
2. **PS 5.1 下 uptime 恒为 0**:Windows PowerShell 5.1 的 `ConvertTo-Json` 把 CIM DateTime 序列化为 `/Date(<epoch-ms>)/`,旧解析器只认 ISO/DMTF。`_win_parse_creation` 现覆盖三种格式;DMTF 时区后缀单位是分钟(`+480` = UTC+8),按带时区换算、不依赖本机时区。
3. **netstat 解析**:按列位置解析、不读表头,中文/非英文系统表头本地化无影响;IPv6 分区索引(`[fe80::1%12]`)与非数字 PID 均已处理。`run_cmd` 用 `errors="replace"` 解码,GBK 输出安全。

## 修改规范

- 保持纯 Python 标准库,不引入第三方运行时依赖(上游 PR #3 的 pywin32/psutil 方案被明确否决)。
- Windows 进程管理改动注意三重校验语义:受控判定 = 锚点进程 + `console-run:<token>` 命令行标记 + PPID 后代树;停止先优雅 `taskkill /T`,失败才升级 `/F`;绝不按端口杀进程。
- 数据目录 `%APPDATA%\总控台`,日志 `%LOCALAPPDATA%\总控台\Logs`,可用 `CONSOLE_DATA_DIR`/`CONSOLE_LOG_DIR` 覆盖。

## 后续待办(优先级从高到低)

1. 打包发布:PyInstaller onedir 或 zip + `start.bat`,可参考上游 PR #3 的可复现构建清单。
2. 开机自启安装脚本(计划任务或 `shell:startup` 快捷方式,替代手动放 vbs)。
3. 性能:`/api/state` 每 2 秒轮询会起多个子进程(netstat/CIM),可做监听缓存与增量采样。
4. 服务列表可考虑加当前用户过滤,减少 SYSTEM 服务噪音(上游 macOS 版行为)。
