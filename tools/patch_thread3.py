# -*- coding: utf-8 -*-
"""Mod 读取重做：线程只读原文（只用标准库），解析留在 UI 线程；带超时回退。

为什么这样拆：
- 新线程有独立的全局环境，`import m3mod`（项目库）不一定解析得到，
  而线程里的异常在 GUI 下是静默的 —— 表现就是"完全不读了"；
- 所以线程只碰 `zlib.unzip` + `string`（标准库），把条目原文当字符串回传给 UI，
  解析（小字符串，微秒级）和缓存都在 UI 线程做。
"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\DELL\Desktop\MMML\launcher\MMMLauncher\dlg\settings2.aardio"
raw = io.open(P, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
text = raw.replace("\r\n", "\n")

START = "function mods_render() {"
END = "// 最终渲染：元数据都读完了（或走缓存），排序 + 标红 + 填表"

i = text.find(START)
j = text.find(END)
if i < 0 or j < 0 or j < i:
    print("  [FAIL] 找不到替换范围")
    sys.exit(1)

NEW = '''// 后台线程会把这些条目的**原文**回传；解析留在 UI 线程，所以线程里不需要项目库。
var MOD_SLOTS = {
	"fabric.mod.json";
	"quilt.mod.json";
	"META-INF/neoforge.mods.toml";
	"META-INF/mods.toml";
	"litemod.json";
	"mcmod.info";
	"META-INF/MANIFEST.MF";
};

// 与 MOD_SLOTS 一一对应的 pick_meta 键
var MOD_SLOT_KEYS = {
	"fabric.mod.json";
	"quilt.mod.json";
	"neoforge.mods.toml";
	"mods.toml";
	"litemod.json";
	"mcmod.info";
	"manifest.mf";
};

// UI 线程：把某个 Mod 的原文解析出元数据并写回行
function mod_apply_texts(idx, t) {
	if (!mod_rows[idx]) return;

	var texts = {};
	for k, key in MOD_SLOT_KEYS {
		var s = t[k];
		if (s and #s > 0) texts[key] = s;
	}

	var meta = m3mod.pick_meta(texts);
	var m = mod_rows[idx];

	m.modid = meta.modid or "";
	m.title = meta.name or "";
	m.mver = meta.version or "";

	if (#m.title == 0) m.title = m.name;
	if (#m.mver == 0) m.mver = "-";

	m3mod.cache_put(m.path, {
		modid = m.modid;
		name = m.title;
		version = m.mver;
		loader = meta.loader or "";
	});

	listMods.setItemText(m.title, idx, 2);
	listMods.setItemText(m.mver, idx, 3);
}

function mods_render() {
	mod_scan_cancel();
	var gen = mod_scan_gen;

	listMods.clear();
	mod_rows = {};
	mod_dup_rows = {};

	mod_scan_done = 0;

	if (!pv_current) {
		mod_prog_hide();
		lblModHint.text = "请先在设置窗口里选择游戏路径。";
		m3list.renumber(listMods);
		mod_btn_update();
		return;
	}

	var dir = m3mod.dir_of(cfg, pv_current);

	if (!dir or !io.exist(dir)) {
		mod_prog_hide();
		lblModHint.text = "此版本没有 mods 文件夹：" ++ tostring(dir);
		m3list.renumber(listMods);
		mod_btn_update();
		return;
	}

	m3mod.cache_load();

	var list = m3mod.scan(dir);

	// 先按文件名铺出来；命中缓存的直接填好
	for i, m in list {
		m.modid = "";
		m.title = m.name;
		m.mver = "-";

		var status = "启用";
		if (!m.enabled) status = "禁用";

		listMods.addItem({ ""; m.title; m.mver; m.file; status });
		table.push(mod_rows, m);
	}

	m3list.renumber(listMods);

	if (#mod_rows == 0) {
		mod_prog_hide();
		lblModHint.text = "此版本未安装 Mod。";
		mod_btn_update();
		return;
	}

	// 缓存里有的先填上；剩下的才需要读压缩包
	var todo = {};

	for i, m in mod_rows {
		var meta = m3mod.cache_peek(m.path);

		if (meta) {
			m.modid = meta.modid or "";
			m.title = meta.name or "";
			m.mver = meta.version or "";

			if (#m.title == 0) m.title = m.name;
			if (#m.mver == 0) m.mver = "-";

			listMods.setItemText(m.title, i, 2);
			listMods.setItemText(m.mver, i, 3);
		}
		else {
			table.push(todo, i);
		}
	}

	mod_scan_done = #mod_rows - #todo;
	mod_prog_show(#mod_rows);
	mod_prog_update(mod_scan_done, #mod_rows);

	if (#todo == 0) {
		mod_prog_hide();
		mods_render_final();
		return;
	}

	lblModHint.text = "正在读取 Mod 信息… " ++ mod_scan_done ++ "/" ++ #mod_rows;

	// ---- 后台线程：只负责把条目原文读出来 ----

	if (!mod_listener) {
		mod_listener = thread.command();

		// 线程回传：gen, 行号, 7 段原文
		mod_listener.on_texts = function(g,
			idx,
			s1, s2, s3, s4, s5, s6, s7) {

			if (g != mod_scan_gen) return;   // 切页/切版本之后迟到的结果，丢弃

			mod_scan_got = true;

			var t = { s1; s2; s3; s4; s5; s6; s7 };
			mod_apply_texts(idx, t);

			mod_scan_done = mod_scan_done + 1;
			mod_prog_update(mod_scan_done, #mod_rows);

			if (mod_scan_done < #mod_rows) {
				lblModHint.text = "正在读取 Mod 信息… " ++ mod_scan_done ++ "/" ++ #mod_rows;
			}
		};

		mod_listener.on_job_done = function(g) {
			if (g != mod_scan_gen) return;

			mod_jobs_left = mod_jobs_left - 1;
			if (mod_jobs_left > 0) return;
			if (mod_scan_done < #mod_rows) return;

			m3mod.cache_save();
			mods_render_final();
		};

		// 线程里出错了：显示原因，并改用同步读取兜底
		mod_listener.on_error = function(g, msg) {
			if (g != mod_scan_gen) return;

			mod_scan_error = tostring(msg);
			mod_sync_scan(gen);
		};
	}

	var paths = {};
	for i, m in mod_rows {
		paths[i] = m.path;
	}

	var worker = 4;
	if (#todo <= 8) worker = 1;
	if (worker > #todo) worker = #todo;

	mod_jobs_left = worker;
	mod_scan_got = false;

	var per = ..math.ceil(#todo / worker);

	for w = 1; worker; 1 {
		var at = (w - 1) * per + 1;
		var to = at + per - 1;
		if (to > #todo) to = #todo;
		if (at > to) break;

		var first = todo[at];
		var last = todo[to];

		// 线程体是自包含的：只 import 标准库（zlib.unzip / string），
		// 不 import 项目库（新线程的全局环境里不一定有）。
		thread.invoke(
			function(listener, paths, first, last, g, slots) {
				import thread.command;
				import zlib.unzip;

				for i = first; last; 1 {
					var out = {};

					var zip = null;
					try {
						zip = zlib.unzip(paths[i], false);
					}
					catch(e) {
						zip = null;
					}

					if (zip) {
						for k, nm in slots {
							var s = null;

							try {
								if (zip.locate(nm)) {
									s = zip.readCurrentFile();
								}
								else {
									var alt = string.replace(nm, "/", "\\\\");
									if (zip.locate(alt)) s = zip.readCurrentFile();
								}
							}
							catch(e) {
								s = null;
							}

							out[k] = s or "";
						}

						try {
							zip.close();
						}
						catch(e) {
						}
					}

					listener.$on_texts(g, i,
						out[1], out[2], out[3], out[4], out[5], out[6], out[7]);
				}

				listener.$on_job_done(g);
			}, mod_listener, paths, first, last, gen, MOD_SLOTS);
	}

	// 看门狗：2 秒内一条回传都没有，就认定后台线程不可用，改同步读
	var watchdog;
	watchdog = function() {
		if (gen != mod_scan_gen) return;
		if (mod_scan_got) return;

		mod_sync_scan(gen);
	};

	winform.setTimeout(watchdog, 2000);
}

// 同步兜底：后台线程不通时，在 UI 线程上分片读（会卡，但至少能读到）
function mod_sync_scan(gen) {
	if (gen != mod_scan_gen) return;
	if (mod_scan_syncing) return;

	mod_scan_syncing = true;

	if (#mod_scan_error > 0) {
		lblModHint.text = "后台读取失败（" ++ mod_scan_error ++ "），改为同步读取…";
	}
	else {
		lblModHint.text = "后台读取超时，改为同步读取…";
	}

	var idx = 1;

	var step;
	step = function() {
		if (gen != mod_scan_gen) {
			mod_scan_syncing = false;
			return;
		}

		var deadline = ..time.tick() + 25;

		var applied = 0;

		while (idx <= #mod_rows and ..time.tick() < deadline) {
			var m = mod_rows[idx];

			if (#m.title > 0 and m.title != m.name) {
				idx = idx + 1;
				continue;
			}

			var meta = m3mod.meta_of(m.path);

			var texts = {};
			mod_apply_texts(idx, { m3mod_texts_of(meta) });

			idx = idx + 1;
			applied = applied + 1;
		}

		if (idx <= #mod_rows) {
			winform.setTimeout(step, 1);
		}
		else {
			mod_scan_syncing = false;
			m3mod.cache_save();
			mods_render_final();
		}
	};

	step();
}

// 最终渲染：元数据都读完了（或走缓存），排序 + 标红 + 填表'''

text = text[:i] + NEW + text[j:]
io.open(P, "w", encoding="utf-8", newline="").write(text.replace("\n", nl))
print("  [ OK ] 已重做（线程只读原文 + 同步兜底）")
