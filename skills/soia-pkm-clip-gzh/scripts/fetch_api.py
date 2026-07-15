#!/usr/bin/env python3
"""
fetch_api.py — Route A (官方 API) for soia-pkm-clip-gzh.

Pulls WeChat Official Account articles that are reachable through the
official server API — freepublish/batchget (articles published via 草稿箱 →
"发布") and material/batchget_material type=news (permanent 图文素材) — and
lands them as Markdown notes in an Obsidian vault.

依据（2026-07 核对 developers.weixin.qq.com，字段名已用于本文件注释；
无法一次性抓到官方页面全文的部分用微信社区帖 + 多方交叉验证补齐，标注见下）：
  - 获取 access_token: GET /cgi-bin/token?grant_type=client_credential&appid=&secret=
    -> {access_token, expires_in} 或 {errcode, errmsg}
    https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
  - 获取成功发布列表: POST /cgi-bin/freepublish/batchget?access_token=
    body {offset, count, no_content} -> {total_count, item_count,
    item:[{article_id, content:{news_item:[{title,author,digest,content,
    content_source_url,thumb_media_id,show_cover_pic,need_open_comment,
    only_fans_can_comment,url,is_deleted}]}, update_time}]}
    https://developers.weixin.qq.com/doc/service/api/public/api_freepublish_batchget
    （官方文档页在抓取时未能取到请求/响应示例全文，字段名已与微信开放社区
    多个独立帖子交叉核对一致，仍标记为「待用户实测校准」）
  - 获取永久素材列表: POST /cgi-bin/material/batchget_material?access_token=
    body {type:"news", offset, count}（count 官方文档标注范围 1-20）->
    {total_count, item_count, item:[{media_id, content:{news_item:[...]},
    update_time}]}
    https://developers.weixin.qq.com/doc/service/api/material/permanent/api_batchgetmaterial

⚠️ COVERAGE LIMITATION（务必先读，别指望这条路能拿到全部历史）：
  - freepublish/batchget 只返回**通过草稿箱「发布」动作**发出的文章；仅"群发"
    但没有走"发布"的内容、以及草稿箱功能上线前的旧版图文消息，官方目前没有
    任何 API 能拿到（微信开放社区多个帖子交叉确认，非官方文档白纸黑字写明）。
  - material/batchget_material（type=news）返回的是永久图文素材；据社区反馈，
    一篇文章一旦经草稿箱正式「发布」，可能就从这个素材列表里消失——这条路和
    freepublish/batchget 是互补关系，不是"取并集就等于全部历史"。
  - 「发布能力」相关接口文档注明：自 2025-07 起，个人主体账号、企业主体未
    认证账号、以及不支持认证的账号，这些接口的调用权限会被回收。也就是说
    多数个人订阅号大概率**整条路线都跑不通**，需要已认证服务号/订阅号。
  - 结论：路 A 更像是"抽查/核对"，不是"全量备份"；要读全部历史（含手动群发
    的老文）用路 B。

Credentials (never commit): WECHAT_APP_ID / WECHAT_APP_SECRET, loaded from
SOIA_PKM_CLIP_GZH_CONFIG_FILE / skill-specific config.yml (see scripts/clip_gzh_env.py)
or plain process env vars.

Usage:
    python3 fetch_api.py [--out <vault-relative-dir>] [--limit N] [--dry-run]
                          [--vault <path>] [--account-name <公众号显示名>]
                          [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

from clip_gzh_env import env_source_hint, load_private_env
from save_articles import (
    html_to_markdown,
    resolve_out_dir,
    resolve_vault,
    save_article,
)

CST = timezone(timedelta(hours=8))
TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
FREEPUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/batchget"
MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/batchget_material"

# material/batchget_material's docs state count is 1-20. freepublish/batchget
# does not document an explicit upper bound; community reports use the same
# 1-20 range. Unverified for freepublish — lower --page-size if you hit 40097.
PAGE_SIZE = 20

# Errcodes worth a specific hint (developers.weixin.qq.com/doc/offiaccount/Error_code.html,
# checked 2026-07; not exhaustive).
ERROR_HINTS = {
    40001: "AppSecret 不对或 access_token 已过期，检查 WECHAT_APP_SECRET",
    40013: "AppID 不合法，检查 WECHAT_APP_ID",
    40125: "invalid appsecret，检查 WECHAT_APP_SECRET 是否复制完整",
    40164: "调用方 IP 不在白名单，去 mp 后台「设置与开发→开发→基本配置」加白名单（本机公网 IP: curl ifconfig.me）",
    40243: "AppSecret 已被冻结，去后台解冻或重置",
    41004: "缺 secret 参数",
    48001: "api unauthorized —— 大概率是未认证的个人订阅号没有这个接口权限（发布能力类接口 2025-07 起对个人主体/未认证账号收权限，见本文件头部注释）",
    50007: "账号被冻结，联系微信客服",
}


def _http_json(url: str, data: bytes | None = None, timeout: int = 20) -> dict:
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"} if data else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise SystemExit(f"❌ HTTP {e.code} calling {url}: {body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"❌ Network error calling {url}: {e}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"❌ Response from {url} was not JSON: {e}")


def _check_wx_error(resp: dict, context: str) -> None:
    errcode = resp.get("errcode")
    if errcode:  # 0 / missing means success
        hint = ERROR_HINTS.get(
            errcode, "查 https://developers.weixin.qq.com/doc/offiaccount/Error_code.html"
        )
        raise SystemExit(
            f"❌ {context} 失败: errcode={errcode} errmsg={resp.get('errmsg')}\n   提示: {hint}"
        )


def get_access_token(app_id: str, secret: str) -> str:
    url = f"{TOKEN_URL}?grant_type=client_credential&appid={app_id}&secret={secret}"
    resp = _http_json(url)
    _check_wx_error(resp, "获取 access_token")
    token = resp.get("access_token")
    if not token:
        raise SystemExit(f"❌ 拿到响应但没有 access_token 字段: {resp}")
    return token


def _news_item_to_article(news: dict, update_time, endpoint: str) -> dict:
    url = news.get("url") or news.get("content_source_url") or ""
    content_html = news.get("content") or ""
    published_at = ""
    if update_time:
        try:
            published_at = (
                datetime.fromtimestamp(int(update_time), tz=timezone.utc)
                .astimezone(CST)
                .strftime("%Y-%m-%d %H:%M")
            )
        except (ValueError, OSError, OverflowError):
            published_at = ""
    return {
        "title": news.get("title", ""),
        "author": news.get("author", ""),
        "url": url,
        "published_at": published_at,
        "content": html_to_markdown(content_html),
        "content_complete": bool(content_html),
        "_endpoint": endpoint,  # debug only, not written to frontmatter
    }


def fetch_freepublish(token: str, limit: int | None, page_size: int) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        if limit is not None and len(out) >= limit:
            break
        body = json.dumps({"offset": offset, "count": page_size, "no_content": 0}).encode("utf-8")
        resp = _http_json(f"{FREEPUBLISH_URL}?access_token={token}", data=body)
        _check_wx_error(resp, "freepublish/batchget")
        items = resp.get("item") or []
        if not items:
            break
        for it in items:
            update_time = it.get("update_time")
            for news in (it.get("content") or {}).get("news_item") or []:
                if news.get("is_deleted"):
                    continue
                out.append(_news_item_to_article(news, update_time, "freepublish"))
        if len(items) < page_size:
            break
        offset += page_size
        time.sleep(0.3)
    return out[:limit] if limit is not None else out


def fetch_material_news(token: str, limit: int | None, page_size: int) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        if limit is not None and len(out) >= limit:
            break
        body = json.dumps({"type": "news", "offset": offset, "count": page_size}).encode("utf-8")
        resp = _http_json(f"{MATERIAL_URL}?access_token={token}", data=body)
        _check_wx_error(resp, "material/batchget_material")
        items = resp.get("item") or []
        if not items:
            break
        for it in items:
            update_time = it.get("update_time")
            for news in (it.get("content") or {}).get("news_item") or []:
                out.append(_news_item_to_article(news, update_time, "material"))
        if len(items) < page_size:
            break
        offset += page_size
        time.sleep(0.3)
    return out[:limit] if limit is not None else out


def dedupe(articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for a in articles:
        key = a.get("url") or a.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def main():
    load_private_env()

    ap = argparse.ArgumentParser(
        description="Route A: pull WeChat 公众号 articles via official API into an Obsidian vault."
    )
    ap.add_argument("--out", help="Vault-relative output dir (overrides OBSIDIAN_GZH_OUT env)")
    ap.add_argument("--vault", help="Path to Obsidian vault (overrides OBSIDIAN_VAULT env)")
    ap.add_argument("--limit", type=int, help="Max number of articles to fetch (default: no limit)")
    ap.add_argument("--page-size", type=int, default=PAGE_SIZE, help=f"API page size (default {PAGE_SIZE})")
    ap.add_argument("--dry-run", action="store_true", help="Fetch and print the list, write nothing")
    ap.add_argument("--force", action="store_true", help="Re-write files that already exist for a given url")
    ap.add_argument(
        "--account-name",
        default=os.environ.get("WECHAT_ACCOUNT_NAME", ""),
        help="公众号显示名，用于文件名/来源信息（两个 API 都不返回昵称）",
    )
    args = ap.parse_args()

    app_id = os.environ.get("WECHAT_APP_ID")
    secret = os.environ.get("WECHAT_APP_SECRET")
    if not (app_id and secret):
        print("❌ 缺 WECHAT_APP_ID / WECHAT_APP_SECRET", file=sys.stderr)
        print(f"   放到私有 config.yml（{env_source_hint()}）或进程环境，勿提交 Git。", file=sys.stderr)
        sys.exit(1)

    print("🔑 换取 access_token …", file=sys.stderr)
    token = get_access_token(app_id, secret)

    print("📰 拉取 freepublish/batchget（API/草稿箱发布列表）…", file=sys.stderr)
    published = fetch_freepublish(token, args.limit, args.page_size)
    print(f"   拿到 {len(published)} 篇", file=sys.stderr)

    remaining = None if args.limit is None else max(0, args.limit - len(published))
    material: list[dict] = []
    if remaining is None or remaining > 0:
        print("🗂  拉取 material/batchget_material（永久图文素材）…", file=sys.stderr)
        material = fetch_material_news(token, remaining, args.page_size)
        print(f"   拿到 {len(material)} 篇", file=sys.stderr)

    articles = dedupe(published + material)
    if args.limit is not None:
        articles = articles[: args.limit]

    print(f"✓ 合并去重后共 {len(articles)} 篇（这不等于你公众号的全部历史，见文件头部「COVERAGE LIMITATION」）", file=sys.stderr)

    if args.dry_run:
        for a in articles:
            print(f"  [dry-run] {a.get('published_at') or '?'}  {a.get('title') or '(无标题)'}  {a.get('url','')}")
        print("dry-run：未写入任何文件。", file=sys.stderr)
        return

    vault = resolve_vault(args.vault)
    out_dir = resolve_out_dir(vault, args.out)

    written = 0
    for a in articles:
        path = save_article(vault, out_dir, a, route="api", account_name=args.account_name, force=args.force)
        if path:
            written += 1
            print(f"✓ {path.relative_to(vault)}")

    print(f"\n完成：写入 {written} / 共 {len(articles)} 篇（其余已存在，跳过；用 --force 覆盖）")


if __name__ == "__main__":
    main()
