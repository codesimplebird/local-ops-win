# 变更记录

本项目的重要变更记录在此。格式参考 Keep a Changelog，版本号使用语义化版本。`VERSION` 是当前版本的唯一权威来源。

每个面向用户的重要功能、修复、安全或兼容性变化先写入
`Unreleased`；发布时再移动到带版本号和日期的章节。纯缓存清理、
一次性构建产物和不影响行为的内部整理由 Git 历史记录，不在此逐项罗列。

## [Unreleased]

### Fixed

- **服务监控进程名被系统目录淹没**：开机自启/托盘应用（如 Ollama）的工作目录常是
  `C:\Windows\System32`，此前表格主标题取「目录末段」，整列显示成 System32/WINDOWS，
  用户按进程名找不到服务。现在家目录与系统目录（`System32`/`WINDOWS`/`Program Files`
  等，见 `_GENERIC_PROJECT_NAMES`）不再作为项目名返回（`project=null`），表格、
  TOP 5、端口发现提示与「加入启动台」预填名全部回退显示真实进程名。
- 设置中心「数据目录」在 Windows 上硬编码显示 macOS 路径；`/api/state` 新增
  `dataDir` 字段，按实际数据目录显示。

### Changed

- 依赖符号链接的测试在 Windows 非管理员/未开开发者模式环境显式跳过
  （`tests.windows_symlink_available`，CI 管理员环境仍真实执行）。

## [1.1.0] - 2026-10-25

### Added

- **Windows 10/11 适配**：后端可在 Windows 上完整运行（Python 3.12 标准库）。
  - 进程扫描改用 `netstat -ano -p tcp` 与 PowerShell `Get-CimInstance`（内存用 WorkingSet 占比）。
  - 受控进程模型改为「锚点进程 + 随机 token 命令行 + PPID 后代树」：`tools/win_anchor.py` 以临时 `.cmd` 批处理执行用户命令，等整棵进程树清空后以原退出码退出，等价于 macOS 的 bash 包装语义。
  - 停止应用用 `taskkill /T`（先优雅、失败自动升级 `/F` 树杀）；`pid_alive` 改用 OpenProcess + GetExitCodeProcess（`os.kill(pid,0)` 在 Windows 上对已退出进程仍返回成功）。
  - 实例锁改用 `msvcrt.locking` 回退（fcntl 仅 POSIX）；数据目录默认 `%APPDATA%\总控台` 与 `%LOCALAPPDATA%\总控台\Logs`。
  - 工作目录经 PEB 只读读取（`NtQueryInformationProcess`，ctypes）；文件/目录选择框用 PowerShell + WinForms。
  - 新增 `start.bat` 启动器；项目识别在 Windows 上用 `python`/`py -3` 并识别 `.bat/.cmd/.ps1` 启动脚本。
  - `/api/state` 与 `/api/health` 增加 `platform` 字段，前端重启/停止提示按平台显示启动器名。
  - 新增 `tests/test_windows.py`（Windows 专属解析与真实生命周期测试），macOS 专属测试在 Windows 上显式跳过；CI 增加 Windows 检查 job（含真实启动冒烟测试）。
  - 项目检查在 Windows 上跳过 bash/plutil 检查（Info.plist 改用 plistlib 校验），并兼容 node 24 的 `--test` 输出格式。
