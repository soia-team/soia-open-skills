#!/usr/bin/env python3
"""把微信读书的所有书同步到个人图书馆 + 阅读记录

双层逻辑：
- 图书馆：全部书目（仅客观信息：title/author/category/source/bookId/deepLink/cover）
- 阅读记录：
  - finishReading=1 → 已完成/<日期> <书名>.md
  - 有 readUpdateTime  → 在读/<书名>.md（读过部分）
  - 没读过 → 不建阅读记录（仅图书馆作为待读）

用法：
  python3 sync_weread_to_library.py                       # 用 --vault/OBSIDIAN_VAULT + 默认书库相对路径
  python3 sync_weread_to_library.py --vault ~/MyVault
  python3 sync_weread_to_library.py --base 40_图书视频馆/30_个人书库
  python3 sync_weread_to_library.py --config my_categories.json

vault 路径解析优先级：--vault > OBSIDIAN_VAULT env > 当前目录。
书库相对路径默认 `40_图书视频馆/30_个人书库`，可用 --base 覆盖。

需要 WEREAD_API_KEY 环境变量。
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from soia_env import env_source_hint, load_private_env

load_private_env()

API = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.3"

DEFAULT_BASE = "40_图书视频馆/30_个人书库"

# category → (显示名, 目录名)（默认值，可用 --config 覆盖 category_map）
DEFAULT_CATEGORY_MAP = {
    '经济理财': ['经济理财', '01_经济理财'],
    '个人成长': ['个人成长', '02_个人成长'],
    '心理':     ['心理',     '03_心理'],
    '哲学宗教': ['哲学宗教', '04_哲学宗教'],
    '文学':     ['文学',     '05_文学'],
    '精品小说': ['精品小说', '06_精品小说'],
    '历史':     ['历史',     '07_历史'],
    '政治军事': ['政治军事', '08_政治军事'],
    '社会文化': ['社会文化', '09_社会文化'],
    '教育学习': ['教育学习', '10_教育学习'],
    '科学技术': ['科学技术', '11_科学技术'],
    '计算机':   ['计算机',   '12_计算机'],
    '生活百科': ['生活百科', '13_生活百科'],
    '人物传记': ['人物传记', '14_人物传记'],
    '医学健康': ['医学健康', '15_医学健康'],
    '童书':     ['童书',     '16_童书'],
    '期刊杂志': ['期刊杂志', '17_期刊杂志'],
    '未分类':   ['未分类',   '99_未分类'],
}


def parse_args(argv):
    p = argparse.ArgumentParser(description="微信读书已读 → 书卡 + 阅读记录")
    p.add_argument("--vault", help="Obsidian vault 根目录（默认读 OBSIDIAN_VAULT env）")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"书库相对 vault 的路径（默认 {DEFAULT_BASE}）")
    p.add_argument("--config", help="JSON 文件，覆盖默认分类表（键：category_map）")
    return p.parse_args(argv)


def resolve_vault(args):
    if args.vault:
        return Path(args.vault).expanduser()
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    print(f"❌ 未指定 vault：请传 --vault 或在私有 env 文件中设置 OBSIDIAN_VAULT（{env_source_hint()}）", file=sys.stderr)
    sys.exit(1)


def load_config(config_path):
    category_map = DEFAULT_CATEGORY_MAP
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if "category_map" in cfg:
            category_map = cfg["category_map"]
    return {k: tuple(v) for k, v in category_map.items()}


def weread_call(api_name, **params):
    api_key = os.environ.get("WEREAD_API_KEY")
    if not api_key:
        print(f"❌ 未设置 WEREAD_API_KEY：请放到私有 env 文件（{env_source_hint()}），不要写入 vault 或开源 skill 仓库")
        sys.exit(1)
    body = {"api_name": api_name, "skill_version": SKILL_VERSION, **params}
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode('utf-8'),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def clean_title(t):
    t = re.sub(r'\s*[\(（].*?[)）]\s*', '', t).strip()
    t = re.sub(r'[:：].*$', '', t).strip()
    t = re.sub(r'\[.*?\]', '', t).strip()
    t = re.sub(r'\s+', ' ', t)
    return re.sub(r'[<>:"/\\|?*]', '', t).strip() or '未命名'


def fuzzy_find(name, existing):
    name_c = re.sub(r'[·:：（）()【】\[\]\s]', '', name)
    for stem in existing:
        stem_c = re.sub(r'[·:：（）()【】\[\]\s]', '', stem)
        if name_c == stem_c:
            return stem
        if name in stem or (stem in name and len(stem) > 3):
            return stem
    return None


def reader_url(deepLink):
    m = re.search(r'[?&]v=([^&\s"]+)', deepLink or '')
    return f"https://weread.qq.com/web/reader/{m.group(1)}" if m else ''


def card_content(title, author, cat, source, bookId, deepLink, cover, note):
    reader = reader_url(deepLink)
    return f"""---
