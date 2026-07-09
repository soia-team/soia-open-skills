#!/usr/bin/env python3
"""sync_weread_highlights.py — 把微信读书的划线 / 想法批量搬到 Obsidian 阅读记录的机器段。

机械层（无 LLM）。每次同步会整段覆盖以下两个二级标题段，用户不要在这两段
里手写笔记（要保留请放在『### 用户笔记』子区块下，本脚本会保留该子区块）：

  ## 📌 划线（来自微信读书 · 自动同步）
  ## 💭 想法（来自微信读书 · 自动同步）

用法：
  python3 sync_weread_highlights.py                    # 列 noteCount 前 30
  python3 sync_weread_highlights.py <书名> [<书名>...] # 单本 / 多本
  python3 sync_weread_highlights.py --all              # 全量（noteCount > 0）
  python3 sync_weread_highlights.py --top N            # 只处理 noteCount 前 N
  python3 sync_weread_highlights.py --book-id <bookId> # 直接按 bookId

  --vault / OBSIDIAN_VAULT env 指定 vault 根目录，--base 覆盖书库相对路径
  （默认 40_图书视频馆/30_个人书库）。以上参数可与任意 mode 组合，例如：
  python3 sync_weread_highlights.py --vault ~/MyVault --all

数据流：
  /user/notebooks   → 得到 bookId 清单 + 笔记数概览
  /book/chapterinfo → 章节 uid → 标题映射
  /book/bookmarklist → 划线
  /review/list/mine → 想法

写入：
  阅读记录/<状态>/<书名>.md
    - 整段替换 ## 📌 划线（来自微信读书 · 自动同步）
    - 整段替换 ## 💭 想法（来自微信读书 · 自动同步）
    - frontmatter 单字段插入/更新 highlights_count / reviews_count /
      last_synced_highlights

需要 WEREAD_API_KEY 环境变量。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from soia_env import env_source_hint, load_private_env, require_weread_skills, weread_api_key_hint

load_private_env()
require_weread_skills()

# ---------- 常量 ----------
API = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.3"

DEFAULT_BASE = "40_图书视频馆/30_个人书库"
# 阅读记录生命周期状态目录（默认值，可用 --config 覆盖 record_status_dirs）
DEFAULT_RECORD_STATUS_DIRS = ["已完成", "在读", "暂停", "搁置"]

HEADING_HIGHLIGHTS = "📌 划线（来自微信读书 · 自动同步）"
HEADING_THOUGHTS = "💭 想法（来自微信读书 · 自动同步）"
PROGRESS_HEADING = "## 📊 阅读进度（微信读书）"

THROTTLE_SEC = 0.4
MAX_RETRY = 1


# ---------- API ----------
def call(name: str, **p):
    key = os.environ.get("WEREAD_API_KEY")
    if not key:
        print(
            f"❌ WEREAD_API_KEY 未设置：请先去微信读书官方 Skill 页面申请/获取 API Key："
            f"{weread_api_key_hint()}；拿到后放到私有 config.yml（{env_source_hint()}），"
            "不要写入 vault 或开源 skill 仓库",
            file=sys.stderr,
        )
        sys.exit(1)
    body = {"api_name": name, "skill_version": SKILL_VERSION, **p}
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    last_exc = None
    for attempt in range(MAX_RETRY + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt < MAX_RETRY:
                time.sleep(0.6)
                continue
    print(f"  ⚠️ {name} 失败: {last_exc}", file=sys.stderr)
    return {}


def throttled(name, **p):
    out = call(name, **p)
    time.sleep(THROTTLE_SEC)
    return out


# ---------- 文件定位 ----------
_FILENAME_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}\s+")


def _strip_prefix(stem: str) -> str:
    return _FILENAME_DATE_PREFIX.sub("", stem)


def find_record(records_dir: Path, status_dirs: list[str], title: str, book_id: str | None = None) -> Path | None:
    """在 阅读记录/{已完成,在读,暂停,搁置}/ 里找记录。

    优先按 bookId 精确匹配（最可靠——微信读书返回的书名常带书名号/合集后缀，
    如"张宏杰：历史的正面与侧面（全7册）"，和本地手动整理的文件名
    "张宏杰.md" 对不上，标题匹配会漏），找不到再退回标题匹配（兼容
    还没写 bookId 的记录）。
    """
    if not records_dir.exists():
        return None
    # 0) 按 bookId 精确匹配
    if book_id:
        bookid_re = re.compile(
            r'^bookId:\s*"?' + re.escape(str(book_id)) + r'"?\s*$', re.MULTILINE
        )
        for f in records_dir.rglob("*.md"):
            if "_模板" in f.parts or "总览" in f.name:
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            if bookid_re.search(text):
                return f
    # 1) 标题精确匹配
    for status in status_dirs:
        d = records_dir / status
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            if "_模板" in f.parts:
                continue
            if _strip_prefix(f.stem) == title or f.stem == title:
                return f
    # 2) 全树兜底
    for f in records_dir.rglob("*.md"):
        if "_模板" in f.parts or "总览" in f.name:
            continue
        if _strip_prefix(f.stem) == title or f.stem == title:
            return f
    return None


# ---------- frontmatter 单字段写入 ----------
def upsert_frontmatter_field(text: str, key: str, value) -> str:
    """在 frontmatter 块里 upsert 单字段，frontmatter 不存在则忽略。"""
    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not fm_match:
        return text
    fm_body = fm_match.group(1)
    line_re = re.compile(rf"^{re.escape(key)}:\s*.*$", re.MULTILINE)
    new_line = f"{key}: {value}"
    if line_re.search(fm_body):
        new_fm = line_re.sub(new_line, fm_body)
    else:
        # 追加到 frontmatter 末尾
        new_fm = fm_body.rstrip() + "\n" + new_line
    return f"---\n{new_fm}\n---\n" + text[fm_match.end() :]


# ---------- 段管理 ----------
def _section_pattern(heading: str):
    """匹配 \n## <heading>\n ... 到下一个 ## 或文末"""
    return re.compile(
        r"\n## " + re.escape(heading) + r"\n.*?(?=\n## |\Z)", re.DOTALL
    )


