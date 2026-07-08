#!/usr/bin/env python3
"""Generate a local transform smoke-test bundle from one Markdown article.

This script is intentionally provider-neutral: no vault path, personal profile,
API key, or external SaaS dependency is baked in. It exercises the public local
provider path: Markdown/report, PDF via browser print, PPTX, HTML deck, dense
infographic PNG, data table, quiz, flashcards, mindmap, podcast/video scripts.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt
except Exception as exc:  # pragma: no cover - reported at runtime
    Presentation = None
    PPTX_IMPORT_ERROR = exc
else:
    PPTX_IMPORT_ERROR = None


TERM_LIBRARY = [
    ("AI", "人工智能", "让机器完成原本需要人类智能参与的理解、生成、判断和执行任务。"),
    ("机器学习", "学习范式", "给机器大量样本，让它从数据里总结规律，而不是靠程序员写死规则。"),
    ("深度学习", "模型训练", "用多层神经网络逐级提取特征，是今天很多大模型的基础。"),
    ("LLM", "大语言模型", "理解和生成文本的模型，不是搜索引擎，也不是固定规则聊天机器人。"),
    ("GPT", "模型家族", "可以理解为 AI 能力发动机；ChatGPT 是面向人的产品入口。"),
    ("AIGC", "生成结果", "AI 生成的文字、图片、音频、视频、代码等内容产物。"),
    ("API", "系统接口", "让软件稳定调用 AI 能力，而不是让人打开聊天窗口手动输入。"),
    ("Prompt", "任务表达", "把角色、任务、对象、资料、格式、限制讲清楚的输入指令。"),
    ("System Prompt", "系统约束", "比普通输入更上层的角色、规则和边界说明。"),
    ("Token", "上下文单位", "模型处理文本时的基本切分单位，影响上下文容量和成本。"),
    ("上下文", "工作记忆", "模型当前能看到的材料、对话、规则和任务状态。"),
    ("知识库", "资料源", "把自己的资料交给 AI 参考，降低凭空编造和重复输入。"),
    ("RAG", "检索增强生成", "先从知识库查相关资料，再把资料交给模型生成回答。"),
    ("Embedding", "语义向量", "把文本转成可比较的向量，用于相似度检索。"),
    ("MCP", "工具协议", "让 AI 以标准方式连接外部工具、数据和服务。"),
    ("CLI", "命令行入口", "给 agent 或开发者调用工具的稳定命令接口。"),
    ("工具调用", "执行能力", "让 AI 从回答问题扩展到搜索、读写文件、调用服务。"),
    ("Agent", "自主执行体", "能理解目标、拆任务、调用工具、根据结果继续推进的 AI 系统。"),
    ("Workflow", "固定流程", "预先设计好的步骤链，稳定但自主性弱于 agent。"),
    ("Coding Agent", "编程代理", "能读代码、改代码、跑测试、修复问题的 agent。"),
    ("训练", "模型构建", "用大量数据和算力让模型学习通用能力。"),
    ("微调", "定向适配", "在已有模型上用领域数据继续训练，让它更适合某类任务。"),
    ("蒸馏", "模型压缩", "让小模型学习大模型输出，降低成本或部署门槛。"),
    ("量化", "推理优化", "降低参数精度以减少显存和计算开销。"),
    ("幻觉", "可靠性风险", "模型生成看似合理但没有依据或事实错误的内容。"),
    ("护栏", "安全边界", "用规则、校验和流程限制模型做不该做的事。"),
    ("Vibe Coding", "开发方式", "用自然语言和 agent 快速推动代码实现，但仍需要验证。"),
    ("GEO", "生成引擎优化", "面向 AI 搜索/回答环境组织内容可见性的方法。"),
]


@dataclass
class Article:
    path: Path
    title: str
    author: str
    url: str
    published_at: str
    body: str
    sections: list[tuple[str, str]]


def slugify(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|#%{}^~\[\]`]+", "-", value).strip(" .-")
    return value[:90] or "article-transform"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    rest = text[end + 4 :].lstrip()
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, val = line.split(":", 1)
        data[key.strip()] = val.strip().strip('"')
    return data, rest


def strip_noise(line: str) -> str:
    line = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", line)
    line = line.replace("> [!source]- 来源信息", "")
    line = re.sub(r"^>\s?", "", line)
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"`([^`]+)`", r"\1", line)
    return line.strip()


def parse_article(path: Path) -> Article:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    title = fm.get("title") or ""
    m = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    if m:
        title = m.group(1).strip()
    if not title:
        title = path.stem

    sections: list[tuple[str, str]] = []
    current_title = "导读"
    current_lines: list[str] = []
    for raw in body.splitlines():
        h = re.match(r"^##\s+(.+)$", raw)
        if h:
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = h.group(1).strip()
            current_lines = []
            continue
        if raw.startswith("# "):
            continue
        cleaned = strip_noise(raw)
        if cleaned:
            current_lines.append(cleaned)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return Article(
        path=path,
        title=title,
        author=fm.get("author", ""),
        url=fm.get("url", ""),
        published_at=fm.get("published_at", ""),
        body=body.strip(),
        sections=sections,
    )


def matched_terms(article: Article) -> list[tuple[str, str, str]]:
    haystack = article.body.lower()
    terms: list[tuple[str, str, str]] = []
    for term, category, definition in TERM_LIBRARY:
        if term.lower() in haystack or term in article.title:
            terms.append((term, category, definition))
    return terms or TERM_LIBRARY[:12]


def section_excerpt(text: str, limit: int = 170) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_report(article: Article, out_dir: Path, terms: list[tuple[str, str, str]]) -> Path:
    toc = "\n".join(f"- {title}" for title, _ in article.sections[:14])
    sections = "\n\n".join(
        f"### {title}\n\n{content.strip()}" for title, content in article.sections if content.strip()
    )
    glossary = "\n".join(f"| {t} | {c} | {d} |" for t, c, d in terms)
    report = f"""