- **Windows 独立发行包**：`tools/build_exe.py` 用 PyInstaller（仅构建期依赖，运行时仍纯标准库）产出免 Python 安装的 onedir 包（`Console.exe` + 静态资源，zip + SHA-256）；CI 新增 windows-package job 对打包产物做解包冒烟。资源与源码树同构铺设在 exe 同目录，打包/开发两种形态共用同一份锚点脚本。
- **开机自启（Windows）**：`--install-autostart` / `--uninstall-autostart` 与设置中心「开机自启」开关，在 `shell:startup` 建/删无窗口快捷方式（pythonw + `--launcher --no-browser`），登录后后台拉起、不弹浏览器、幂等；`POST /api/autostart` 走既有跨站防护通道，`/api/state` 增加 `autostartInstalled`。
- 项目启动识别增加 Poetry 支持；检测到 `poetry.lock` 时，Python Web 项目候选命令使用 `poetry run`（Windows 社区版同步合入，并保留 `python`/`python3` 平台适配与 uv 支持）。
- 顶栏新增 GitHub 仓库图标按钮，点击在新标签页打开项目源码仓库。
- 增加用户/开发文档、备份恢复和升级卸载指南。
- 布局升级为指挥台结构：左侧图标导航轨、启动台与服务监控双视图 KPI 概览卡（含 CPU/内存火花线）、右侧实时动态/实时告警与端口/资源 TOP 5 信息栏、小贴士、页头快捷操作，以及服务/任务分区筛选芯片；服务表格增加 PID、状态列与 CPU 迷你负载条。结构样式集中于 `base.css`。
- 导航轨与侧栏补齐聚合能力：日志中心弹层（⌘J 呼出，应用与总控台日志目录页，⌘L 为浏览器保留键故用 ⌘J）、设置中心弹层（任务完成通知开关、浅色/深色/自动外观、版本与目录信息）、快捷操作部件的批量停止服务（确认后逐个安全停止，绝不按端口结束进程）。
- 服务表格新增**进程溯源**：沿 PPID 链识别并显示每个服务的启动者（AI 编程助手/编辑器/终端/总控台），副标题行展示来源图标与名称。
- 新增「Ops 指挥台」为唯一 UI 主题（深空蓝黑/雾灰双色、柔和圆角细边、蓝色强调），主题清单中固定排首位；保留 `#themeCss` 整包加载与 `uiTheme` 配置机制，但不再提供多主题与主题选择界面。
- 增加统一项目检查入口、显式测试发现和发布核对表。
- 增加项目权利声明与第三方素材清单。
- 增加根目录 `VERSION` 统一版本源，`/api/state` 暴露版本/schema/降级信息，并增加不执行进程扫描的 `/api/health`。
- 增加 `schemaVersion=1` 和显式、幂等的逐版配置迁移器。
- 增加 `SECURITY.md`、`CONTRIBUTING.md`、社区行为规范以及 GitHub Issue/PR 模板。
- 增加 `ASSET_PROVENANCE.md`，并用路径、SHA-256 与发布状态检查覆盖字体、品牌图片、插画和程序化纹理。
- 增加统一品牌标识、网页 favicon、Apple Touch Icon、macOS App Icon 与可重建的品牌导出脚本。
- 命令面板增加“添加服务”和“添加批处理任务”入口；应用卡片增加可取消的键盘排序。
- 服务监控增加会话级新端口发现栏，可将新监听服务加入启动台、忽略隐藏或暂时关闭。
- 应用状态增加只读配置健康检查，在运行前识别丢失的工作目录、脚本和运行时，并提供修复入口。

### Changed

- **Windows 轮询性能收敛**：全量进程快照（PowerShell CIM）加 1.2s TTL 缓存并供受管识别/进程详情/来源溯源/关注进程共享，稳态每轮轮询从 4 个相同快照减为 1 个；系统总内存改 ctypes `GlobalMemoryStatusEx` 直读；受管进程树只为应用锚点构建（此前为全系统每个进程各建一棵）；锚点后代探测改 ctypes Toolhelp 快照（此前每 2 秒一个 PowerShell 全量查询）。
- **真实 CPU%（Windows）**：由连续两次快照的 User/KernelModeTime 差值推算（100ns 整型、按全部逻辑核心归一、上限 100），服务表格与 KPI 火花线显示真实占用（此前恒为 0）。
- **服务监控按真实用户过滤（Windows）**：按进程所有者过滤（ctypes 毫秒级优先；提升权限/受保护进程由后台 CIM 批量补查并记忆化），svchost 等 SYSTEM 服务不再混入服务监控；所有者未知的进程保持显示，绝不因读取失败隐藏可能是当前用户的服务。
- README 精简为「快速开始 / 使用 / 参与贡献」入口，完整的使用手册、数据与备份、故障排查和开发者指南迁往仓库 Wiki。
- 默认将配置/图标移至 `~/Library/Application Support/总控台`，日志移至 `~/Library/Logs/总控台`。新目标不存在时仅首次复制旧 `data/`，不删除原文件。
- `config.json.bak` 现保留修改前的上一份良好配置，而不是与主配置相同的副本。
- 运行目录权限收紧为 `0700`，配置、图标和日志文件为 `0600`。
- 项目自有代码和文档改用 MIT License；README 明确 Preview / Alpha、源码预览和非远程运维边界。
- 公开发行检查会拒绝仍标记为 `BLOCKED` 或 `TO_REPLACE` 的素材，并要求对 `REVIEW_REQUIRED` 项形成人工结论。
- 表单把外观设置收进可选区域，服务/任务分别优先聚焦“选择项目”和“选择脚本”。
- 修正 900px 附近顶栏导航异常放大，并补齐移动端、高对比度、键盘焦点和表格语义。
- 移除来源和再分发链路不完整的精简中文字体，改用 macOS 系统字体栈。
- 批处理结果改为成功、取消、失败、中止四态；脚本内部用户取消统一使用退出码 130。
- 任务运行中的动作统一使用“中止”，服务继续使用“停止”，诊断和编辑提示随类型变化。
- 多个启动配置现在可以共享同一端口；项目归属由受管进程身份和工作目录判断，只有实际启动时的监听占用才会阻止运行。