def replace_or_insert_machine_section(
    text: str, heading: str, body: str
) -> str:
    """整段替换具名机器段。段不存在则插入到『## 📊 阅读进度（微信读书）』之前；
    若也没有阅读进度段，则追加到文末。

    会保留段内『### 用户笔记』子区块（用户在机器段里也想留东西的逃生口）。
    """
    pattern = _section_pattern(heading)
    new_block = f"\n## {heading}\n\n{body.rstrip()}\n"

    m = pattern.search(text)
    if m:
        # 保留段内的 ### 用户笔记 子区块
        old_section = m.group(0)
        user_note_m = re.search(
            r"\n### 用户笔记\n[\s\S]*?(?=\n### |\n## |\Z)", old_section
        )
        if user_note_m:
            new_block = new_block.rstrip() + "\n" + user_note_m.group(0).lstrip("\n") + "\n"
        return pattern.sub(new_block, text)

    # 段不存在：插到阅读进度之前
    if PROGRESS_HEADING in text:
        idx = text.index(PROGRESS_HEADING)
        # 找到该段前一个换行的位置
        head = text[:idx].rstrip() + "\n"
        tail = text[idx:]
        return head + new_block.lstrip("\n") + "\n" + tail
    return text.rstrip() + "\n" + new_block


# ---------- 章节映射 ----------
def build_chapter_map(chapter_resp: dict) -> dict:
    """uid → 章节标题"""
    out = {}
    for c in (chapter_resp or {}).get("chapters", []) or []:
        uid = c.get("chapterUid")
        if uid is None:
            continue
        out[uid] = (c.get("title") or "").strip() or f"第 {uid} 章"
    return out


def chapter_order_key(uid, chapter_map: dict):
    """让有标题的章节按 chapterUid 数值排，无标题的归到末尾。"""
    if uid is None:
        return (1, 1 << 30)
    return (0 if uid in chapter_map else 1, uid)


# ---------- markdown 渲染 ----------
def _weread_link(book_id, chapter_uid=None, range_str=None) -> str:
    parts = [f"bookId={book_id}"]
    if chapter_uid is not None:
        parts.append(f"chapterUid={chapter_uid}")
    if range_str:
        parts.append(f"range={range_str}")
    return "weread://bestbookmark?" + "&".join(parts)


def render_highlights(bookmarks: list, chapter_map: dict, book_id: str) -> str:
    """按章节分组的 markdown。"""
    if not bookmarks:
        return "> _暂无划线_"

    # 按 chapterUid 分组
    groups: dict = {}
    for bm in bookmarks:
        uid = bm.get("chapterUid")
        groups.setdefault(uid, []).append(bm)

    # 章内按 range 内的起点排
    def _bm_sort_key(bm):
        r = bm.get("range", "")
        m = re.match(r"(\d+)", r)
        return int(m.group(1)) if m else 0

    lines = []
    for uid in sorted(groups.keys(), key=lambda x: chapter_order_key(x, chapter_map)):
        chap_title = chapter_map.get(uid) or (bookmarks[0].get("chapterName") if uid is None else f"第 {uid} 章")
        chap_title = chap_title or "未分章"
        lines.append(f"### {chap_title}")
        lines.append("")
        for bm in sorted(groups[uid], key=_bm_sort_key):
            mark_text = (bm.get("markText") or "").strip()
            if not mark_text:
                continue
            # 多行划线用 blockquote
            for ln in mark_text.splitlines():
                lines.append(f"> {ln}")
            link = _weread_link(book_id, uid, bm.get("range"))
            lines.append("")
            lines.append(f"_([weread 链接]({link}))_")
            lines.append("")
    return "\n".join(lines).rstrip()