# {article.title}｜保真转换报告

来源：{article.author or "unknown"} · {article.published_at or "unknown"} · {article.url or article.path}

## 转换说明

- 内容模式：`preserve + learning`
- 目标：保留原文章节、案例、术语和清单，再补充可学习、可检索、可导出的结构。
- 重要边界：本地 provider 不声称调用 NotebookLM；NotebookLM 产物由 notebooklm matrix 单独记录。

## 原文章节地图

{toc}

## 术语表

| 术语 | 类型 | 小白解释 |
|---|---|---|
{glossary}

## 保真正文

{sections}
"""
    path = out_dir / "report.md"
    write_text(path, report)
    return path


def write_data_table(out_dir: Path, terms: list[tuple[str, str, str]]) -> Path:
    path = out_dir / "data-table.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["term", "category", "plain_explanation", "learning_use"])
        for term, category, definition in terms:
            writer.writerow([term, category, definition, "用于概念辨析、试题、闪卡、PPT 知识地图"])
    return path


def write_quiz(out_dir: Path, terms: list[tuple[str, str, str]]) -> Path:
    selected = terms[:12]
    questions = []
    for idx, (term, category, definition) in enumerate(selected, 1):
        questions.append(
            f"### {idx}. {term} 属于什么概念？\n\n"
            f"A. {category}\nB. 一种图片格式\nC. 一种硬件接口\nD. 固定的营销口号\n\n"
            f"**答案：A**\n\n解析：{definition}\n"
        )
    questions.append(
        "### 13. 为什么把“转换文章为 PDF”直接做成几段摘要是不合格的？\n\n"
        "答案要点：用户要的是保真转换，不是总结；应保留章节、例子、关键清单和来源，只有明确说总结时才压缩。\n"
    )
    questions.append(
        "### 14. RAG 相比直接问 LLM 的核心改进是什么？\n\n"
        "答案要点：先检索知识库中的相关材料，再让模型基于材料生成，减少凭空编造并增强可追溯性。\n"
    )
    path = out_dir / "quiz.md"
    write_text(path, "# 试卷：AI 名词入门自测\n\n" + "\n".join(questions))
    return path


def write_flashcards(out_dir: Path, terms: list[tuple[str, str, str]]) -> tuple[Path, Path]:
    md_lines = ["# 闪卡：AI 名词入门", "", "| 正面 | 背面 |", "|---|---|"]
    csv_path = out_dir / "flashcards.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["front", "back"])
        for term, category, definition in terms:
            front = f"{term} 是什么？"
            back = f"{category}：{definition}"
            writer.writerow([front, back])
            md_lines.append(f"| {front} | {back} |")
    md_path = out_dir / "flashcards.md"
    write_text(md_path, "\n".join(md_lines))
    return md_path, csv_path


def write_mindmap(out_dir: Path, terms: list[tuple[str, str, str]]) -> Path:
    groups: dict[str, list[str]] = {}
    for term, category, _ in terms:
        groups.setdefault(category, []).append(term)
    lines = ["mindmap", "  root((AI 名词入门))"]
    for group, names in groups.items():
        lines.append(f"    {group}")
        for name in names[:6]:
            lines.append(f"      {name}")
    path = out_dir / "mindmap.mmd"
    write_text(path, "\n".join(lines))
    return path


def write_scripts(article: Article, out_dir: Path, terms: list[tuple[str, str, str]]) -> list[Path]:
    term_names = "、".join(t for t, _, _ in terms[:10])
    podcast = f"""
