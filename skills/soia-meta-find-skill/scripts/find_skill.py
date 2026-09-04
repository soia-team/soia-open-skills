#!/usr/bin/env python3
"""Discover SOIA skills without choosing or executing an installation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROUTER_SKILL_NAME = "soia-meta-find-skill"
RESULT_LIMIT = 3
DEFAULT_GLOBAL_SKILLS_DIR = Path.home() / ".agents" / "skills"
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / "references" / "skill-directory.json"
DEFAULT_HINTS = Path(__file__).resolve().parents[1] / "references" / "query-hints.json"
SCOPE_PRIORITY = {"project": 0, "global": 1}


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


def load_hints(path: Path) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read query hints {path}: {exc}") from exc
    if not isinstance(payload, Mapping) or payload.get("version") != 1:
        raise ValueError("query hints must be a version 1 JSON object")

    def mapping(name: str) -> dict[str, tuple[str, ...]]:
        raw_mapping = payload.get(name)
        if not isinstance(raw_mapping, Mapping):
            raise ValueError(f"query hints field {name} must be an object")
        result: dict[str, tuple[str, ...]] = {}
        for key, raw_values in raw_mapping.items():
            if not isinstance(key, str) or not key or not isinstance(raw_values, list):
                raise ValueError(f"query hints field {name} has an invalid entry")
            values = tuple(normalized(value) for value in raw_values if isinstance(value, str) and value)
            if not values:
                raise ValueError(f"query hints field {name} has an empty entry")
            result[normalized(key)] = values
        return result

    return mapping("query_hints"), mapping("domain_hints")


def query_terms(query: str, hints: Mapping[str, Sequence[str]]) -> list[str]:
    normalized_query = normalized(query)
    primary = [normalized(term) for term in re.split(r"[\s,，/；;]+", query) if term.strip()]
    terms: list[str] = list(primary)
    for phrase, expansions in hints.items():
        if phrase in normalized_query:
            terms.append(phrase)
            terms.extend(expansions)
    return list(dict.fromkeys(term for term in terms if term))


def domain_terms(domain: str | None, hints: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    if not domain:
        return ()
    key = normalized(domain)
    return tuple(dict.fromkeys((key, *hints.get(key, ()))))


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def selected_roots(args: argparse.Namespace) -> tuple[list[tuple[str, Path]], str | None]:
    project = args.project.expanduser().resolve() if args.project else find_project_root(Path.cwd())
    requested_scope = args.scope
    if requested_scope == "auto":
        if project:
            return [("project", project / ".agents" / "skills")], "project"
        if args.skills_dir:
            return [("global", args.skills_dir.expanduser())], "global"
        return [], None
    if requested_scope == "global":
        return [("global", (args.skills_dir or DEFAULT_GLOBAL_SKILLS_DIR).expanduser())], "global"
    if not project:
        raise ValueError(f"--scope {requested_scope} requires --project or a git project in the current directory")
    project_root = project / ".agents" / "skills"
    if requested_scope == "project":
        return [("project", project_root)], "project"
    return [
        ("project", project_root),
        ("global", (args.skills_dir or DEFAULT_GLOBAL_SKILLS_DIR).expanduser()),
    ], "both"


def installed_candidates(roots: Iterable[tuple[str, Path]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_locations: set[tuple[str, str]] = set()
    for scope, skills_dir in roots:
        if not skills_dir.is_dir():
            continue
        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            parsed = parse_frontmatter(skill_md)
            if not parsed:
                continue
            name, description = parsed
            if name == ROUTER_SKILL_NAME or not name.startswith("soia-"):
                continue
            real_path = str(skill_md.resolve())
            location = (name, real_path)
            if location in seen_locations:
                continue
            seen_locations.add(location)
            candidates.append(
                {
                    "name": name,
                    "description": description,
                    "installed": True,
                    "source_scope": scope,
                    "path": real_path,
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
        if not isinstance(entry, Mapping):
            raise ValueError(f"skill directory entry {index} must be an object")
        name = entry.get("name")
        description = entry.get("description")
        source = entry.get("source")
        if not isinstance(source, Mapping):
            repo = entry.get("repo")
            source = {"repository": repo} if isinstance(repo, str) else None
        repository = source.get("repository") if isinstance(source, Mapping) else None
        if not all(isinstance(value, str) and value for value in (name, description, repository)):
            raise ValueError(f"skill directory entry {index} is missing required fields")
        candidates.append(
            {
                "name": name,
                "description": description,
                "installed": False,
                "source_scope": "directory",
                "source": {"repository": repository},
            }
        )
    return candidates


def score_candidate(candidate: Mapping[str, Any], terms: list[str], domains: tuple[str, ...]) -> int:
    name = normalized(str(candidate.get("name", "")))
    description = normalized(str(candidate.get("description", "")))
    repository = normalized(str(candidate.get("repository", "")))
    haystack = f"{name}\n{description}\n{repository}"
    if domains and not any(term in haystack for term in domains):
        return 0
    score = 0
    for term in terms:
        if term in name:
            score += 8
        if term in description:
            score += 4
        if term in repository:
            score += 2
    if terms and score == 0:
        return 0
    return score + (1 if candidate.get("installed") else 0)


def merge_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        name = str(candidate["name"])
        item = merged.setdefault(
            name,
            {
                "name": name,
                "description": candidate["description"],
                "installed_locations": [],
                "source": candidate.get("source"),
            },
        )
        if candidate.get("source") and not item.get("source"):
            item["source"] = candidate["source"]
        if candidate.get("installed"):
            item["installed_locations"].append(candidate)
            if SCOPE_PRIORITY.get(candidate["source_scope"], 99) < SCOPE_PRIORITY.get(
                item.get("preferred_scope", ""), 99
            ):
                item["description"] = candidate["description"]
                item["preferred_scope"] = candidate["source_scope"]
    for item in merged.values():
        item["installed_locations"].sort(
            key=lambda location: (SCOPE_PRIORITY.get(location["source_scope"], 99), location["path"])
        )
        item["installed"] = bool(item["installed_locations"])
        item["repository"] = str((item.get("source") or {}).get("repository", ""))
    return list(merged.values())


def install_selection(
    candidate: Mapping[str, Any], discovery_scope: str | None, requested_agents: list[str]
) -> dict[str, Any]:
    target_scope = discovery_scope if discovery_scope in {"project", "global"} else None
    pending: list[str] = []
    if not candidate.get("installed") and target_scope is None:
        pending.append("scope")
    if not candidate.get("installed") and not requested_agents:
        pending.append("agents")
    return {
        "scope": target_scope,
        "agents": requested_agents,
        "target": {"kind": "skill", "name": candidate["name"]},
        "available_target_kinds": ["skill", "domain", "all"],
        "selection_required": bool(pending),
        "pending": pending,
    }


def ranked(
    candidates: Iterable[dict[str, Any]],
    terms: list[str],
    domains: tuple[str, ...],
    requested_scope: str | None,
    requested_agents: list[str],
    legacy_install_cmd: bool,
) -> list[dict[str, Any]]:
    scored = [(score_candidate(candidate, terms, domains), candidate) for candidate in merge_candidates(candidates)]
    matched = [(score, candidate) for score, candidate in scored if score > 0]
    matched.sort(key=lambda item: (-item[0], normalized(str(item[1]["name"]))))
    result: list[dict[str, Any]] = []
    for _, candidate in matched[:RESULT_LIMIT]:
        locations = candidate["installed_locations"]
        scopes = list(dict.fromkeys(location["source_scope"] for location in locations))
        public: dict[str, Any] = {
            "name": candidate["name"],
            "description": candidate["description"],
            "installed": candidate["installed"],
            "installed_scopes": scopes,
            "source_scope": locations[0]["source_scope"] if locations else "directory",
            "requested_agents": requested_agents,
            "install_selection": install_selection(candidate, requested_scope, requested_agents),
        }
        if locations:
            public["path"] = locations[0]["path"]
        if candidate.get("source"):
            public["source"] = candidate["source"]
        if legacy_install_cmd and not candidate["installed"] and candidate.get("source"):
            public["install_cmd"] = (
                f"npx skills add soia-team/{candidate['source']['repository']} -g -a '*' -s {candidate['name']} -y"
            )
            public["install_cmd_deprecated"] = True
        result.append(public)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="One or more discriminating keywords")
    parser.add_argument("--domain", help="Optional SOIA domain or domain summary filter")
    parser.add_argument("--project", type=Path, help="Project root used for .agents/skills discovery")
    parser.add_argument(
        "--scope",
        choices=("auto", "project", "global", "both"),
        default="auto",
        help="Discovery scope; auto prefers the current project and never falls back to global",
    )
    parser.add_argument("--agent", action="append", default=[], help="Requested installation agent; repeatable")
    parser.add_argument(
        "--legacy-install-cmd",
        action="store_true",
        help="Deprecated: include the legacy global all-agent install command for old consumers",
    )
    parser.add_argument("--skills-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY, help=argparse.SUPPRESS)
    parser.add_argument("--hints", type=Path, default=DEFAULT_HINTS, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        query_hints, domain_hints = load_hints(args.hints)
        terms = query_terms(args.query, query_hints)
        if not terms:
            print("error: --query must contain at least one keyword", file=sys.stderr)
            return 2
        roots, effective_scope = selected_roots(args)
        candidates = [*installed_candidates(roots), *directory_candidates(args.directory)]
        result = ranked(
            candidates,
            terms,
            domain_terms(args.domain, domain_hints),
            effective_scope,
            list(dict.fromkeys(args.agent)),
            args.legacy_install_cmd,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
