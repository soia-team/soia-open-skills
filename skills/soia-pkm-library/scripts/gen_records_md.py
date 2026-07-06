#!/usr/bin/env python3
"""个人阅读记录：按（书卡权威）一级分类+二级分类生成 markdown 总览，
每本书附带状态/开始时间/完成时间/进度/最后阅读/划线数等阅读属性。

分类以图书馆书卡的 category/subcategory 为准（阅读记录自己的 category
字段是重构前的旧值，可能过时），通过 book: "[[书名]]" 反查书卡。

用法：
  python3 gen_records_md.py                       # 用 --vault/OBSIDIAN_VAULT + 默认书库相对路径
  python3 gen_records_md.py --vault ~/MyVault
  python3 gen_records_md.py --base 40_阅读与摘抄/30_个人书库
  python3 gen_records_md.py --config my_categories.json
  python3 gen_records_md.py --output /tmp/preview.md    # 干跑，不覆盖 vault 里的总览文件

vault 路径解析优先级：--vault > OBSIDIAN_VAULT env > 当前目录。
书库相对路径默认 `40_阅读与摘抄/30_个人书库`，可用 --base 覆盖。
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

DEFAULT_BASE = "40_阅读与摘抄/30_个人书库"

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

# 阅读记录生命周期 7 态（默认值，可用 --config 覆盖 status_icon/status_order）
DEFAULT_STATUS_ICON = {
    '想读': '💭',
    '待读': '📥',
    '计划读': '🗓️',
    '在读': '🔖',
    '暂停': '⏸️',
    '搁置': '📕',
    '完成': '✅',
}

# 状态展示顺序：按阅读推进的生命周期排列
DEFAULT_STATUS_ORDER = ['想读', '待读', '计划读', '在读', '暂停', '搁置', '完成']


def parse_args(argv):
    p = argparse.ArgumentParser(description="重生成个人阅读记录总览")
    p.add_argument("--vault", help="Obsidian vault 根目录（默认读 OBSIDIAN_VAULT env）")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"书库相对 vault 的路径（默认 {DEFAULT_BASE}）")
    p.add_argument("--config", help="JSON 文件，覆盖默认分类表/状态表"
                                     "（键：category_order / sub_order_by_dir / status_icon / status_order）")
    p.add_argument("--output", help="输出文件路径（默认写回 vault 的 阅读记录/阅读记录-总览.md；"
                                     "传此参数可干跑到别处，不覆盖 vault 原文件）")
    return p.parse_args(argv)


def resolve_vault(args):
    import os
    if args.vault:
        return Path(args.vault).expanduser()
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    print("❌ 未指定 vault：请传 --vault 或设置 OBSIDIAN_VAULT env", file=sys.stderr)
    sys.exit(1)


def load_config(config_path):
    category_order = DEFAULT_CATEGORY_ORDER
    sub_order_by_dir = DEFAULT_SUB_ORDER_BY_DIR
    status_icon = DEFAULT_STATUS_ICON
    status_order = DEFAULT_STATUS_ORDER
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if "category_order" in cfg:
            category_order = cfg["category_order"]
        if "sub_order_by_dir" in cfg:
            sub_order_by_dir = cfg["sub_order_by_dir"]
        if "status_icon" in cfg:
            status_icon = cfg["status_icon"]
        if "status_order" in cfg:
            status_order = cfg["status_order"]
    return [tuple(x) for x in category_order], sub_order_by_dir, status_icon, list(status_order)


def parse_fm(text):
    """解析 frontmatter，顺带砍掉行尾 `# 注释`（book/source 字段常带）。"""
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


def parse_wikilink(v):
    v = (v or '').strip()
    m = re.match(r'^\[\[(.+?)\]\]$', v)
    target = m.group(1) if m else v
    return target.split('|')[0].strip()


def main(argv):
    args = parse_args(argv)
    vault = resolve_vault(args)
    base = vault / args.base
    lib_src = base / "00_图书馆" / "书目"
    rec_src = base / "阅读记录"
    dst = Path(args.output).expanduser() if args.output else rec_src / "阅读记录-总览.md"

    category_order, sub_order_by_dir, status_icon, status_order = load_config(args.config)

    if not lib_src.is_dir():
        print(f"❌ 书目目录不存在：{lib_src}", file=sys.stderr)
        sys.exit(1)
    if not rec_src.is_dir():
        print(f"❌ 阅读记录目录不存在：{rec_src}", file=sys.stderr)
        sys.exit(1)

    # ---- 1. 建立书卡索引（权威分类来源）----
    lib_by_stem = {}
    lib_by_title = {}
    for f in lib_src.rglob("*.md"):
        fm = parse_fm(f.read_text(encoding='utf-8'))
        lib_by_stem[f.stem] = fm
        if fm.get('title'):
            lib_by_title[fm['title']] = fm

    # ---- 2. 解析阅读记录，反查书卡拿权威分类 ----
    records = []
    no_card = 0
    for f in rec_src.rglob("*.md"):
        if "_模板" in f.parts or f.name == "阅读记录-总览.md":
            continue
        fm = parse_fm(f.read_text(encoding='utf-8'))
        if not fm.get('title'):
            continue

        target = parse_wikilink(fm.get('book', ''))
        card = lib_by_stem.get(target) or lib_by_title.get(target)
        if card:
            category = card.get('category') or '未分类'
            subcategory = card.get('subcategory') or '其他'
        else:
            no_card += 1
            print(f"[警告] 找不到对应书卡，使用记录自带分类：{f.name}（book={target!r}）", file=sys.stderr)
            category = fm.get('category') or '未分类'
            subcategory = '其他'

        status = fm.get('status', '')
        progress = fm.get('progress', '')
        progress_disp = '100%' if status == '完成' else (f"{progress}%" if progress else '')

        records.append({
            'title':             fm['title'],
            'author':            fm.get('author', ''),
            'category':          category,
            'subcategory':       subcategory,
            'status':            status,
            'started':           fm.get('started', ''),
            'finished':          fm.get('finished', ''),
            'progress_disp':     progress_disp,
            'last_read':         fm.get('last_read', ''),
            'highlights_count':  fm.get('highlights_count', ''),
            'filename':          f.stem,
        })

    # ---- 3. 按 category → subcategory → 记录 分组 ----
    groups = defaultdict(lambda: defaultdict(list))
    for r in records:
        groups[r['category']][r['subcategory']].append(r)
    for cat in groups:
        for sub in groups[cat]:
            groups[cat][sub].sort(key=lambda x: x['title'])

    def sub_sort_key(s):
        return (sub_order_by_dir.get(s, 99), s)

    # ---- 4. 状态统计 ----
    status_count = defaultdict(int)
    for r in records:
        status_count[r['status'] or '未知'] += 1

    out = []
    out.append("# 个人阅读记录 · 总览\n")
    out.append(f"> 全部 **{len(records)}** 条记录 · 数据库视图打开 [[阅读记录.base]]\n")
    out.append("> 完整书目仓库在 [[../00_图书馆/图书馆-按分类.md|图书馆]]\n")
    out.append("\n---\n")

    # 阅读状态统计
    out.append("## 阅读状态\n")
    out.append("| 状态 | 数量 |")
    out.append("|------|------|")
    for s in status_order:
        if status_count.get(s):
            out.append(f"| {status_icon.get(s, '')} {s} | {status_count[s]} |")
    out.append(f"| **合计** | **{len(records)}** |")
    out.append("\n---\n")

    # 按分类统计（一级 + 二级），与图书馆总览同款
    out.append("## 按分类统计\n")
    out.append("| 分类 | 二级 | 记录数 |")
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
    out.append(f"| **合计** | | **{len(records)}** |")
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
            # 锚点须与二级标题 `### {emoji} {sub}（{n} 本）` 完全一致，否则 Obsidian 跳不过去
            out.append(f"  - [[#{emoji_prefix} {sub}（{n} 本）|{sub}（{n}本）]]")
    out.append("\n---\n")

    # 各一级分类 → 二级分类 → 记录
    for cat_key, cat_name in category_order:
        if cat_key not in groups:
            continue
        cat_total = sum(len(v) for v in groups[cat_key].values())
        out.append(f"\n## {cat_name}\n")
        out.append(f"共 **{cat_total}** 本\n")

        emoji_prefix = cat_name.split(' ')[0]
        subs = sorted(groups[cat_key].keys(), key=sub_sort_key)

        sub_links = " · ".join(
            f"[[#{emoji_prefix} {s}（{len(groups[cat_key][s])} 本）|{s} {len(groups[cat_key][s])}]]"
            for s in subs
        )
        out.append(f"**跳转**：{sub_links}\n")

        for sub in subs:
            rs = groups[cat_key][sub]
            out.append(f"\n### {emoji_prefix} {sub}（{len(rs)} 本）\n")
            out.append("| 书名 | 作者 | 状态 | 开始时间 | 完成时间 | 进度 | 最后阅读 | 划线数 |")
            out.append("|------|------|------|---------|---------|------|---------|--------|")
            for r in rs:
                status_disp = f"{status_icon.get(r['status'], '')} {r['status']}".strip()
                out.append(
                    f"| [[{r['filename']}\\|{r['title']}]] "
                    f"| {r['author']} "
                    f"| {status_disp} "
                    f"| {r['started']} "
                    f"| {r['finished']} "
                    f"| {r['progress_disp']} "
                    f"| {r['last_read']} "
                    f"| {r['highlights_count']} |"
                )
            out.append("")
            out.append(f"[[#{cat_name}|⬆️ 返回 {cat_name} 目录]] ｜ [[#目录|📚 全局目录]]\n")

    out.append("\n---\n")
    out.append(f"_共 {len(records)} 条 · 自动生成，数据源：`阅读记录/` 目录 + `00_图书馆/书目/` 权威分类_")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text('\n'.join(out), encoding='utf-8')
    print(f"已写入：{dst}")
    print(f"共 {len(records)} 条，{len(groups)} 个一级分类，{no_card} 条找不到对应书卡")


if __name__ == "__main__":
    main(sys.argv[1:])
