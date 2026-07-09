#!/usr/bin/env python3
"""Generate 开源项目图书馆 project cards from a directory of upstream git clones.

soia-pkm-clip-repo skill 机械层。扫描 `--upstream` 下每个子目录（一个子目录 = 一个
上游代码仓库），为每个仓库生成/更新一张项目卡到
`<vault>/60_开源项目/00_图书馆/项目卡/<仓名>.md`。

字段来源：
- `github`    ← `git -C <dir> remote get-url origin`，转成 owner/repo 形式
- `分类`      ← 仓名→分类映射表 `REPO_CATEGORY_MAP`（写死，11 类）；未列出的仓库按
                名字/README 关键词启发式归类，兜底「工具其他」
- `语言`      ← 启发式扫根目录 Cargo.toml/go.mod/package.json/pyproject.toml|
                setup.py/pom.xml/Package.swift，取最匹配的一个，测不出填「未知」
- `访问链接`  ← 由 `github` 拼出的完整 URL `https://github.com/<owner>/<repo>`
- `最近提交`  ← `git -C <dir> log -1 --format=%cs`
- 简介        ← README 里第一句叙述性句子：跳过标题/徽章/HTML 装饰行、纯命令行
                （npm/brew/pip/cargo/curl/$/> 等开头）、导航条式短行、代码围栏内容，
                截断到 ~120 字；抓不到时留「(待补描述)」
- 正文「## 关联调研」← 扫 `10_调研笔记/` 下文件名（或其 frontmatter `关联仓库`）
                含本仓名的笔记，自动列 wikilink

幂等：重跑只更新自动字段（github/分类/语言/最近提交/本地路径/访问链接/简介/
关联调研），**不覆盖** `用途`、`状态`（若已有值）、`stars`（若已有值）这些人工可
编辑字段，也不覆盖「## 我的笔记」——已存在的卡片这段内容原样保留。

非 git 目录（如没跑 `git clone` 而是手动拷贝的项目）优雅处理：github/最近提交
留空，不报错。

单仓归档模式（给一个 GitHub URL，一键 clone + 建卡 + 起调研笔记骨架 + 双链）：
  python3 gen_repo_catalog.py --add https://github.com/<owner>/<repo>
clone 失败（私有/无权限/网络问题）时跳过 clone，只用 URL 生成最小卡并提示。

用法：
  python3 gen_repo_catalog.py --upstream /path/to/upstream --vault /path/to/vault
  python3 gen_repo_catalog.py --add https://github.com/openai/codex --upstream /path/to/upstream --vault /path/to/vault

vault / upstream 定位（不在脚本里写死任何个人路径）：
  --vault    优先级：命令行 --vault > 环境变量 OBSIDIAN_VAULT
  --upstream 优先级：命令行 --upstream > 环境变量 SOIA_REPO_UPSTREAM_DIR
两者都可以放进私有 config.yml（见 soia_env.py），不要写进 vault 或本开源 skill 仓库。
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

from soia_env import env_source_hint, load_private_env

CARD_SUBDIR = Path("60_开源项目") / "00_图书馆" / "项目卡"
NOTES_SUBDIR = Path("60_开源项目") / "10_调研笔记"
SKIP_NAMES = {".DS_Store", "__pycache__"}

LANG_MARKERS = [
    ("Cargo.toml", "Rust"),
    ("go.mod", "Go"),
    ("package.json", "JS/TS"),
    ("pyproject.toml", "Python"),
    ("setup.py", "Python"),
    ("pom.xml", "Java"),
    ("Package.swift", "Swift"),
]

README_NAMES = ["README.md", "Readme.md", "README.MD", "README.rst", "README", "README.txt"]

# ---- 分类映射（写死，11 类；未列出的仓库走启发式兜底）----

REPO_CATEGORY_MAP: dict[str, str] = {
    # 编码CLI与代理
    "claude-code": "编码CLI与代理",
    "codex": "编码CLI与代理",
    "gemini-cli": "编码CLI与代理",
    "opencli": "编码CLI与代理",
    "opencli-rs": "编码CLI与代理",
    "opencli-rs-skill": "编码CLI与代理",
    "ccmate": "编码CLI与代理",
    "gstack": "编码CLI与代理",
    "claw-code-main": "编码CLI与代理",
    "claw-code-parity": "编码CLI与代理",
    "openclaw": "编码CLI与代理",
    "fastclaw": "编码CLI与代理",
    # Agent框架与SDK
    "agentscope": "Agent框架与SDK",
    "agentscope-java": "Agent框架与SDK",
    "agentscope-runtime": "Agent框架与SDK",
    "CoPaw": "Agent框架与SDK",
    "open-agent-sdk": "Agent框架与SDK",
    "open-agent-sdk-rust": "Agent框架与SDK",
    "open-agents": "Agent框架与SDK",
    "craft-agents-oss": "Agent框架与SDK",
    "nanobot": "Agent框架与SDK",
    "intro-agentic-ai": "Agent框架与SDK",
    "pi-mono": "Agent框架与SDK",
    "OpenMAIC": "Agent框架与SDK",
    # 桌面应用与UI
    "hermes-agent": "桌面应用与UI",
    "hermes-desktop-main": "桌面应用与UI",
    "hermes-swift-mac": "桌面应用与UI",
    "hermes-webui": "桌面应用与UI",
    "frontman": "桌面应用与UI",
    "claudecodeui": "桌面应用与UI",
    # 微信与社交生态
    "claude-plugin-wechat": "微信与社交生态",
    "wechat-ai": "微信与社交生态",
    # 设计与图标资源
    "feather": "设计与图标资源",
    "lucide": "设计与图标资源",
    "tabler-icons": "设计与图标资源",
    "iconoir": "设计与图标资源",
    "icon-guides": "设计与图标资源",
    "awesome-design-md": "设计与图标资源",
    "open-design": "设计与图标资源",
    # 爬虫与数据抓取
    "Scrapling": "爬虫与数据抓取",
    # 教程与源码拆解
    "14days-build-claude-code-cli": "教程与源码拆解",
    "claude-code-from-scratch": "教程与源码拆解",
    "how-claude-code-works": "教程与源码拆解",
    "how-pi-agent-works": "教程与源码拆解",
    # 技能与插件
    "baoyu-skills": "技能与插件",
    # 架构与知识库
    "awesome-architecture": "架构与知识库",
    # MCP与工具
    "mcp-server-macos-use": "MCP与工具",
    # 代码评审
    "code-review-graph": "代码评审",
}

# 未列入 REPO_CATEGORY_MAP 的仓库（如 --add 新归档的项目）按关键词启发式归类
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "编码CLI与代理": ["cli", "coding agent", "code agent", "terminal agent"],
    "Agent框架与SDK": ["agent sdk", "agent framework", "multi-agent", "multi agent"],
    "桌面应用与UI": ["desktop app", "electron", "tauri", "desktop client"],
    "微信与社交生态": ["wechat", "微信", "telegram", "discord bot"],
    "设计与图标资源": ["icon set", "icon library", "design system", "svg icons"],
    "爬虫与数据抓取": ["scraping", "web crawler", "spider"],
    "教程与源码拆解": ["from scratch", "how it works", "walkthrough", "tutorial"],
    "技能与插件": ["skill", "plugin"],
    "架构与知识库": ["awesome list", "curated list", "architecture"],
    "MCP与工具": ["model context protocol", " mcp "],
    "代码评审": ["code review"],
}
DEFAULT_CATEGORY = "工具其他"

HTML_TAG_RE = re.compile(r"<[^>]+>")
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
BOLD_RE = re.compile(r"\*\*|__")
REF_LINK_DEF_RE = re.compile(r"^\[[^\]]+\]:\s*\S")
SECTION_HEADING_RE = re.compile(r"^## (.+)$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。!?])\s+")
COMMAND_PREFIX_RE = re.compile(
    r"^(npm|npx|yarn|pnpm|brew|pip3?|cargo|go\s+(get|install|run)|docker|curl|wget|"
    r"git\s+clone|sudo|python3?|node|bash|sh|make|cmake)\b",
    re.IGNORECASE,
)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


# ---- 路径解析 ----


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


# ---- git 元数据 ----


def run_git(args: list[str], cwd: Path | None) -> str | None:
    if cwd is None:
        return None
    try:
        proc = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def github_slug(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    m = re.match(r"^(?:https?://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else ""


def build_access_url(github: str) -> str:
    return f"https://github.com/{github}" if github else ""


# ---- 语言启发式 ----


def detect_language(repo_dir: Path | None) -> str:
    if repo_dir is None:
        return "未知"
    for fname, lang in LANG_MARKERS:
        if (repo_dir / fname).is_file():
            return lang
    return "未知"


# ---- 分类启发式 ----


def detect_category(repo_name: str, repo_dir: Path | None) -> str:
    if repo_name in REPO_CATEGORY_MAP:
        return REPO_CATEGORY_MAP[repo_name]
    haystack = repo_name.lower()
    readme = find_readme(repo_dir) if repo_dir else None
    if readme:
        try:
            haystack += " " + readme.read_text(encoding="utf-8", errors="ignore")[:2000].lower()
        except OSError:
            pass
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            return category
    return DEFAULT_CATEGORY


# ---- README 简介抽取 ----


def find_readme(repo_dir: Path) -> Path | None:
    for name in README_NAMES:
        p = repo_dir / name
        if p.is_file():
            return p
    candidates = sorted(repo_dir.glob("[Rr][Ee][Aa][Dd][Mm][Ee]*"))
    return candidates[0] if candidates else None


def is_command_like(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if t.startswith(("$", ">", "#!", "|")):
        return True
    return bool(COMMAND_PREFIX_RE.match(t))


def clean_line(line: str) -> str:
    line = MD_IMAGE_RE.sub("", line)
    line = HTML_TAG_RE.sub(" ", line)  # 用空格而非空串替换，避免相邻词粘连
    line = MD_LINK_RE.sub(r"\1", line)
    line = BOLD_RE.sub("", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip(" \t*_>")


def first_sentence(text: str) -> str:
    """从一段可能含多句的文本里取第一句像样的话。"""
    for part in SENTENCE_SPLIT_RE.split(text.strip()):
        part = part.strip()
        if len(part) >= 6 and re.search(r"[A-Za-z一-鿿]", part):
            return part
    return text.strip()


def looks_like_real_sentence(cleaned: str) -> bool:
    """过滤掉语言切换条/徽章标签/单个仓名这类"不是句子"的短词条。

    含中文按字符长度判断（中文无空格分词，词数判断不适用）；纯拉丁文本要求
    至少 3 个空格分词的词，或总长度 >=25，排除 "English"/"Packages" 这类孤词。
    """
    if re.search(r"[一-鿿]", cleaned):
        return len(cleaned) >= 6
    words = cleaned.split()
    return len(words) >= 3 or len(cleaned) >= 25


def truncate_summary(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    if sp > limit * 0.3:
        cut = cut[:sp]
    return cut.rstrip(" ,;:，；：") + "…"


def first_summary_line(repo_dir: Path | None) -> str:
    if repo_dir is None:
        return ""
    readme = find_readme(repo_dir)
    if not readme:
        return ""
    try:
        text = readme.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    # HTML 注释（常见于给 AI agent 的隐藏安装说明，可能跨多行）必须整份剥离，否则
    # 逐行扫描看不到 <!-- 和 --> 的跨行边界，注释体里的示例命令会漏出来当简介。
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    # HTML 标签（含多行属性，如换行写的 <img\n  src=...\n/>）同理必须在整份文本上
    # 一次性剥离，否则按行处理时正则看不到跨行的 `<...>` 边界，会把属性值（如
    # src="..."）当成普通文本漏出去。
    text = HTML_TAG_RE.sub(" ", text)
    in_fence = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line or line.startswith("#"):
            continue
        if line.startswith(("---", "===", "<!--", ">")):
            continue
        if re.match(r"^[-*]\s", line):
            continue  # markdown 列表项，通常是功能清单而非一句话简介
        if REF_LINK_DEF_RE.match(line):
            continue
        if is_command_like(line):
            continue
        cleaned = clean_line(line)
        if is_command_like(cleaned):
            continue
        if len(cleaned) < 6:
            continue
        if cleaned.startswith(("[", "!", "http")):
            continue  # 残留未清干净的徽章/图片/裸链接
        if not re.search(r"[A-Za-z一-鿿]", cleaned):
            continue
        if any(sep in cleaned for sep in ("|", "·")) and not re.search(r"[.!?。！？]", cleaned):
            continue  # 导航条/语言切换条（如 "English | 简体中文" / "English · 简体中文"），不是句子
        if not looks_like_real_sentence(cleaned):
            continue  # 孤立词条（如 "English"/"Packages"），不是句子
        if re.search(r"https?://", cleaned):
            remainder = re.sub(r"https?://\S+", "", cleaned).strip(" :,-")
            if len(remainder.split()) < 3:
                continue  # 整行本质上是"标签 + 链接"（如 "Official website: https://..."）
        return truncate_summary(first_sentence(cleaned))
    return ""


# ---- 卡片 frontmatter / 正文的解析与保留（幂等核心）----


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    fm_block = text[4:end]
    body = text[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    data: dict[str, str] = {}
    for line in fm_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        val = val.split(" #", 1)[0].strip()
        val = val.strip().strip('"')
        data[key.strip()] = val
    return data, body


def split_sections(body: str) -> dict[str, str]:
    """把正文按 `## 标题` 切段，返回 {标题: 段内容(不含标题行，已去首尾空行)}"""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        m = SECTION_HEADING_RE.match(line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip("\n")
            current = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip("\n")
    return sections


def esc(value: str) -> str:
    return value.replace('"', "'")


# ---- 关联调研自动回填 ----


def normalize_for_match(s: str) -> str:
    return re.sub(r"-", "", s).lower()


def scan_related_notes(repo_name: str, notes_dir: Path) -> list[str]:
    """扫 notes_dir 下的调研笔记，找文件名或 frontmatter `关联仓库` 提到本仓的。"""
    if not notes_dir.is_dir():
        return []
    norm_repo = normalize_for_match(repo_name)
    matched: list[str] = []
    for note_path in sorted(notes_dir.glob("*.md")):
        stem = note_path.stem
        if stem == "INDEX":
            continue
        is_match = norm_repo in normalize_for_match(stem)
        if not is_match:
            try:
                text = note_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            fm, _ = parse_frontmatter(text)
            linked = WIKILINK_RE.findall(fm.get("关联仓库", ""))
            is_match = any(name.strip() == repo_name for name in linked)
        if is_match:
            matched.append(stem)
    return matched


def build_access_line(access_url: str, local_path: str) -> str:
    gh_part = f"[GitHub]({access_url})" if access_url else "GitHub：（未知，非 git 或无 remote）"
    local_part = local_path if local_path else "（未 clone）"
    return f"🔗 {gh_part} · 本地：{local_part}"


# ---- 建卡 ----


def build_card(
    repo_name: str,
    repo_dir: Path | None,
    existing_text: str | None,
    notes_dir: Path,
    github_hint: str = "",
) -> str:
    is_git = bool(repo_dir) and (repo_dir / ".git").is_dir()
    github = github_slug(run_git(["remote", "get-url", "origin"], repo_dir)) if is_git else ""
    if not github and github_hint:
        github = github_hint
    last_commit = (run_git(["log", "-1", "--format=%cs"], repo_dir) if is_git else None) or ""
    language = detect_language(repo_dir)
    category = detect_category(repo_name, repo_dir)
    summary = first_summary_line(repo_dir)
    local_path = str(repo_dir.resolve()) if repo_dir else ""
    access_url = build_access_url(github)

    purpose, status, stars = "", "研究中", ""
    notes_section = ""
    if existing_text:
        fm, body = parse_frontmatter(existing_text)
        if fm.get("用途"):
            purpose = fm["用途"]
        if fm.get("状态"):
            status = fm["状态"]
        if fm.get("stars"):
            stars = fm["stars"]
        sections = split_sections(body)
        notes_section = sections.get("我的笔记", "")

    related_notes = scan_related_notes(repo_name, notes_dir)

    stars_line = f"stars: {stars}" if stars else "stars: "

    fm_lines = [
        "---",
        "tags: [开源项目]",
        f'仓名: "{esc(repo_name)}"',
        f"github: {github}",
        f"分类: {category}",
        f"语言: {language}",
        f'用途: "{esc(purpose)}"  # 简述它做什么 + 归类，可人工/AI 补',
        f"状态: {status}",
        f'本地路径: "{esc(local_path)}"',
        f'访问链接: "{access_url}"',
        f'最近提交: "{last_commit}"',
        stars_line,
        "---",
        "",
    ]

    body_lines = [
        f"# {repo_name}",
        "",
        summary or "(待补描述)",
        "",
        build_access_line(access_url, local_path),
        "",
        "## 我的笔记",
        "",
    ]
    if notes_section:
        body_lines.append(notes_section)
        body_lines.append("")
    body_lines.append("## 关联调研")
    body_lines.append("")
    if related_notes:
        body_lines.extend(f"- [[{name}]]" for name in related_notes)
        body_lines.append("")

    return "\n".join(fm_lines + body_lines)


# ---- 单仓归档模式（--add）----


def ensure_research_note_skeleton(notes_dir: Path, repo_name: str) -> tuple[Path, bool]:
    """若还没有该仓的调研笔记，起一篇骨架；已存在则原样返回，不重复创建。"""
    notes_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(notes_dir.glob(f"*-调研-{repo_name}.md"))
    if existing:
        return existing[0], False
    today = dt.date.today().isoformat()
    note_path = notes_dir / f"{today}-调研-{repo_name}.md"
    content = (
        "---\n"
        "tags: [调研]\n"
        f'关联仓库: "[[{repo_name}]]"\n'
        "---\n"
        "\n"
        f"# {today}-调研-{repo_name}\n"
        "\n"
        "## 是什么\n"
        "\n"
        "## 架构与代码\n"
        "\n"
        "## 对我的价值\n"
        "\n"
        "## 运行验证\n"
        "\n"
        "## 我的结论\n"
    )
    note_path.write_text(content, encoding="utf-8")
    return note_path, True


def add_single_repo(url: str, upstream: Path, vault: Path, notes_dir_rel: Path) -> int:
    owner_repo = github_slug(url)
    if not owner_repo:
        print(
            f"无法从 URL 解析 owner/repo：{url}"
            "（请确认是 https://github.com/<owner>/<repo> 或 git@github.com:<owner>/<repo>.git 形式）"
        )
        return 1
    owner, repo_name = owner_repo.split("/", 1)
    repo_dir: Path | None = upstream / repo_name

    if repo_dir.is_dir():
        print(f"upstream 已存在 {repo_dir}，跳过 clone，直接建卡")
    else:
        clone_url = url if url.startswith(("http://", "https://", "git@")) else f"https://github.com/{owner_repo}"
        print(f"clone {clone_url} -> {repo_dir}")
        proc = None
        try:
            proc = subprocess.run(
                ["git", "clone", clone_url, str(repo_dir)],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"clone 出错：{exc}")
        if proc is None or proc.returncode != 0:
            stderr = proc.stderr.strip()[:300] if proc is not None else ""
            print(f"clone 失败（可能私有/无权限/网络问题），跳过 clone，只用 URL 生成最小卡：{stderr}")
            repo_dir = None

    card_dir = vault / CARD_SUBDIR
    card_dir.mkdir(parents=True, exist_ok=True)
    card_path = card_dir / f"{repo_name}.md"
    existing_text = card_path.read_text(encoding="utf-8") if card_path.is_file() else None

    notes_dir = vault / notes_dir_rel
    note_path, note_created = ensure_research_note_skeleton(notes_dir, repo_name)

    card_text = build_card(repo_name, repo_dir, existing_text, notes_dir, github_hint=owner_repo)
    card_path.write_text(card_text, encoding="utf-8")

    print(f"项目卡：{'新建' if existing_text is None else '更新'} {card_path}")
    print(f"调研笔记：{'新建骨架' if note_created else '已存在，跳过新建'} {note_path}")
    print("双链：卡片「## 关联调研」已自动列出该笔记；笔记 frontmatter `关联仓库` 已指向该卡")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upstream",
        help="上游 git 仓库根目录；不传则读取私有 config.yml 的 SOIA_REPO_UPSTREAM_DIR（二选一，--upstream 优先）",
    )
    parser.add_argument(
        "--vault",
        help="Obsidian vault 路径；不传则读取环境变量 OBSIDIAN_VAULT（二选一，--vault 优先）",
    )
    parser.add_argument(
        "--add",
        metavar="URL",
        help="单仓归档模式：给一个 GitHub URL，clone（已存在则跳过）+ 建/更新该仓项目卡 + "
        "起调研笔记骨架 + 双链；不影响其它仓库",
    )
    parser.add_argument(
        "--notes-dir",
        help=f"调研笔记目录（相对 vault）；默认 {NOTES_SUBDIR}",
    )
    return parser.parse_args()


def main() -> int:
    load_private_env()
    args = parse_args()

    vault = resolve_path(args.vault) or resolve_path(os.environ.get("OBSIDIAN_VAULT"))
    if not vault:
        print(
            f"错误：未指定 --vault 且未设置环境变量 OBSIDIAN_VAULT（{env_source_hint()}）",
            file=sys.stderr,
        )
        return 1
    if not vault.is_dir():
        print(f"错误：vault 路径不存在：{vault}", file=sys.stderr)
        return 1

    upstream = resolve_path(args.upstream) or resolve_path(os.environ.get("SOIA_REPO_UPSTREAM_DIR"))
    notes_dir_rel = Path(args.notes_dir) if args.notes_dir else NOTES_SUBDIR

    if args.add:
        if not upstream:
            print(
                f"错误：未指定 --upstream 且未设置私有 config.yml 的 SOIA_REPO_UPSTREAM_DIR（{env_source_hint()}）",
                file=sys.stderr,
            )
            return 1
        return add_single_repo(args.add, upstream, vault, notes_dir_rel)

    if not upstream or not upstream.is_dir():
        print(
            f"错误：--upstream 目录不存在或未指定（也可设置私有 config.yml 的 SOIA_REPO_UPSTREAM_DIR，"
            f"{env_source_hint()}）：{upstream}",
            file=sys.stderr,
        )
        return 1

    card_dir = vault / CARD_SUBDIR
    card_dir.mkdir(parents=True, exist_ok=True)
    notes_dir = vault / notes_dir_rel

    repo_dirs = sorted(
        p for p in upstream.iterdir() if p.is_dir() and p.name not in SKIP_NAMES and not p.name.startswith(".")
    )
    print(f"扫描 upstream：{upstream}，发现 {len(repo_dirs)} 个仓库目录")

    created, updated = 0, 0
    for repo_dir in repo_dirs:
        repo_name = repo_dir.name
        card_path = card_dir / f"{repo_name}.md"
        existing_text = card_path.read_text(encoding="utf-8") if card_path.is_file() else None
        card_text = build_card(repo_name, repo_dir, existing_text, notes_dir)
        card_path.write_text(card_text, encoding="utf-8")
        if existing_text is None:
            created += 1
        else:
            updated += 1

    total = created + updated
    print(f"共扫 {len(repo_dirs)} 仓、生成/更新 {total} 张项目卡（新建 {created}、更新 {updated}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