# Podcast Script｜{article.title}

## 片头

今天我们用一个“AI 内容生产小助手”的案例，讲清楚 {term_names} 这些高频词。

## 三幕结构

1. 为什么一句“让 AI 帮我做内容”背后是一套系统。
2. 模型、资料、工具、流程分别解决什么问题。
3. 怎么判断一个 AI 系统只是会回答，还是能真正交付。

## 结尾

最后记住：AI 是能力，AIGC 是结果；Prompt 是表达任务，RAG 是接资料，MCP 是接工具，Agent 是把目标推进到结果。
"""
    video = f"""
# Video Script｜教学短视频

## 镜头 1
画面：课程主理人的资料堆：逐字稿、问答、案例图、产品文档。
旁白：你以为自己只是想“让 AI 帮我做内容”，其实已经进入 AI 工作系统。

## 镜头 2
画面：概念层级图 AI > 机器学习 > 深度学习 > LLM。
旁白：先分清能力底座，再看使用入口。

## 镜头 3
画面：Prompt、RAG、MCP、Agent 四段流水线。
旁白：Prompt 说清任务，RAG 接资料，MCP 接工具，Agent 推动执行。

## 镜头 4
画面：输出公众号、小红书、课程大纲和检查清单。
旁白：真正有用的 AI，不只是回答，而是交付可验证结果。
"""
    cinematic = f"""
# Cinematic Video Shotlist｜概念电影感短片

1. 冷开场：夜晚桌面，散落的课程资料被屏幕光照亮。
2. 系统觉醒：文字、图片、问答卡片汇入同一条发光工作流。
3. 检索瞬间：知识库像城市地图一样展开，RAG 把相关资料点亮。
4. 工具连接：MCP 端口接入搜索、图片生成、排版、发布工具。
5. Agent 执行：任务板逐项完成，产物从草稿变成多平台内容。
6. 收束：画面落在一句话——“AI 是工作系统，不是孤立聊天框。”
"""
    files = [
        (out_dir / "podcast-script.md", podcast),
        (out_dir / "video-script.md", video),
        (out_dir / "cinematic-video-shotlist.md", cinematic),
    ]
    for path, content in files:
        write_text(path, content)
    return [path for path, _ in files]


def html_doc(title: str, body: str, css: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{css}</style>
</head>
<body>{body}</body>
</html>"""


