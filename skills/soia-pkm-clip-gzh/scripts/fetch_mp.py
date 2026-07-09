#!/usr/bin/env python3
"""
fetch_mp.py — Route C (公众号后台接口) for soia-pkm-clip-gzh.

Reads a WeChat Official Account's *full* article history — including old
articles that were only ever sent via 手动群发 and never went through the
official "发布" API — by replaying the same two requests the mp.weixin.qq.com
后台 web UI makes while you are logged in: search_biz (name -> fakeid) and
appmsg?action=list_ex (fakeid -> paginated article list). This is the same
technique as Route B (profile_ext), but against the *后台* (author-facing)
endpoints instead of the *前台* (reader-facing) profile_ext endpoint — in
practice it is the route most public write-ups converge on for "我自己的号,
要全部历史" and is generally reported as more stable / longer-lived tokens
than profile_ext's key/pass_ticket combo.

⚠️ UNOFFICIAL / REVERSE-ENGINEERED — not documented at developers.weixin.qq.com.
Same caveats as Route B apply: use only to archive an Official Account you
yourself administer; treat every field below as verified-against-source-code
but still "待用户实测校准", not an official contract; WeChat can change this
without notice.

接口依据（核对方式：不是转述文档，是直接读了两个参考仓库的源码 —— 它们各自
的 docs/README 都写了"具体参数见代码"，所以真正核对的是下面两个源文件）：

  1. searchbiz（公众号名 -> fakeid）
     GET https://mp.weixin.qq.com/cgi-bin/searchbiz
     params: action=search_biz, begin=0, count=5, query=<公众号名>,
             token=<token>, lang=zh_CN, f=json, ajax=1
     headers: Cookie: <登录态 Cookie>
     response: {"base_resp":{"ret":0,"err_msg":"ok"},
                "list":[{"alias","fakeid","nickname","round_head_img",
                         "service_type"}, ...]}
     两个独立仓库的参数完全一致，交叉核对来源：
       - wnma3mz/wechat_articles_spider
         wechatarticles/ArticlesUrls.py :: PublicAccountsWeb.official_info()
         https://github.com/wnma3mz/wechat_articles_spider/blob/master/wechatarticles/ArticlesUrls.py
       - cv-cat/WechatOAApis
         utils/wx_utils.py :: get_fakeid_params()
         https://github.com/cv-cat/WechatOAApis/blob/master/utils/wx_utils.py
     文档索引（参数本身文档未写全，"见代码"，故以上面两个源文件为准）：
       https://github.com/wnma3mz/wechat_articles_spider/blob/master/docs/使用的微信公众号接口.md

  2. appmsg?action=list_ex（fakeid -> 分页文章列表）
     GET https://mp.weixin.qq.com/cgi-bin/appmsg
     params: action=list_ex, begin=<0,5,10,...>, count=5, fakeid=<fakeid>,
             type=9, query=, token=<token>, lang=zh_CN, f=json, ajax=1
     headers: Cookie: <登录态 Cookie>
     response: {"base_resp":{"ret":0,"err_msg":"ok"}, "app_msg_cnt":<total>,
                "app_msg_list":[{"aid","appmsgid","cover","digest",
                                 "itemidx","link","title","update_time"}, ...]}
     依据：wnma3mz/wechat_articles_spider 同一文件
       wechatarticles/ArticlesUrls.py :: PublicAccountsWeb.__get_articles_data()
     注意：app_msg_list 的条目**不含 author 字段**（这条接口就是不返回作者，
     不是脚本漏抓）——落地时 author 用 --account-name / WECHAT_ACCOUNT_NAME
     兜底，不保证等于真实署名作者，需要精确作者请人工核对原文页。

  ⚠️ cv-cat/WechatOAApis 拉文章列表用的其实是**另一个更新的接口**
  `cgi-bin/appmsgpublish`（sub=list&sub_action=list_ex&type=101_1，响应结构
  是 base_resp/publish_page，publish_page 还要再 json.loads 一次，里面才是
  publish_list，每条 publish_info 又是一层 JSON 字符串）——和这里用的
  `cgi-bin/appmsg?action=list_ex` 不是同一个接口，字段也不同。两者应该是
  mp 后台新旧两版前端各自调用的接口，档案里没有交叉验证过 appmsgpublish 这条
  路，本脚本按用户需求实现的是 appmsg/list_ex 这条（也是 wnma3mz 项目实际
  验证过的那条）。如果某天 appmsg/list_ex 失效了，appmsgpublish 是待评估的
  备选，不在本次改动范围内。

  base_resp.ret 错误码提示（非官方文档，社区逆向交叉核对，见 RET_HINTS 附
  搜索来源；仍标记「待用户实测校准」）：
    200003 invalid session  —— token/cookie 已过期
    200013 freq control     —— 触发限流，社区报告需等待较长时间（不等于几秒）
    200040 invalid csrf token —— token 和 Cookie 不是同一次登录会话抓的

Credentials (never commit): WECHAT_MP_TOKEN / WECHAT_MP_COOKIE, loaded from
$SOIA_PKM_ENV_FILE / ~/.config/soia-pkm/env / ~/.soia-pkm.env (see
scripts/soia_env.py), or plain process env vars.

Usage:
    python3 fetch_mp.py [--name <公众号名>] [--fakeid <fakeid>]
                         [--out <dir>] [--limit N] [--dry-run]
                         [--vault <path>] [--account-name <显示名>]
                         [--force] [--sleep 3] [--page-size 5]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
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
SEARCHBIZ_URL = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
APPMSG_URL = "https://mp.weixin.qq.com/cgi-bin/appmsg"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# search_biz / appmsg 两个接口社区实测都稳定在 count<=5；调大官方未文档化过，
# 容易先触发别的报错，保持 5 作为默认值。
PAGE_SIZE = 5

# base_resp.ret 错误码提示，来源：CSDN/知乎等社区帖交叉核对（非官方文档），
# 检索日期 2026-07；仍标记「待用户实测校准」。
RET_HINTS = {
    200003: "invalid session —— token/cookie 已过期，重新登录 mp.weixin.qq.com 后台抓取新的 token/Cookie",
    200013: "freq control —— 触发微信后台限流，社区报告通常需等较长时间（不是几秒）再试，别立刻重跑",
    200040: "invalid csrf token —— token 和 Cookie 疑似不是同一次登录会话抓的，两个要配对重新抓包",
}


def _http_get(url: str, headers: dict, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"❌ HTTP {e.code} calling {url}")
    except urllib.error.URLError as e:
        raise SystemExit(f"❌ Network error calling {url}: {e}")


def _get_json(url: str, headers: dict, context: str) -> dict:
    raw = _http_get(url, headers)
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(
            f"❌ {context} 没返回合法 JSON（大概率是 token/cookie 已过期或不完整，"
            "去已登录 mp.weixin.qq.com 后台的浏览器网络面板重新抓取 token/Cookie）。\n"
            "   原始响应前 300 字: " + raw[:300]
        )
    _check_ret(resp, context)
    return resp


def _check_ret(resp: dict, context: str) -> None:
    base = resp.get("base_resp") or {}
    ret = base.get("ret")
    if ret in (0, "0", None):
        return
    try:
        ret_int = int(ret)
    except (TypeError, ValueError):
        ret_int = None
    hint = RET_HINTS.get(ret_int, "去 mp.weixin.qq.com 后台重新登录、重新抓 token/Cookie 再试")
    raise SystemExit(
        f"❌ {context} 失败: ret={ret} err_msg={base.get('err_msg')}\n   提示: {hint}"
    )


def search_biz(name: str, token: str, cookie: str) -> dict:
    """公众号名 -> 第一个匹配结果（{'alias','fakeid','nickname',...}）。

    读自己的号：搜自己公众号名，取第一个匹配结果。如果搜索结果不止一个、
    或第一个看起来不像你自己的号，改用 --fakeid 直接指定，不要盲信排序。
    """
    params = {
        "action": "search_biz",
        "begin": "0",
        "count": str(PAGE_SIZE),
        "query": name,
        "token": token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    url = f"{SEARCHBIZ_URL}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": UA, "Cookie": cookie, "Referer": "https://mp.weixin.qq.com/"}
    resp = _get_json(url, headers, "searchbiz")
    matches = resp.get("list") or []
    if not matches:
        raise SystemExit(
            f"❌ searchbiz 没搜到与「{name}」匹配的公众号。检查名称是否完全一致，"
            "或改用 --fakeid 直接指定（从后台任意文章编辑页 URL 里的 __biz/fakeid 拿）。"
        )
    return matches[0]


def list_page(fakeid: str, token: str, cookie: str, begin: int, page_size: int) -> dict:
    params = {
        "action": "list_ex",
        "begin": str(begin),
        "count": str(page_size),
        "fakeid": fakeid,
        "type": "9",
        "query": "",
        "token": token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    url = f"{APPMSG_URL}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": UA, "Cookie": cookie, "Referer": "https://mp.weixin.qq.com/"}
    return _get_json(url, headers, "appmsg")


def fetch_article_list(
    fakeid: str, token: str, cookie: str, limit: int | None, page_size: int, sleep_s: float
) -> list[dict]:
    stubs: list[dict] = []
    seen_links: set[str] = set()
    begin = 0
    total: int | None = None
    while True:
        if limit is not None and len(stubs) >= limit:
            break
        resp = list_page(fakeid, token, cookie, begin, page_size)
        if total is None and resp.get("app_msg_cnt") is not None:
            total = int(resp["app_msg_cnt"])
        items = resp.get("app_msg_list") or []
        if not items:
            break
        new_count = 0
        for it in items:
            link = it.get("link") or ""
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            stubs.append(it)
            new_count += 1
        suffix = f" / 共 {total}" if total is not None else ""
        print(f"   begin={begin} 拿到 {len(items)} 条（新 {new_count}），累计 {len(stubs)}{suffix}", file=sys.stderr)
        if new_count == 0:
            break  # 整页都是重复链接，防止死循环
        begin += page_size
        if total is not None and begin >= total:
            break
        if len(items) < page_size:
            break
        time.sleep(sleep_s)
    return stubs[:limit] if limit is not None else stubs


def fetch_article_body(url: str) -> tuple[str, bool]:
    """GET a public article page and pull #js_content. Returns (markdown, complete).

    复用 Route B（fetch_cookie.py）同一套思路：appmsg 列表拿到的 link 是公开
    文章页 URL，不需要额外 cookie 就能直接 GET，解析同一个 #js_content 容器。
    """
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


def _stub_to_article(stub: dict, account_name: str) -> dict:
    update_time = stub.get("update_time")
    published_at = ""
    if update_time:
        try:
            published_at = (
                datetime.fromtimestamp(int(update_time), tz=timezone.utc).astimezone(CST).strftime("%Y-%m-%d %H:%M")
            )
        except (ValueError, OSError, OverflowError):
            pass
    return {
        "title": stub.get("title", ""),
        # appmsg/list_ex 不返回 author 字段（见文件头注释），用账号显示名兜底，
        # 不保证等于文章真实署名作者。
        "author": account_name or "",
        "url": stub.get("link", ""),
        "published_at": published_at,
    }


def main():
    load_private_env()

    ap = argparse.ArgumentParser(
        description="Route C: pull WeChat 公众号 full article history via mp 后台接口 into an Obsidian vault."
    )
    ap.add_argument("--name", help="公众号名称，用于 searchbiz 搜 fakeid（读自己的号：搜自己公众号名）")
    ap.add_argument("--fakeid", default=os.environ.get("WECHAT_MP_FAKEID"), help="已知 fakeid 时直接指定，跳过 searchbiz")
    ap.add_argument("--out", help="Vault-relative output dir (overrides OBSIDIAN_GZH_OUT env)")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT env)")
    ap.add_argument("--limit", type=int, help="Max number of articles to fetch (default: no limit)")
    ap.add_argument("--page-size", type=int, default=PAGE_SIZE, help=f"分页大小（默认 {PAGE_SIZE}，社区实测上限，别调大）")
    ap.add_argument("--dry-run", action="store_true", help="只拉列表打印标题+链接，不抓正文、不写文件")
    ap.add_argument("--force", action="store_true", help="Re-write files that already exist for a given url")
    ap.add_argument("--account-name", default=os.environ.get("WECHAT_ACCOUNT_NAME", ""), help="公众号显示名，用于文件名/落地 author 兜底")
    ap.add_argument("--sleep", type=float, default=3.0, help="每页/每篇请求之间的秒数（默认 3，别调太快，容易触发 freq control）")
    args = ap.parse_args()

    token = os.environ.get("WECHAT_MP_TOKEN")
    cookie = os.environ.get("WECHAT_MP_COOKIE")
    missing = [name for name, val in [("WECHAT_MP_TOKEN", token), ("WECHAT_MP_COOKIE", cookie)] if not val]
    if missing:
        print(f"❌ 缺 {', '.join(missing)}", file=sys.stderr)
        print(f"   放到私有 env 文件（{env_source_hint()}）。", file=sys.stderr)
        print(
            "   获取方式：登录 mp.weixin.qq.com 后台，随便打开一篇文章编辑/列表页，F12 打开「网络」面板，"
            "从任意 mp.weixin.qq.com 请求的 URL 里复制 token 参数、从请求头复制完整 Cookie 字符串。",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.name and not args.fakeid:
        print("❌ 缺 --name 或 --fakeid（二选一，指定要归档的公众号）", file=sys.stderr)
        sys.exit(1)

    account_name = args.account_name
    fakeid = args.fakeid
    if not fakeid:
        print(f"🔍 searchbiz 搜「{args.name}」…", file=sys.stderr)
        match = search_biz(args.name, token, cookie)
        fakeid = match.get("fakeid", "")
        nickname = match.get("nickname", "")
        alias = match.get("alias", "")
        print(f"   命中: nickname={nickname!r} alias={alias!r} fakeid={fakeid}", file=sys.stderr)
        print("   ⚠️ 请确认这就是你自己管理的公众号——不是则 Ctrl+C 中断，改用 --fakeid 精确指定。", file=sys.stderr)
        if not account_name:
            account_name = nickname

    print(f"📖 翻页拉取文章列表（fakeid={fakeid}, page_size={args.page_size}）…", file=sys.stderr)
    stubs = fetch_article_list(fakeid, token, cookie, args.limit, args.page_size, args.sleep)
    print(f"✓ 列表共 {len(stubs)} 篇", file=sys.stderr)

    if args.dry_run:
        for s in stubs:
            a = _stub_to_article(s, account_name)
            print(f"  [dry-run] {a.get('published_at') or '?'}  {a.get('title') or '(无标题)'}  {a.get('url','')}")
        print("dry-run：未抓正文、未写入任何文件。", file=sys.stderr)
        return

    print(f"开始逐篇抓正文（每篇间隔 {args.sleep}s）…", file=sys.stderr)
    articles = []
    for i, s in enumerate(stubs, 1):
        a = _stub_to_article(s, account_name)
        print(f"  [{i}/{len(stubs)}] {a.get('title','')}", file=sys.stderr)
        body, complete = fetch_article_body(a["url"]) if a["url"] else ("", False)
        a["content"] = body
        a["content_complete"] = complete
        articles.append(a)
        time.sleep(args.sleep)

    vault = resolve_vault(args.vault)
    out_dir = resolve_out_dir(vault, args.out)

    written = 0
    for a in articles:
        path = save_article(vault, out_dir, a, route="mp-backend", account_name=account_name, force=args.force)
        if path:
            written += 1
            print(f"✓ {path.relative_to(vault)}")

    print(f"\n完成：写入 {written} / 共 {len(articles)} 篇（其余已存在，跳过；用 --force 覆盖）")


if __name__ == "__main__":
    main()
