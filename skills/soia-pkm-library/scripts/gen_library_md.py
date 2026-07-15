#!/usr/bin/env python3
"""个人书库：按一级分类+二级分类生成 markdown 总览

用法：
  python3 gen_library_md.py                       # 用 --vault/OBSIDIAN_VAULT + 默认书库相对路径
  python3 gen_library_md.py --vault ~/MyVault
  python3 gen_library_md.py --base 40_图书视频馆/30_个人书库
  python3 gen_library_md.py --config my_categories.json
  python3 gen_library_md.py --output /tmp/preview.md    # 干跑，不覆盖 vault 里的总览文件

vault 路径解析优先级：--vault > OBSIDIAN_VAULT env > 当前目录。
书库相对路径默认 `40_图书视频馆/30_个人书库`，可用 --base 覆盖。
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

from library_env import env_source_hint, load_private_env

load_private_env()

DEFAULT_BASE = "40_图书视频馆/30_个人书库"

# 一级分类显示顺序与图标（默认值，可用 --config 的 JSON 覆盖）
DEFAULT_CATEGORY_ORDER = [
    ['经济理财', '💰 经济理财'],
    ['个人成长', '🌱 个人成长'],
    ['心理',     '🧠 心理'],
    ['哲学宗教', '💭 哲学宗教'],
    ['文学',     '📖 文学'],
    ['精品小说', '📚 精品小说'],
    ['历史',     '🏛️ 历史'],
    ['政治军事', '⚔️ 政治军事'],
    ['社会文化', '🌍 社会文化'],
    ['教育学习', '🎓 教育学习'],
    ['科学技术', '🔬 科学技术'],
    ['计算机',   '💻 计算机'],
    ['生活百科', '🍳 生活百科'],
    ['人物传记', '👤 人物传记'],
    ['医学健康', '🏥 医学健康'],
    ['童书',     '🧒 童书'],
    ['期刊杂志', '📰 期刊杂志'],
    ['未分类',   '❓ 未分类'],
]

# 二级分类显示顺序：来自各大类目录序号（如 01_财经 → 财经）
DEFAULT_SUB_ORDER_BY_DIR = {
    # 经济理财
    '经济学': 1, '财经': 2, '团队领导': 3, '管理哲学': 4, '项目管理': 5, '理财': 6, '商业': 7, '保险': 8,
    # 个人成长
    '沟通表达': 1, '人生哲学': 2, '认知思维': 3, '情绪心灵': 4, '人在职场': 5,
    # 心理
    '心理学研究': 1, '心理学应用': 2,
    # 哲学宗教
    '西方哲学': 1, '东方哲学': 2,
    # 文学
    '散文杂著': 1, '欧美经典': 2, '当代外国': 3, '少儿成长': 4, '外国文学': 5, '经典作品': 6, '文学鉴赏': 7, '古代诗词': 8,
    # 精品小说
    '社会小说': 1, '悬疑推理': 2,
    # 历史
    '史学方法': 1, '历史典籍': 2, '中国古代': 3, '中国近现代': 4, '世界史': 5, '历史小说': 6,
    # 政治军事
    '政治': 1, '军事': 2,
    # 社会文化
    '社科': 1, '文化': 2,
    # 教育学习
    '育儿': 1,
    # 科学技术
    '自然科学': 1, '科学科普': 2,
    # 计算机
    '计算机综合': 1, '编程设计': 2,
    # 生活百科
    '时尚': 1, '美食': 2,
    # 人物传记
    '政治人物': 1, '商业人物': 2, '文学家': 3, '思想家': 4,
}


def parse_args(argv):
    p = argparse.ArgumentParser(description="重生成个人书库按分类 md 总览")
    p.add_argument("--vault", help="Obsidian vault 根目录（默认读 OBSIDIAN_VAULT env）")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"书库相对 vault 的路径（默认 {DEFAULT_BASE}）")
    p.add_argument("--config", help="JSON 文件，覆盖默认分类表（键：category_order / sub_order_by_dir）")
    p.add_argument("--output", help="输出文件路径（默认写回 vault 的 00_图书馆/图书馆-按分类.md；"
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
    """返回 (category_order, sub_order_by_dir)，未传 --config 则用默认值。"""
    category_order = DEFAULT_CATEGORY_ORDER
    sub_order_by_dir = DEFAULT_SUB_ORDER_BY_DIR
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if "category_order" in cfg:
            category_order = cfg["category_order"]
        if "sub_order_by_dir" in cfg:
            sub_order_by_dir = cfg["sub_order_by_dir"]
    return [tuple(x) for x in category_order], sub_order_by_dir


def parse_fm(text):
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm


def display_array(v):
    v = v.strip().strip('"').strip("'")
    if v.startswith('[') and v.endswith(']'):
        v = v[1:-1]
    return v.strip()


def main(argv):
    args = parse_args(argv)
    vault = resolve_vault(args)
    base = vault / args.base
    src = base / "00_图书馆" / "书目"
    dst = Path(args.output).expanduser() if args.output else base / "00_图书馆" / "图书馆-按分类.md"

    category_order, sub_order_by_dir = load_config(args.config)

    if not src.is_dir():
        print(f"❌ 书目目录不存在：{src}", file=sys.stderr)
        sys.exit(1)

    books = []
    for f in src.rglob("*.md"):
        fm = parse_fm(f.read_text(encoding='utf-8'))
        if not fm.get('title'):
            continue
        books.append({
            'title':       fm['title'],
            'author':      fm.get('author', '').strip('"').strip("'"),
            'category':    fm.get('category', ''),
            'subcategory': fm.get('subcategory', '').strip('"').strip("'") or '其他',
            'source':      display_array(fm.get('source', '')),
            'note':        fm.get('note', ''),
            'filename':    f.stem,
        })

    # 按 category → subcategory → books 三层分组
    groups = defaultdict(lambda: defaultdict(list))
    for b in books:
        groups[b['category']][b['subcategory']].append(b)
    for cat in groups:
        for sub in groups[cat]:
            groups[cat][sub].sort(key=lambda x: x['title'])

    def sub_sort_key(s):
        return (sub_order_by_dir.get(s, 99), s)

    out = []
    out.append("# 个人书库 · 按分类浏览\n")
    out.append(f"> 全部 **{len(books)}** 本书目 · 数据库视图打开 [[图书馆.base]]\n")
    out.append("> 我的阅读状态与读书笔记在 [[../阅读记录/阅读记录.base|阅读记录]]\n")
    out.append("\n---\n")

    # 统计（按一级 + 二级）
    out.append("## 统计\n")
    out.append("| 分类 | 二级 | 书目数 |")
    out.append("|------|------|--------|")
    for cat_key, cat_name in category_order:
        if cat_key not in groups:
            continue
        cat_total = sum(len(v) for v in groups[cat_key].values())
        subs = sorted(groups[cat_key].keys(), key=sub_sort_key)
        for i, sub in enumerate(subs):
            n = len(groups[cat_key][sub])
            cat_cell = f"**{cat_name}** ({cat_total})" if i == 0 else ""
            out.append(f"| {cat_cell} | {sub} | {n} |")
    out.append(f"| **合计** | | **{len(books)}** |")
    out.append("\n---\n")

    # 目录（一级 + 二级 嵌套）
    out.append("## 目录\n")
    for cat_key, cat_name in category_order:
        if cat_key not in groups:
            continue
        cat_total = sum(len(v) for v in groups[cat_key].values())
        out.append(f"- [[#{cat_name}|{cat_name}（{cat_total}本）]]")
        emoji_prefix = cat_name.split(' ')[0]
        subs = sorted(groups[cat_key].keys(), key=sub_sort_key)
        for sub in subs:
            n = len(groups[cat_key][sub])
            out.append(f"  - [[#{emoji_prefix} {sub}|{sub}（{n}本）]]")
    out.append("\n---\n")

    # 各一级分类 → 二级分类 → 书目
    for cat_key, cat_name in category_order:
        if cat_key not in groups:
            continue
        cat_total = sum(len(v) for v in groups[cat_key].values())
        out.append(f"\n## {cat_name}\n")
        out.append(f"共 **{cat_total}** 本\n")

        emoji_prefix = cat_name.split(' ')[0]
        subs = sorted(groups[cat_key].keys(), key=sub_sort_key)

        sub_links = " · ".join(
            f"[[#{emoji_prefix} {s}|{s} {len(groups[cat_key][s])}]]"
            for s in subs
        )
        out.append(f"**跳转**：{sub_links}\n")

        for sub in subs:
            bs = groups[cat_key][sub]
            out.append(f"\n### {emoji_prefix} {sub}（{len(bs)} 本）\n")
            out.append("| 书名 | 作者 | 二级 | 来源 | 备注 |")
            out.append("|------|------|------|------|------|")
            for b in bs:
                out.append(
                    f"| [[{b['filename']}]] "
                    f"| {b['author']} "
                    f"| {b['subcategory']} "
                    f"| {b['source']} "
                    f"| {b['note']} |"
                )
            out.append("")
            out.append(f"[⬆️ 返回 {cat_name} 目录](#{cat_name.replace(' ', '%20')}) ｜ [📚 全局目录](#目录)\n")

    out.append("\n---\n")
    out.append(f"_共 {len(books)} 本 · 自动生成，数据源：`书目/` 目录_")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text('\n'.join(out), encoding='utf-8')
    print(f"已写入：{dst}")
    print(f"共 {len(books)} 本，{len(groups)} 个一级分类")


if __name__ == "__main__":
    main(sys.argv[1:])