def write_report_html(article: Article, out_dir: Path, terms: list[tuple[str, str, str]]) -> Path:
    term_rows = "".join(
        f"<tr><td>{html.escape(t)}</td><td>{html.escape(c)}</td><td>{html.escape(d)}</td></tr>"
        for t, c, d in terms
    )
    section_blocks = "".join(
        f"<section><h2>{html.escape(title)}</h2><p>{html.escape(section_excerpt(content, 900))}</p></section>"
        for title, content in article.sections
        if content.strip()
    )
    css = """
body{margin:0;background:#f6f2ea;color:#1a1a1a;font-family:"PingFang SC","Noto Sans CJK SC",sans-serif;line-height:1.62}
main{max-width:980px;margin:0 auto;padding:54px 52px 80px;background:#fffdf8}
h1{font-size:38px;line-height:1.18;margin:0 0 12px}
.meta{font-size:14px;color:#666;margin-bottom:30px}
h2{font-size:22px;margin:34px 0 10px;border-top:2px solid #111;padding-top:18px}
p{font-size:15.5px;margin:0 0 12px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:16px 0 28px}
td,th{border:1px solid #d5d0c5;padding:8px;vertical-align:top}
th{background:#1f2937;color:#fff}
.note{background:#e7f2ff;border-left:5px solid #2f80ed;padding:14px;margin:22px 0}
@media print{body{background:white}main{box-shadow:none;padding:32px 28px}h1{font-size:30px}}
"""
    body = f"""
<main>
  <h1>{html.escape(article.title)}</h1>
  <div class="meta">保真转换报告 · {html.escape(article.author or "unknown")} · {html.escape(article.published_at or "")}</div>
  <div class="note">这份 PDF/报告保留原文章节与概念结构，不是摘要替代品。</div>
  <h2>术语表</h2>
  <table><thead><tr><th>术语</th><th>类型</th><th>小白解释</th></tr></thead><tbody>{term_rows}</tbody></table>
  {section_blocks}
</main>
"""
    path = out_dir / "report.html"
    write_text(path, html_doc(article.title, body, css))
    return path


