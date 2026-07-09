#!/usr/bin/env python3
"""
Rebuild the two-level MOC (Map of Content) for an Obsidian article vault.

Clears `_MOC/`, scans every article's `topics` frontmatter, builds a
topic→article map, and regenerates level-1 (category) + level-2 (topic) MOC files.

This is the mechanical layer under `soia-pkm-organize`. It is vault-agnostic:
pass `--vault` (or set OBSIDIAN_VAULT). The category→topic table has a sensible
built-in default and can be overridden per-vault with a JSON file — see --help.

Usage:
    python3 rebuild_moc.py --vault /path/to/vault
    python3 rebuild_moc.py --vault . --date 2026-07-02
    python3 rebuild_moc.py --vault <vault-path>

Per-vault category override (optional):
    Put `<vault>/<articles-subdir>/_MOC/.categories.json` shaped like
    {"AI编程": ["Agent开发", ...], "产品与商业": [...]} to replace the default table.
"""

import argparse
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path
from collections import defaultdict

from soia_env import load_private_env

# ── Default category → topic table ───────────────────────────────────────────
# Vault-agnostic default. Override per-vault via _MOC/.categories.json.

DEFAULT_CATEGORY_TOPICS = {
    "AI编程": [
        "AI与LLM", "Agent开发", "Claude Code", "AI编程", "Codex", "Skills",
        "Prompt工程", "多Agent", "Harness工程", "MCP", "AI工程师",
        "Vibe Coding", "Anthropic", "DeepSeek", "OpenAI", "Qwen", "Ollama",
    ],
    "AI应用": [
        "视频生成", "本地大模型", "图像生成", "数字人", "视频翻译",
        "音视频处理", "AI工具", "GEO", "预言与趋势",
    ],
    "技术与开源": [
        "开源项目", "GitHub", "自动化", "前端", "架构设计", "爬虫与抓取",
        "API中转", "源码分析", "工作流", "组件库", "半导体", "网络安全",
        "OCR", "数据分析", "云服务器", "Cloudflare", "GitHub Pages",
        "域名与DNS", "SEO", "Schema标记", "云计算", "反代",
        "Google", "Reddit",
    ],
    "产品与商业": [
        "内容创作", "一人公司", "副业", "出海", "行业观察", "创业与商业",
        "变现", "战略与战术", "自媒体", "支付与开卡", "中国经济", "职业发展",
        "投资理财", "YouTube", "订阅与账号", "中文创作者", "人物访谈",
        "公众号", "Twitter运营", "赚钱思维", "股票投资", "黄金与避险",
        "小红书", "产品与设计", "亚马逊", "闲鱼", "公司治理", "跨境金融",
        "跨境公司注册", "Stripe", "远程办公", "加密货币", "UI设计", "数字身份",
    ],
    "效率与工具": [
        "效率工具", "知识管理", "Obsidian", "代理与VPN", "第二大脑",
        "macOS工具", "精力管理", "PPT", "PARA", "飞书", "微信读书",
        "Mac", "PDF", "工具", "Telegram", "科学上网", "路由器",
    ],
    "学习": [
        "教育", "英语学习", "读书", "心理学", "少儿编程", "学习资源", "职场",
    ],
    "社会": [
        "制度问题", "历史", "国际关系", "育儿", "澳洲", "食品安全",
        "移民与海外", "健康", "家庭关系", "香港", "美国", "英国",
        "新加坡", "政治", "社会观察",
    ],
}

# ── Runtime config (populated in main) ───────────────────────────────────────

ARTICLES_DIR: Path
MOC_DIR: Path
TODAY: str
CATEGORY_TOPICS: dict
TOPIC_TO_CATEGORY: dict = {}


def load_category_topics(articles_dir: Path) -> dict:
    """Load per-vault override from _MOC/.categories.json, else built-in default."""
    override = articles_dir / "_MOC" / ".categories.json"
    if override.is_file():
        try:
            data = json.loads(override.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                print(f"Using category override: {override}")
                return data
        except Exception as e:
            print(f"  WARN: bad .categories.json ({e}); using default table")
    return DEFAULT_CATEGORY_TOPICS


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter as raw dict (minimal parser, no pyyaml needed)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_text = text[3:end].strip()
    result = {}
    lines = fm_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\w[\w_-]*):\s*(.*)', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            if val == "" or val is None:
                items = []
                i += 1
                while i < len(lines) and lines[i].startswith("  ") or (i < len(lines) and lines[i].startswith("- ")):
                    sub = lines[i].strip()
                    if sub.startswith("- "):
                        items.append(sub[2:].strip().strip('"').strip("'"))
                    i += 1
                result[key] = items
                continue
            else:
                result[key] = val
        i += 1
    return result


