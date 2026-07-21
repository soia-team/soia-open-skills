#!/usr/bin/env python3
"""按类型分组生成图书馆 md 总览（单级类型分组，原为「孩子书库」场景）。

用法：
  python3 gen_genre_library_md.py                       # 用 --vault/OBSIDIAN_VAULT + 默认书库相对路径
  python3 gen_genre_library_md.py --vault ~/MyVault
  python3 gen_genre_library_md.py --base <vault-book-library-dir>
  python3 gen_genre_library_md.py --config my_genres.json
  python3 gen_genre_library_md.py --output /tmp/preview.md    # 干跑，不覆盖 vault 里的总览文件

vault 路径解析优先级：--vault > OBSIDIAN_VAULT env > 当前目录。
书库相对路径默认 `Books`，可用 --base 覆盖。
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

from library_env import env_source_hint, load_private_env

load_private_env()

DEFAULT_BASE = "Books"

# 类型显示顺序与中文描述（默认值，可用 --config 覆盖）
DEFAULT_GENRE_ORDER = [
    ["绘本",     "🎨 绘本（0-7岁）"],
    ["科普绘本", "🌱 科普绘本"],
    ["生活",     "👧 生活"],
    ["经典",     "📚 经典儿童文学"],
    ["奇幻",     "🧙 奇幻"],
    ["科幻",     "🚀 科幻"],
    ["冒险",     "🗺️ 冒险"],
    ["推理",     "🔍 推理"],
    ["幽默",     "😄 幽默"],
    ["寓言",     "🦊 寓言"],
    ["诗歌",     "🎭 诗歌"],
    ["漫画",     "📖 漫画"],
    ["散文",     "✒️ 散文"],
    ["科普",     "🔬 科普"],
    ["科学",     "🧪 科学（初中+）"],
    ["哲学",     "💭 哲学"],
    ["历史",     "🏛️ 历史"],
    ["地理",     "🌍 地理"],
    ["艺术",     "🎨 艺术"],
    ["国学",     "🀄 国学"],
    ["传记",     "👤 传记"],
]


def parse_args(argv):
    p = argparse.ArgumentParser(description="重生成按类型分组的图书馆 md 总览")
    p.add_argument("--vault", help="Obsidian vault 根目录（默认读 OBSIDIAN_VAULT env）")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"书库相对 vault 的路径（默认 {DEFAULT_BASE}）")
    p.add_argument("--config", help="JSON 文件，覆盖默认类型表（键：genre_order）")
    p.add_argument("--output", help="输出文件路径（默认写回 vault 的 00_图书馆/图书馆-按类型.md；"
                                     "传此参数可干跑到别处，不覆盖 vault 原文件）")
    return p.parse_args(argv)


def resolve_vault(args):
    import os
    if args.vault:
        return Path(args.vault).expanduser()
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    print(f"❌ 未指定 vault：请传 --vault 或在私有 config.yml中设置 OBSIDIAN_VAULT（{env_source_hint()}）", file=sys.stderr)
    sys.exit(1)


def load_config(config_path):
    genre_order = DEFAULT_GENRE_ORDER
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if "genre_order" in cfg:
            genre_order = cfg["genre_order"]
    return [tuple(x) for x in genre_order]


def parse_frontmatter(text):
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm


def stars(n):
    """难度图标"""
    return '★' * n + '☆' * (3 - n)


def main(argv):
    args = parse_args(argv)
    vault = resolve_vault(args)
    base = vault / args.base
    src = base / "00_图书馆" / "书目"
    dst = Path(args.output).expanduser() if args.output else base / "00_图书馆" / "图书馆-按类型.md"

    genre_order = load_config(args.config)

    if not src.is_dir():
        print(f"❌ 书目目录不存在：{src}", file=sys.stderr)
        sys.exit(1)

    # 收集所有书（递归子目录）
    books = []
    for f in sorted(src.rglob("*.md")):
        text = f.read_text(encoding='utf-8')
        fm = parse_frontmatter(text)
        if not fm.get('title'):
            continue
        # 提取推荐理由（## 推荐理由 后第一段）
        reason_match = re.search(r'## 推荐理由\s*\n+([^\n#]+)', text)
        reason = reason_match.group(1).strip() if reason_match else ""
        books.append({
            'title':    fm.get('title', f.stem),
            'author':   fm.get('author', ''),
            'age_min':  int(fm.get('age_min', 99)),
            'age_band': fm.get('age_band', ''),
            'genre':    fm.get('genre', '其他'),
            'level':    int(fm.get('level', 2)),
            'gender':   fm.get('gender', '通用'),
            'theme':    fm.get('theme', ''),
            'reason':   reason,
            'filename': f.stem,
            'subdir':   f.parent.name,
        })

    # 按类型分组
    groups = defaultdict(list)
    for b in books:
        groups[b['genre']].append(b)
    # 每组内按 age_min 排序
    for g in groups:
        groups[g].sort(key=lambda x: (x['age_min'], x['title']))

    # 生成 md
    out = []
    out.append("# 图书馆 · 按类型浏览\n")
    out.append(f"> 全部 {len(books)} 本书 · 按类型分组，方便快速浏览与挑选\n")
    out.append("> 数据库视图请打开 [[图书馆.base]]，本页是 markdown 版静态视图\n")
    out.append("\n---\n")

    # 目录（用 wikilink 跳转同文件标题，避开 markdown 链接括号歧义）
    out.append("## 目录\n")
    for genre_key, genre_name in genre_order:
        if genre_key in groups:
            count = len(groups[genre_key])
            out.append(f"- [[#{genre_name}|{genre_name}（{count}本）]]")
    out.append("\n---\n")

    # 每个类型一节
    for genre_key, genre_name in genre_order:
        if genre_key not in groups:
            continue
        books_g = groups[genre_key]
        out.append(f"\n## {genre_name}\n")
        out.append(f"共 **{len(books_g)}** 本\n")
        out.append("| 书名 | 作者 | 适读 | 难度 | 性别 | 主题 | 推荐理由 |")
        out.append("|------|------|------|------|------|------|---------|")
        for b in books_g:
            # 短 wikilink（书名全 vault 唯一，无路径无 alias，Live Preview 单击即跳）
            out.append(
                f"| [[{b['filename']}]] "
                f"| {b['author']} "
                f"| {b['age_band']} "
                f"| {stars(b['level'])} "
                f"| {b['gender']} "
                f"| {b['theme']} "
                f"| {b['reason']} |"
            )
        out.append("")

    out.append("\n---\n")
    out.append(f"\n_共 {len(books)} 本 · 自动生成，请勿手工编辑（数据源：`书目/` 目录）_")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text('\n'.join(out), encoding='utf-8')
    print(f"已写入：{dst}")
    print(f"共 {len(books)} 本书，{len(groups)} 个类型")


if __name__ == "__main__":
    main(sys.argv[1:])