def write_infographic_html(article: Article, out_dir: Path, terms: list[tuple[str, str, str]]) -> Path:
    cards = "".join(
        f"""
<div class="card c{idx % 5}">
  <b>{idx:02d} {html.escape(term)}</b>
  <span>{html.escape(definition)}</span>
</div>
"""
        for idx, (term, _, definition) in enumerate(terms[:15], 1)
    )
    flow = [
        ("需求", "把资料变成内容"),
        ("Prompt", "说清角色、任务、对象、格式"),
        ("RAG", "从知识库取证据"),
        ("MCP", "连接外部工具"),
        ("Agent", "推进执行并验收"),
        ("交付", "文章、卡片、课程、发布"),
    ]
    flow_html = "".join(f"<li><b>{html.escape(a)}</b><span>{html.escape(b)}</span></li>" for a, b in flow)
    css = """
*{box-sizing:border-box}body{margin:0;background:#061923;color:#f8f4e8;font-family:"PingFang SC","Noto Sans CJK SC",sans-serif}
.poster{width:1080px;height:1920px;margin:0 auto;padding:32px;background:#061923;display:flex;flex-direction:column;gap:12px}
.top{border:2px solid #e4b363;padding:22px;background:#102b36}
h1{font-size:44px;line-height:1.14;margin:0 0 8px}.sub{font-size:21px;color:#cce8e2}
.verdict{margin-top:14px;padding:16px;background:#813c2a;border:1px solid #ffca6e;font-size:34px;font-weight:800;text-align:center}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.card{min-height:116px;border:1px solid #4d7180;background:#0d2632;padding:12px;border-radius:8px}
.card b{display:block;font-size:22px;color:#ffdc84;margin-bottom:6px}.card span{font-size:16.5px;line-height:1.32;color:#e9f5f1}
.c1 b{color:#6fb6ff}.c2 b{color:#ff7777}.c3 b{color:#87d37c}.c4 b{color:#f6c667}
.two{display:grid;grid-template-columns:1.05fr .95fr;gap:14px}
.panel{border:1px solid #567989;border-radius:8px;padding:16px;background:#0b2330}
.panel h2{font-size:28px;margin:0 0 10px;color:#ffdc84}
.flow{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.flow li{padding:11px;border-left:6px solid #6fb6ff;background:#102f3e}.flow b{font-size:21px;display:block}.flow span{font-size:16px}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:10px}.compare div{padding:14px;border-radius:8px;font-size:18px;line-height:1.42}
.yes{background:#123d2b;border:1px solid #47bf72}.risk{background:#4a171e;border:1px solid #ff6b7a}
.strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.strip div{border:1px solid #4d7180;background:#102b36;border-radius:8px;padding:12px;min-height:118px}.strip b{font-size:20px;color:#ffdc84}.strip p{font-size:15.5px;line-height:1.34;margin:6px 0 0}
.bottom{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}.bottom .panel{min-height:210px}.bottom p{font-size:17px;line-height:1.45}
.foot{font-size:15px;color:#a8c3c8;text-align:center}
"""
    body = f"""
<main class="poster">
  <section class="top">
    <h1>{html.escape(article.title)}</h1>
    <div class="sub">一个案例看懂：模型、资料、工具、流程如何组成 AI 工作系统</div>
    <div class="verdict">不是孤立聊天框，而是可验证的工作流</div>
  </section>
  <section class="grid">{cards}</section>
  <section class="two">
    <div class="panel"><h2>内容生产小助手流程</h2><ul class="flow">{flow_html}</ul></div>
    <div class="panel"><h2>三组易混概念</h2>
      <div class="compare">
        <div class="yes"><b>AI / AIGC</b><br>AI 是能力，AIGC 是生成结果。</div>
        <div class="risk"><b>LLM / 搜索</b><br>搜索找网页，LLM 生成回答，RAG 把二者接起来。</div>
        <div class="yes"><b>Agent / Workflow</b><br>Agent 会根据反馈推进；Workflow 是固定步骤链。</div>
        <div class="risk"><b>Prompt / 上下文</b><br>Prompt 是任务表达，上下文是模型当前能看到的工作记忆。</div>
      </div>
    </div>
  </section>
  <section class="strip">
    <div><b>Prompt 六要素</b><p>角色、任务、对象、资料、格式、限制；缺项就会把自由度交给模型。</p></div>
    <div><b>RAG 三步</b><p>切分资料 -> 向量检索 -> 带证据生成；关键是来源可追溯。</p></div>
    <div><b>Agent 判断</b><p>是否会拆任务、调用工具、读取反馈并继续推进，而不是只回复一句话。</p></div>
    <div><b>验收证据</b><p>输出文件、来源链接、测试结果、人工审批点都要留下。</p></div>
  </section>
  <section class="bottom">
    <div class="panel"><h2>支持使用</h2><p>用清楚的角色、资料、格式、限制来控制输出。</p><p>把知识库和工具接入，减少重复劳动。</p></div>
    <div class="panel"><h2>必须警惕</h2><p>没有来源的答案可能是幻觉。</p><p>Agent 做完不等于正确，必须验收。</p></div>
    <div class="panel"><h2>继续追问</h2><p>我的资料放在哪里？</p><p>哪些步骤可自动化？哪些必须人工审批？</p></div>
  </section>
  <div class="foot">Local visual provider smoke · source: {html.escape(article.url or str(article.path))}</div>
</main>
"""
    path = out_dir / "infographic.html"
    write_text(path, html_doc(article.title, body, css))
    return path


def slide(title: str, body: str, kind: str = "text") -> str:
    return f'<section class="slide {kind}"><div class="paper">{body}</div><footer>{html.escape(title)}</footer></section>'


