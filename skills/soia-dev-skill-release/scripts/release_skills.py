#!/usr/bin/env python3
"""Finish local skill installation after a skill PR has merged."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INSTALL_ROOTS = (".agents/skills", ".claude/skills", ".soia/skills", ".workbuddy/skills", ".codex/skills")
RECEIPT_LINK_ROOTS = (".agents/skills", ".claude/skills", ".codex/skills")


class ReleaseError(RuntimeError):
    """A release step failed; callers report the completed boundary."""


@dataclass
class SkillReceipt:
    name: str
    action: str
    repository_version: str = "-"
    installed_version: str = "-"
    links: str = "-"
    result: str = "pending"


def parse_names(value: str) -> list[str]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    if not names:
        raise argparse.ArgumentTypeError("must contain at least one skill name")
    return list(dict.fromkeys(names))


def home_path(home: Path, relative: str) -> Path:
    return home / relative


def installed_skill_dir(home: Path, name: str) -> Path:
    return home_path(home, ".agents/skills") / name


def default_repo_dir(repo: str, home: Path) -> Path:
    """Use the documented local checkout convention, with --repo-dir as an escape hatch."""
    return home / "owen/code/gitrepo/jiuan/server/v7" / repo.rsplit("/", 1)[-1]


def version_from_skill(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ReleaseError(f"cannot read {path}: {exc}") from exc
    if not lines or lines[0].strip() != "---":
        raise ReleaseError(f"missing frontmatter in {path}")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    raise ReleaseError(f"missing version in {path}")


def run_command(command: list[str]) -> None:
    try:
        completed = subprocess.run(command, check=False, text=True, capture_output=True)
    except OSError as exc:
        raise ReleaseError(f"cannot run {' '.join(command)}: {exc}") from exc
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReleaseError(f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}")


def remove_entry(path: Path, dry_run: bool) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if dry_run:
        return True
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
    return True


def remove_old_skills(home: Path, names: Iterable[str], dry_run: bool) -> dict[str, int]:
    removed: dict[str, int] = {}
    for name in names:
        count = 0
        for root in INSTALL_ROOTS:
            if remove_entry(home_path(home, root) / name, dry_run):
                count += 1
        removed[name] = count
    return removed


def relative_link(source: Path, destination: Path) -> str:
    return os.path.relpath(source.resolve(strict=False), destination.parent.resolve(strict=False))


def fill_codex_links(home: Path, dry_run: bool) -> list[str]:
    source_root = home_path(home, ".agents/skills")
    target_root = home_path(home, ".codex/skills")
    if not source_root.is_dir():
        return []
    created: list[str] = []
    for source in sorted(source_root.iterdir(), key=lambda item: item.name):
        # Only installed skills are linked. Historical evidence directories do
        # not carry SKILL.md and intentionally remain outside Codex discovery.
        if not source.is_dir() or not (source / "SKILL.md").is_file():
            continue
        destination = target_root / source.name
        if destination.exists() or destination.is_symlink():
            continue
        created.append(source.name)
        if not dry_run:
            target_root.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(relative_link(source, destination), target_is_directory=True)
    return created


def load_lock(home: Path) -> dict[str, object]:
    path = home / ".agents/.skill-lock.json"
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot read skill lock {path}: {exc}") from exc
    skills = content.get("skills") if isinstance(content, dict) else None
    if not isinstance(skills, dict):
        raise ReleaseError("skill lock has no skills mapping")
    return skills


def verify_lock(home: Path, repo: str, skills: Iterable[str], removed: Iterable[str]) -> None:
    entries = load_lock(home)
    missing = [name for name in skills if not isinstance(entries.get(name), dict) or entries[name].get("source") != repo]
    lingering = [name for name in removed if name in entries]
    if missing or lingering:
        parts: list[str] = []
        if missing:
            parts.append("missing/wrong source: " + ", ".join(missing))
        if lingering:
            parts.append("removed names still in lock: " + ", ".join(lingering))
        raise ReleaseError("lock reconciliation failed; " + "; ".join(parts))


def link_status(home: Path, name: str) -> str:
    states = []
    for root in RECEIPT_LINK_ROOTS:
        path = home_path(home, root) / name
        states.append(f"{root.split('/')[0][1:]}={'✓' if path.is_symlink() else '—'}")
    return "; ".join(states)


def print_receipt(rows: Iterable[SkillReceipt]) -> None:
    print("| 技能 | 动作 | 仓库版本 | 装机版本 | 软链(三处) | 结果 |")
    print("| --- | --- | --- | --- | --- | --- |")
    for row in rows:
        print(f"| {row.name} | {row.action} | {row.repository_version} | {row.installed_version} | {row.links} | {row.result} |")


def release(args: argparse.Namespace, *, home: Path | None = None) -> int:
    user_home = Path.home() if home is None else home
    skills = parse_names(args.skills)
    removed = parse_names(args.removed) if args.removed else []
    agents = args.agents
    rows = [SkillReceipt(name, "install/update") for name in skills]
    rows.extend(SkillReceipt(name, "remove") for name in removed)
    repo_dir = Path(args.repo_dir).expanduser() if args.repo_dir else default_repo_dir(args.repo, user_home)

    if args.dry_run:
        for row in rows:
            row.result = "planned"
        print("dry-run: no command or filesystem write was executed")
        print_receipt(rows)
        return 0

    try:
        # 1. Install each requested skill so a failure names its exact target.
        for name in skills:
            agent_flags=[flag for a in agents.split(",") for flag in ("-a", a.strip()) if a.strip()]
            run_command(["npx", "skills", "add", args.repo, "-g", *agent_flags, "-s", name, "-y"])

        # 2. Remove renamed/deleted skills in both skills.sh and all managed homes.
        if removed:
            for name in removed:
                agent_flags=[flag for a in agents.split(",") for flag in ("-a", a.strip()) if a.strip()]
                run_command(["npx", "skills", "remove", args.repo, "-g", *agent_flags, "-s", name, "-y"])
            remove_old_skills(user_home, removed, dry_run=False)

        # 3. Update cross-referenced skills.
        run_command(["npx", "skills", "update", "-g", "-y"])

        # 4. Fill the Codex discovery directory from the installed canonical source.
        fill_codex_links(user_home, dry_run=False)

        # 5. Keep SOIA and WorkBuddy consumer links in sync.
        sync_script = installed_skill_dir(user_home, "soia-dev-sync-skills") / "scripts/sync_soia_skills.py"
        run_command([sys.executable, str(sync_script), "--targets", "soia,workbuddy"])

        # 6. Verify the installer lock only after all installer-mutating commands.
        verify_lock(user_home, args.repo, skills, removed)

        # 7. Verify repository and installed versions with independent file reads.
        for row in rows:
            if row.name in removed:
                row.result = "removed"
                continue
            row.repository_version = version_from_skill(repo_dir / "skills" / row.name / "SKILL.md")
            row.installed_version = version_from_skill(installed_skill_dir(user_home, row.name) / "SKILL.md")
            row.links = link_status(user_home, row.name)
            if row.repository_version != row.installed_version:
                raise ReleaseError(f"version mismatch for {row.name}: {row.repository_version} != {row.installed_version}")
            row.result = "ok"
    except ReleaseError as exc:
        print(f"release stopped: {exc}", file=sys.stderr)
        print_receipt(rows)
        return 1

    print_receipt(rows)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="skills.sh source, for example owner/name")
    parser.add_argument("--skills", required=True, help="comma-separated installed skill names")
    parser.add_argument("--removed", help="comma-separated legacy skill names to remove")
    parser.add_argument("--agents", default="claude-code,codex", help="skills.sh agent list")
    parser.add_argument("--repo-dir", help="local checkout used for version verification")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without commands or writes")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(release(parse_args()))
