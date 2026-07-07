#!/usr/bin/env python3
"""对指定的书（按书名）调用 5 个微信读书 API，把详细信息补充进图书馆书卡。

用法：
  python3 enrich_book_details.py <书名>
  python3 enrich_book_details.py 系统之美 失控  # 多本
  python3 enrich_book_details.py --all                  # 批量处理所有未补全的
  python3 enrich_book_details.py --refresh-chapters     # 只刷新被截断的章节目录

  --vault / OBSIDIAN_VAULT env 指定 vault 根目录，--base 覆盖书库相对路径
  （默认 40_图书视频馆/30_个人书库）。可与上述任意模式组合，例如：
  python3 enrich_book_details.py --vault ~/MyVault 系统之美

写入位置：
  1. /book/info       → 书卡正文 "## 书籍信息"
  2. /book/chapterinfo → 书卡正文 "## 章节目录"
  3. /book/getprogress → 阅读记录 frontmatter `progress` + "## 阅读进度"
  4. /book/recommend  → 书卡正文 "## 推荐理由（微信读书）"
  5. /book/similar    → 书卡正文 "## 相似书"

需要 WEREAD_API_KEY 环境变量。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from soia_env import env_source_hint, load_private_env

load_private_env()

API = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.3"

DEFAULT_BASE = "40_图书视频馆/30_个人书库"


def call(name, **p):
    key = os.environ.get("WEREAD_API_KEY")
    if not key:
        print(f"❌ WEREAD_API_KEY 未设置：请放到私有 env 文件（{env_source_hint()}），不要写入 vault 或开源 skill 仓库")
        sys.exit(1)
    body = {"api_name": name, "skill_version": SKILL_VERSION, **p}
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode('utf-8'),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠️ {name}: {e}")
        return {}


def find_card(books_dir, title):
    for f in books_dir.rglob("*.md"):
        if f.stem == title:
            return f
    return None


def find_record(records_dir, title):
    for f in records_dir.rglob("*.md"):
        if "_模板" in f.parts or "总览" in f.name:
            continue
        # 文件名可能带日期前缀
        stem = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', f.stem)
        if stem == title:
            return f
    return None


def get_book_id(card_path):
    txt = card_path.read_text(encoding='utf-8')
    m = re.search(r'^bookId:\s*"?([^"\n]+)"?', txt, re.MULTILINE)
    return m.group(1).strip() if m else None


def replace_or_append_section(text, heading, content):
    """替换文中已有的二级标题段，没有就追加到文末"""
    pattern = re.compile(r'\n## ' + re.escape(heading) + r'\n.*?(?=\n## |\Z)', re.DOTALL)
    section = f"\n## {heading}\n\n{content}\n"
    if pattern.search(text):
        return pattern.sub(section, text)
    return text.rstrip() + '\n' + section


def enrich(books_dir, records_dir, title):
    print(f"\n📖 {title}")
    card = find_card(books_dir, title)
    if not card:
        print("  ❌ 找不到书卡")
        return
    bid = get_book_id(card)
    if not bid:
        print("  ❌ 无 bookId")
        return
    print(f"  bookId: {bid}")

    card_txt = card.read_text(encoding='utf-8')

    # 1. /book/info
    info = call("/book/info", bookId=bid)
    if info:
        intro = (info.get('intro') or info.get('intro_short') or '').strip()
        publisher = info.get('publisher', '')
        publishTime = info.get('publishTime', '')
        wordCount = info.get('wordCount', 0)
        rating = info.get('newRating', 0)
        rcount = info.get('newRatingCount', 0)
        ratingTitle = (info.get('newRatingDetail') or {}).get('title', '')
        readingCount = info.get('readingCount', 0)

        block = []
        if publisher:
            block.append(f"- **出版社**：{publisher}")
        if publishTime:
            block.append(f"- **出版时间**：{publishTime}")
        if wordCount:
            block.append(f"- **字数**：约 {wordCount:,} 字")
        if rating:
            block.append(f"- **微信读书评分**：{rating/10:.1f} 分（{ratingTitle}，{rcount} 人评分）")
        if readingCount:
            block.append(f"- **正在阅读人数**：{readingCount:,}")
        if intro:
            block.append("")
            block.append("**简介**：")
            block.append("")
            block.append(intro[:500] + ("..." if len(intro) > 500 else ""))
        if block:
            card_txt = replace_or_append_section(card_txt, "📖 书籍信息（微信读书）", '\n'.join(block))
            print("  ✓ /book/info")

    # 2. /book/chapterinfo（全部章节）
    chap = call("/book/chapterinfo", bookId=bid)
    chapters_list = (chap or {}).get('chapters', [])
    if chapters_list:
        lines = []
        for c in chapters_list:
            title_ = c.get('title', '').strip()
            level = c.get('level', 1)
            wc = c.get('wordCount', 0)
            prefix = '  ' * (level - 1) + ('- ' if level > 1 else '- ')
            wc_str = f" *({wc}字)*" if wc else ''
            lines.append(f"{prefix}{title_}{wc_str}")
        block = f"_共 {len(chapters_list)} 章_\n\n" + '\n'.join(lines)
        card_txt = replace_or_append_section(card_txt, "📑 章节目录", block)
        print(f"  ✓ /book/chapterinfo ({len(chapters_list)} 章)")

    # 3. /book/similar — 相似书（基于这本书）
    sim = call("/book/similar", bookId=bid, count=10, maxIdx=0)
    sim_books = (sim or {}).get('booksimilar', {}).get('books', []) if sim else []
    if sim_books:
        lines = []
        for b in sim_books[:8]:
            bk = b.get('book', {}).get('bookInfo', b)
            lines.append(f"- **{bk.get('title', '')}** — {bk.get('author', '')}")
        card_txt = replace_or_append_section(card_txt, "🔗 相似书（微信读书）", '\n'.join(lines))
        print(f"  ✓ /book/similar ({len(sim_books)} 本)")

    # 4. /book/recommend — 个性化推荐（非本书相关，写到独立区）
    # 注：recommend 是用户级推荐，不针对某本书；这里写入用于发现新书
    # 如果希望保留这块，取消注释
    # rec = call("/book/recommend", count=10)
    # rec_books = (rec or {}).get('books', [])
    # if rec_books:
    #     lines = []
    #     for b in rec_books[:8]:
    #         bk = b.get('bookInfo', b)
    #         lines.append(f"- **{bk.get('title', '')}** — {bk.get('author', '')}")
    #     card_txt = replace_or_append_section(card_txt, "🎯 微信读书为你推荐", '\n'.join(lines))
    #     print(f"  ✓ /book/recommend ({len(rec_books)} 本)")

    card.write_text(card_txt, encoding='utf-8')

    # 5. /book/getprogress → 阅读记录
    record = find_record(records_dir, title)
    if record:
        prog = call("/book/getprogress", bookId=bid)
        if prog:
            pct = prog.get('progress', 0)
            updateTime = prog.get('updateTime', 0)
            readingTime = prog.get('readingTime', 0)
            currentChapter = (prog.get('chapter') or {}).get('title', '')

            block = [f"- **当前进度**：{pct}%"]
            if currentChapter:
                block.append(f"- **当前章节**：{currentChapter}")
            if readingTime:
                block.append(f"- **累计阅读**：{readingTime // 60} 分钟")
            if updateTime:
                block.append(f"- **最后阅读**：{datetime.fromtimestamp(updateTime).strftime('%Y-%m-%d %H:%M')}")

            rec_txt = record.read_text(encoding='utf-8')

            # frontmatter 加 progress
            if 'progress:' not in rec_txt:
                rec_txt = re.sub(r'(^last_read:\s*[^\n]*\n)', r'\1progress: ' + str(pct) + '\n', rec_txt, count=1, flags=re.MULTILINE)

            rec_txt = replace_or_append_section(rec_txt, "📊 阅读进度（微信读书）", '\n'.join(block))
            record.write_text(rec_txt, encoding='utf-8')
            print(f"  ✓ /book/getprogress → 阅读记录 ({pct}%)")


def refresh_chapters_only(books_dir, sleep_sec=0.3):
    """只刷章节段（用于章节被旧版本截断时一次性更新）"""
    targets = []
    for f in books_dir.rglob("*.md"):
        txt = f.read_text(encoding='utf-8')
        m = re.search(r'^bookId:\s*"?([\w_]+)', txt, re.MULTILINE)
        if not m:
            continue
        bid = m.group(1)
        m = re.search(r'^title:\s*"?([^"\n]*)"?$', txt, re.MULTILINE)
        if not m:
            continue
        title = m.group(1).strip()
        # 跳过没有章节段的（说明之前 chapter API 失败了，跳过避免拖慢）
        if '## 📑 章节目录' not in txt:
            continue
        # 跳过已经是全章节的（不含"仅显示前"）
        if '仅显示前' not in txt:
            continue
        targets.append((f, bid, title))

    print(f"📚 待刷新章节: {len(targets)} 本（跳过已是全章节的）\n")
    ok, fail = 0, 0
    for i, (f, bid, title) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {title}", end=' ', flush=True)
        try:
            chap = call("/book/chapterinfo", bookId=bid)
            chapters_list = (chap or {}).get('chapters', [])
            if not chapters_list:
                print("⚠️ 无章节")
                fail += 1
                continue
            lines = []
            for c in chapters_list:
                title_ = c.get('title', '').strip()
                level = c.get('level', 1)
                wc = c.get('wordCount', 0)
                prefix = '  ' * (level - 1) + ('- ' if level > 1 else '- ')
                wc_str = f" *({wc}字)*" if wc else ''
                lines.append(f"{prefix}{title_}{wc_str}")
            block = f"_共 {len(chapters_list)} 章_\n\n" + '\n'.join(lines)

            txt = f.read_text(encoding='utf-8')
            txt = replace_or_append_section(txt, "📑 章节目录", block)
            f.write_text(txt, encoding='utf-8')
            print(f"✓ {len(chapters_list)} 章")
            ok += 1
        except Exception as e:
            print(f"⚠️ {e}")
            fail += 1
        time.sleep(sleep_sec)

    print(f"\n=== 完成 ===\n  成功: {ok}\n  失败: {fail}")


def enrich_all(books_dir, records_dir, sleep_sec=0.4, skip_if_enriched=True):
    """批量：对所有有 bookId 的书卡调用 5 API"""
    targets = []
    for f in books_dir.rglob("*.md"):
        txt = f.read_text(encoding='utf-8')
        if not re.search(r'^bookId:\s*"?[\w_]+', txt, re.MULTILINE):
            continue
        if skip_if_enriched and '## 📖 书籍信息（微信读书）' in txt:
            continue
        m = re.search(r'^title:\s*"?([^"\n]*)"?$', txt, re.MULTILINE)
        if m:
            targets.append(m.group(1).strip())

    print(f"📚 共 {len(targets)} 本书待处理\n")
    ok, fail = 0, 0
    for i, t in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}]", end=' ', flush=True)
        try:
            enrich(books_dir, records_dir, t)
            ok += 1
        except Exception as e:
            print(f"  ⚠️ 失败: {e}")
            fail += 1
        time.sleep(sleep_sec)

    print("\n=== 完成 ===")
    print(f"  成功: {ok}")
    print(f"  失败: {fail}")


def resolve_vault(vault_arg):
    if vault_arg:
        return Path(vault_arg).expanduser()
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    print(f"❌ 未指定 vault：请传 --vault 或在私有 env 文件中设置 OBSIDIAN_VAULT（{env_source_hint()}）", file=sys.stderr)
    sys.exit(1)


def parse_args(argv):
    p = argparse.ArgumentParser(description="补单本书详情（微信读书 5 个 API）")
    p.add_argument("--vault", help="Obsidian vault 根目录（默认读 OBSIDIAN_VAULT env）")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"书库相对 vault 的路径（默认 {DEFAULT_BASE}）")
    p.add_argument("--all", action="store_true", help="批量处理所有未补全的")
    p.add_argument("--refresh-chapters", action="store_true", help="只刷新被截断的章节目录")
    p.add_argument("titles", nargs="*", help="书名（可多本）")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    vault = resolve_vault(args.vault)
    base = vault / args.base
    books_dir = base / "00_图书馆" / "书目"
    records_dir = base / "阅读记录"

    if args.all:
        enrich_all(books_dir, records_dir)
    elif args.refresh_chapters:
        refresh_chapters_only(books_dir)
    elif args.titles:
        for t in args.titles:
            enrich(books_dir, records_dir, t)
    else:
        print("用法：")
        print("  python3 enrich_book_details.py <书名> [书名 ...]")
        print("  python3 enrich_book_details.py --all                  # 批量处理所有未补全的")
        print("  python3 enrich_book_details.py --refresh-chapters     # 只刷新被截断的章节目录")
        return

    print("\n完成后请重生成 md 总览：")
    print("  python3 gen_library_md.py")
    print("  python3 gen_records_md.py")


if __name__ == "__main__":
    main(sys.argv[1:])
