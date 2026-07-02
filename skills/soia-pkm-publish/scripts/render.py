#!/usr/bin/env python3
"""render.py — Markdown → 带样式 HTML（公众号可直接贴）。soia-pkm-publish 的渲染器。

三级强调：**短语** → 主题色加粗；==关键== → 红色加粗；`code` → 等宽。
风格：editorial（干净）/ tech（代码块+表格）。纯标准库，无外部依赖。

用法：python3 render.py <in.md> <out.html> [--style tech|editorial]
"""
import re
import argparse
from pathlib import Path

THEME = "#c0392b"  # 主题色，可改


def parse_fm(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    fm, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
        body = text[m.end():]
    return fm, body


def inline(s):
    s = re.sub(r"==(.+?)==", rf'<strong style="color:{THEME}">\1</strong>', s)  # L2 关键→红加粗
    s = re.sub(r"\*\*(.+?)\*\*", rf'<strong style="color:{THEME}">\1</strong>', s)  # L1 短语→主题色加粗
    s = re.sub(r"`(.+?)`", r'<code style="background:#f6f8fa;padding:1px 4px;border-radius:3px">\1</code>', s)
    return s


def render(md, style):
    fm, body = parse_fm(md)
    out, in_code = [], False
    for line in body.splitlines():
        if line.startswith("```"):
            if not in_code:
                out.append('<pre style="background:#f6f8fa;padding:12px;border-radius:6px;overflow:auto"><code>')
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            continue
        if in_code:
            out.append(line)
            continue
        if re.match(r"^#{1,6} ", line):
            lv = len(line) - len(line.lstrip("#"))
            txt = line.lstrip("# ").strip()
            out.append(f'<h{lv} style="font-weight:700;margin:22px 0 12px">{inline(txt)}</h{lv}>')
        elif line.strip() == "":
            out.append("")
        else:
            out.append(f'<p style="line-height:1.75;margin:16px 0">{inline(line)}</p>')
    title = fm.get("title", "")
    wrap = "max-width:677px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#333;font-size:16px"
    return (
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title></head>'
        f'<body style="{wrap}">\n' + "\n".join(out) + "\n</body></html>"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--style", default="editorial", choices=["tech", "editorial"])
    a = ap.parse_args()
    html = render(Path(a.inp).read_text(encoding="utf-8"), a.style)
    Path(a.out).write_text(html, encoding="utf-8")
    print(f"✅ 渲染完成：{a.out}（{len(html)} 字节，风格 {a.style}）")
