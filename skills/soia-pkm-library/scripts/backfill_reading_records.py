#!/usr/bin/env python3
"""补建阅读记录：为图书馆里「有书卡、无阅读记录」的书批量生成「待读」记录。

- 幂等：目标文件已存在则跳过，可重复运行（新书入库后再跑一次即可补齐）。
- 默认状态「待读」，存到 阅读记录/待读/。
- 透传书卡的可选字段（bookId/readerLink/deepLink/cover/pdf_path），方便日后转「在读」。

判定「无阅读记录」的口径与 gen_records_md.py 一致：
阅读记录通过 book: "[[书名]]" 反查书卡（stem 或 title），没有任何记录指向的书卡即为待补。

用法：
  python3 backfill_reading_records.py                       # 用 --vault/OBSIDIAN_VAULT + 默认书库相对路径
  python3 backfill_reading_records.py --vault ~/MyVault
  python3 backfill_reading_records.py --base 40_图书视频馆/30_个人书库
  python3 backfill_reading_records.py --config my_backfill.json

vault 路径解析优先级：--vault > OBSIDIAN_VAULT env > 当前目录。
书库相对路径默认 `40_图书视频馆/30_个人书库`，可用 --base 覆盖。
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

from soia_env import env_source_hint, load_private_env

load_private_env()

DEFAULT_BASE = "40_图书视频馆/30_个人书库"

DEFAULT_STATUS = "待读"
DEFAULT_ICON = "📥"
DEFAULT_PASSTHROUGH = ["bookId", "readerLink", "deepLink", "cover", "pdf_path"]


def parse_args(argv):
    p = argparse.ArgumentParser(description="有书卡无阅读记录 → 补建「待读」记录")
    p.add_argument("--vault", help="Obsidian vault 根目录（默认读 OBSIDIAN_VAULT env）")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"书库相对 vault 的路径（默认 {DEFAULT_BASE}）")
    p.add_argument("--config", help="JSON 文件，覆盖默认值（键：default_status / icon / passthrough）")
    return p.parse_args(argv)


def resolve_vault(args):
    if args.vault:
        return Path(args.vault).expanduser()
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    print(f"❌ 未指定 vault：请传 --vault 或在私有 config.yml中设置 OBSIDIAN_VAULT（{env_source_hint()}）", file=sys.stderr)
    sys.exit(1)


def load_config(config_path):
    default_status = DEFAULT_STATUS
    icon = DEFAULT_ICON
    passthrough = DEFAULT_PASSTHROUGH
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if "default_status" in cfg:
            default_status = cfg["default_status"]
        if "icon" in cfg:
            icon = cfg["icon"]
        if "passthrough" in cfg:
            passthrough = cfg["passthrough"]
    return default_status, icon, list(passthrough)


def parse_fm(text):
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ':' not in line:
            continue
        k, v = line.split(':', 1)
        v = re.sub(r'\s+#.*$', '', v.strip())
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def wl(v):
    v = (v or '').strip()
    m = re.match(r'^\[\[(.+?)\]\]$', v)
    return (m.group(1) if m else v).split('|')[0].strip()


def main(argv):
    args = parse_args(argv)
    vault = resolve_vault(args)
    base = vault / args.base
    lib = base / "00_图书馆/书目"
    rec = base / "阅读记录"
    dst_dir = rec / "待读"

    default_status, icon, passthrough = load_config(args.config)

    if not lib.is_dir():
        print(f"❌ 书目目录不存在：{lib}", file=sys.stderr)
        sys.exit(1)
    if not rec.is_dir():
        print(f"❌ 阅读记录目录不存在：{rec}", file=sys.stderr)
        sys.exit(1)

    # ---- 1. 图书馆书卡索引 ----
    lib_index, lib_titles = {}, defaultdict(list)
    for f in lib.rglob("*.md"):
        if "_模板" in f.parts:
            continue
        fm = parse_fm(f.read_text(encoding='utf-8'))
        lib_index[f.stem] = fm
        if fm.get('title'):
            lib_titles[fm['title']].append(f.stem)

    # ---- 2. 已被阅读记录引用到的书卡 ----
    referenced = set()
    for f in rec.rglob("*.md"):
        if "_模板" in f.parts or f.name == "阅读记录-总览.md":
            continue
        fm = parse_fm(f.read_text(encoding='utf-8'))
        if not fm.get('title'):
            continue
        b = wl(fm.get('book', ''))
        if b in lib_index:
            referenced.add(b)
        elif b in lib_titles:
            for s in lib_titles[b]:
                referenced.add(s)

    unread = [(s, lib_index[s]) for s in sorted(lib_index) if s not in referenced]

    # ---- 3. 逐本补建「待读」记录 ----
    dst_dir.mkdir(parents=True, exist_ok=True)
    created, skipped = 0, 0
    for stem, fm in unread:
        dst = dst_dir / f"{stem}.md"
        if dst.exists():
            skipped += 1
            continue

        title = fm.get('title') or stem
        author = fm.get('author', '')
        category = fm.get('category', '')
        source = fm.get('source', '')

        fmlines = [
            "---", "tags: [阅读记录]", f"title: {title}",
            f'book: "[[{stem}]]"', f"status: {default_status}",
            "started:", "finished:", "rating:",
            f"category: {category}", f"author: {author}",
        ]
        if source:
            fmlines.append(f"source: {source}")
        for key in passthrough:
            if fm.get(key):
                fmlines.append(f'{key}: "{fm[key]}"')
        fmlines.append("---")

        parts = []
        if author:
            parts.append(f"**{author}**")
        if category:
            parts.append(category)
        parts.append(f"{icon} {default_status}")
        meta = " ｜ ".join(parts)

        body = (
            f"\n# {title} · 阅读记录\n\n"
            f"> {meta}\n"
            f"> 书卡：[[{stem}]]\n\n"
            f"## 选读理由\n\n"
            f"> 为什么想读 / 从哪儿听说的\n\n"
            f"## 读书笔记\n\n"
            f"> 开始读之后在这里记\n"
        )

        fm_block = "\n".join(line.rstrip() for line in fmlines)  # 空值字段不留尾随空格
        dst.write_text(fm_block + "\n" + body, encoding='utf-8')
        created += 1

    print(f"补建 {created} 条，跳过（已存在）{skipped} 条 → {dst_dir}")
    print(f"图书馆 {len(lib_index)} 本，已有记录 {len(referenced)} 本，本次识别待补 {len(unread)} 本")


if __name__ == "__main__":
    main(sys.argv[1:])