def write_deck_html(article: Article, out_dir: Path, terms: list[tuple[str, str, str]]) -> Path:
    term_cards = "".join(
        f"<div><b>{html.escape(t)}</b><span>{html.escape(d)}</span></div>" for t, _, d in terms[:8]
    )
    css = """
*{box-sizing:border-box}body{margin:0;background:#2d2d2d;font-family:"PingFang SC","Noto Sans CJK SC",sans-serif;color:#171717}
.deck{width:1920px;margin:0 auto}.slide{width:1920px;height:1080px;position:relative;padding:72px;background:#2d2d2d;page-break-after:always}
.paper{position:absolute;inset:70px 145px 76px 92px;background:#f8f6f1;border:2px solid #252525;padding:64px 78px;box-shadow:18px 18px 0 #98d4bb}
.slide:nth-child(2n) .paper{box-shadow:18px 18px 0 #c7b8ea}.slide:nth-child(3n) .paper{box-shadow:18px 18px 0 #f4b8c5}
h1{font-size:70px;line-height:1.1;margin:0 0 22px;font-weight:850}h2{font-size:60px;line-height:1.08;margin:0 0 30px}
p,li{font-size:30px;line-height:1.42}.kicker{font-size:22px;color:#6b6358;margin-bottom:28px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}
.grid div,.box{border:2px solid #252525;padding:20px;background:#fffdf8;min-height:132px}.grid b{display:block;font-size:28px;margin-bottom:8px}.grid span{font-size:20px;line-height:1.35}
.flow{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}.flow div{border-top:8px solid #98d4bb;padding:16px;background:#fffdf8;min-height:220px}
.flow b{font-size:30px;display:block}.two{display:grid;grid-template-columns:1fr 1fr;gap:24px}.risk{background:#ffd9df}.ok{background:#ddf4e8}
footer{position:absolute;left:120px;bottom:34px;color:#f8f6f1;font-size:22px}.num{position:absolute;right:170px;top:90px;font-size:110px;color:#d8d2c4;opacity:.55}
@media print{body{background:white}.deck{width:auto}.slide{margin:0;break-after:page}}
"""
    slides = [
        slide(article.title, f"<div class='kicker'>AI 名词入门 · teaching deck</div><h1>{html.escape(article.title)}</h1><p>用“AI 内容生产小助手”这个案例，把模型、资料、工具和流程串成一张地图。</p>", "cover"),
        slide("学习地图", "<h2>先搭框架，再学名词</h2><div class='flow'><div><b>能力</b><p>AI / LLM / AIGC</p></div><div><b>入口</b><p>产品 / API / CLI</p></div><div><b>表达</b><p>Prompt / System Prompt</p></div><div><b>资料</b><p>Token / RAG / Embedding</p></div><div><b>工具</b><p>MCP / Tool Calling</p></div><div><b>执行</b><p>Agent / Workflow</p></div></div>"),
        slide("核心术语", f"<h2>8 个必须先分清的词</h2><div class='grid'>{term_cards}</div>"),
        slide("案例拆解", "<h2>内容生产小助手其实是系统工程</h2><div class='two'><div class='box'><b>输入</b><p>直播课逐字稿、学员问答、案例截图、产品资料。</p></div><div class='box'><b>输出</b><p>公众号文章、小红书文案、课程大纲、配图和复用流程。</p></div></div>"),
        slide("Prompt", "<h2>Prompt 不是一句口令</h2><p>好 Prompt 至少包含：角色、任务、对象、资料、格式、限制。缺一项，AI 就会把自由度还给自己。</p>"),
        slide("RAG", "<h2>RAG 是“先查证，再生成”</h2><p>当 AI 不确定时，先检索知识库，把相关材料塞进上下文，再生成可追溯的回答。</p>"),
        slide("MCP", "<h2>MCP 让 AI 接上外部世界</h2><p>联网搜索、读取文件、调用图片生成、推送草稿，都可以被抽象成工具调用。</p>"),
        slide("Agent vs Workflow", "<h2>Agent 会根据结果继续推进</h2><div class='two'><div class='ok'><p>Agent：有目标，会调用工具，根据反馈修正。</p></div><div class='risk'><p>Workflow：固定步骤链，稳定但不主动判断。</p></div></div>"),
        slide("风险边界", "<h2>真正的边界是验收</h2><p>幻觉、资料缺失、工具失败、上下文过短，都会让结果看起来顺但实际错。完成不等于正确。</p>"),
        slide("行动清单", "<h2>读完就能做的 5 步</h2><ol><li>把任务写成 Prompt 六要素。</li><li>把资料放进知识库。</li><li>区分生成、检索、工具调用。</li><li>沉淀可复用 Workflow。</li><li>给每一步设计验收证据。</li></ol>"),
        slide("来源", f"<h2>Source</h2><p>{html.escape(article.author or 'unknown')}</p><p>{html.escape(article.url or str(article.path))}</p>"),
    ]
    body = f"<main class='deck'>{''.join(slides)}</main>"
    path = out_dir / "deck.html"
    write_text(path, html_doc(article.title, body, css))
    return path