tags: [书库]
title: {title}
author: {author}
category: {cat}
source: [{source}]
bookId: "{bookId}"
deepLink: "{deepLink}"
readerLink: "{reader}"
cover: "{cover}"
note: {note}
---

# {title}

> **{author}** ｜ {cat}
>
> [📖 去阅读]({reader}) ｜ [详情页]({deepLink}) ｜ bookId: `{bookId}`

![封面|150]({cover})

## 选书理由

> 微信读书已保存，自动同步

## 关联书目

"""


def record_done(title, author, cat, source, finish_date, bookId, deepLink):
    return f"""---
tags: [阅读记录]
title: {title}
book: "[[{title}]]"
status: 完成
started:
finished: {finish_date}
rating:
category: {cat}
author: {author}
source: [{source}]
bookId: "{bookId}"
---

# {title} · 阅读记录

> **{author}** ｜ {cat} ｜ 完成（{finish_date}）
> 书卡：[[{title}]] ｜ [📖 继续阅读]({reader_url(deepLink)})

## 核心观点

1.
2.
3.

## 读书笔记



## 金句摘录



## 读后感



## 行动清单

- [ ]
"""


def record_reading(title, author, cat, source, last_read, bookId, deepLink):
    return f"""---
tags: [阅读记录]
title: {title}
book: "[[{title}]]"
status: 在读
started:
last_read: {last_read}
finished:
rating:
category: {cat}
author: {author}
source: [{source}]
bookId: "{bookId}"
---

# {title} · 阅读记录

> **{author}** ｜ {cat} ｜ 在读（最近：{last_read}）
> 书卡：[[{title}]] ｜ [📖 继续阅读]({reader_url(deepLink)})

## 读书笔记



## 金句摘录



## 当前思考



"""


def main(argv):
    args = parse_args(argv)
    vault = resolve_vault(args)
    base = vault / args.base
    books_dir = base / "00_图书馆" / "书目"
    records_done = base / "阅读记录" / "已完成"
    records_reading = base / "阅读记录" / "在读"
    category_map = load_config(args.config)

    for d in (books_dir, records_done, records_reading):
        d.mkdir(parents=True, exist_ok=True)

    print("📚 拉取微信读书书架...")
    shelf = weread_call("/shelf/sync")
    books = shelf['books']
    print(f"书架共 {len(books)} 本\n")

    # 扫描已有
    existing_cards = {f.stem: f for f in books_dir.rglob("*.md")}
    existing_done = {re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', f.stem): f for f in records_done.glob("*.md")}
    existing_reading = {f.stem: f for f in records_reading.glob("*.md")}

    n_card, n_done, n_reading = 0, 0, 0

    for b in books:
        title    = b['title']
        author   = b['author'] if b.get('author') != 'Unknown Author' else ''
        wr_cat   = (b.get('category') or '').split('-')[0]
        bookId   = b.get('bookId', '')
        deepLink = b.get('deepLink', '')
        cover    = b.get('cover', '')
        ts       = b.get('readUpdateTime', 0)
        finished = b.get('finishReading') == 1
        name     = clean_title(title)

        if not name:
            continue
        cat, dir_ = category_map.get(wr_cat, ('未分类', '99_未分类'))

        # 1. 书卡
        matched = fuzzy_find(name, existing_cards.keys())
        if not matched:
            card_path = books_dir / dir_ / f"{name}.md"
            if not card_path.exists():
                card_path.parent.mkdir(parents=True, exist_ok=True)
                card_path.write_text(
                    card_content(name, author, cat, '微信读书', bookId, deepLink, cover, f'微信读书原分类：{wr_cat}'),
                    encoding='utf-8'
                )
                existing_cards[name] = card_path
                n_card += 1

        # 2. 阅读记录
        if finished and ts:
            date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            rname = fuzzy_find(name, existing_done.keys())
            if not rname:
                path = records_done / f"{date} {name}.md"
                if not path.exists():
                    path.write_text(record_done(name, author, cat, '微信读书', date, bookId, deepLink), encoding='utf-8')
                    n_done += 1
        elif ts:  # 读过部分
            last = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            rname = fuzzy_find(name, existing_reading.keys())
            if not rname:
                path = records_reading / f"{name}.md"
                if not path.exists():
                    path.write_text(record_reading(name, author, cat, '微信读书', last, bookId, deepLink), encoding='utf-8')
                    existing_reading[name] = path
                    n_reading += 1

    print("=== 同步完成 ===")
    print(f"  新增书卡:       {n_card}")
    print(f"  新增已完成记录: {n_done}")
    print(f"  新增在读记录:   {n_reading}")
    print("\n下一步：")
    print("  python3 gen_library_md.py")
    print("  python3 gen_records_md.py")


if __name__ == "__main__":
    main(sys.argv[1:])
