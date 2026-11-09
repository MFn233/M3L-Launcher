# MFn's Minimalism Mclauncher

极简的 Minecraft 启动器。仅支持 Windows。

别称：**M³ Launcher** / **M3L** / **MMML**

- 无配色，只用黑白灰
- 无广告、无推送、无后台常驻
- 绿色、portable：配置写在 exe 同目录的 `config.json`

---

## 组成

| 部分 | 说明 | 目录 |
|---|---|---|
| **MMM-C** (core) | 启动逻辑。接收参数 → 找 Java → 拼命令 → 启动游戏 → 返回 PID 或错误码。不碰下载、不碰界面。 | `core/` |
| **MMM-L** (launcher) | 图形界面。让用户舒服地调用 core。 | `launcher/` |
| **MMM-DL** (downloader) | 下载工具。下载并校验游戏本体、模组、整合包。与启动器相互独立。 | `downloader/`（未开始） |

## 当前状态

版本 **0.1.2**（第四段是 aardio 自增的内部构建号，界面上不显示）。

已完成：

- 多游戏目录管理（官方目录不可删除）
- 版本管理：隔离开关、重命名、删除（进回收站）、打开目录、真实游戏版本与加载器识别
- Java 管理：自动检测、厂商识别、黑名单、版本不匹配时的提示与切换
- 离线账号：多账号、自定义 UUID
- 设置：内存、窗口大小、优先级、多开、日志窗口、启动后隐藏、状态栏
- 日志窗口：分实例、可打包成 zip
- 崩溃处理：原因分析、疑似模组、防截图、日志打包

未开始：

- 下载器（MMM-DL）
- 正版登录、外置登录
- 界面自定义

## 目录结构

```
.
├── core/                 无界面、可被别的项目 embed 的代码
│   ├── launch/           MMM-C：启动核心
│   │   ├── MMMLC.aardio      库源码（权威，两个工程都 import MMMLC）
│   │   └── MMMLCore/         命令行工程
│   └── download/         下载核心（MMMDLC，未开始）
├── launcher/             MMM-L
│   ├── MMMLauncher/      启动器工程
│   └── ICON design/      图标源文件
├── downloader/           MMM-DL（未开始）
├── 设计文稿/              设计文档
├── 工作日志/              按日期记录的开发日志
├── tools/                辅助脚本
├── LICENSE               GPL-3.0
└── README.md
```

`core/` 下按**功能**分层（launch / download），不按角色命名——所以不会有"两个 core"的歧义。
库名同样成对：`MMMLC`（启动核心）与 `MMMDLC`（下载核心）。

`test/`、`launchertest/` 是本地测试数据与发布版试运行目录，不纳入版本控制。

## 运行与构建

需要 [aardio](https://www.aardio.com/)（Windows）。

1. 打开 `launcher/MMMLauncher/default.aproj`；
2. **F5** 直接运行；
3. 发布：工程 → 发布，产物在 `launcher/MMMLauncher/dist/MMMLauncher.exe`。

**发布后必须验一次**，否则可能出现「在别人机器上打不开、报找不到库」：

```
pwsh -File tools\check-publish.ps1
```

它检查 exe 里是否真的内嵌了所有库（PE 资源类型 `LIB`）与所有窗体（`DLG/NAME.AARDIO`），
并逐项打印 `[ OK ]` / `[MISS]`。**有 `[MISS]` 就不要发出去。**

新增 `dlg/*.aardio` 后忘了在 IDE 里「同步本地目录」，发布版就会缺窗体——
这个脚本正是用来兜住这类漏项的。

**改了 core 之后要重新部署**：

```
tools\deploy-core-lib.bat
```

它把 `core/launch/MMMLC.aardio` 复制到 aardio 的用户库目录（`<aardio>\lib\MMMLC.aardio`）。
两个工程都是 `import MMMLC`，实际加载的是用户库目录里那一份，不跑这一步改动不生效。

## 测试

- **日常**：F5 直接跑；或把发布的 exe 放到 `launchertest/` 里跑（那里有自己的 `config.json`）。
- **崩溃窗口**：设置里打开「调试模式」，然后 **Ctrl + 右键**点标题 → 崩溃窗口测试台。
  内置几份崩溃报告样本，可当场看原因分析与多窗口表现，不必真的把游戏弄崩。
- **控件样式**：调试模式下 **右键**点标题 → 控件样式测试台（改主题时对照用）。

## 配置与数据

- `config.json` 与 exe 同目录，纯文本，可手工编辑；
- 启动器不写注册表，卸载直接删目录；
- 版本目录里的 `.m3l.json`（边车文件）由 MMM-DL 写入，记录下载时确定的游戏版本与加载器；
  没有这个文件时，启动器按版本 JSON 自行推断。

## 许可证

**GNU General Public License v3.0 or later**，全文见 [LICENSE](LICENSE)。

## 鸣谢

**第三方**

- **aardio** —— 开发工具与运行时
- **Mojang** —— Minecraft 本体与版本清单格式
- **HMCL** —— 崩溃原因分析规则的参考实现（GPL-3.0）

**实现协作**

- **DeepSeek** —— 代码实现、文档整理与测试

**参与测试**

- 见程序内「关于 → 鸣谢」

本项目为个人非营利项目，与上述公司、项目无隶属关系。
「Minecraft」是 Mojang Studios 的商标，本项目与 Mojang 无关联。
