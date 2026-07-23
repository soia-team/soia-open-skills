#!/usr/bin/env python3
"""Generate the public SOIA skill routing manifest from GitHub repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


OWNER = "soia-team"

# Public routing sources, including empty incubators so the published topology
# and routing inputs stay aligned. Private skills never enter this manifest:
# corp/private incremental routing is owned and published by the corresponding
# private repository.
PUBLIC_REPOSITORIES = (
    "soia-open-skills",
    "soia-open-env-skills",
    "soia-open-pkm-clip-skills",
    "soia-open-pkm-vault-skills",
    "soia-open-media-content-skills",
    "soia-open-cwork-office-skills",
    "soia-open-dev-coding-skills",
    "soia-open-dev-design-skills",
    "soia-open-dev-infra-skills",
    "soia-open-safe-skills",
    "soia-open-edu-course-skills",
    "soia-open-dev-product-skills",
    "soia-open-dev-testing-skills",
    "soia-open-dev-release-skills",
)

PORTAL_REPOSITORY = "soia-open-skills"


def routing_entry(repo: str, skill_name: str) -> dict[str, str]:
    return {
        "skill_name": skill_name,
        "repo": repo,
        "skillPath": f"skills/{skill_name}",
        "visibility": "public",
    }


def entries_from_contents(repo: str, contents: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Convert one GitHub contents response into normalized routing entries."""
    names = {
        item.get("name")
        for item in contents
        if item.get("type") == "dir"
        and isinstance(item.get("name"), str)
        and item["name"].startswith("soia-")
    }
    return [routing_entry(repo, name) for name in sorted(names)]


def build_manifest(
    repository_contents: Mapping[str, Sequence[Mapping[str, Any]]],
    repositories: Sequence[str] = PUBLIC_REPOSITORIES,
) -> list[dict[str, str]]:
    """Build a deterministic, duplicate-free manifest from repository fixtures."""
    entries: list[dict[str, str]] = []
    for repo in repositories:
        if repo not in repository_contents:
            raise ValueError(f"missing contents payload for repository: {repo}")
        entries.extend(entries_from_contents(repo, repository_contents[repo]))

    entries.sort(key=lambda item: (item["skill_name"], item["repo"]))
    duplicates = sorted(
        name
        for name in {item["skill_name"] for item in entries}
        if sum(item["skill_name"] == name for item in entries) > 1
    )
    if duplicates:
        raise ValueError(f"duplicate public skill names: {', '.join(duplicates)}")
    return entries


def format_manifest(entries: Sequence[Mapping[str, str]]) -> str:
    """Serialize the manifest with stable human-reviewable formatting."""
    return json.dumps(list(entries), ensure_ascii=False, indent=2) + "\n"


def fetch_github_contents(repo: str) -> list[dict[str, Any]]:
    command = ["gh", "api", f"repos/{OWNER}/{repo}/contents/skills?ref=main"]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
        raise RuntimeError(f"failed to enumerate {OWNER}/{repo}: {detail}")
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise ValueError(f"unexpected contents payload for {repo}: expected a JSON array")
    return payload


def local_portal_contents(repo_root: Path) -> list[dict[str, str]]:
    """Preview an unmerged portal branch while all spoke repos still use GitHub."""
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        raise ValueError(f"local portal has no skills directory: {skills_dir}")
    return [
        {"name": path.name, "type": "dir"}
        for path in sorted(skills_dir.iterdir())
        if path.is_dir() and (path / "SKILL.md").is_file()
    ]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("routing/routing-manifest.json"),
        help="Output path (default: routing/routing-manifest.json)",
    )
    parser.add_argument(
        "--local-portal-root",
        type=Path,
        help="Use a local unmerged soia-open-skills checkout for the portal entry only",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payloads: dict[str, Sequence[Mapping[str, Any]]] = {}
    try:
        for repo in PUBLIC_REPOSITORIES:
            if repo == PORTAL_REPOSITORY and args.local_portal_root is not None:
                payloads[repo] = local_portal_contents(args.local_portal_root.resolve())
            else:
                payloads[repo] = fetch_github_contents(repo)
        manifest = build_manifest(payloads)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(format_manifest(manifest), encoding="utf-8")
    print(
        f"wrote {len(manifest)} public skills from "
        f"{len(PUBLIC_REPOSITORIES)} repositories to {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
