# core/download

MMM-DL 的核心：下载与校验。**未开始**。

约定（将来写在这里时照着做）：

- 只做下载与校验，不启动游戏、不做界面。
- 以 aardio 用户库形式提供，库名 **`MMMDLC`**（MMM Download Core），
  和启动核心 `MMMLC` 成对。
- 被 `downloader/` 或第三方项目通过 `import MMMDLC` 使用。
- 改完跑 `tools\deploy-core-lib.bat` 部署到 aardio 用户库目录。

接口设计参考 `设计文稿/设计文档v2.md` 第五节。
