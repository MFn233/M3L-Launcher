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

版本 **0.2.2**（第四段是 aardio 自增的内部构建号，界面上不显示）。
启动日志第一行会打印「启动器版本 + 核心构建标记」，用于区分发布版与本地调试。

> 发行版与本地调试的表现可能不同：exe 里内嵌的是发布那一刻的库。
> 遇到「发行版不行、F5 可以」时，先看日志里的核心构建标记。

已完成：

- 多游戏目录管理（官方目录不可删除）
- 版本管理：隔离开关、重命名、删除（进回收站）、打开目录、真实游戏版本与加载器识别
- Java 管理：自动检测、厂商识别、黑名单、版本不匹配时的提示与切换
- 离线账号：多账号、自定义 UUID
- 设置：内存、窗口大小、优先级、多开、日志窗口、启动后隐藏、状态栏
- 日志窗口：分实例、分级别灰阶、按级别筛选、可打包成 zip
- 崩溃处理：原因分析、疑似模组、防截图、日志打包
- **正版登录**：微软 OAuth 2.0 设备码流程，令牌本地保存、快到期自动续期
- **外置登录**：authlib-injector（自动下载 jar 并挂 `-javaagent`）
- 版本独立设置：内存、窗口、优先级、JVM 参数、Java、关闭文件校验
- 启动前自动兼容异常版本文件（可一键关闭，退回"照 JSON 原样"）
- 每次启动把启动器日志落到 `versions/<版本>/m3l-launch.txt`

未开始：

- 下载器（MMM-DL）
- 界面自定义
- 整合包随包声明（作者模式：锁定设置、隐藏版本选择）

## 登录

| 方式 | 说明 |
|---|---|
| 离线 | 只填用户名，UUID 可按用户名生成或手填 |
| 正版 | 微软 OAuth 2.0 **设备码**流程：显示代码 → 浏览器授权 → 自动换取 Minecraft 令牌 |
| 外置 | authlib-injector：填服务器地址与账号密码，启动时自动挂 `-javaagent` |

正版登录需要一个 **Azure 应用（客户端 ID）**：

- 默认内置本项目自己的公共客户端 ID，用户也可在设置里填自己的；
- 微软侧需要在「身份验证 → 允许公共客户端流」选「是」；
- **还需要在 Minecraft 官方申请加入允许名单**，否则换令牌时会返回
  `403 Invalid app registration`。申请方式见 [设计文稿/正版登录配置.md](设计文稿/正版登录配置.md)。

令牌只保存在本机 `config.json`，不上传、不参与统计。

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
- **登录链路**：F5 跑 `launcher/MMMLauncher/test-auth.aardio`，选 1 测微软、2 测外置登录。
- **库解析回归**（不需要启动游戏）：

  ```
  python tools/check-classpath.py
  ```

  按 core 的规则解析本机所有版本，检查不变量（重复条目、文件存在、客户端 jar、natives），
  并与 `tools/snapshots/classpath.json` 比对，报告"哪个版本的 classpath 变了"。
  `--update` 重写快照，`--show <版本名>` 打印某个版本的解析结果。

## 配置与数据

运行时文件都在 **exe 同目录的 `M3L\` 下**，exe 旁边只留程序本身：

```
M3L\
├── config.json            配置（纯文本，可手工编辑）
├── config.pending.json    设置窗口草稿
├── migrate.log            旧布局迁移记录（只有搬过东西才有）
├── cache\                 元数据缓存
├── diag\                  诊断输出（mod-scan.txt / mod-diag.txt）
├── logs\                  预留：日志打包输出
└── authlib-injector\      外置登录用的 jar
```

- 启动器不写注册表，卸载直接删目录（连 `M3L\` 一起删）；
- **从旧布局升级**：启动时会自动把散落在 exe 旁边的文件搬进 `M3L\`
  （只在目标不存在时搬，不覆盖）；也可以手动跑迁移工具 `migrate-layout.aardio`
  （发布成 exe 放在启动器旁边，支持 `--dry` 只看计划）；
- 版本目录里的 `.m3l-meta.json`（边车文件）由 MMM-DL 写入，记录下载时确定的游戏版本与加载器；
  没有这个文件时，启动器按版本 JSON 自行推断。

## 许可证

**GNU General Public License v3.0 or later**，全文见 [LICENSE](LICENSE)。

## 鸣谢

**第三方**

- **aardio** —— 开发工具与运行时
- **Mojang** —— Minecraft 本体与版本清单格式
- **Minecraft 社区公开文档与讨论** —— 崩溃原因分析思路的参考

**实现协作**

- **DeepSeek** —— 代码实现、文档整理与测试

**参与测试**

- 见程序内「设置 → 鸣谢」

本项目为个人非营利项目，与上述公司、项目无隶属关系。
「Minecraft」是 Mojang Studios 的商标，本项目与 Mojang 无关联。
