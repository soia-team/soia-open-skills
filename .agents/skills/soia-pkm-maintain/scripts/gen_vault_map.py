#!/usr/bin/env python3
"""
gen_vault_map.py — 生成 Obsidian vault 的叶级地图（soia-pkm-maintain skill 机械层）

遍历全 vault 目录树，产出一份可点击跳转的 markdown 地图；`.md` 笔记渲染成
wikilink，非 `.md` 文件只列文件名。超过 40 个文件的目录做压缩显示（前 2 + 末 1 +
计数），避免地图本身变成又一个难读的大文件。头部的"文件数/目录数/GB"统计和生成
日期都是运行时动态计算，不是写死的历史快照。

用法：
  python3 gen_vault_map.py --vault /path/to/vault
  python3 gen_vault_map.py --vault /path/to/vault --output /tmp/preview.md   # 干跑预览，不覆盖 vault

默认输出路径：<vault>/20_资料库/OB知识库地图.md（可用 --output 覆盖）。
重新生成：让 AI 说"重建全库地图"（soia-pkm-maintain skill）。
"""
import argparse
import datetime
import os
import sys

from maintain_env import env_source_hint, load_private_env

load_private_env()

SKIP = {".obsidian", ".git", ".trash", "node_modules", ".DS_Store"}
DEFAULT_RELATIVE_OUTPUT = "20_资料库/OB知识库地图.md"


def parse_args():
    ap = argparse.ArgumentParser(description="生成 Obsidian vault 叶级地图")
    ap.add_argument(
        "--vault", default=os.environ.get("OBSIDIAN_VAULT"),
        help="vault 根目录（或在私有 config.yml设置 OBSIDIAN_VAULT，二选一，--vault 优先）",
    )
    ap.add_argument(
        "--output", default=None,
        help=f"输出文件路径（默认 <vault>/{DEFAULT_RELATIVE_OUTPUT}；"
             "传入其他路径可干跑预览，不覆盖 vault 原文件）",
    )
    return ap.parse_args()


def fmt_link(rel, name):
    if name.lower().endswith(".md"):
        return f"[[{rel[:-3]}|{name[:-3]}]]"
    return name


def build_map(root):
    out = []
    stats = {"files": 0, "dirs": 0, "size": 0}

    def walk(path, rel, depth):
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return
        dirs = [
            e for e in entries
            if os.path.isdir(os.path.join(path, e)) and e not in SKIP and not e.startswith(".")
        ]
        files = [
            e for e in entries
            if os.path.isfile(os.path.join(path, e)) and e not in SKIP and not e.startswith(".")
        ]
        ind = "  " * depth
        stats["files"] += len(files)
        for f in files:
            try:
                stats["size"] += os.path.getsize(os.path.join(path, f))
            except OSError:
                pass
        for d in dirs:
            sub = os.path.join(path, d)
            stats["dirs"] += 1
            nf = sum(len(fs) for _, _, fs in os.walk(sub))
            out.append(f"{ind}- **📂 {d}/** · {nf}项")
            walk(sub, f"{rel}{d}/", depth + 1)
        if len(files) > 40:
            for f in files[:2]:
                out.append(f"{ind}- {fmt_link(rel + f, f)}")
            out.append(f"{ind}- …（共{len(files)}个文件）")
            out.append(f"{ind}- {fmt_link(rel + files[-1], files[-1])}")
        else:
            for f in files:
                out.append(f"{ind}- {fmt_link(rel + f, f)}")

    walk(root, "", 0)
    return out, stats


def main():
    args = parse_args()
    if not args.vault:
        print(f"错误：未指定 --vault 且未在私有 config.yml设置 OBSIDIAN_VAULT（{env_source_hint()}）", file=sys.stderr)
        sys.exit(1)
    vault = os.path.abspath(os.path.expandvars(os.path.expanduser(args.vault)))
    if not os.path.isdir(vault):
        print(f"错误：vault 路径不存在：{vault}", file=sys.stderr)
        sys.exit(1)

    output = args.output or os.path.join(vault, DEFAULT_RELATIVE_OUTPUT)
    output = os.path.abspath(os.path.expanduser(output))

    out, stats = build_map(vault)
    today = datetime.date.today().isoformat()
    size_gb = stats["size"] / (1024 ** 3)
    header = f"""---
type: map
title: OB知识库地图（叶级）
updated: {today}
tags: [知识库, 地图, MOC]
---

# 🗺️ OB 知识库地图（到叶子节点）

> 全库约 {stats['files']:,} 文件 / {stats['dirs']:,} 目录 / {size_gb:.1f}GB。`.md` 笔记可直接点击跳转；`>40` 个文件的目录做了压缩显示（前2+末1+计数）。
> 重新生成：让 AI 说"重建全库地图"（soia-pkm-maintain skill）。

"""

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as fp:
        fp.write(header + "\n".join(out) + "\n")

    print(f"done, {len(out)} lines, {stats['files']} files / {stats['dirs']} dirs / {size_gb:.1f}GB")
    print(f"output: {output}")


if __name__ == "__main__":
    main()
