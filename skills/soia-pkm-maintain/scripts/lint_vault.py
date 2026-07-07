#!/usr/bin/env python3
"""
lint_vault.py — Obsidian vault 只读体检脚本（soia-pkm-maintain skill 机械层）

四类检查（全部只读，不修改 vault 里任何文件，可重复运行）：
  a) 死链 wikilink   —— [[target]] 剥离 |别名 和 #锚点后，在全库 .md 文件名/
                         相对路径索引里找不到对应文件
  b) 重复文件名      —— 同名 .md 出现在多个目录
  c) 主标签漂移      —— frontmatter tags 首标签存在但不在白名单
                         （完全没有 tags 字段/空列表的文件单独计为"未打标"，不算漂移）
  d) 过期文章        —— frontmatter time_sensitive: true 且 review_after
                         早于当前年月

用法：
  python3 lint_vault.py --vault /path/to/vault
  python3 lint_vault.py --vault /path/to/vault --json
  python3 lint_vault.py --vault /path/to/vault --exclude "20_资料库/OB知识库地图.md,某目录/某文件.md"
  python3 lint_vault.py --vault /path/to/vault --tags "书库,童书,日记,调研,文章摘抄,阅读记录,阅读计划,重读,周报"

注意：--exclude / --tags 传参会整体覆盖内置默认值（不是追加），需要保留默认排除项时
记得把它一起写进去。

设计说明：
  - 链接目标若带常见附件扩展名（图片/PDF/office 文档等）视为附件引用，不纳入死链检查
    （本脚本只维护 .md 文件名/路径索引，附件不在索引范围内）。
  - --exclude 命中的文件仍会留在"目标索引"里（别的文件链接过去依然算有效），只是不会被
    当作扫描源（不解析它的链接/不参与重复名/标签/过期检查）——这样排除类似"全库地图"这种
    自动生成的大快照文件时，不会把指向它的正常链接误判成死链。
"""
import argparse
import datetime
import json
import os
import re
import sys

from soia_env import env_source_hint, load_private_env

load_private_env()

SKIP_DIRS = {".git", ".obsidian", ".trash"}

DEFAULT_EXCLUDE = ["20_资料库/OB知识库地图.md"]

DEFAULT_TAGS = [
    "书库", "童书", "日记", "调研", "文章摘抄",
    "阅读记录", "阅读计划", "重读", "周报",
]

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

ATTACHMENT_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp",
    ".pdf", ".mp4", ".mov", ".mp3", ".wav", ".m4a",
    ".zip", ".excalidraw", ".canvas",
    ".docx", ".xlsx", ".pptx", ".csv", ".txt",
}


def parse_args():
    ap = argparse.ArgumentParser(
        description="Obsidian vault 只读体检：死链 / 重复文件名 / 主标签漂移 / 过期文章",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--vault", default=os.environ.get("OBSIDIAN_VAULT"),
        help="vault 根目录（或在私有 env 文件设置 OBSIDIAN_VAULT，二选一，--vault 优先）",
    )
    ap.add_argument(
        "--json", action="store_true",
        help="输出 JSON 而非默认的 markdown 报告",
    )
    ap.add_argument(
        "--exclude", default=",".join(DEFAULT_EXCLUDE),
        help="逗号分隔的相对路径，跳过扫描（整体覆盖默认值，默认：%s；"
             "支持文件路径或目录前缀）" % ",".join(DEFAULT_EXCLUDE),
    )
    ap.add_argument(
        "--tags", default=",".join(DEFAULT_TAGS),
        help="主标签白名单，逗号分隔（整体覆盖默认值，默认：%s）" % ",".join(DEFAULT_TAGS),
    )
    return ap.parse_args()


def collect_md_files(vault):
    """返回全库 .md 文件的相对路径列表（相对 vault 根，正斜杠分隔，已排序）。"""
    results = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_root = os.path.relpath(root, vault)
        rel_root = "" if rel_root == "." else rel_root.replace(os.sep, "/")
        for f in files:
            if not f.lower().endswith(".md"):
                continue
            rel = f if not rel_root else f"{rel_root}/{f}"
            results.append(rel)
    return sorted(results)


def is_excluded(rel, exclude_set):
    if rel in exclude_set:
        return True
    return any(rel.startswith(ex.rstrip("/") + "/") for ex in exclude_set)


UNREADABLE_FILES = []  # 编码异常等无法读取的文件（相对路径），运行结束汇总提示


