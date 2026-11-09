# -*- coding: utf-8 -*-
"""把边车文件从 .m3l.json 改名为 .m3l-meta.json（代码 + 文档），并统一新文件的命名。

为什么整体替换是安全的：
- 边车只由 MMM-DL 写，而 MMM-DL 还没实现，磁盘上不存在真实的 .m3l.json；
- 老文件读不到时行为不变（read_sidecar 返回 null，退回按版本 JSON 推断）。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

files = [
    r"C:\Users\DELL\Desktop\MMML\launcher\MMMLauncher\lib\m3version.aardio",
    r"C:\Users\DELL\Desktop\MMML\设计文稿\设计文档v2.md",
    r"C:\Users\DELL\Desktop\MMML\README.md",
]

# 1) 代码：常量 + 注释
P = files[0]
raw = io.open(P, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
text = raw.replace("\r\n", "\n")

old = '''	// 下载器（MMM-DL）在版本目录里写的边车文件：<版本目录>\\.m3l.json
	// 例：{"game":"1.20.1","loader":"Fabric","loader_version":"0.19.3","source":"mmmd"}
	// 有这个文件就说明版本是下载器装的，里面的信息比任何推断都可靠。
	function read_sidecar(minecraft_dir, name) {
		if (!minecraft_dir or !name) return null;

		var file = minecraft_dir ++ "\\versions\\" ++ name ++ "\\.m3l.json";
		if (!io.exist(file)) return null;
'''
new = '''	// 下载器（MMM-DL）在版本目录里写的边车文件：<版本目录>\\.m3l-meta.json
	// 例：{"game":"1.20.1","loader":"Fabric","loader_version":"0.19.3","source":"mmmd"}
	// 有这个文件就说明版本是下载器装的，里面的信息比任何推断都可靠。
	// 命名约定：.m3l-meta.json = 下载元信息；.m3l.options.json = 版本独立设置（以后做）。
	function read_sidecar(minecraft_dir, name) {
		if (!minecraft_dir or !name) return null;

		var file = minecraft_dir ++ "\\versions\\" ++ name ++ "\\.m3l-meta.json";
		if (!io.exist(file)) return null;
'''
if text.count(old) != 1:
    print("  [FAIL] read_sidecar 段命中 %d 次" % text.count(old))
    sys.exit(1)
text = text.replace(old, new)

text = text.replace(
    "if (string.startsWith(fname, \".\")) continue;   // 跳过边车文件 .m3l.json",
    "if (string.startsWith(fname, \".\")) continue;   // 跳过边车文件（.m3l-meta.json / .m3l.options.json）",
)

io.open(P, "w", encoding="utf-8", newline="").write(text.replace("\n", nl))
print("  [ OK ] m3version.aardio 边车文件名已改")

# 2) 文档：设计文档 v2
P = files[1]
raw = io.open(P, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
text = raw.replace("\r\n", "\n")

text = text.replace(
    "- 下载完成后在版本目录写入边车文件 `.m3l.json`：",
    "- 下载完成后在版本目录写入边车文件 `.m3l-meta.json`：",
)
text = text.replace(
    "- 不与 `m3l.json` 混用：那个边车是下载器写的（记录 game / loader / source），用途不同。",
    "- 命名约定：`.m3l-meta.json` 是下载器写的**元信息**（game / loader / source）；\n"
    "  `.m3l.options.json` 是**版本独立设置**。两者不合并，用途不同。",
)
text = text.replace(
    "- 位置：`versions/<版本名>/m3l-options.json`，放在版本目录里，重命名/删除版本时自然跟随。",
    "- 位置：`versions/<版本名>/.m3l.options.json`，放在版本目录里，重命名/删除版本时自然跟随。",
)
io.open(P, "w", encoding="utf-8", newline="").write(text.replace("\n", nl))
print("  [ OK ] 设计文档v2 已同步命名")

# 3) README
P = files[2]
raw = io.open(P, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
text = raw.replace("\r\n", "\n")
text = text.replace("版本目录里的 `.m3l.json`（边车文件）", "版本目录里的 `.m3l-meta.json`（边车文件）")
io.open(P, "w", encoding="utf-8", newline="").write(text.replace("\n", nl))
print("  [ OK ] README 已同步命名")