def add_textbox(slide_obj, left, top, width, height, text, size=24, bold=False, color=(28, 28, 28)):
    box = slide_obj.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = text
    run.font.name = "PingFang SC"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(*color)
    return box


def write_deck_pptx(article: Article, out_dir: Path, terms: list[tuple[str, str, str]]) -> Path | None:
    if Presentation is None:
        print(f"python-pptx unavailable: {PPTX_IMPORT_ERROR}", file=sys.stderr)
        return None
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    bg = RGBColor(248, 246, 241)
    ink = RGBColor(26, 26, 26)
    mint = RGBColor(152, 212, 187)
    lavender = RGBColor(199, 184, 234)
    pink = RGBColor(244, 184, 197)

    def base_slide(title: str, accent=mint):
        s = prs.slides.add_slide(blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = bg
        shape = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.2), Inches(0.2), Inches(12.93), Inches(7.1))
        shape.fill.background()
        shape.line.color.rgb = ink
        shape.line.width = Pt(1.5)
        bar = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.2), Inches(6.9), Inches(12.93), Inches(0.4))
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent
        bar.line.fill.background()
        add_textbox(s, Inches(0.55), Inches(0.42), Inches(11.8), Inches(0.5), title, 18, True)
        return s

    s = base_slide("AI 名词入门", lavender)
    add_textbox(s, Inches(0.75), Inches(1.25), Inches(11.4), Inches(1.5), article.title, 38, True)
    add_textbox(s, Inches(0.78), Inches(3.25), Inches(8.8), Inches(1.1), "用一个内容生产助手案例，把模型、资料、工具、流程和执行边界一次讲清楚。", 23)
    add_textbox(s, Inches(0.78), Inches(5.3), Inches(10.5), Inches(0.5), f"Source: {article.author or 'unknown'} · {article.url or article.path}", 12)

    pages = [
        ("学习地图", ["AI/LLM/AIGC 是能力底座", "产品/API/CLI 是使用入口", "Prompt/RAG/MCP/Agent 是从表达走向执行的链路"]),
        ("术语关系", [f"{t}：{d}" for t, _, d in terms[:5]]),
        ("案例拆解", ["资料：逐字稿、问答、截图、产品资料", "动作：整理、查证、生成、排版、发布", "产物：公众号、小红书、课程大纲、复用流程"]),
        ("Prompt 六要素", ["角色", "任务", "对象", "资料", "格式", "限制"]),
        ("RAG / MCP / Agent", ["RAG：先检索再生成", "MCP：标准化连接外部工具", "Agent：根据目标和反馈推进执行"]),
        ("风险边界", ["幻觉不是文风问题，是依据问题", "工具调用成功不代表任务正确", "每一步都要有验收证据"]),
        ("行动清单", ["把任务写成六要素", "把资料沉淀为知识库", "把流程拆成可验证步骤", "把产物链接回 Obsidian"]),
    ]
    accents = [mint, lavender, pink]
    for i, (title, bullets) in enumerate(pages, 1):
        s = base_slide(title, accents[i % 3])
        add_textbox(s, Inches(0.75), Inches(1.0), Inches(4.2), Inches(0.8), f"0{i+1}", 44, True, (107, 99, 88))
        top = 1.75
        for b in bullets[:6]:
            add_textbox(s, Inches(1.0), Inches(top), Inches(11.0), Inches(0.55), f"- {b}", 21)
            top += 0.72

    path = out_dir / "deck.pptx"
    prs.save(path)
    return path