def read_text(vault, rel):
    """读文件全文；读不了（权限/编码异常等）记入 UNREADABLE_FILES 并返回 None。"""
    path = os.path.join(vault, rel.replace("/", os.sep))
    try:
        with open(path, "r", encoding="utf-8") as fp:
            return fp.read()
    except (OSError, UnicodeDecodeError):
        UNREADABLE_FILES.append(rel)
        return None


def read_frontmatter_block(text):
    """提取 frontmatter 原始文本（--- 与下一个 --- 之间），无 frontmatter 返回空串。"""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end == -1:
        return ""
    return text[3:end]


def parse_list_field(fm_text, field_name):
    """
    解析 frontmatter 里的列表字段，兼容：
      - 单行：tags: [书库]  /  tags: [文章摘抄, 重读]
      - 多行：tags:\n  - 书库\n  - 重读
      - 标量：tags: 书库
    字段不存在返回 None；字段存在但为空返回 []。
    """
    m = re.search(rf"^{re.escape(field_name)}:[ \t]*", fm_text, re.MULTILINE)
    if not m:
        return None
    rest = fm_text[m.end():]
    lines = rest.split("\n")
    first_line = lines[0].strip()

    if first_line.startswith("["):
        buf = first_line
        idx = 1
        while "]" not in buf and idx < len(lines):
            buf += "\n" + lines[idx]
            idx += 1
        start = buf.find("[")
        end_b = buf.find("]", start)
        content = buf[start + 1:end_b] if end_b != -1 else buf[start + 1:]
        return [x.strip().strip('"').strip("'") for x in content.split(",") if x.strip()]

    if first_line == "":
        items = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("- "):
                items.append(stripped[2:].strip().strip('"').strip("'"))
            elif stripped == "":
                continue
            else:
                break
        return items

    val = first_line.strip().strip('"').strip("'")
    return [val] if val else []


