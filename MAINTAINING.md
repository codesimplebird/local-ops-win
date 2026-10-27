# 维护指南(Windows 社区版)

本仓库是 [laogou717/local-ops](https://github.com/laogou717/local-ops) 的 Windows 社区衍生版,基线为 [dontpanic1/local-ops](https://github.com/dontpanic1/local-ops) 的 `windows-support` 分支(上游 PR #2)。MIT 许可证,版权归原项目及贡献者所有。

## Remote 布局

| Remote | 指向 | 用途 |
| --- | --- | --- |
| `origin` | codesimplebird/local-ops-win | 本仓库（Windows 社区版发布仓），v1.1.0 起在此发布 Release |
| `upstream` | laogou717/local-ops | 上游,定期合并同步 |
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

- 全量 193 个测试，本机预期:**0 失败、13 跳过、3 个 ERROR**。
- 3 个 ERROR 全部是符号链接测试(`test_symlink_*`):创建符号链接需要开发者模式或管理员特权,普通环境必然失败,属环境限制而非代码缺陷。开启系统"开发者模式"后可归零。
- `python tools/check_project.py` 本机同样因这 3 个符号链接 ERROR 计为失败（12 项检查中其余通过）；CI 的 Windows runner 以管理员运行可建符号链接，是绿的。
- `tests/test_windows.py` 是 Windows 专属测试(解析器纯函数 + 真实进程生命周期);涉及 Windows 的改动必须在这里补回归测试。
- 构建 exe 需 PyInstaller（PEP 668 环境用独立 venv）：`python -m venv %TEMP%\console-build-venv && .../Scripts/python -m pip install pyinstaller`，然后以该 venv 的 python 运行 `tools/build_exe.py`。

## 已修复的 Windows 专属问题(改动时别回退)

1. **`--launcher` 崩溃(OSError 9)**:`redirect_console_output` 在标准句柄缺失(pythonw、隐藏窗口启动)时,`os.open` 会占用刚腾空的 fd 1/2,`dup2` 变自别名空操作、`finally` 误关标准句柄。现先 dup 两次腾挪到高位,并对 `msvcrt.setmode(1/2)` 加守卫;`sys.stdout` 为 None 时重建输出流。打包形态(`--noconsole`)入口无条件重定向。
2. **PS 5.1 下 uptime 恒为 0**:Windows PowerShell 5.1 的 `ConvertTo-Json` 把 CIM DateTime 序列化为 `/Date(<epoch-ms>)/`,旧解析器只认 ISO/DMTF。`_win_parse_creation` 现覆盖三种格式;DMTF 时区后缀单位是分钟(`+480` = UTC+8),按带时区换算、不依赖本机时区。
3. **netstat 解析**:按列位置解析、不读表头,中文/非英文系统表头本地化无影响;IPv6 分区索引(`[fe80::1%12]`)与非数字 PID 均已处理。`run_cmd` 用 `errors="replace"` 解码,GBK 输出安全。
4. **PID 复用幽灵成员(1.1.0)**:孤儿进程 ppid 常指向已退出进程,PID 值被受管树成员复用时被误纳入成员表,「停止」等待被无关长命进程拖到超时。`_win_tree_of` 现按「后代创建时间不得早于父进程」过滤(任一侧时间不可解析保守保留)。taskkill 按真实 OS 树执行,本就不会误杀。
5. **受保护进程所有者判定(1.1.0)**:lsass 等 PPL 进程 OpenProcess 任何访问权都被拒,存活判定不能用 `pid_alive`,改用 CIM 进程表(跨用户可读)。提升权限的用户进程(ctypes 读不出所有者)由后台 CIM GetOwner 批量补查记忆化,不能直接当非本用户过滤。
6. **锚点批处理编码(1.1.0 发布当天)**:Python 开启 UTF-8 模式(uv 解释器)时 `locale.getpreferredencoding` 返回 UTF-8,而 cmd 解析 .cmd 永远走系统 ANSI 代码页——中文路径被读成乱码报 exit 9009。锚点批处理固定用 `mbcs` 写入。同理:`start.bat` 必须纯 ASCII + CRLF(cmd 按 ANSI 解析,.gitattributes 已强制 `.bat/.cmd` eol=crlf);非中文代码页系统上中文路径批处理 cmd 本身无法执行,产品按 errors=replace 降级。
7. **系统目录淹没进程名(1.1.0 发布次日)**:开机自启/托盘应用的 cwd 几乎都是 `C:\Windows\System32`,服务表格主标题优先取「目录末段」,Ollama 等服务在表格/TOP5 里全叫「System32」,用户按名字搜不到。`project_name` 现把家目录与系统目录(`_GENERIC_PROJECT_NAMES`,大小写不敏感,含反斜杠结尾)判为无项目名,前端各展示位回退进程名;`project` 是纯展示字段,不影响启停/认领逻辑(那两处用的是完整 cwd 路径)。
8. **符号链接测试在本地 Windows 报 WinError 1314**:非管理员且未开开发者模式时 `os.symlink` 被拒,CI 的 Windows runner 以管理员运行则可建。`tests/__init__.py` 的 `windows_symlink_available()` 统一探测,三个依赖符号链接的测试据此 skipIf,不算失败。
9. **启动器幽灵实例(1.1.0 发布次日)**:`find_console_instances` 按「argv 含 server.py + cwd 为项目目录」匹配,启动链上的包装层全部命中——uv 的 python shim(argv 就是 `python server.py …`,等待子进程期间一直活着)、bash/cmd/PowerShell(argv 以脚本文本或 -ArgumentList 形式携带 server.py 字样)——于是 `--launcher` 判定"已有实例",打开一个页面后静默退出,表现为**双击 start.bat 没反应**。修复双保险:`_console_argv_matches` 要求解释器本身(python*/py/pyw,打包形态为 exe 名)亲自运行 server.py;再排除自身 PPID 祖先链(≤10 层,祖先已退出时靠自身 ppid 仍可走一段)。调试此问题时的教训:PowerShell 的 CIM CreationDate 是本地时间;`win<NNNNNN>.log` 是**应用**日志不是总控台启动日志,别看错文件。
10. **监听家族合并的两个陷阱(同日)**:①Explorer.EXE 自身监听内部端口,而所有从开始菜单/桌面启动的应用都是它的后代——若不把系统壳(见 `_FAMILY_SHELL_ANCHORS`)在家族判定中透明穿透,Steam/WorkBuddy 等互不相干的服务会被并成一行(实测 12 个服务被吞);②子进程可与主成员共享同一监听端口(句柄复制,如 steamwebhelper),`extraPorts` 必须排除与主端口相同的项,否则主端口重复出现。

## 修改规范

- 保持纯 Python 标准库,不引入第三方运行时依赖(上游 PR #3 的 pywin32/psutil 方案被明确否决;PyInstaller 仅构建期,已入 requirements-dev.txt)。
- **前端改动必须浏览器实测**:node --check 与 check_project 的绑定检查只能抓语法/未绑定引用,抓不住 TDZ(模块级调用先于 const 声明)这类运行时错误——一旦某模块求值失败,整条 import 链(app.js 起)全灭,页面按钮全部无响应。实测方法:打开页面后控制台执行 `typeof window.__poll` 应为 `'function'`(模块链存活的全局哨兵),再点一遍新增交互。
- Windows 进程管理改动注意三重校验语义:受控判定 = 锚点进程 + `console-run:<token>` 命令行标记 + PPID 后代树;停止先优雅 `taskkill /T`,失败才升级 `/F`;绝不按端口杀进程。
- 进程全量快照走 `_win_process_table()`(1.2s TTL 缓存,`fresh=True` 绕过);写路径(启停校验)必须用即时表。
- 数据目录 `%APPDATA%\总控台`,日志 `%LOCALAPPDATA%\总控台\Logs`,可用 `CONSOLE_DATA_DIR`/`CONSOLE_LOG_DIR` 覆盖。

## 后续待办(优先级从高到低)

1. 自动更新检查(GitHub Release 比对 + 提示,不做静默自更新)。
2. exe 代码签名(SmartScreen 提示消除,需要证书,暂缓)。
3. `/api/state` 进一步增量采样(当前稳态每轮 1 个 PowerShell + 1 个 netstat,已够用)。
4. 关注进程(watched)列表同样按所有者过滤(当前仅服务监控过滤)。
