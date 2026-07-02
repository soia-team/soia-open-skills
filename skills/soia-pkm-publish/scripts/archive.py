#!/usr/bin/env python3
"""archive.py — 发布后归档：frontmatter status → 已发布 + 记链接/日期。
soia-pkm-publish 的归档器。用法：python3 archive.py --article <md> --url <link> [--date YYYY-MM-DD]
"""
import re
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--date", help="发布日期 YYYY-MM-DD（默认由调用方传入）")
    a = ap.parse_args()

    p = Path(a.article)
    t = p.read_text(encoding="utf-8")
    pub_date = a.date or ""

    if re.search(r"^status:", t, re.M):
        t = re.sub(r"^status:.*$", "status: 已发布", t, count=1, flags=re.M)
    else:
        t = t.replace("---\n", "---\nstatus: 已发布\n", 1)

    if "published_url:" not in t:
        add = f"published_url: {a.url}\n"
        if pub_date:
            add += f"published_date: {pub_date}\n"
        t = re.sub(r"^status: 已发布$", "status: 已发布\n" + add.rstrip(), t, count=1, flags=re.M)

    p.write_text(t, encoding="utf-8")
    print(f"✅ 已归档：{p.name} → status: 已发布，链接已记（{a.url}）")


if __name__ == "__main__":
    main()
