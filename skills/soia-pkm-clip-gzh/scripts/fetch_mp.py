#!/usr/bin/env python3
"""
fetch_mp.py — Route C (公众号后台接口) for soia-pkm-clip-gzh.

Reads a WeChat Official Account's *full* article history — including old
articles that were only ever sent via 手动群发 and never went through the
official "发布" API — by replaying requests the mp.weixin.qq.com 后台 web UI
makes while you are logged in. Two independent endpoints under this same
后台（作者登录态）umbrella, selected automatically by how you invoke the script:

  - 不带 --name / --fakeid（默认，推荐）：读**你自己**当前登录的这个账号的
    「发表记录」，走 appmsgpublish（sub=list&sub_action=list_ex&type=101_1）。
    这是本 skill 2026-07-09 由用户实测验证通过的路径（ret=0，total_count 正常
    返回），也是读"自己号"更合适的入口——下面的 searchbiz 是按名字模糊搜索
    公众号列表，面向"找到别人的号"场景，搜自己的号经常搜不到自己（返回空
    列表），不适合当成"我已经登录、我就是这个号"的默认路径。
  - 带 --name 或 --fakeid（读指定/别人的号）：保留原本的 search_biz（name ->
    fakeid）+ appmsg?action=list_ex（fakeid -> paginated article list）两步，
    适合你知道目标账号名称/fakeid、但没有以该账号身份登录后台的场景。

两条路都能读到全部历史（含手动群发的老文，不止草稿箱正式发布过的），这点和
路 A（官方 API，见 fetch_api.py）不同；路 A 的覆盖范围限制见 SKILL.md。appmsg
系两个接口（search_biz / appmsg?action=list_ex）是本 skill 早前实现、和路 B
(profile_ext) 同一批，一般被报告为比 profile_ext 的 key/pass_ticket 组合更
稳定、token 存活更久。

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

  3. appmsgpublish（读自己号「发表记录」，默认路径，本次新增）
     GET https://mp.weixin.qq.com/cgi-bin/appmsgpublish
     params: sub=list, begin=<0,20,40,...>, count=20, type=101_1,
             free_publish_type=1, sub_action=list_ex, token=<token>,
             lang=zh_CN, f=json, ajax=1
     headers: Cookie: <登录态 Cookie>
     response 是三层嵌套 JSON，解析时注意（见 list_own_account_page()）：
       resp = json.loads(body)                    # 第一层：HTTP body
       resp["base_resp"]["ret"] == 0 才 ok（复用 _check_ret，同上）
       page = json.loads(resp["publish_page"])     # 第二层：publish_page 本身是 JSON 字符串
       # page == {"total_count": N, "publish_list": [...]}
       for item in page["publish_list"]:
           info = json.loads(item["publish_info"])  # 第三层：publish_info 也是 JSON 字符串
           for a in info["appmsgex"]:                # 每条含 title / link / update_time / digest
               ...
     翻页：begin += count（默认 20），直到某页 publish_list 为空。
     依据：cv-cat/WechatOAApis 项目源码级核对（同上 searchbiz 交叉核对来源之
     一：utils/wx_utils.py），并已于 2026-07-09 由本 skill 用户在真实账号上
     实测验证通过（ret=0，total_count=152，成功读到自己号「发表记录」全量
     条目）——是三个接口里目前唯一有"真实账号实测"背书的一条；searchbiz /
     appmsg?action=list_ex 仍停留在"源码级核对、待用户实测校准"。
     和 searchbiz / appmsg?action=list_ex 是 mp 后台新旧两版前端各自调用的
     接口，响应结构、分页步长都不同，不能混用同一套解析逻辑，脚本里是两套
     独立实现（fetch_article_list() vs list_own_account()）。

  base_resp.ret 错误码提示（非官方文档，社区逆向交叉核对，见 RET_HINTS 附
  搜索来源；仍标记「待用户实测校准」，appmsgpublish 走同一套错误码提示）：
    200003 invalid session  —— token/cookie 已过期
    200013 freq control     —— 触发限流，社区报告需等待较长时间（不等于几秒）
    200040 invalid csrf token —— token 和 Cookie 不是同一次登录会话抓的

Credentials (never commit): WECHAT_MP_TOKEN / WECHAT_MP_COOKIE, loaded from
$SOIA_PKM_ENV_FILE / ~/.config/soia-pkm/env / ~/.soia-pkm.env (see
scripts/soia_env.py), or plain process env vars. token 取自登录 mp 后台后
**地址栏 URL 里的 `token=` 那一串数字**（不是网络面板里某个请求参数名叫
`appmsg_token` 的那个，两者是不同的票据，appmsgpublish 认的是地址栏 token）。

Usage:
    # 默认（不带 --name/--fakeid）：读你自己登录的账号（appmsgpublish，推荐）
    python3 fetch_mp.py [--out <dir>] [--limit N] [--dry-run]
                         [--vault <path>] [--account-name <显示名>]
                         [--force] [--sleep 3] [--page-size 20]

    # 带 --name 或 --fakeid：读指定/别人的号（searchbiz + appmsg?action=list_ex）
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
APPMSGPUBLISH_URL = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# search_biz / appmsg 两个接口社区实测都稳定在 count<=5；调大官方未文档化过，
# 容易先触发别的报错，保持 5 作为默认值。用于「读指定/别人的号」路径
# （--name / --fakeid）。
PAGE_SIZE = 5

# appmsgpublish（读自己号「发表记录」，默认路径）2026-07-09 实测 count=20 正常
# 返回；和上面 PAGE_SIZE 是两个独立接口的分页步长，不需要一致。
OWN_PAGE_SIZE = 20

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


def list_own_account_page(token: str, cookie: str, begin: int, page_size: int) -> list[dict]:
    """One page of *your own* account's 「发表记录」via appmsgpublish.

    与 list_page()（searchbiz+appmsg 路径）不是同一个接口：不需要 fakeid（用的
    是当前登录态本身对应的账号），响应结构也不同 —— 是三层嵌套 JSON，需要
    两次额外的 json.loads 才能拿到真正的文章条目（见模块头部注释「接口依据」
    第 3 条）。返回本页拍平后的 appmsgex 条目列表（每条含
    title/link/update_time/digest），拿不到合法内层 JSON 时按空页处理，不
    中断整个翻页流程（可能只是这一页恰好为空/格式漂移）。
    """
    params = {
        "sub": "list",
        "begin": str(begin),
        "count": str(page_size),
        "type": "101_1",
        "free_publish_type": "1",
        "sub_action": "list_ex",
        "token": token,
        "lang": "zh_CN",
        "f": "json",
        "ajax": "1",
    }
    url = f"{APPMSGPUBLISH_URL}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": UA, "Cookie": cookie, "Referer": "https://mp.weixin.qq.com/"}
    resp = _get_json(url, headers, "appmsgpublish")

    pp_raw = resp.get("publish_page")
    if not pp_raw:
        return []
    try:
        page = json.loads(pp_raw)
    except json.JSONDecodeError:
        print(
            "  ⚠️ appmsgpublish 的 publish_page 字段不是合法 JSON 字符串（接口大概率已改版），"
            "跳过这一页。",
            file=sys.stderr,
        )
        return []

    stubs: list[dict] = []
    for item in page.get("publish_list") or []:
        info_raw = item.get("publish_info")
        if not info_raw:
            continue
        try:
            info = json.loads(info_raw)
        except json.JSONDecodeError:
            continue
        stubs.extend(info.get("appmsgex") or [])
    return stubs


def list_own_account(
    token: str, cookie: str, limit: int | None, page_size: int, sleep_s: float
) -> list[dict]:
    """读你自己当前登录账号的全部「发表记录」（appmsgpublish，默认路径）。

    不需要 fakeid/searchbiz——appmsgpublish 只认 token+Cookie 对应的登录态，
    天然就是"我自己这个号"，不存在 search_biz 那样"搜自己号搜不到"的问题。
    翻页策略和 fetch_article_list() 类似（按 link 去重、空页/不足一页判定
    终止），但不依赖 app_msg_cnt 式的总数字段——appmsgpublish 的 total_count
    位于 page 内部，这里只用它做日志展示，不用来判定终止（终止条件是拿到
    空 publish_list）。
    """
    stubs: list[dict] = []
    seen_links: set[str] = set()
    begin = 0
    while True:
        if limit is not None and len(stubs) >= limit:
            break
        items = list_own_account_page(token, cookie, begin, page_size)
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
        print(f"   begin={begin} 拿到 {len(items)} 条（新 {new_count}），累计 {len(stubs)}", file=sys.stderr)
        if new_count == 0:
            break  # 整页都是重复链接，防止死循环
        begin += page_size
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
    ap.add_argument(
        "--name",
        help="读指定/别人的号：公众号名称，用于 searchbiz 搜 fakeid。不传 --name/--fakeid 时默认改走"
        "「读自己当前登录的号」（appmsgpublish），不需要这个参数。",
    )
    ap.add_argument(
        "--fakeid",
        default=os.environ.get("WECHAT_MP_FAKEID"),
        help="读指定/别人的号：已知 fakeid 时直接指定，跳过 searchbiz。同上，默认路径不需要这个参数。",
    )
    ap.add_argument("--out", help="Vault-relative output dir (overrides OBSIDIAN_GZH_OUT env)")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT env)")
    ap.add_argument("--limit", type=int, help="Max number of articles to fetch (default: no limit)")
    ap.add_argument(
        "--page-size",
        type=int,
        default=None,
        help=f"分页大小（默认：读自己号 {OWN_PAGE_SIZE}，读指定/别人号（--name/--fakeid）{PAGE_SIZE}，"
        "均为已验证/社区实测的稳定值，别调大）",
    )
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
            "从地址栏 URL 里复制 token 参数（不是网络面板某个请求参数名叫 appmsg_token 的那个）、"
            "从请求头复制完整 Cookie 字符串。",
            file=sys.stderr,
        )
        sys.exit(1)

    account_name = args.account_name
    use_own_account = not args.name and not args.fakeid

    if use_own_account:
        page_size = args.page_size or OWN_PAGE_SIZE
        print("📖 读取你自己当前登录账号的「发表记录」（appmsgpublish，默认路径）…", file=sys.stderr)
        stubs = list_own_account(token, cookie, args.limit, page_size, args.sleep)
    else:
        page_size = args.page_size or PAGE_SIZE
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

        print(f"📖 翻页拉取文章列表（fakeid={fakeid}, page_size={page_size}）…", file=sys.stderr)
        stubs = fetch_article_list(fakeid, token, cookie, args.limit, page_size, args.sleep)

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