def render_thoughts(reviews: list, chapter_map: dict, book_id: str) -> str:
    """想法：可选带原文 abstract + 我的想法正文。"""
    if not reviews:
        return "> _暂无想法_"

    groups: dict = {}
    for rv in reviews:
        uid = rv.get("chapterUid")
        groups.setdefault(uid, []).append(rv)

    def _rv_sort_key(rv):
        return rv.get("createTime") or 0

    lines = []
    for uid in sorted(groups.keys(), key=lambda x: chapter_order_key(x, chapter_map)):
        chap_title = chapter_map.get(uid) or (
            reviews[0].get("chapterName") if uid is None else (f"第 {uid} 章" if uid is not None else "未分章")
        )
        chap_title = chap_title or "未分章"
        lines.append(f"### {chap_title}")
        lines.append("")
        for rv in sorted(groups[uid], key=_rv_sort_key):
            abstract = (rv.get("abstract") or "").strip()
            content = (rv.get("content") or "").strip()
            if abstract:
                for ln in abstract.splitlines():
                    lines.append(f"> **{ln}**")
                lines.append("")
            if content:
                lines.append(f"💭 我的想法：{content}")
                lines.append("")
            link = _weread_link(book_id, uid, rv.get("range"))
            lines.append(f"_([weread 链接]({link}))_")
            lines.append("")
    return "\n".join(lines).rstrip()


# ---------- 同步单本 ----------
def sync_one(records_dir: Path, status_dirs: list[str], book_id: str, title: str) -> str:
    """返回 'ok' / 'skip:<reason>' / 'fail:<reason>'。"""
    print(f"\n📖 {title}  (bookId={book_id})", file=sys.stderr)

    record = find_record(records_dir, status_dirs, title, book_id)
    if not record:
        print("  ⚠️ 找不到阅读记录，跳过", file=sys.stderr)
        return "skip:no_record"

    # 拉数据
    bm_resp = throttled("/book/bookmarklist", bookId=book_id)
    rv_resp = throttled("/review/list/mine", bookid=book_id)
    ch_resp = throttled("/book/chapterinfo", bookId=book_id)

    bookmarks = (bm_resp or {}).get("updated", []) or []
    if not bookmarks:
        # 某些返回结构兜底
        bookmarks = (bm_resp or {}).get("bookmarks", []) or []

    reviews_raw = (rv_resp or {}).get("reviews", []) or []
    # reviews 列表内每条形如 {review: {...}}
    reviews = []
    for r in reviews_raw:
        if isinstance(r, dict) and "review" in r and isinstance(r["review"], dict):
            reviews.append(r["review"])
        else:
            reviews.append(r)

    chapter_map = build_chapter_map(ch_resp)
    print(f"  划线 {len(bookmarks)}  想法 {len(reviews)}  章节 {len(chapter_map)}", file=sys.stderr)

    # 渲染 + 写
    text = record.read_text(encoding="utf-8")
    highlights_md = render_highlights(bookmarks, chapter_map, book_id)
    thoughts_md = render_thoughts(reviews, chapter_map, book_id)

    text = replace_or_insert_machine_section(text, HEADING_HIGHLIGHTS, highlights_md)
    text = replace_or_insert_machine_section(text, HEADING_THOUGHTS, thoughts_md)

    today = datetime.now().strftime("%Y-%m-%d")
    text = upsert_frontmatter_field(text, "highlights_count", len(bookmarks))
    text = upsert_frontmatter_field(text, "reviews_count", len(reviews))
    text = upsert_frontmatter_field(text, "last_synced_highlights", today)

    record.write_text(text, encoding="utf-8")
    print(f"  ✓ 写入 {record.relative_to(records_dir.parent.parent)}", file=sys.stderr)
    return "ok"


# ---------- notebook 概览 ----------
def fetch_notebooks() -> list:
    resp = call("/user/notebooks", count=200)
    books = (resp or {}).get("books", []) or []
    # 每条形如 {book: {...}, noteCount: N, reviewCount: M, ...}
    flat = []
    for item in books:
        b = item.get("book") or {}
        flat.append(
            {
                "bookId": b.get("bookId") or item.get("bookId"),
                "title": (b.get("title") or item.get("title") or "").strip(),
                "author": b.get("author") or item.get("author") or "",
                "noteCount": item.get("noteCount", 0),
                "reviewCount": item.get("reviewCount", 0),
                "bookmarkCount": item.get("bookmarkCount", 0),
                "sort": item.get("sort", 0),
            }
        )
    flat.sort(key=lambda x: x["noteCount"], reverse=True)
    return flat


