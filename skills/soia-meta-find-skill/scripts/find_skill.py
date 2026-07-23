#!/usr/bin/env python3
"""Find the best installed SOIA skills, falling back to the public directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROUTER_SKILL_NAME = "soia-meta-find-skill"
RESULT_LIMIT = 3
DEFAULT_SKILLS_DIR = Path.home() / ".agents" / "skills"
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / "references" / "skill-directory.json"

DOMAIN_HINTS = {
    "剪藏网盘": ("pkm-clip", "drive-ops", "alipan", "baidu"),
    "知识提炼": ("pkm-vault", "pkm-library", "pkm-distill", "pkm-interpret", "pkm-transform"),
    "新媒发布": ("media-", "media-content"),
    "编码审查终端": (
        "dev-coding",
        "code-review",
        "fix-loop",
        "github-ops",
        "task-execute",
        "terminal-ops",
    ),
    "设计图表": ("dev-design", "design-", "diagram", "drawio", "archify"),
    "产品prd": ("dev-product", "draft-prd"),
    "软件测试": ("dev-testing", "draft-test"),
    "软件发版": ("dev-release", "plan-release"),
    "办公协作": ("cwork-", "cwork-office"),
    "教育课程": ("edu-", "edu-course"),
    "环境安装": ("env-", "open-env"),
    "生态管理": ("meta-", "open-skills"),
}

QUERY_HINTS = {
    "剪藏": ("clip", "归档"),
    "网盘": ("drive", "alipan", "baidu", "云盘"),
    "提炼": ("distill", "interpret", "分析"),
    "发版": ("release", "发布清单"),
    "运维": ("ops", "巡检"),
    "课程": ("course", "lesson", "教案"),
}


def clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> tuple[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        if key in {"name", "description"}:
            values[key] = clean_scalar(raw)
    name = values.get("name", "")
    description = values.get("description", "")
    if not name or not description:
        return None
    return name, description


def normalized(value: str) -> str:
    return value.casefold().strip()


def query_terms(query: str) -> list[str]:
    primary = [normalized(term) for term in re.split(r"[\s,，/；;]+", query) if term.strip()]
    terms: list[str] = []
    for term in primary:
        terms.append(term)
        terms.extend(normalized(hint) for hint in QUERY_HINTS.get(term, ()))
    return list(dict.fromkeys(terms))


def domain_terms(domain: str | None) -> tuple[str, ...]:
    if not domain:
        return ()
    key = normalized(domain)
    hints = DOMAIN_HINTS.get(key)
    if hints:
        return tuple(normalized(value) for value in (key, *hints))
    return (key,)


def score_candidate(candidate: dict[str, Any], terms: list[str], domains: tuple[str, ...]) -> int:
    name = normalized(str(candidate.get("name", "")))
    description = normalized(str(candidate.get("description", "")))
    repo = normalized(str(candidate.get("repo", "")))
    haystack = f"{name}\n{description}\n{repo}"
    if domains and not any(term in haystack for term in domains):
        return 0
    score = 0
    for term in terms:
        if term in name:
            score += 8
        if term in description:
            score += 4
        if term in repo:
            score += 2
    if terms and score == 0:
        return 0
    return score + (1 if candidate.get("installed") else 0)


def installed_candidates(skills_dir: Path) -> list[dict[str, Any]]:
    if not skills_dir.is_dir():
        return []
    candidates: list[dict[str, Any]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        parsed = parse_frontmatter(skill_md)
        if not parsed:
            continue
        name, description = parsed
        if name == ROUTER_SKILL_NAME or not name.startswith("soia-"):
            continue
        candidates.append(
            {
                "name": name,
                "description": description,
                "installed": True,
                "path": str(skill_md.resolve()),
            }
        )
    return candidates


def directory_candidates(directory_path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(directory_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read skill directory {directory_path}: {exc}") from exc
    if not isinstance(payload, list):
        raise ValueError("skill directory must contain a JSON array")
    candidates: list[dict[str, Any]] = []
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise ValueError(f"skill directory entry {index} must be an object")
        required = ("name", "repo", "description", "install_cmd")
        if not all(isinstance(entry.get(key), str) and entry[key] for key in required):
            raise ValueError(f"skill directory entry {index} is missing required fields")
        candidates.append(
            {
                "name": entry["name"],
                "repo": entry["repo"],
                "description": entry["description"],
                "installed": False,
                "install_cmd": entry["install_cmd"],
            }
        )
    return candidates


def ranked(
    candidates: Iterable[dict[str, Any]], terms: list[str], domains: tuple[str, ...]
) -> list[dict[str, Any]]:
    scored = [
        (score_candidate(candidate, terms, domains), candidate)
        for candidate in candidates
    ]
    matched = [(score, candidate) for score, candidate in scored if score > 0]
    matched.sort(key=lambda item: (-item[0], normalized(str(item[1]["name"]))))
    result: list[dict[str, Any]] = []
    for _, candidate in matched[:RESULT_LIMIT]:
        public = {
            "name": candidate["name"],
            "description": candidate["description"],
            "installed": candidate["installed"],
        }
        location_key = "path" if candidate["installed"] else "install_cmd"
        public[location_key] = candidate[location_key]
        result.append(public)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="One or more discriminating keywords")
    parser.add_argument("--domain", help="Optional SOIA domain or domain summary filter")
    parser.add_argument("--skills-dir", type=Path, default=DEFAULT_SKILLS_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    terms = query_terms(args.query)
    if not terms:
        print("error: --query must contain at least one keyword", file=sys.stderr)
        return 2
    domains = domain_terms(args.domain)
    local_matches = ranked(installed_candidates(args.skills_dir.expanduser()), terms, domains)
    try:
        result = local_matches or ranked(directory_candidates(args.directory), terms, domains)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
