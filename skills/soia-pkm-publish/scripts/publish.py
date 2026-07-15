#!/usr/bin/env python3
"""publish.py — 渲染 + 推微信公众号草稿箱。soia-pkm-publish 的发布器（框架）。

凭据从环境变量 / 私有 config.yml 读 WECHAT_APP_ID / WECHAT_APP_SECRET。
--dry-run 只渲染不推送。安全：只建草稿（draft/add），绝不群发。

用法：python3 publish.py --article <md> [--cover <png>] [--dry-run]
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

from publish_env import load_private_env

# 自动探测 skill-specific 私有 config.yml，
# 把 WECHAT_APP_ID / WECHAT_APP_SECRET 等 setdefault 进环境（不覆盖已有进程变量）。
load_private_env()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", required=True)
    ap.add_argument("--cover")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    md = Path(a.article)
    html_path = md.with_suffix(".html")

    # 1. 渲染（调同目录 render.py）
    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "render.py"), str(md), str(html_path)],
        check=True,
    )

    if a.dry_run:
        print(f"[dry-run] 已渲染 {html_path}，未推送。去掉 --dry-run 才实际建草稿。")
        return

    # 2. 凭据
    app_id = os.environ.get("WECHAT_APP_ID")
    secret = os.environ.get("WECHAT_APP_SECRET")
    if not (app_id and secret):
        print("❌ 缺 WECHAT_APP_ID / WECHAT_APP_SECRET：请放到私有 config.yml或进程环境，勿提交 Git")
        sys.exit(1)

    # 3. 微信 API（待实现的框架）：
    #    a) GET /cgi-bin/token?grant_type=client_credential → access_token
    #    b) 扫 HTML 里的图片 → POST media/uploadimg 换成微信 CDN URL；上传封面 → thumb_media_id
    #    c) POST /cgi-bin/draft/add  body={articles:[{title,content=html,thumb_media_id,...}]}
    print("TODO: access_token → media/uploadimg（图片/封面）→ draft/add（建草稿）")
    print("⚠️ 本脚本只建草稿；群发请在公众号后台手动确认。")


if __name__ == "__main__":
    main()