def parse_scalar_field(fm_text, field_name):
    m = re.search(rf"^{re.escape(field_name)}:[ \t]*(.*)$", fm_text, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


def clean_wikilink_target(raw):
    """[[target#anchor|alias]] → target（去掉 |别名 和 #锚点）。"""
    target = raw.split("|", 1)[0]
    target = target.split("#", 1)[0]
    return target.strip()


def check_dead_links(vault, scan_files, index_files):
    all_set = set(index_files)
    name_index = {}
    for rel in index_files:
        stem = os.path.basename(rel)[:-3]  # 去掉 .md
        name_index.setdefault(stem, []).append(rel)

    findings = []
    for rel in scan_files:
        text = read_text(vault, rel)
        if text is None:
            continue
        for raw in WIKILINK_RE.findall(text):
            target = clean_wikilink_target(raw)
            if not target:
                continue  # 纯锚点/同文件标题链接（如 [[#某标题]]），不检查
            _, ext = os.path.splitext(target)
            if ext.lower() in ATTACHMENT_EXTS:
                continue  # 附件引用不在 .md 索引范围内
            normalized = target.replace("\\", "/").lstrip("/")
            if "/" in normalized:
                cand = normalized if normalized.lower().endswith(".md") else normalized + ".md"
                hit = cand in all_set or any(p.endswith("/" + cand) for p in all_set)
            else:
                stem = normalized[:-3] if normalized.lower().endswith(".md") else normalized
                hit = stem in name_index
            if not hit:
                findings.append((rel, target))
    return findings


def check_duplicate_filenames(scan_files):
    name_index = {}
    for rel in scan_files:
        base = os.path.basename(rel)
        name_index.setdefault(base, []).append(rel)
    return {name: paths for name, paths in name_index.items() if len(paths) > 1}


def check_tag_drift(vault, scan_files, whitelist):
    drift = []
    untagged = []
    for rel in scan_files:
        text = read_text(vault, rel)
        if text is None:
            continue
        fm = read_frontmatter_block(text)
        if not fm:
            continue  # 没有 frontmatter 块的文件（README/AGENTS 等）不在标签检查范围内
        tags = parse_list_field(fm, "tags")
        if tags is None or len(tags) == 0:
            untagged.append(rel)
            continue
        first_tag = tags[0]
        if first_tag not in whitelist:
            drift.append((rel, first_tag))
    return drift, untagged


def check_stale_articles(vault, scan_files):
    today = datetime.date.today()
    cur_ym = (today.year, today.month)
    stale = []
    for rel in scan_files:
        text = read_text(vault, rel)
        if text is None:
            continue
        fm = read_frontmatter_block(text)
        if not fm:
            continue
        ts = parse_scalar_field(fm, "time_sensitive")
        if not ts or ts.lower() != "true":
            continue
        review_after = parse_scalar_field(fm, "review_after")
        if not review_after:
            continue
        m = re.match(r"^(\d{4})-(\d{2})", review_after)
        if not m:
            continue
        ym = (int(m.group(1)), int(m.group(2)))
        if ym < cur_ym:
            stale.append((rel, review_after))
    return stale


def render_markdown(vault, dead_links, dup_names, tag_drift, untagged, stale, unreadable):
    lines = []
    lines.append("# Vault Lint 报告")
    lines.append("")
    lines.append(f"- vault: `{vault}`")
    lines.append(f"- 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    lines.append("## a. 死链 wikilink")
    lines.append("")
    if dead_links:
        for rel, target in dead_links:
            lines.append(f"- `{rel}` → `[[{target}]]`")
    else:
        lines.append("无")
    lines.append("")

    lines.append("## b. 重复文件名")
    lines.append("")
    if dup_names:
        for name, paths in sorted(dup_names.items()):
            lines.append(f"- `{name}`：")
            for p in paths:
                lines.append(f"  - `{p}`")
    else:
        lines.append("无")
    lines.append("")

    lines.append("## c. 主标签漂移")
    lines.append("")
    if tag_drift:
        for rel, tag in tag_drift:
            lines.append(f"- `{rel}` → 首标签 `{tag}` 不在白名单")
    else:
        lines.append("无")
    if untagged:
        lines.append("")
        lines.append(f"未打标（不计入漂移，共 {len(untagged)} 篇）：")
        for rel in untagged[:20]:
            lines.append(f"  - `{rel}`")
        if len(untagged) > 20:
            lines.append(f"  - …（仅列前 20，共 {len(untagged)} 篇）")
    lines.append("")

    lines.append("## d. 过期文章")
    lines.append("")
    if stale:
        for rel, review_after in stale:
            lines.append(f"- `{rel}` → review_after `{review_after}` 早于当前年月")
    else:
        lines.append("无")
    lines.append("")

    lines.append("## 汇总")
    lines.append("")
    lines.append(f"- 死链：{len(dead_links)}")
    lines.append(f"- 重复文件名：{len(dup_names)} 组")
    lines.append(f"- 主标签漂移：{len(tag_drift)}（未打标 {len(untagged)}，不计入漂移）")
    lines.append(f"- 过期文章：{len(stale)}")
    if unreadable:
        lines.append(f"- 读取失败（编码异常等，已跳过，不计入以上四类）：{len(unreadable)}")
        for rel in unreadable:
            lines.append(f"  - `{rel}`")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    if not args.vault:
        print(f"错误：未指定 --vault 且未在私有 env 文件设置 OBSIDIAN_VAULT（{env_source_hint()}）", file=sys.stderr)
        sys.exit(1)
    vault = os.path.abspath(os.path.expandvars(os.path.expanduser(args.vault)))
    if not os.path.isdir(vault):
        print(f"错误：vault 路径不存在：{vault}", file=sys.stderr)
        sys.exit(1)

    exclude_set = {x.strip() for x in args.exclude.split(",") if x.strip()}
    whitelist = [t.strip() for t in args.tags.split(",") if t.strip()]

    UNREADABLE_FILES.clear()

    all_files = collect_md_files(vault)
    scan_files = [f for f in all_files if not is_excluded(f, exclude_set)]

    dead_links = check_dead_links(vault, scan_files, all_files)
    dup_names = check_duplicate_filenames(scan_files)
    tag_drift, untagged = check_tag_drift(vault, scan_files, whitelist)
    stale = check_stale_articles(vault, scan_files)
    unreadable = sorted(set(UNREADABLE_FILES))

    if args.json:
        payload = {
            "vault": vault,
            "scanned_files": len(scan_files),
            "excluded_files": len(all_files) - len(scan_files),
            "dead_links": [{"file": rel, "target": t} for rel, t in dead_links],
            "duplicate_filenames": dup_names,
            "tag_drift": [{"file": rel, "tag": t} for rel, t in tag_drift],
            "untagged": untagged,
            "stale_articles": [{"file": rel, "review_after": r} for rel, r in stale],
            "unreadable_files": unreadable,
            "summary": {
                "dead_links": len(dead_links),
                "duplicate_filenames": len(dup_names),
                "tag_drift": len(tag_drift),
                "untagged": len(untagged),
                "stale_articles": len(stale),
                "unreadable_files": len(unreadable),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(vault, dead_links, dup_names, tag_drift, untagged, stale, unreadable))


if __name__ == "__main__":
    main()