def parse_topics(text: str) -> list:
    """
    Parse topics from article frontmatter. Supports:
    - Multi-line:  topics:\n  - "[[Topic]]"\n  - "[[Topic2]]"
    - Single-line: topics: ["[[Topic]]", "[[Topic2]]"]
    Returns list of plain topic names (no [[ ]]).
    """
    topics = []
    m = re.search(r'^topics:[ \t]*', text, re.MULTILINE)
    if not m:
        return topics

    rest = text[m.end():]
    first_line = rest.split('\n')[0].strip()

    if first_line.startswith("["):
        for item in re.findall(r'\[\[([^\]]+)\]\]', first_line):
            topics.append(item.strip())
    else:
        candidate_lines = []
        if first_line.startswith("- "):
            candidate_lines.append(first_line)
        for line in rest.split('\n')[1:]:
            stripped = line.strip()
            if stripped.startswith("- "):
                candidate_lines.append(stripped)
            elif stripped == "":
                continue
            else:
                break

        for stripped in candidate_lines:
            inner = stripped[2:].strip().strip('"').strip("'")
            found = re.findall(r'\[\[([^\]]+)\]\]', inner)
            if found:
                topics.extend(t.strip() for t in found)
            elif inner:
                topics.append(inner)

    return topics


def extract_title(text: str) -> str:
    """Extract first H1 heading from article body (after frontmatter)."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            if len(title) > 40:
                title = title[:40] + "…"
            return title
    return "(无标题)"


# ── Step 1: Clear _MOC/ ───────────────────────────────────────────────────────

def clear_moc_dir():
    """Clear _MOC/ but preserve the optional .categories.json override."""
    override = MOC_DIR / ".categories.json"
    saved = override.read_text(encoding="utf-8") if override.is_file() else None
    if MOC_DIR.exists():
        shutil.rmtree(MOC_DIR)
        print(f"Cleared: {MOC_DIR}")
    MOC_DIR.mkdir(parents=True, exist_ok=True)
    if saved is not None:
        override.write_text(saved, encoding="utf-8")
    print(f"Created: {MOC_DIR}")


# ── Step 2: Scan articles ─────────────────────────────────────────────────────

def scan_articles() -> dict:
    """Returns: topic → list of article dicts. Scans every 4-digit year dir."""
    topic_map = defaultdict(list)
    year_dirs = sorted(
        d for d in ARTICLES_DIR.iterdir()
        if d.is_dir() and re.fullmatch(r'\d{4}', d.name)
    )

    skipped_no_topics = 0
    skipped_unknown_topics = 0
    total_files = 0
    total_pairs = 0

    for year_dir in year_dirs:
        for md_file in sorted(year_dir.rglob("*.md")):
            total_files += 1
            try:
                text = md_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  WARN: cannot read {md_file.name}: {e}")
                continue

            topics = parse_topics(text)
            if not topics:
                skipped_no_topics += 1
                continue

            fm = parse_frontmatter(text)
            captured_at = str(fm.get("captured_at", "")).strip()
            published_at = str(fm.get("published_at", "")).strip()
            title = extract_title(text)
            filename = md_file.stem

            for topic in topics:
                if topic not in TOPIC_TO_CATEGORY:
                    skipped_unknown_topics += 1
                    continue
                topic_map[topic].append({
                    "filename": filename,
                    "title": title,
                    "captured_at": captured_at,
                    "published_at": published_at,
                })
                total_pairs += 1

    print(f"\nScan complete: {total_files} files, {total_pairs} article-topic pairs")
    print(f"  Skipped (no topics): {skipped_no_topics}")
    print(f"  Skipped topic placements (unknown topic): {skipped_unknown_topics}")
    return topic_map


# ── Step 3: Generate level-2 MOC files ───────────────────────────────────────

def generate_level2(topic_map: dict) -> dict:
    category_stats = defaultdict(dict)

    for cat, topics in CATEGORY_TOPICS.items():
        cat_dir = MOC_DIR / cat
        cat_dir.mkdir(parents=True, exist_ok=True)

        for topic in topics:
            articles = topic_map.get(topic, [])
            if not articles:
                continue

            sorted_articles = sorted(
                articles,
                key=lambda a: (a.get("captured_at") or a.get("published_at") or ""),
                reverse=True,
            )

            count = len(sorted_articles)
            category_stats[cat][topic] = count

            lines = [
                "---",
                "tags: [MOC]",
                f"topic: {topic}",
                "level: 2",
                f'parent: "[[{cat}]]"',
                f"updated: {TODAY}",
                "---",
                "",
                f"# MOC · {topic}",
                "",
                f"> 上级：[[{cat}]]",
                "",
                f"## 文章列表（共 {count} 篇）",
                "",
            ]
            for art in sorted_articles:
                lines.append(f"- [[{art['filename']}]] — {art['title']}")
            lines.append("")

            (cat_dir / f"{topic}.md").write_text("\n".join(lines), encoding="utf-8")

    return category_stats


# ── Step 4: Generate level-1 MOC files ───────────────────────────────────────

def generate_level1(topic_map: dict, category_stats: dict):
    for cat, topic_counts in category_stats.items():
        if not topic_counts:
            continue

        lines = [
            "---",
            "tags: [MOC]",
            f"category: {cat}",
            "level: 1",
            f"updated: {TODAY}",
            "---",
            "",
            f"# MOC · {cat}",
            "",
        ]
        for topic in CATEGORY_TOPICS[cat]:
            count = topic_counts.get(topic)
            if count is None:
                continue
            articles = topic_map.get(topic, [])
            sorted_articles = sorted(
                articles,
                key=lambda a: (a.get("captured_at") or a.get("published_at") or ""),
                reverse=True,
            )
            lines.append(f"## {topic}（{count} 篇）→ [[{cat}/{topic}]]")
            lines.append("")
            for art in sorted_articles[:3]:
                lines.append(f"- [[{art['filename']}]] — {art['title']}")
            lines.append("")

        (MOC_DIR / f"{cat}.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"  Written level-1: {cat}.md")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global ARTICLES_DIR, MOC_DIR, TODAY, CATEGORY_TOPICS, TOPIC_TO_CATEGORY

    load_private_env()
    parser = argparse.ArgumentParser(description="Rebuild two-level MOC for an Obsidian article vault.")
    parser.add_argument("--vault", default=os.environ.get("OBSIDIAN_VAULT"),
                        help="vault root (or set OBSIDIAN_VAULT)")
    parser.add_argument("--articles-subdir", default="Articles",
                        help="articles dir relative to vault (default: Articles)")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="date stamp written into MOC frontmatter (default: today)")
    args = parser.parse_args()

    if not args.vault:
        parser.error("no vault given: pass --vault or set OBSIDIAN_VAULT")

    vault = Path(args.vault).expanduser().resolve()
    ARTICLES_DIR = vault / args.articles_subdir
    MOC_DIR = ARTICLES_DIR / "_MOC"
    TODAY = args.date

    if not ARTICLES_DIR.is_dir():
        parser.error(f"articles dir not found: {ARTICLES_DIR}")

    CATEGORY_TOPICS = load_category_topics(ARTICLES_DIR)
    TOPIC_TO_CATEGORY = {t: cat for cat, topics in CATEGORY_TOPICS.items() for t in topics}

    print("=" * 60)
    print(f"Rebuild Obsidian MOC · {vault.name}")
    print("=" * 60)

    print("\n[Step 1] Clearing _MOC/ ...")
    clear_moc_dir()

    print("\n[Step 2] Scanning articles ...")
    topic_map = scan_articles()

    print("\n[Step 3] Generating level-2 MOC files ...")
    category_stats = generate_level2(topic_map)

    print("\n[Step 4] Generating level-1 MOC files ...")
    generate_level1(topic_map, category_stats)

    print("\n" + "=" * 60)
    print("Final Report")
    print("=" * 60)
    grand_total_topics = 0
    grand_total_pairs = 0
    for cat in CATEGORY_TOPICS:
        stats = category_stats.get(cat, {})
        grand_total_topics += len(stats)
        grand_total_pairs += sum(stats.values())
        if stats:
            print(f"\n{cat}:  {len(stats)} topics, {sum(stats.values())} pairs")
            for topic, cnt in sorted(stats.items(), key=lambda x: -x[1]):
                print(f"    {topic}: {cnt} 篇")
    print(f"\n{'─'*40}")
    print(f"Grand total: {grand_total_topics} topics, {grand_total_pairs} article-topic pairs")
    print("Done.")


if __name__ == "__main__":
    main()
