# -*- coding: utf-8 -*-
import io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def clean(s):
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s.startswith("/*", i):
            j = s.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if s.startswith("//", i):
            j = s.find("\n", i + 2)
            i = n if j < 0 else j + 1
            continue
        ch = s[i]
        if ch == '"':
            j = s.find('"', i + 1)
            i = n if j < 0 else j + 1
            out.append("S")
            continue
        if ch == "'":
            i += 1
            while i < n:
                if s[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                if s[i] == "'":
                    i += 1
                    break
                i += 1
            out.append("S")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


root = r"C:\Users\DELL\Desktop\MMML\launcher\MMMLauncher"
files = [os.path.join(root, "main.aardio")]
files += [os.path.join(root, "lib", f) for f in sorted(os.listdir(os.path.join(root, "lib"))) if f.endswith(".aardio")]
files += [os.path.join(root, "dlg", f) for f in sorted(os.listdir(os.path.join(root, "dlg"))) if f.endswith(".aardio")]

bad = 0
for f in files:
    s = clean(io.open(f, encoding="utf-8").read())
    b = (s.count("{"), s.count("}"), s.count("("), s.count(")"))
    if b[0] != b[1] or b[2] != b[3]:
        bad += 1
        print("  BAD", os.path.basename(f), b)
print("  files:", len(files), "unbalanced:", bad)

# 检查「函数引用的局部变量是否声明得更晚」（aardio 的 var 只从声明处往后可见）
p = os.path.join(root, "dlg", "settings2.aardio")
lines = io.open(p, encoding="utf-8").read().split("\n")
decl = {}
for i, line in enumerate(lines, 1):
    for m in re.finditer(r"\bvar\s+([\w\s,]+?)=", line):
        for name in m.group(1).split(","):
            name = name.strip()
            if name and name not in decl:
                decl[name] = i

funcs = []
cur = None
for i, line in enumerate(lines, 1):
    m = re.match(r"\s*(?:var\s+)?(\w+)\s*=\s*function", line) or re.match(r"\s*function\s+(\w+)", line)
    if m:
        cur = m.group(1)
        funcs.append([cur, i, []])
        continue
    if cur and re.match(r"^\}", line):
        cur = None
        continue
    if cur:
        for name in re.findall(r"\b([a-z][A-Za-z0-9_]*)\b", line):
            funcs[-1][2].append((name, i))

watch = {
    "comboMode", "editW", "editH", "editMem", "editJava", "comboPri", "comboPath",
    "chkLog", "chkHide", "chkStatus", "chkDebug", "chkMulti", "chkShot",
    "lblAccount", "lblVersion", "lblAboutVer", "lblAboutName", "editCredits",
    "btnAuto", "btnDefault", "btnJava", "btnPaths", "btnsAccount", "btnsVersions",
    "P1", "P2", "P3", "P4", "P5", "P6", "P7", "PAGES", "nav_titles",
}

risk = 0
for fname, fline, uses in funcs:
    for name, uline in uses:
        if name in watch and name in decl and decl[name] > fline:
            print("  RISK: %s (line %d) uses %s declared at line %d" % (fname, fline, name, decl[name]))
            risk += 1
print("  use-before-declare risks:", risk)
