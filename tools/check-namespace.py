# -*- coding: utf-8 -*-
"""库文件体检：namespace 里有没有"没 import 就裸用"的全局库。

为什么需要：aardio 在 namespace 内部解析名字时只看命名空间成员，
`table.push` / `math.max` 这种如果没 `import`，拿到的是 null，运行时报
「不支持此操作: _get table / 名字:'table'」。这两处都已经踩过。

用法：python tools/check-namespace.py
退出码：0 = 全部干净；1 = 有可疑裸用。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 常见的全局库；表里没有的也可以直接加
LIBS = [
    "math", "table", "string", "io", "fsys", "json", "process", "time",
    "crypt", "zlib", "win", "sys", "os", "raw", "key", "mouse", "thread",
]


def aardio_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", ".build", "dist", "_backup", "test")]
        for name in files:
            if name.endswith(".aardio"):
                yield os.path.join(base, name)


def check(path):
    text = io.open(path, encoding="utf-8", errors="replace").read()

    # 只检查有 namespace 的文件
    if not re.search(r"^\s*namespace\s+\w+\s*\{", text, re.M):
        return None

    imported = set(re.findall(r"^\s*import\s+([\w\.]+)\s*;", text, re.M))
    roots = set(x.split(".")[0] for x in imported)

    risky = {}

    for lib in LIBS:
        if lib in roots:
            continue

        for m in re.finditer(r"(?<![\.\w])" + lib + r"\.", text):
            start = text.rfind("\n", 0, m.start()) + 1
            line = text[start:text.find("\n", m.start())]
            if "import" in line or line.lstrip().startswith("//"):
                continue
            risky[lib] = risky.get(lib, 0) + 1

    return risky


def main():
    bad = 0

    for path in sorted(aardio_files()):
        risky = check(path)
        if risky is None:
            continue

        rel = os.path.relpath(path, ROOT)
        if risky:
            bad += 1
            detail = ", ".join("%s×%d" % (k, v) for k, v in sorted(risky.items()))
            print("  [RISK] %-52s %s" % (rel, detail))
            print("         → 加 import，或写成 ..%s.xxx" % sorted(risky)[0])
        else:
            print("  [ OK ] %s" % rel)

    print()
    if bad:
        print("  RESULT: %d 个库存在未 import 的裸用" % bad)
        return 1

    print("  RESULT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