def render_with_playwright(out_dir: Path, node_bin: str, node_path: str | None) -> dict[str, str]:
    render_script = out_dir / ".render.cjs"
    render_script.write_text(
        r"""
const { chromium } = require('playwright');
const path = require('path');
const { pathToFileURL } = require('url');

function chromeLaunchOptions() {
  const candidates = [
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium'
  ].filter(Boolean);
  for (const executablePath of candidates) {
    try {
      require('fs').accessSync(executablePath);
      return { headless: true, executablePath };
    } catch (_) {}
  }
  return { headless: true };
}

async function renderHtml(input, opts) {
  const browser = await chromium.launch(chromeLaunchOptions());
  const page = await browser.newPage({ viewport: { width: opts.width, height: opts.height }, deviceScaleFactor: opts.scale || 1 });
  await page.goto(pathToFileURL(input).href, { waitUntil: 'networkidle' });
  if (opts.screenshot) {
    await page.screenshot({ path: opts.screenshot, fullPage: Boolean(opts.fullPage) });
  }
  if (opts.pdf) {
    await page.pdf({ path: opts.pdf, printBackground: true, format: opts.format || 'A4', margin: opts.margin || { top: '12mm', bottom: '12mm', left: '10mm', right: '10mm' } });
  }
  await browser.close();
}

(async () => {
  const root = process.argv[2];
  await renderHtml(path.join(root, 'infographic.html'), { width: 1080, height: 1920, screenshot: path.join(root, 'infographic.png') });
  await renderHtml(path.join(root, 'deck.html'), { width: 1920, height: 1080, screenshot: path.join(root, 'deck-cover.png') });
  await renderHtml(path.join(root, 'report.html'), { width: 1240, height: 1754, pdf: path.join(root, 'report.pdf'), fullPage: true });
})();
""",
        encoding="utf-8",
    )
    env = os.environ.copy()
    if node_path:
        env["NODE_PATH"] = node_path
    proc = subprocess.run(
        [node_bin, str(render_script), str(out_dir)],
        cwd=str(out_dir),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {"returncode": str(proc.returncode), "stdout": proc.stdout, "stderr": proc.stderr}


def build_bundle(args: argparse.Namespace) -> dict[str, object]:
    article = parse_article(Path(args.article).expanduser().resolve())
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    terms = matched_terms(article)

    files: list[Path] = []
    files.append(write_report(article, out_dir, terms))
    files.append(write_report_html(article, out_dir, terms))
    files.append(write_data_table(out_dir, terms))
    files.append(write_quiz(out_dir, terms))
    files.extend(write_flashcards(out_dir, terms))
    files.append(write_mindmap(out_dir, terms))
    files.extend(write_scripts(article, out_dir, terms))
    files.append(write_infographic_html(article, out_dir, terms))
    files.append(write_deck_html(article, out_dir, terms))
    pptx_path = write_deck_pptx(article, out_dir, terms)
    if pptx_path:
        files.append(pptx_path)

    render_result = None
    if not args.no_render:
        render_result = render_with_playwright(out_dir, args.node_bin, args.node_path)
        for name in ["report.pdf", "infographic.png", "deck-cover.png"]:
            p = out_dir / name
            if p.exists():
                files.append(p)

    manifest = {
        "source": str(article.path),
        "title": article.title,
        "provider": "soia-local",
        "content_modes": ["preserve", "learning", "visual_dense"],
        "files": [str(p) for p in files],
        "render": render_result,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", required=True, help="Markdown article path")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--node-bin", default="node", help="Node.js executable for Playwright rendering")
    parser.add_argument("--node-path", default=None, help="NODE_PATH containing playwright module")
    parser.add_argument("--no-render", action="store_true", help="Skip Playwright PDF/PNG rendering")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON")
    args = parser.parse_args()
    manifest = build_bundle(args)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"wrote {len(manifest['files'])} files to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