def print_overview(books: list, top: int = 30):
    print(f"📚 笔记本概览（共 {len(books)} 本，按 noteCount 倒序前 {top}）\n")
    print(f"{'#':>3}  {'划线':>4} {'想法':>4} {'bookId':<14}  书名 — 作者")
    print("-" * 80)
    for i, b in enumerate(books[:top], 1):
        title = b["title"][:40]
        author = b["author"][:20]
        print(
            f"{i:>3}  {b['bookmarkCount']:>4} {b['reviewCount']:>4} "
            f"{str(b['bookId'])[:14]:<14}  {title} — {author}"
        )


# ---------- 配置 ----------
def resolve_vault(vault_arg):
    if vault_arg:
        return Path(vault_arg).expanduser()
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return Path(env).expanduser()
    print(f"❌ 未指定 vault：请传 --vault 或在私有 config.yml中设置 OBSIDIAN_VAULT（{env_source_hint()}）", file=sys.stderr)
    sys.exit(1)


def load_config(config_path):
    status_dirs = DEFAULT_RECORD_STATUS_DIRS
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        if "record_status_dirs" in cfg:
            status_dirs = cfg["record_status_dirs"]
    return list(status_dirs)


# ---------- 入口 ----------
def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="微信读书划线/想法 → 阅读记录追加")
    p.add_argument("--vault", help="Obsidian vault 根目录（默认读 OBSIDIAN_VAULT env）")
    p.add_argument("--base", default=DEFAULT_BASE,
                   help=f"书库相对 vault 的路径（默认 {DEFAULT_BASE}）")
    p.add_argument("--config", help="JSON 文件，覆盖默认状态目录表（键：record_status_dirs）")
    p.add_argument("--all", action="store_true", help="全量同步（noteCount > 0）")
    p.add_argument("--top", type=int, help="只处理 noteCount 前 N 本")
    p.add_argument("--book-id", dest="book_id", help="直接按 bookId 同步单本")
    p.add_argument("titles", nargs="*", help="按书名同步（可多本）")
    return p.parse_args(argv)


def main(argv: list[str]):
    args = _parse_args(argv)
    vault = resolve_vault(args.vault)
    records_dir = vault / args.base / "阅读记录"
    status_dirs = load_config(args.config)

    if args.book_id:
        mode = "book_id"
    elif args.all:
        mode = "all"
    elif args.top is not None:
        mode = "top"
    elif args.titles:
        mode = "titles"
    else:
        mode = "overview"

    if mode == "overview":
        books = fetch_notebooks()
        print_overview(books, top=30)
        return

    if mode == "book_id":
        # 没有标题时用 bookId 兜底；尝试从 notebooks 反查标题
        books = fetch_notebooks()
        title = next((b["title"] for b in books if str(b["bookId"]) == str(args.book_id)), "")
        if not title:
            print(f"⚠️ notebooks 里查不到 bookId={args.book_id} 的标题", file=sys.stderr)
            return
        sync_one(records_dir, status_dirs, args.book_id, title)
        return

    if mode == "titles":
        books = fetch_notebooks()
        by_title = {b["title"]: b for b in books}
        ok = skip = fail = 0
        for t in args.titles:
            b = by_title.get(t)
            if not b:
                print(f"⚠️ notebooks 里查不到《{t}》，跳过", file=sys.stderr)
                skip += 1
                continue
            r = sync_one(records_dir, status_dirs, b["bookId"], b["title"])
            if r == "ok":
                ok += 1
            elif r.startswith("skip"):
                skip += 1
            else:
                fail += 1
        print(f"\n=== 完成 === ok={ok} skip={skip} fail={fail}", file=sys.stderr)
        return

    if mode in ("all", "top"):
        books = fetch_notebooks()
        targets = [b for b in books if b.get("noteCount", 0) > 0]
        if mode == "top":
            targets = targets[: args.top]
        print(f"📚 待同步 {len(targets)} 本\n", file=sys.stderr)
        ok = skip = fail = 0
        for i, b in enumerate(targets, 1):
            print(f"[{i}/{len(targets)}]", end=" ", file=sys.stderr)
            try:
                r = sync_one(records_dir, status_dirs, b["bookId"], b["title"])
            except KeyboardInterrupt:
                print("\n中断，已写入的不回滚。", file=sys.stderr)
                break
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠️ 失败: {e}", file=sys.stderr)
                r = f"fail:{e}"
            if r == "ok":
                ok += 1
            elif r.startswith("skip"):
                skip += 1
            else:
                fail += 1
        print(f"\n=== 完成 === ok={ok} skip={skip} fail={fail}", file=sys.stderr)
        return


if __name__ == "__main__":
    main(sys.argv[1:])
