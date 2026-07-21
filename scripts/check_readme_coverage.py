#!/usr/bin/env python3
"""Check that every skill under skills/ is mentioned in the top-level README.md.

Scope (intentionally narrow): this script only checks whether each real skill
name appears as a literal substring somewhere in the repository root
README.md. It does NOT do any semantic validation — it does not check
whether the description is accurate, whether the "现在能用?" status marker
is correct, or whether the skill is filed under the right table/section.
That is a deliberate design decision: semantic checks would require parsing
prose and judging correctness, which is high-maintenance and prone to false
positives/negatives. A plain substring check is cheap, deterministic, and
catches the failure mode that actually recurs in practice — a skill quietly
existing on disk with zero mentions in the repo's front door.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """Walk up from `start` looking for a directory containing `.git`.

    Falls back to `start` itself if no `.git` is found (e.g. when running
    from a checkout that isn't a full git repo, or in some CI archive
    extraction scenarios).
    """
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def discover_skill_names(repo_root: Path) -> list[str]:
    """Return the sorted list of real skill names under skills/.

    A "real" skill is any immediate subdirectory of skills/ that contains a
    SKILL.md file. This skips non-skill entries such as skills/README.md
    (a file, not a directory) or any stray directory without a SKILL.md.
    """
    skills_dir = repo_root / "skills"
    names: list[str] = []
    if not skills_dir.is_dir():
        return names
    for entry in skills_dir.iterdir():
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            names.append(entry.name)
    return sorted(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root to check (default: walk up from cwd to the "
        "nearest directory containing .git; falls back to cwd).",
    )
    args = parser.parse_args()

    repo_root = (
        Path(args.repo_root).resolve()
        if args.repo_root
        else find_repo_root(Path.cwd())
    )

    readme_path = repo_root / "README.md"
    if not readme_path.is_file():
        print(f"✗ README.md not found at {readme_path}", file=sys.stderr)
        return 1

    skill_names = discover_skill_names(repo_root)
    readme_text = readme_path.read_text(encoding="utf-8")

    missing = [name for name in skill_names if name not in readme_text]

    if missing:
        for name in missing:
            print(name)
        return 1

    print(f"✓ 全部 {len(skill_names)} 个技能都在 README.md 里被提及")
    return 0


if __name__ == "__main__":
    sys.exit(main())
