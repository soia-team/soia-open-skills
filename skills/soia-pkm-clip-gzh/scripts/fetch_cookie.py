#!/usr/bin/env python3
"""
fetch_cookie.py — Route B (登录态 Cookie) for soia-pkm-clip-gzh.

Reads a WeChat Official Account's *full* article history — including old
articles that were only ever sent via 手动群发 and never went through the
official "发布" API — by replaying the same requests the mp.weixin.qq.com
web UI makes while you are logged in.

⚠️ UNOFFICIAL / REVERSE-ENGINEERED — not documented at developers.weixin.qq.com.
The endpoint, parameters and response shape below are compiled from
cross-checking multiple independent community write-ups (博客园/CSDN/知乎,
2019-2024, all describing the same mp/profile_ext?action=getmsg contract).
No two sources disagree on the field names, but none is an official spec —
treat every field below as "待用户实测校准", not ground truth. See SKILL.md
"路 B 接口依据" for the source list.

⚠️ Use only to archive a WeChat Official Account you yourself administer.
This bypasses WeChat's public developer API surface entirely; several of the
community sources note it likely violates WeChat's Terms of Service and
recommend "仅用于学习研究目的" — this script exists for personal self-archival,
not for scraping third-party accounts.

⚠️ key / pass_ticket / appmsg_token are session-bound tickets that expire —
community reports range from a few hours to a couple of days. There is no
refresh flow here: when a run fails with ret != 0 or a non-JSON response,
re-capture fresh values from your browser's Network panel and retry.

接口依据（社区逆向，交叉核对，非官方）：
  请求：GET https://mp.weixin.qq.com/mp/profile_ext
    ?action=getmsg&__biz=<biz>&f=json&offset=<offset>&count=10&is_ok=1
    &scene=124&uin=<uin,通常固定777>&key=<key>&pass_ticket=<pass_ticket>
    &wxtoken=&appmsg_token=<appmsg_token>&x5=0
    需要请求头 Cookie: <登录态 Cookie>
  响应：{"ret":0,"errmsg":"ok","msg_count":N,"can_msg_continue":0|1,
    "general_msg_list":"<JSON 字符串，需要二次 json.loads>","next_offset":N, ...}
  general_msg_list 解析后结构：
    {"list":[{"comm_msg_info":{"datetime":<unix ts>, ...},
              "app_msg_ext_info":{"title","author","content_url","digest",
                "cover","is_multi","multi_app_msg_item_list":[同字段的子项]}}]}
  __biz / appmsg_token / pass_ticket 三者的常见取法：登录 mp.weixin.qq.com 后
  打开该公众号任意一篇历史文章或 profile_ext?action=home，在浏览器开发者工具
  「网络」面板里找同域请求，从请求 URL /请求头里复制。

Credentials (never commit): WECHAT_BIZ / WECHAT_KEY / WECHAT_PASS_TICKET /
WECHAT_COOKIE / WECHAT_APPMSG_TOKEN, loaded from SOIA_PKM_CLIP_GZH_CONFIG_FILE /
skill-specific config.yml, or plain process env vars.

Usage:
    python3 fetch_cookie.py --biz <__biz> [--out <dir>] [--limit N]
                             [--dry-run] [--vault <path>]
                             [--account-name <显示名>] [--sleep 1.5]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

from soia_env import env_source_hint, load_private_env
from save_articles import (
    extract_js_content_markdown,
    resolve_out_dir,
    resolve_vault,
    save_article,
)

CST = timezone(timedelta(hours=8))
LIST_URL = "https://mp.weixin.qq.com/mp/profile_ext"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _http_get(url: str, headers: dict, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"❌ HTTP {e.code} calling {url}")
    except urllib.error.URLError as e:
        raise SystemExit(f"❌ Network error calling {url}: {e}")


def list_page(biz, key, pass_ticket, cookie, appmsg_token, uin, offset, count=10) -> dict:
    params = (
        f"action=getmsg&__biz={biz}&f=json&offset={offset}&count={count}"
        f"&is_ok=1&scene=124&uin={uin}&key={key}&pass_ticket={pass_ticket}"
        f"&wxtoken=&appmsg_token={appmsg_token}&x5=0"
    )
    url = f"{LIST_URL}?{params}"
    headers = {"User-Agent": UA, "Cookie": cookie, "Referer": "https://mp.weixin.qq.com/"}
    raw = _http_get(url, headers)
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(
            "❌ 列表接口没返回合法 JSON（大概率是 key/pass_ticket/appmsg_token 过期，"
            "或 Cookie 失效）——去浏览器登录态下重新抓包替换这几个值。\n"
            "   原始响应前 300 字: " + raw[:300]
        )
    ret = resp.get("ret")
    if ret not in (0, "0", None):
        raise SystemExit(
            f"❌ 列表接口返回 ret={ret} errmsg={resp.get('errmsg')}（大概率票据过期，重新抓包再跑）"
        )
    return resp


def parse_general_msg_list(resp: dict) -> list[dict]:
    raw = resp.get("general_msg_list")
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print("⚠️  general_msg_list 不是合法 JSON，跳过这一页", file=sys.stderr)
        return []
    out = []
    for entry in parsed.get("list", []):
        comm = entry.get("comm_msg_info") or {}
        ext = entry.get("app_msg_ext_info") or {}
        if not ext:
            continue
        candidates = [ext] + (ext.get("multi_app_msg_item_list") or [])
        for c in candidates:
            content_url = c.get("content_url") or ""
            if not content_url:
                continue
            out.append(
                {
                    "title": c.get("title", ""),
                    "author": c.get("author", ""),
                    "content_url": html.unescape(content_url),
                    "datetime": comm.get("datetime"),
                }
            )
    return out


def fetch_article_body(url: str) -> tuple[str, bool]:
    """GET a public article page and pull #js_content. Returns (markdown, complete)."""
    try:
        raw = _http_get(url, {"User-Agent": UA, "Referer": "https://mp.weixin.qq.com/"})
    except SystemExit as e:
        print(f"  ⚠️ 正文抓取失败: {e}", file=sys.stderr)
        return "", False
    md, found = extract_js_content_markdown(raw)
    if not found:
        print("  ⚠️ 页面里没找到 #js_content（文章可能已删除/迁移/需要额外验证）", file=sys.stderr)
        return "", False
    return md, bool(md)


