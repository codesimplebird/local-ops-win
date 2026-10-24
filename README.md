# 总控台(Windows 社区版)

**Preview / Alpha · 源码预览**

> 本仓库是 [laogou717/local-ops](https://github.com/laogou717/local-ops) 的社区 Windows 衍生版,基于 [dontpanic1 的双平台适配分支](https://github.com/dontpanic1/local-ops/tree/windows-support)(即上游 PR #2)建立,在同一份代码上运行 macOS 与 Windows。MIT 许可证,版权归原项目及贡献者所有。上游通过 `origin` remote 跟踪,Windows 特有问题的修复与维护在本仓库进行;维护方式见 [MAINTAINING.md](MAINTAINING.md)。

总控台是一个面向本地的服务与批处理任务快速启动、运行监测工具。它把常用项目命令、长期服务和一次性批处理任务集中到本地网页中，并用 Python 3 标准库提供只绑定回环地址的后端；前端是无构建、无 CDN 的原生 HTML/CSS/JavaScript。

> 总控台只服务当前 Mac 和当前用户，不是远程运维、多人协作或公网管理面板。它能以当前用户权限执行你保存的命令，请勿通过反向代理、SSH 隧道或端口映射暴露到不受信任的网络。当前仍为 Preview / Alpha 阶段，接口、配置格式和安装方式可能调整；`总控台.app` 是项目内启动器，不是可单独复制的自包含应用。

**📚 文档**：[使用手册](https://github.com/laogou717/local-ops/wiki/使用手册) · [数据与备份](https://github.com/laogou717/local-ops/wiki/数据与备份) · [故障排查](https://github.com/laogou717/local-ops/wiki/故障排查) · [开发者与发布指南](https://github.com/laogou717/local-ops/wiki/开发者与发布指南) · [Wiki 主页](https://github.com/laogou717/local-ops/wiki)

## 亮点

- 每 2 秒查看当前用户本地监听服务的 CPU、内存、运行时长与**启动者溯源**（Codex/Claude 等 AI 助手、VS Code/Cursor 等编辑器、终端或总控台）。
- 保存常用服务与批处理任务，集中启动、停止、重启、查日志与诊断；运行 token + 进程组 + UID 三重校验，不会因端口相同就杀掉外部进程。
- 选择工作区文件夹后只读识别项目启动命令（Node/pnpm、Hexo、Django/FastAPI、Go、Rust、静态站点等），不安装依赖、不执行项目代码。
- 新端口发现与一键加入启动台、全局命令面板 ⌘K、日志中心 ⌘J、Ops 指挥台单一主题（浅色/深色/跟随系统）、拖拽与键盘排序。

## 界面预览

以下截图使用脱敏演示数据，不包含真实用户名、目录、命令或服务信息。

| 启动台 | 服务监控 |
| --- | --- |
| ![Ops 指挥台 · 启动台](docs/screenshots/ops-launchpad.jpg) | ![Ops 指挥台 · 服务监控](docs/screenshots/ops-services.jpg) |

## 快速开始

- **macOS 12 或更高版本**，或 **Windows 10/11（64 位）**。
- Python 3.12。运行时仅使用 Python 标准库，无需安装任何第三方包。
- macOS 自带的 `ps`、`lsof`、`osascript` 等系统工具；Windows 自带的
  `netstat`、`taskkill`、`powershell`（PowerShell 5.1 已内置）。
- Safari、Chrome、Edge 或其他支持 ES Modules 的现代浏览器。

启动方式有三种，效果相同，按习惯选择：

| 方式 | 操作 | 适用场景 |
| --- | --- | --- |
| 双击应用 | 双击 `总控台.app` | macOS 日常使用。后台运行，无 Terminal 窗口和 Dock 图标 |
| 双击脚本 | 双击 `start.command`（macOS）/ `start.bat`（Windows） | 想在终端窗口里看实时输出 |
| 命令行 | `python3 server.py`（macOS）/ `py -3 server.py`（Windows），均可用 `[--no-browser] [--preferred-port 9603]` | 调试、脚本化或远程启动 |

首次打开互联网下载的 `总控台.app`，右键 → 打开（点「打开」），或执行 `xattr -dr com.apple.quarantine "总控台.app"`，只需一次。这是 macOS 对互联网下载应用的常规隔离提示，不是程序损坏；解压后请保持目录结构完整，不要单独移动 `总控台.app`。

启动后自动打开 `http://127.0.0.1:9600`，被占则尝试 9601–9609。实际地址看顶栏「重启 :9600」按钮，或终端输出 / `~/Library/Logs/总控台/console.log`。

## Windows 适配说明

总控台在 Windows 上以等价语义运行，平台差异如下：

- **受控进程模型**：Windows 没有进程组/信号。每个应用由一个小型 Python
  “锚点”进程承载（`tools/win_anchor.py`，命令行带随机 token），用户命令
  写入临时 `.cmd` 批处理文件后由 `cmd /c` 执行——这是 Windows 上能原样
  执行任意命令的唯一稳妥通道。受控身份 = 锚点 PID + token 命令行 +
  PPID 后代树；锚点会等到整棵进程树清空才退出（等价于 macOS 的 `wait`）。
- **停止语义**：Windows 没有 SIGTERM。点“停止”会先尝试 `taskkill /T`
  （仅对带窗口进程有效），失败自动升级为 `taskkill /T /F` 强制结束整棵
  进程树。因此被停止的应用不会收到优雅退出通知，正在写入的数据可能丢失。
- **进程扫描**：`lsof`/`ps` 换成 `netstat -ano -p tcp` 与
  PowerShell `Get-CimInstance Win32_Process`；CPU% 在 Windows 上
  暂不提供（置 0），内存使用 WorkingSet 占比。
- **工作目录读取**：通过 `NtQueryInformationProcess` 读 PEB（ctypes，
  只读）；同架构进程可读，被拒绝访问时该进程不显示目录。
- **文件选择框**：PowerShell + WinForms 原生对话框（目录/文件）。
- **系统通知**：任务完成通知由浏览器 Web Notification 实现，两平台一致。
- **数据目录**：Windows 默认 `%APPDATA%\总控台`（配置/图标）与
  `%LOCALAPPDATA%\总控台\Logs`（日志）；同样支持
  `CONSOLE_DATA_DIR`/`CONSOLE_LOG_DIR` 覆盖。Windows 无 POSIX 权限位，
  目录/文件安全由 NTFS ACL 保障（健康检查会自动跳过权限位校验）。
- **启动台自动识别**：Windows 上 Python 项目使用 `python`/`py -3` 运行器，
  并额外识别 `start.bat`/`dev.bat`/`start.cmd`/`start.ps1` 等启动脚本。

## 使用

左侧导航轨切换「启动台 / 服务监控」，右侧信息栏展示实时动态；所有数据每 2 秒自动刷新，断连时显示横幅提示。

- **启动台**：点「+ 添加服务」选择工作区，自动识别项目并给出候选命令（也可「选择脚本」或手动填写）；卡片大按钮启停（任务是运行/中止），右侧常显复制/日志/诊断/重启/编辑/删除；支持拖拽排序、键盘排序、分区筛选与批量停止。
- **服务监控**：概览卡 + 服务表格；页面打开期间新出现的未管理监听端口会单独提醒，可「加入启动台」（自动识别项目并原子认领进程）、「忽略并隐藏」或「暂时关闭」。
- **日志中心（⌘J）/ 设置中心 / 命令面板（⌘K）**：从导航轨或快捷键进入；命令面板支持全局搜索与全键盘操作。
- 红色按钮会结束进程或删除应用，需要二次确认。顶栏「重启 / 停止」控制的是总控台自身，**不会**停止启动台里已经运行的应用——它们是独立进程组，会继续运行。
- 选择批处理脚本时，总控台只保存脚本的绝对路径和生成的执行命令，不复制或托管脚本内容；脚本移动、改名或删除后任务会失效。

任务退出码约定：自然退出 `0` = 成功，其他非零 = 失败；脚本内用户主动取消请退出 `130`（显示「已取消」）；总控台按钮主动中止显示为「已中止」。此约定只用于 `task`，长期服务仍按普通退出处理。

### 服务监控（看这台 Mac 在跑什么）

- **概览卡**：在线服务/后台应用/总 CPU/总内存（带最近一分钟负载曲线）/端口警告/最后更新。
- **服务表格**：每个服务的 PID、端口、目录、负载、时长、状态，以及**启动者徽标**——溯源显示这个进程是哪个 AI 助手（Codex/Claude/Kimi 等）、编辑器（VS Code/Cursor 等）、终端或总控台启动的。点端口直接打开服务；行尾按钮可加入启动台、置顶、隐藏、展开完整命令或安全结束进程。
- **发现新端口**：页面打开期间新出现的监听端口会单独提醒，可一键「加入启动台」（自动识别项目并原子认领进程）、「忽略并隐藏」或「暂时关闭」。
- **后台与已隐藏**：系统/GUI 应用进程默认折叠在「应用后台」；被隐藏的服务可随时恢复。
- **关注的进程**：输入关键字（如 `ffmpeg`）回车，匹配进程实时列出。

### 日志中心（⌘J）

导航轨「日志中心」或快捷键 ⌘J（⌘L 是浏览器保留键）：所有应用按运行中优先排列，点开任意一行看实时日志；底部固定总控台自身日志入口。

### 设置中心

导航轨齿轮：任务完成通知开关（系统通知，切走页面也能收到）、外观三态（自动/浅色/深色）、版本/端口/工作目录/数据目录信息。

### 命令面板（⌘K）

全局搜索并执行：添加服务/任务、启动/停止/重启任意应用、打开页面、查看日志、切换视图、开关任务通知、查看总控台日志等，全键盘操作。

### 使用要点

- 红色按钮会结束进程或删除应用，需要二次确认。
- 批处理任务自然退出 `0` 表示成功，其他非零退出码表示失败；脚本内部用户主动取消请退出 `130`（显示为「已取消」）；总控台按钮主动中止单独显示为「已中止」。
- 选择批处理脚本时，总控台只保存脚本的绝对路径和生成的执行命令，不会复制或托管脚本内容。脚本移动、改名或删除后，任务会失效；建议将个人脚本放在长期稳定、会单独备份的自动化目录中。
- 停止总控台不会自动停止已启动的独立服务；配置里的应用、图标、关注关键字和隐藏/置顶标记都会保留。

### 批处理退出码约定

任务自然退出 `0` = 成功，其他非零 = 失败；脚本内部用户主动取消请退出 `130`（显示为「已取消」而非失败）；总控台按钮中止显示为「已中止」。Python 用 `raise SystemExit(130)`，Shell 用 `exit 130`，Node.js 设 `process.exitCode = 130`。此约定只用于 `task`，长期服务仍按普通退出处理。

### 新端口发现的基线规则

「服务监控」只提醒**页面打开后新出现**、尚未纳入启动台的本地服务。首次载入、页面从后台恢复、断线重连或总控台重启后的第一份状态只用于建立静默基线，不会把已有端口全部弹一遍。「忽略并隐藏」写入配置并可恢复；「暂时关闭」只影响当前页面会话。

## 数据、隐私与备份

运行数据与程序目录分离，默认放在 macOS 用户资料库：

| 路径 | 内容 | 备份建议 |
| --- | --- | --- |
| macOS `~/Library/Application Support/总控台/config.json`<br>Windows `%APPDATA%\总控台/config.json` | 应用命令、本地路径、端口、标记和运行识别信息 | 必须 |
| `config.json.bak` | 上一份已知良好的配置 | 必须 |
| `icons/` | 用户上传的图标和站点图标 | 按需 |
| macOS `~/Library/Logs/总控台/`<br>Windows `%LOCALAPPDATA%\总控台\Logs` | 应用与总控台运行日志 | 通常不需 |

目录权限会收紧为 `0700`，配置、图标和日志文件为 `0600`。这些文件仍可能含个人路径、完整 shell 命令和日志内容；不应进入 Git，也不应随发行包或故障报告对外传播。

### 旧版数据首次迁移

如果新目标目录尚不存在，首次启动会将项目内旧 `data/config.json{,.bak}` 和 `data/icons/` 安全复制到 Application Support，将 `data/logs/` 复制到 Library Logs。迁移使用临时目录后原子落位，并且：

- 旧 `data/` 始终保留，不会自动删除。
- 目标已存在时绝不覆盖或合并，避免把更新的用户数据换回旧版。
- 符号链接和非普通文件不会被复制。
- 显式设置 `CONSOLE_DATA_DIR` 或 `CONSOLE_LOG_DIR` 时，对应目录不执行旧数据自动迁移。

需要自定义路径时：

```bash
CONSOLE_DATA_DIR="/private/path/console-data" \
CONSOLE_LOG_DIR="/private/path/console-logs" \
python3 server.py
```

自定义值必须是非空的绝对路径，并指向总控台专用的非符号链接子目录；不要直接填 `/`、用户主目录或项目根目录。

### 备份

1. 不再执行新的启动、停止或编辑操作。
2. 停止总控台。
3. 将 `~/Library/Application Support/总控台/` 复制到受保护的备份目录。
4. 记录当前 `VERSION`，以便恢复时匹配配置格式。

### 恢复

1. 确保总控台已停止，并另存当前 `~/Library/Application Support/总控台/`。
2. 将备份中的 `config.json` 和 `icons/` 复制回对应位置，权限分别设为 `0600` 和 `0700`。
3. 重新启动，逐项确认命令、工作目录和端口。

如果主配置损坏，程序会验证 `config.json.bak` 并恢复主文件。如果两份都不可用，服务进入只读保护状态，不会用空配置覆盖它们。`config.json.bak` 保留的是每次修改之前的上一份良好配置，而不是主文件的同内容副本。

## 升级

1. 阅读 `CHANGELOG.md`，确认是否有配置或平台变更。
2. 停止总控台并完整备份 `~/Library/Application Support/总控台/`。
3. 用新版本替换程序文件；用户数据保持在 Library 目录中。
4. 运行 `make check`。
5. 启动后检查应用数量、主题、关注关键字和一个可控服务的完整启停。

配置包含 `schemaVersion`，启动时逐版执行显式、幂等迁移。新程序不会静默降级它不认识的更高 schema；回退程序时仍应同时恢复与该版本匹配的数据备份。

## 卸载

1. 如果不希望已启动的服务继续运行，先在启动台逐个停止它们。
2. 停止总控台。
3. 按需导出 `~/Library/Application Support/总控台/` 备份。
4. 将整个项目目录移到废纸篓。
5. 确认不再需要数据后，手动删除 `~/Library/Application Support/总控台/` 和 `~/Library/Logs/总控台/`。

程序不会安装系统启动项，卸载时也不会自动删除用户数据。

（上游已将使用细节迁往 [Wiki](https://github.com/laogou717/local-ops/wiki/使用手册)；本仓库为便于离线查阅保留了上述完整章节，内容以上游 Wiki 为准做同步。）

## 安全边界

- 只添加你已检查且信任的命令和工作目录；总控台能以当前用户权限执行保存的 shell 命令。
- 不要将服务绑定到 `0.0.0.0`，不要通过反向代理、SSH 隧道或端口映射对外暴露；不要在共享或不受信任的用户账户中运行。
- 不要把 `~/Library/Application Support/总控台/config.json`、日志或故障截图未经脱敏就上传。
- 本地回环绑定只是第一层边界，不能替代写接口的 Host/Origin/控制令牌防护；发布验收必须执行 [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) 中的安全项。

## 维护说明

总控台由作者个人维护：功能的新增、修改与完善以作者日常使用中的实际需求为准，迭代节奏不定；PR 不承诺审阅或合入。

如果你希望增加功能、修复问题或适配其他平台，欢迎 **Fork 本仓库自行修改**，并在 Discussions 中提交衍生版本说明。经过试用评估后，优秀的衍生版本会收录到下方 [社区衍生版本](#社区衍生版本) 列表推荐给大家；衍生版本由各自作者维护，未经原作者审阅或测试，使用前请自行评估。

## 社区衍生版本

以下衍生版本由社区贡献者各自维护，未经原作者审阅或测试，收录仅作推荐。提交新衍生版本或更新说明，请前往 Discussions。

| 衍生版本 | 说明 | 出处 |
| --- | --- | --- |
| Windows 10/11 适配（双平台运行） | 共享代码 + 平台分支收敛，不新增运行时依赖，含 Windows 专属测试与 CI | PR [#2](https://github.com/laogou717/local-ops/pull/2)（dontpanic1） |
| Windows 11 安全优先移植（Draft） | Job Objects、签名回执、CREATE_SUSPENDED 等更严格的进程所有权模型，含打包体系 | PR [#3](https://github.com/laogou717/local-ops/pull/3)（songconmaisaix31-design） |
| Windows 后端 `server_win.py` | 独立 Windows 后端（纯标准库），复用本仓库前端 | PR [#4](https://github.com/laogou717/local-ops/pull/4)（Hexvork） |
| sysops.py 跨平台抽象层方案 | psutil 唯一新增依赖，macOS 分支零改动，作者已在日常使用 | [Issue #1 提案](https://github.com/laogou717/local-ops/issues/1)（FL411） |

## 参与贡献

**推荐路径（不需要等待审阅）**：

1. Fork 本仓库，自行开发并长期维护自己的版本；
2. 阅读 [CONTRIBUTING.md](CONTRIBUTING.md)——安全校验不得削弱（回环绑定、当前 UID、run token、进程组）、一个 PR 只解决一个主题、提交前运行 `make check`、不提交个人路径/日志/未脱敏素材；
3. 在 Discussions 提交衍生版本说明（名称、定位、fork 地址）；
4. 经试用评估后，收录到上方「社区衍生版本」推荐列表。

Issue 与 PR 同样可以提交，欢迎讨论与参考，但不承诺审阅或合入（见「维护说明」）。行为规范见 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)；安全问题请按 [`SECURITY.md`](SECURITY.md) 私下报告，不要公开披露。

## 更多文档

- [Wiki 主页](https://github.com/laogou717/local-ops/wiki)：[使用手册](https://github.com/laogou717/local-ops/wiki/使用手册) / [数据与备份](https://github.com/laogou717/local-ops/wiki/数据与备份) / [故障排查](https://github.com/laogou717/local-ops/wiki/故障排查) / [开发者与发布指南](https://github.com/laogou717/local-ops/wiki/开发者与发布指南)
- [`CHANGELOG.md`](CHANGELOG.md) — 变更记录
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — 发布人工验收清单

## 许可与第三方素材

项目自有代码和文档采用 [`MIT License`](LICENSE)。Lucide、Geist Mono 以及项目生成图像等素材可能适用各自的许可或发布限制，不因根目录 MIT 许可证而自动改变，详见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 与 [`ASSET_PROVENANCE.md`](ASSET_PROVENANCE.md)。
