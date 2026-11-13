#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动库解析的离线回归与自检。

用途
----
1. 自检（invariants）：任何版本解析出来后必须满足
   - 同一 group:artifact:classifier 只出现一次
   - classpath 里每个文件都在磁盘上
   - 客户端 jar 能找到
   - natives 包存在
2. 快照比对：把每个版本的 classpath 记进 tools/snapshots/classpath.json，
   以后跑一次就能看出"这次改动/环境变化"有没有把某个版本弄坏。

怎么跑
------
    python tools/check-classpath.py            # 比对（首次会生成快照）
    python tools/check-classpath.py --update   # 重写快照
    python tools/check-classpath.py --show 1.16.5-Fabric 0.16.0   # 打印某个版本的解析结果

注意
----
这里是我们 core 解析规则的一份**镜像**。改 `core/launch/MMMLC.aardio` 的解析逻辑时，
这个文件要同步改 —— 它抓的是"磁盘/清单变化带来的漂移"与"不变量被破坏"，
不是替代真机启动。
"""
import argparse
import io
import json
import os
import sys

# 默认要检查的游戏根目录（存在才检查）
ROOTS = [
    r"D:\PCL\.minecraft",
    r"D:\making_modpacks\.minecraft",
    r"C:\Users\DELL\AppData\Roaming\.minecraft",
]

SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots", "classpath.json")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------- 解析规则（与 core 对齐） ----------

def windows_ok(lib):
    rules = lib.get("rules")
    if not rules:
        return True
    allowed = False
    for r in rules:
        act = r.get("action")
        osn = (r.get("os") or {}).get("name")
        if act == "allow" and (osn is None or osn == "windows"):
            allowed = True
        if act == "disallow" and osn in (None, "windows"):
            allowed = False
    return allowed


def maven_rel(name):
    p = name.split(":")
    if len(p) < 3:
        return None
    f = "%s-%s" % (p[1], p[2])
    if len(p) > 3 and p[3]:
        f += "-" + p[3]
    return p[0].replace(".", "/") + "/" + p[1] + "/" + p[2] + "/" + f + ".jar"


def native_ok(cls):
    """只取当前平台（Windows x86_64）的 natives。"""
    if "arm64" in cls:
        return False
    if "macos" in cls or "linux" in cls:
        return False
    if "x86" in cls and "x86_64" not in cls:
        return False
    return True


def version_tuple(v):
    out = []
    for part in str(v or "").split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        out.append(int(num) if num else 0)
    return out


def newer(a, b):
    x, y = version_tuple(a), version_tuple(b)
    n = max(len(x), len(y))
    x += [0] * (n - len(x))
    y += [0] * (n - len(y))
    return x > y


def dedupe(entries):
    """与 core 一致：key 相同的只留一份，位置用首次出现、内容用版本最高的那份。"""
    first, best = {}, {}
    for i, (key, rel, ver) in enumerate(entries):
        if key not in first:
            first[key] = i
        if key not in best or newer(ver, entries[best[key]][2]):
            best[key] = i

    out, seen = [], set()
    for i, (key, rel, ver) in enumerate(entries):
        if key in seen:
            continue
        seen.add(key)
        out.append(entries[best[key]])

    # 同一路径出现两次也去掉
    uniq, paths = [], set()
    for key, rel, ver in out:
        if rel in paths:
            continue
        paths.add(rel)
        uniq.append((key, rel, ver))

    return uniq


def load_chain(root, name, depth=0):
    p = os.path.join(root, "versions", name, name + ".json")
    if not os.path.exists(p) or depth > 4:
        return None
    j = json.load(io.open(p, encoding="utf-8"))
    chain = [j]
    parent = j.get("inheritsFrom")
    if parent:
        pj = load_chain(root, parent, depth + 1)
        if pj:
            chain = pj + chain
    return chain


def resolve(root, name):
    """返回 (entries, natives, missing, main_class, java_version)。

    entries: [(group:artifact[:classifier], 相对路径)]
    """
    chain = load_chain(root, name)
    if not chain:
        return None

    libs_dir = os.path.join(root, "libraries")
    entries, natives, missing = [], [], []
    main_class = ""
    java_version = None

    for j in chain:
        if j.get("mainClass"):
            main_class = j["mainClass"]
        jv = (j.get("javaVersion") or {}).get("majorVersion")
        if jv:
            java_version = jv

        for lib in j.get("libraries", []):
            n = lib.get("name")
            if not n or not windows_ok(lib):
                continue

            parted = n.split(":")
            cls = parted[3] if len(parted) > 3 else None

            if cls and cls.startswith("natives-"):
                if not native_ok(cls):
                    continue

            rel = ((lib.get("downloads") or {}).get("artifact") or {}).get("path")
            if not rel:
                rel = maven_rel(n)
            if not rel:
                continue

            key = parted[0] + ":" + parted[1] + ((":" + cls) if cls else "")
            ver = parted[2] if len(parted) > 2 else ""
            p = os.path.join(libs_dir, rel.replace("/", os.sep))

            if os.path.exists(p):
                entries.append((key, rel, ver))
            else:
                # 老格式 natives 的 artifact 常是占位空包，不算缺
                if not lib.get("natives"):
                    missing.append(rel)

            # 老格式 natives：natives.windows -> classifiers
            nat = (lib.get("natives") or {}).get("windows")
            if nat:
                nat = nat.replace("${arch}", "64")
                ent = ((lib.get("downloads") or {}).get("classifiers") or {}).get(nat)
                if ent and ent.get("path"):
                    np = os.path.join(libs_dir, ent["path"].replace("/", os.sep))
                    if os.path.exists(np):
                        natives.append(ent["path"])
                    else:
                        missing.append(ent["path"])

    jar_id = chain[-1].get("jar") or name
    client = os.path.join(root, "versions", name if jar_id == name else jar_id, jar_id + ".jar")
    if not os.path.exists(client):
        client = os.path.join(root, "versions", name, name + ".jar")
    if not os.path.exists(client):
        missing.append("(客户端 jar) " + name + ".jar")

    entries = dedupe(entries)

    return {
        "entries": entries,
        "natives": natives,
        "missing": missing,
        "main_class": main_class,
        "java_version": java_version,
    }


# ---------- 不变量 ----------

def check_invariants(root, name, res):
    problems = []

    seen = {}
    for key, rel, _ver in res["entries"]:
        if key in seen:
            problems.append("重复条目 %s（%s 与 %s）" % (key, seen[key], rel))
        seen[key] = rel

    if not res["entries"]:
        problems.append("classpath 为空")

    if res["missing"]:
        problems.append("缺 %d 个文件：%s" % (len(res["missing"]), ", ".join(res["missing"][:3])))

    return problems


# ---------- 主流程 ----------

def pick_versions(root):
    vdir = os.path.join(root, "versions")
    if not os.path.isdir(vdir):
        return []
    out = []
    for d in sorted(os.listdir(vdir)):
        if os.path.exists(os.path.join(vdir, d, d + ".json")):
            out.append(d)
    return out


def snapshot_key(root, name):
    return root + "::" + name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="重写快照")
    ap.add_argument("--show", help="打印指定版本的解析结果")
    ap.add_argument("--quiet", action="store_true", help="只报问题")
    args = ap.parse_args()

    if args.show:
        for root in ROOTS:
            if not os.path.isdir(root):
                continue
            res = resolve(root, args.show)
            if not res:
                continue
            print("== %s / %s" % (root, args.show))
            print("   主类: %s   Java: %s" % (res["main_class"], res["java_version"]))
            print("   classpath %d 项:" % len(res["entries"]))
            for key, rel, ver in res["entries"]:
                print("     %-46s %s" % ((key + ":" + ver)[:46], rel))
            print("   natives %d 个，缺 %d 个" % (len(res["natives"]), len(res["missing"])))
            for m in res["missing"]:
                print("     缺 " + m)
            return 0
        print("没找到版本：" + args.show)
        return 1

    old = {}
    if os.path.exists(SNAPSHOT):
        old = json.load(io.open(SNAPSHOT, encoding="utf-8"))

    new = {}
    bad = 0       # 快照漂移：算失败
    warn = 0      # 缺文件这类环境事实：只提醒
    checked = 0
    skipped = []

    for root in ROOTS:
        if not os.path.isdir(root):
            continue
        if not os.path.isdir(os.path.join(root, "libraries")):
            skipped.append(root)
            continue
        for name in pick_versions(root):
            res = resolve(root, name)
            if not res:
                continue
            checked += 1
            k = snapshot_key(root, name)
            new[k] = {
                "count": len(res["entries"]),
                "natives": len(res["natives"]),
                "java": res["java_version"],
                "main": res["main_class"],
                "jars": sorted([rel.split("/")[-1] for _k, rel, _v in res["entries"]]),
            }

            problems = check_invariants(root, name, res)
            if problems:
                warn += len(problems)
                print("[提醒] %s / %s" % (root, name))
                for p in problems:
                    print("    " + p)

    # 快照比对
    if args.update or not old:
        os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
        io.open(SNAPSHOT, "w", encoding="utf-8").write(
            json.dumps(new, ensure_ascii=False, indent=1, sort_keys=True))
        if not args.quiet:
            print("已写入快照：%d 个版本 → %s" % (len(new), SNAPSHOT))
    else:
        for k in sorted(set(old) | set(new)):
            a, b = old.get(k), new.get(k)
            if a is None:
                print("[新增版本] " + k)
                continue
            if b is None:
                print("[版本消失] " + k)
                continue
            if a["count"] != b["count"]:
                print("[条目数变化] %s：%d → %d" % (k, a["count"], b["count"]))
                bad += 1
            else:
                gone = set(a["jars"]) - set(b["jars"])
                more = set(b["jars"]) - set(a["jars"])
                if gone or more:
                    print("[库变了] " + k)
                    for x in sorted(gone):
                        print("    - " + x)
                    for x in sorted(more):
                        print("    + " + x)
                    bad += 1
            if a["java"] != b["java"]:
                print("[Java 下限变化] %s：%s → %s" % (k, a["java"], b["java"]))
                bad += 1

    if not args.quiet:
        for root in skipped:
            print("跳过（没有 libraries）：" + root)
        print("检查 %d 个版本：漂移 %d 处，提醒 %d 条。" % (checked, bad, warn))

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