def main():
    load_private_env()

    ap = argparse.ArgumentParser(
        description="Route B: pull WeChat 公众号 full article history via login cookie into an Obsidian vault."
    )
    ap.add_argument("--biz", default=os.environ.get("WECHAT_BIZ"), help="__biz（也可从 env WECHAT_BIZ 读）")
    ap.add_argument("--out", help="Vault-relative output dir (overrides OBSIDIAN_GZH_OUT env)")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT env)")
    ap.add_argument("--limit", type=int, help="Max number of articles to fetch")
    ap.add_argument("--dry-run", action="store_true", help="Fetch and print the list, write nothing")
    ap.add_argument("--force", action="store_true", help="Re-write files that already exist for a given url")
    ap.add_argument("--account-name", default=os.environ.get("WECHAT_ACCOUNT_NAME", ""))
    ap.add_argument("--sleep", type=float, default=1.5, help="每次请求之间的秒数（默认 1.5，别调太快，容易触发风控）")
    args = ap.parse_args()

    if not args.biz:
        print("❌ 缺 __biz：传 --biz 或设置 env WECHAT_BIZ", file=sys.stderr)
        sys.exit(1)

    key = os.environ.get("WECHAT_KEY")
    pass_ticket = os.environ.get("WECHAT_PASS_TICKET")
    cookie = os.environ.get("WECHAT_COOKIE")
    appmsg_token = os.environ.get("WECHAT_APPMSG_TOKEN")
    uin = os.environ.get("WECHAT_UIN", "777")
    missing = [
        name
        for name, val in [
            ("WECHAT_KEY", key),
            ("WECHAT_PASS_TICKET", pass_ticket),
            ("WECHAT_COOKIE", cookie),
            ("WECHAT_APPMSG_TOKEN", appmsg_token),
        ]
        if not val
    ]
    if missing:
        print(f"❌ 缺 {', '.join(missing)}", file=sys.stderr)
        print(f"   放到私有 config.yml（{env_source_hint()}）。", file=sys.stderr)
        print("   这几个值需要从已登录 mp.weixin.qq.com 的浏览器「网络」面板抓包，几小时到几天会过期。", file=sys.stderr)
        sys.exit(1)

    print("📖 翻页拉取历史消息列表 …", file=sys.stderr)
    stubs: list[dict] = []
    offset = 0
    while True:
        if args.limit is not None and len(stubs) >= args.limit:
            break
        resp = list_page(args.biz, key, pass_ticket, cookie, appmsg_token, uin, offset)
        page_items = parse_general_msg_list(resp)
        stubs.extend(page_items)
        print(f"   offset={offset} 拿到 {len(page_items)} 条，累计 {len(stubs)}", file=sys.stderr)
        if not resp.get("can_msg_continue"):
            break
        next_offset = resp.get("next_offset")
        if next_offset is None or int(next_offset) <= offset:
            break
        offset = int(next_offset)
        time.sleep(args.sleep)

    if args.limit is not None:
        stubs = stubs[: args.limit]
    print(f"✓ 列表共 {len(stubs)} 篇，开始逐篇抓正文（每篇间隔 {args.sleep}s）…", file=sys.stderr)

    articles = []
    for i, s in enumerate(stubs, 1):
        dt = s.get("datetime")
        published_at = ""
        if dt:
            try:
                published_at = (
                    datetime.fromtimestamp(int(dt), tz=timezone.utc).astimezone(CST).strftime("%Y-%m-%d %H:%M")
                )
            except (ValueError, OSError, OverflowError):
                pass
        print(f"  [{i}/{len(stubs)}] {s.get('title','')}", file=sys.stderr)
        body, complete = fetch_article_body(s["content_url"])
        articles.append(
            {
                "title": s.get("title", ""),
                "author": s.get("author", ""),
                "url": s["content_url"],
                "published_at": published_at,
                "content": body,
                "content_complete": complete,
            }
        )
        time.sleep(args.sleep)

    if args.dry_run:
        for a in articles:
            print(f"  [dry-run] {a.get('published_at') or '?'}  {a.get('title') or '(无标题)'}  {a.get('url','')}")
        print("dry-run：未写入任何文件。", file=sys.stderr)
        return

    vault = resolve_vault(args.vault)
    out_dir = resolve_out_dir(vault, args.out)

    written = 0
    for a in articles:
        path = save_article(vault, out_dir, a, route="cookie", account_name=args.account_name, force=args.force)
        if path:
            written += 1
            print(f"✓ {path.relative_to(vault)}")

    print(f"\n完成：写入 {written} / 共 {len(articles)} 篇（其余已存在，跳过；用 --force 覆盖）")


if __name__ == "__main__":
    main()