### Fixed

- 修复 Windows 上 PID 复用把无关孤儿进程误纳入受管成员表、导致「停止」被长命进程拖到超时的问题（受管树按「后代创建时间不得早于父进程」过滤；taskkill 按真实 OS 树执行本就不受影响，无误杀风险）。
- 修复 Windows PowerShell 5.1 下所有进程 uptime 恒为 0 的问题（`ConvertTo-Json` 把创建时间序列化为 `/Date(毫秒)/`，旧解析器只认 ISO/DMTF；现覆盖三种格式并按 DMTF 分钟制时区正确换算）。
- 修复 `--launcher` 在标准句柄缺失（pythonw / 隐藏窗口启动）时崩溃的问题（OSError 9：句柄重定向自别名空操作 + 收尾误关标准句柄）。
- 修复从服务监控加入启动台时只创建卡片、未认领来源进程的问题；创建与进程认领现由后端原子完成，项目命令识别完成前不能提前保存。明确认领的服务在 Next/Vite 等框架重建监听子进程、PID 变化后，会按端口、当前用户与真实项目目录唯一重新关联。
- 修复 Candy 主题超大标题的英文粗体描边出现双重轮廓，并让英文副标题在窄屏明确换行。
- 修复批处理脚本内取消被误报为运行成功，以及任务成功退出被诊断成“服务过早退出”。
- 重启服务前先检查当前配置，避免脚本或目录失效时先停止仍在工作的旧进程。
- 修复外部进程碰巧监听停止卡片的配置端口时被误认成该卡片、且不会触发新端口发现的问题；端口诊断增加打开占用服务和修改原卡片两种非破坏性处理方式。
- 修复测试服务器、热重载等短命监听停止后仍长期残留在“发现新的监听端口”列表的问题。
- 修复从服务监控把正在运行的进程加入启动台后，新卡片反而把来源进程识别成端口占用者的问题；保存时现在会立即认领来源 PID。

### Removed

- 移除已被统一品牌图、Candy 新插画和系统字体栈替代的旧 Logo、旧插画及两份中文字体文件。
- 移除 Apollo/Candy/8-Bit 三套 UI 主题与主题选择面板、命令面板主题切换项及 Candy 专用 hero 卡；产品收敛为单一「Ops 指挥台」主题，旧的 `uiTheme` 偏好自动回退到 ops。
- 随主题移除不再使用的 Apollo 程序化纹理（deck/metal-brush 系列）、Candy 启动台插画与 `tools/gen_textures.py`；`ASSET_PROVENANCE.md` 与 `THIRD_PARTY_NOTICES.md` 同步核销。

### Security

- 将用户配置、日志、图标、token 和临时发行产物排除出版本控制默认范围。
- 主配置与备份均无法验证时进入只读保护，防止用空默认配置覆盖尚可恢复的用户数据。
- 增加私密漏洞报告、Issue/PR 脱敏和公开仓库安全披露门禁。

## [1.0.0] - 2026-07-23

### Added

- Python 3 标准库本地 HTTP 后端，只绑定 `127.0.0.1`。
- 启动台：服务与批处理任务的创建、编辑、排序、启动、停止、重启、日志与诊断。
- 服务监控：端口、进程、CPU、内存、运行时间、关注关键字与分组。
- 读取常见项目配置并提供候选启动命令的本地项目识别。
- 基于 run token、进程组和 UID 的受控进程识别。
- 原子配置写入、同步备份、有界日志读取与轮转。
- Apollo/Candy 双 UI 主题、深浅色模式、命令面板和原生 macOS 文件选择。
- `总控台.app` 后台启动器与 `start.command` 调试入口。
