# -*- coding: utf-8 -*-
"""把 m3mod 的四段计量写进 mod-scan.txt；慢条目改成"最慢的 5 个"。

原来 #slow 只收"前 6 个 >=30ms"的（按文件名顺序），看不出尾部谁最慢。
现在维护一个"最慢 5 个"的小表，谁更慢就替换掉最慢的那个。
"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\DELL\Desktop\MMML\launcher\MMMLauncher\dlg\settings2.aardio"
raw = io.open(P, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
text = raw.replace("\r\n", "\n")


def one(old, new, label):
    global text
    n = text.count(old)
    if n != 1:
        print("  [FAIL] %s (命中 %d)" % (label, n))
        sys.exit(1)
    text = text.replace(old, new)
    print("  [ OK ] " + label)


# 1) 扫描开始前重置计量
one('''	var at = 1;
	var t_start = ..time.tick();
	var t_meta = 0;
	var slow = {};''',
    '''	var at = 1;
	var t_start = ..time.tick();
	var t_meta = 0;
	var slow = {};      // 最慢的 5 个（保持降序）

	m3mod.stats_reset();''',
    "扫描前重置计量")

# 2) 慢条目改成最慢 5 个
one('''			if (ms >= 30 and #slow < 6) {
				table.push(slow, ms ++ "ms  " ++ mod_rows[idx].file);
			}''',
    '''			// 维护"最慢 5 个"：比表里最慢的还快就不记
			var rec = string.format("%6dms  %s", ms, mod_rows[idx].file);
			var cnt = #slow;

			if (cnt < 5) {
				table.push(slow, rec);
			}
			elseif (ms > tonumber(string.left(string.trim(slow[cnt]), #slow[cnt])) ) {
				slow[cnt] = rec;
			}

			// 插入后按耗时降序（只有 5 个，冒泡够用）
			for a = 1; #slow - 1; 1 {
				for b = 1; #slow - a; 1 {
					var ms_a = tonumber(string.match(slow[b], "^%s*(%d+)"));
					var ms_b = tonumber(string.match(slow[b + 1], "^%s*(%d+)"));

					if (ms_a and ms_b and ms_a < ms_b) {
						var tmp = slow[b];
						slow[b] = slow[b + 1];
						slow[b + 1] = tmp;
					}
				}
			}''',
    "慢条目改最慢 5 个")

# 3) 统计里带上四段
one('''		mod_scan_stats = {
			total = ..time.tick() - t_start;
			meta = t_meta;
			slow = slow;
		};''',
    '''		mod_scan_stats = {
			total = ..time.tick() - t_start;
			meta = t_meta;
			slow = slow;
			st = m3mod.stats_get();
		};''',
    "统计带上四段")

# 4) 写文件时输出四段
one('''	if (mod_scan_stats) {
		table.push(lines, "#ms_total=" ++ mod_scan_stats.total ++ "  #ms_meta=" ++ mod_scan_stats.meta);

		for i, s in mod_scan_stats.slow {
			table.push(lines, "#slow=" ++ s);
		}
	}''',
    '''	if (mod_scan_stats) {
		table.push(lines, "#ms_total=" ++ mod_scan_stats.total ++ "  #ms_meta=" ++ mod_scan_stats.meta);

		var st = mod_scan_stats.st;
		if (st) {
			table.push(lines, "#ms_breakdown: open=" ++ st.open ++ "  locate=" ++ st.locate
				++ "  read=" ++ st.read ++ "  parse=" ++ st.parse);
			table.push(lines, "#entries: hit=" ++ st.hit ++ "  miss=" ++ st.miss);
		}

		for i, s in mod_scan_stats.slow {
			table.push(lines, "#slow=" ++ s);
		}
	}''',
    "写文件输出四段")

io.open(P, "w", encoding="utf-8", newline="").write(text.replace("\n", nl))
print("  [ OK ] 已写回")
