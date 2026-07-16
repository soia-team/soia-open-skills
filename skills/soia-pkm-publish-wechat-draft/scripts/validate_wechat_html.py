#!/usr/bin/env python3
"""validate_wechat_html.py — 微信公众号 HTML 排版红线校验（soia-pkm-publish-wechat-draft skill 机械层）

公众号编辑器（网页粘贴 / draft/add 接口）会主动过滤或丢弃大量 HTML/CSS 写法，
排版稿一旦踩中这些红线，样式大概率在粘贴或推送后整段消失。本脚本只读扫描一份
渲染好的 HTML，按 SKILL.md「微信平台红线」逐条核对，报告每处违规的行号 + 类型。

硬性违规（命中任意一条即 exit 1，必须先改渲染结果再推草稿箱）：
  - <div ...>                        —— 微信不识别，块级容器改用 <section>/<p>
  - class="..." / id="..."           —— 编辑器会剥离，样式必须全部内联在 style=""
  - style 属性值里出现 position: / float:
  - <style>...</style> 整块           —— 样式必须逐个内联，不能用 <style> 标签
  - @media / @keyframes               —— 响应式断点 / 动画规则微信不支持
  - CSS 变量：var(--x) 用法 / --x: 声明 —— 自定义属性不支持，颜色等要写死字面值

软性提示（warning，不计入 exit code，建议顺手修）：
  - 裸文字节点：块级/行内标签（p、section、h1-6、li、blockquote、strong、em、a…）
    直接包裹的可见文字，没有再套一层 <span style="...">——公众号编辑器复制粘贴时
    经常按标签边界取样式，裸文字最容易在粘贴后掉样式。<code>/<pre> 内的等宽文本
    本身就是"原样展示"，不强制要求再套 span。

用法：
  python3 validate_wechat_html.py --file article.html
  cat article.html | python3 validate_wechat_html.py
  python3 validate_wechat_html.py --file article.html --json

exit code：0 = 无硬性违规（可能仍有 warning）；1 = 至少一条硬性违规。
纯标准库实现（html.parser），无第三方依赖。
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# 解析后仍视为"已经自带样式承载能力"的标签：直接挂在它们下面的文字不算裸文字节点。
SPAN_LIKE_TAGS = {"span"}
# 这些标签下的文字本身就是原样/等宽展示，不强制套 span（<style>/<script> 内容另有专门检查）。
SKIP_BARE_TEXT_PARENTS = {"style", "script", "code", "pre", "title"}
# 不进入 tag 栈的 void / 自闭合元素（没有对应闭合标签，不应该影响"当前父标签"判断）。
VOID_TAGS = {"br", "img", "hr", "meta", "link", "input", "area", "base", "col", "embed", "source", "track", "wbr"}

FORBIDDEN_CSS_PATTERNS = [
    (re.compile(r"position\s*:", re.I), "position"),
    (re.compile(r"float\s*:", re.I), "float"),
    (re.compile(r"@media", re.I), "media-query"),
    (re.compile(r"@keyframes", re.I), "keyframes"),
    (re.compile(r"var\(\s*--", re.I), "css-var-use"),
    (re.compile(r"--[a-zA-Z][\w-]*\s*:", re.I), "css-var-decl"),
]


class WeChatHTMLChecker(HTMLParser):
    """遍历 HTML，收集硬性违规（errors）和软性提示（warnings）。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.errors = []
        self.warnings = []
        self.tag_stack = []
        self.style_block_depth = 0

    def _record(self, bucket, kind, detail, line=None, col=None):
        if line is None:
            line, col0 = self.getpos()
            col = col0 + 1
        bucket.append({"line": line, "col": col, "type": kind, "detail": detail})

    def _check_attrs(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "div":
            self._record(self.errors, "div-tag", "<div> 标签，微信不认，改用 <section>/<p>")
        if tag == "style":
            self._record(self.errors, "style-block", "<style> 标签，样式必须内联在 style=\"\"")
        if "class" in attrs_d:
            self._record(self.errors, "class-attr", f'class="{attrs_d.get("class")}"，编辑器会剥离该属性')
        if "id" in attrs_d:
            self._record(self.errors, "id-attr", f'id="{attrs_d.get("id")}"，编辑器会剥离该属性')
        style_val = attrs_d.get("style") or ""
        for pattern, label in FORBIDDEN_CSS_PATTERNS:
            if pattern.search(style_val):
                self._record(self.errors, f"style-{label}", f'style="{style_val}" 中出现 {label}')

    def handle_starttag(self, tag, attrs):
        tag_l = tag.lower()
        self._check_attrs(tag_l, attrs)
        if tag_l == "style":
            self.style_block_depth += 1
        if tag_l not in VOID_TAGS:
            self.tag_stack.append(tag_l)

    def handle_startendtag(self, tag, attrs):
        # 自闭合写法（<img .../> 等），不进 tag 栈，但属性仍要检查
        self._check_attrs(tag.lower(), attrs)

    def handle_endtag(self, tag):
        tag_l = tag.lower()
        if tag_l == "style" and self.style_block_depth > 0:
            self.style_block_depth -= 1
        if tag_l in self.tag_stack:
            for i in range(len(self.tag_stack) - 1, -1, -1):
                if self.tag_stack[i] == tag_l:
                    del self.tag_stack[i:]
                    break

    def handle_data(self, data):
        if self.style_block_depth > 0:
            base_line, _ = self.getpos()
            for pattern, label in FORBIDDEN_CSS_PATTERNS:
                for mm in pattern.finditer(data):
                    line = base_line + data.count("\n", 0, mm.start())
                    self._record(
                        self.errors, f"style-{label}",
                        f"<style> 内容中出现 {label}", line=line, col=1,
                    )
            return
        if not data.strip():
            return
        parent = self.tag_stack[-1] if self.tag_stack else None
        if parent in SPAN_LIKE_TAGS or parent in SKIP_BARE_TEXT_PARENTS:
            return
        snippet = re.sub(r"\s+", " ", data.strip())
        if len(snippet) > 24:
            snippet = snippet[:24] + "…"
        self._record(
            self.warnings, "bare-text",
            f'文字 "{snippet}" 未被 <span> 包裹（父标签：<{parent or "根"}>）',
        )


def render_markdown(errors, warnings, source):
    lines = ["# 微信 HTML 红线校验报告", "", f"- 来源：`{source}`",
              f"- 硬性违规：{len(errors)}", f"- 提示（warning）：{len(warnings)}", ""]

    lines.append("## 硬性违规（必须修，否则粘贴/推送后大概率掉样式或被吃掉）")
    lines.append("")
    if errors:
        lines.append("| 行号 | 类型 | 详情 |")
        lines.append("|---|---|---|")
        for e in sorted(errors, key=lambda x: (x["line"], x["col"])):
            lines.append(f'| {e["line"]} | {e["type"]} | {e["detail"]} |')
    else:
        lines.append("无")
    lines.append("")

    lines.append("## 提示（warning，不阻塞发布，建议顺手清一遍）")
    lines.append("")
    if warnings:
        lines.append("| 行号 | 类型 | 详情 |")
        lines.append("|---|---|---|")
        for w in sorted(warnings, key=lambda x: (x["line"], x["col"])):
            lines.append(f'| {w["line"]} | {w["type"]} | {w["detail"]} |')
    else:
        lines.append("无")
    lines.append("")

    if errors:
        lines.append(f"结论：❌ {len(errors)} 处硬性违规，先修渲染结果再推草稿箱。")
    else:
        lines.append("结论：✅ 无硬性违规，可以进入 publish.py 推草稿箱。")
    return "\n".join(lines) + "\n"


def parse_args():
    ap = argparse.ArgumentParser(
        description="微信公众号 HTML 排版红线校验（div/class/id/position/float/media/keyframes/css var/style 块）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--file", help="待校验 HTML 文件路径；不传则从 stdin 读取")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非默认的 markdown 报告")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.file:
        html_text = Path(args.file).read_text(encoding="utf-8")
        source = args.file
    else:
        html_text = sys.stdin.read()
        source = "<stdin>"

    checker = WeChatHTMLChecker()
    checker.feed(html_text)
    checker.close()

    if args.json:
        payload = {
            "source": source,
            "errors": checker.errors,
            "warnings": checker.warnings,
            "summary": {"errors": len(checker.errors), "warnings": len(checker.warnings)},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(checker.errors, checker.warnings, source))

    sys.exit(1 if checker.errors else 0)


if __name__ == "__main__":
    main()
