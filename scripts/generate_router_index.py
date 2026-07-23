#!/usr/bin/env python3
"""Generate the two-tier router's public skill directory from GitHub."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Mapping, Sequence


OWNER = "soia-team"
DEFAULT_MANIFEST = Path("routing/routing-manifest.json")
DEFAULT_OUTPUT = Path("skills/soia-meta-find-skill/references/skill-directory.json")
SKILL_NAME_PATTERN = re.compile(r"^soia-[a-z0-9]+(?:-[a-z0-9]+)+$")
REPOSITORY_PATTERN = re.compile(r"^soia-open-[a-z0-9]+(?:-[a-z0-9]+)*$")


def clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        if value[0] == "'":
            return value[1:-1].replace("''", "'")
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
        return parsed if isinstance(parsed, str) else value[1:-1]
    return value


def frontmatter_description(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md has no YAML frontmatter")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        if key.strip() == "description":
            description = clean_scalar(raw)
            if not description or description in {">", "|", ">-", "|-"}:
                raise ValueError("frontmatter description must be a non-empty scalar line")
            return description
    raise ValueError("frontmatter description is missing")


def load_manifest(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("routing manifest must contain a JSON array")
    entries: list[dict[str, str]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, Mapping):
            raise ValueError(f"routing manifest entry {index} must be an object")
        skill_name = item.get("skill_name")
        repo = item.get("repo")
        skill_path = item.get("skillPath")
        if not all(
            isinstance(value, str) and value
            for value in (skill_name, repo, skill_path)
        ):
            raise ValueError(f"routing manifest entry {index} is missing required fields")
        if SKILL_NAME_PATTERN.fullmatch(str(skill_name)) is None:
            raise ValueError(f"routing manifest entry {index} has an invalid skill_name")
        if REPOSITORY_PATTERN.fullmatch(str(repo)) is None:
            raise ValueError(f"routing manifest entry {index} has an invalid repo")
        if skill_path != f"skills/{skill_name}":
            raise ValueError(f"routing manifest entry {index} has an inconsistent skillPath")
        entries.append(
            {
                "skill_name": str(skill_name),
                "repo": str(repo),
                "skillPath": str(skill_path),
            }
        )
    names = [entry["skill_name"] for entry in entries]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate routed skill names: {', '.join(duplicates)}")
    return entries


def fetch_skill_md(repo: str, skill_path: str) -> str:
    command = [
        "gh",
        "api",
        "-H",
        "Accept: application/vnd.github.raw+json",
        f"repos/{OWNER}/{repo}/contents/{skill_path}/SKILL.md?ref=main",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
        raise RuntimeError(f"failed to fetch {repo}/{skill_path}/SKILL.md: {detail}")
    return result.stdout


def directory_entry(entry: Mapping[str, str], skill_md: str) -> dict[str, str]:
    name = entry["skill_name"]
    repo = entry["repo"]
    return {
        "name": name,
        "repo": repo,
        "description": frontmatter_description(skill_md),
        "install_cmd": f"npx skills add {OWNER}/{repo} -g -a '*' -s {name} -y",
    }


def build_directory(
    manifest: Sequence[Mapping[str, str]],
    fetcher: Callable[[str, str], str] = fetch_skill_md,
    workers: int = 12,
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_entries = {
            executor.submit(fetcher, entry["repo"], entry["skillPath"]): entry
            for entry in manifest
        }
        for future in as_completed(future_entries):
            entry = future_entries[future]
            try:
                results.append(directory_entry(entry, future.result()))
            except Exception as exc:
                raise RuntimeError(
                    f"cannot build directory entry for {entry['skill_name']}: {exc}"
                ) from exc
    results.sort(key=lambda item: (item["name"], item["repo"]))
    return results


def format_directory(entries: Sequence[Mapping[str, str]]) -> str:
    return json.dumps(list(entries), ensure_ascii=False, indent=2) + "\n"


def check_or_write(path: Path, content: str, check: bool) -> bool:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            print(f"out of date: {path}", file=sys.stderr)
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path}")
    return True


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--jobs", type=int, default=12, help="Concurrent gh api requests")
    parser.add_argument("--check", action="store_true", help="Fail when the generated index is stale")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        directory = build_directory(manifest, workers=args.jobs)
        current = check_or_write(args.output, format_directory(directory), args.check)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not current:
            return 1
        print(f"router index is current ({len(directory)} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
