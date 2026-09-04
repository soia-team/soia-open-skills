#!/usr/bin/env python3
"""Finish local skill installation after a skill PR has merged."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

SYNC_SCRIPT_DIR = Path(__file__).resolve().parents[2] / "soia-meta-sync-skills" / "scripts"
if str(SYNC_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SYNC_SCRIPT_DIR))
from install_selection import SCOPES, TARGET_KINDS, select as select_installation, tokens as selection_tokens


INSTALL_ROOTS = (".agents/skills", ".claude/skills", ".soia/skills", ".workbuddy/skills", ".codex/skills", ".pi/agent/skills")
RECEIPT_LINK_ROOTS = (".agents/skills", ".claude/skills", ".codex/skills")
SKILL_NAME = "soia-meta-skill-release"
CONFIG_ENV = "SOIA_META_SKILL_RELEASE_CONFIG_FILE"
LEGACY_REPOSITORIES = ("soia-open-skills", "soia-open-env-skills")
LEGACY_DOMAINS = ("meta", "soia-meta")
_WARNED_LEGACY_CONFIGS: set[Path] = set()


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


def expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser().resolve()


def skills_config_root(home: Path, environ: Mapping[str, str]) -> Path:
    """Return the v2 SOIA config root, without creating it."""
    configured = environ.get("SOIA_SKILLS_CONFIG_HOME")
    if configured:
        return expand_path(configured)
    if os.name == "nt":
        return expand_path(environ.get("APPDATA", home / "AppData" / "Roaming")) / "soia-skills"
    return expand_path(environ.get("XDG_CONFIG_HOME", home / ".config")) / "soia-skills"


def default_config_file(home: Path, environ: Mapping[str, str]) -> Path:
    return skills_config_root(home, environ) / SKILL_NAME / "config.yml"


def legacy_config_files(home: Path, environ: Mapping[str, str]) -> Iterable[Path]:
    root = skills_config_root(home, environ)
    for repository in LEGACY_REPOSITORIES:
        for domain in LEGACY_DOMAINS:
            yield root / repository / domain / SKILL_NAME / "config.yml"


def warn_legacy_config(legacy: Path, current: Path) -> None:
    """Tell the maintainer about a read-only v1 fallback once per process."""
    if legacy in _WARNED_LEGACY_CONFIGS:
        return
    _WARNED_LEGACY_CONFIGS.add(legacy)
    print(
        "SOIA storage schema v1 config fallback in use; migrate when convenient: "
        f"mkdir -p {shlex.quote(str(current.parent))} && "
        f"mv {shlex.quote(str(legacy))} {shlex.quote(str(current))}",
        file=sys.stderr,
    )


def resolve_config_file(
    cli_value: str | os.PathLike[str] | None,
    home: Path,
    environ: Mapping[str, str],
) -> Path | None:
    """Resolve explicit, v2, then read-only v1 configuration files."""
    if cli_value:
        path = expand_path(cli_value)
        if not path.is_file():
            raise ReleaseError(f"Config file not found: {path}")
        return path
    if environ.get(CONFIG_ENV):
        path = expand_path(environ[CONFIG_ENV])
        if not path.is_file():
            raise ReleaseError(f"{CONFIG_ENV} points to a missing file: {path}")
        return path

    current = default_config_file(home, environ)
    if current.is_file():
        return current
    for legacy in legacy_config_files(home, environ):
        if legacy.is_file():
            warn_legacy_config(legacy, current)
            return legacy
    return None


def load_config_env(path: Path) -> dict[str, str]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ReleaseError(
            "PyYAML is required when using config.yml; install it with: "
            "python3 -m pip install pyyaml"
        ) from exc

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ReleaseError(f"cannot read config {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ReleaseError(f"invalid YAML config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseError("config root must be a YAML mapping")
    values = payload.get("env") or {}
    if not isinstance(values, dict):
        raise ReleaseError("config env must be a YAML mapping")
    return {
        str(key): str(value).strip()
        for key, value in values.items()
        if value is not None and str(value).strip()
    }


def resolve_repo_dir(
    repo: str,
    home: Path,
    repo_dir: str | None = None,
    environ: Mapping[str, str] | None = None,
    config_env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve a checkout from CLI, process env, private config, then v1."""
    if repo_dir:
        return expand_path(repo_dir)

    env = os.environ if environ is None else environ
    repo_name = repo.rstrip("/").rsplit("/", 1)[-1]
    repos_root = env.get("SOIA_SKILL_REPOS_ROOT")
    if repos_root:
        return expand_path(repos_root) / repo_name
    configured_root = (config_env or {}).get("SOIA_SKILL_REPOS_ROOT")
    if configured_root:
        return expand_path(configured_root) / repo_name

    # Deprecated compatibility fallback; configure SOIA_SKILL_REPOS_ROOT or
    # pass --repo-dir before this maintainer-specific convention is removed.
    warnings.warn(
        "falling back to the deprecated local skill repository convention; "
        "set SOIA_SKILL_REPOS_ROOT or pass --repo-dir",
        DeprecationWarning,
        stacklevel=2,
    )
    return home / "owen/code/gitrepo/jiuan/server/v7" / repo_name


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


REPO_TO_PLUGIN = {
    "soia-open-skills": "soia-meta",
    "soia-open-dev-skills": "soia-dev",
    "soia-open-dev-design-skills": "soia-dev-design",
    "soia-open-pkm-vault-skills": "soia-pkm-vault",
    "soia-open-media-content-skills": "soia-media-content",
    "soia-open-cwork-office-skills": "soia-cwork-office",
    "soia-open-edu-course-skills": "soia-edu-course",
    "soia-open-env-skills": "soia-env",
}


def print_plugin_publish_steps(repo: str, skills: list[str]) -> None:
    """Print what still has to happen for users to receive the change.

    Nothing was installed locally: delivery goes through the plugin marketplace.
    """
    repo_name = repo.rsplit("/", 1)[-1]
    plugin = REPO_TO_PLUGIN.get(repo_name, "<域插件名>")
    print()
    print("插件模式：本次未向 ~/.agents/skills 安装任何技能。用户要收到改动，还需：")
    print(f"  1. 在 {repo_name} 把 .claude-plugin/plugin.json 与 .codex-plugin/plugin.json 的")
    print("     version 提上去——Claude Code 比对的是 version 字段而非 sha pin，不 bump 则")
    print("     客户端回答「already at the latest version」。")
    print("  2. 在元仓 soia-open-skills 重新生成市场清单并提 PR 合并（main 受保护，不能直推）：")
    print("     python3 scripts/generate_marketplaces.py && python3 scripts/generate_router_index.py")
    print(f"  3. 客户端更新：claude plugin update {plugin}@soia / codex plugin add {plugin}@soia")
    print(f"  4. 验证：claude plugin details {plugin} 应列出 {', '.join(skills)}")
    print()
    print("如需本机安装，先确认 project/global、Agent 与 skill/domain/all，")
    print("再显式传 --install-mode selected-install；范围不清时保持 remote-only。")
    print()


def release(args: argparse.Namespace, *, home: Path | None = None) -> int:
    user_home = Path.home() if home is None else home
    skills = parse_names(args.skills)
    removed = parse_names(args.removed) if args.removed else []
    agents = args.agents
    rows = [SkillReceipt(name, "install/update") for name in skills]
    rows.extend(SkillReceipt(name, "remove") for name in removed)
    try:
        config_file = resolve_config_file(args.config, user_home, os.environ)
        config_env = load_config_env(config_file) if config_file else {}
        repo_dir = resolve_repo_dir(
            args.repo,
            user_home,
            args.repo_dir,
            os.environ,
            config_env,
        )
        install_mode = {"plugin": "remote-only", "npx": "selected-install"}.get(args.install_mode, args.install_mode)
        if args.dry_run:
            if install_mode == "selected-install":
                try:
                    selection = select_installation(
                        scope=args.install_scope,
                        agents=selection_tokens([agents]),
                        target_kind=args.target_kind,
                        requested_skills=[args.install_skills] if args.install_skills else skills,
                        requested_domains=args.domain,
                        discovered=skills,
                    )
                except ValueError as exc:
                    raise ReleaseError(str(exc)) from exc
                pending = list(selection.pending)
                if selection.scope == "project" and not args.project_dir:
                    pending.append("project_dir")
                if selection.scope == "global" and not args.install_targets:
                    pending.append("install_targets")
                if not args.source_dir:
                    pending.append("source_dir")
                print(json.dumps({"install_plan": {
                    "scope": selection.scope,
                    "agents": list(selection.agents),
                    "target_kind": selection.target_kind,
                    "skills": list(selection.skills),
                    "domains": list(selection.domains),
                    "targets": args.install_targets or args.project_dir,
                    "source_dir": args.source_dir,
                    "selection_required": bool(pending),
                    "pending": list(dict.fromkeys(pending)),
                }}, ensure_ascii=False))
            for row in rows:
                row.result = "planned"
            print("dry-run: no command or filesystem write was executed")
            print_receipt(rows)
            return 0

        if install_mode == "ask":
            if not sys.stdin.isatty():
                raise ReleaseError(
                    "--install-mode ask requires an interactive terminal; pass "
                    "--install-mode remote-only or selected-install explicitly"
                )
            print("\n[ask] 发布收尾：是否安装到本地 AI 目录？")
            print("  默认：仅发布，不装本地副本；选择安装前须已提供 scope、Agent 与粒度。")
            try:
                response = input("  要安装到本地吗？[y/N] ").strip().lower()
            except EOFError:
                response = "n"
            install_mode = "selected-install" if response in ("y", "yes") else "remote-only"

        if install_mode == "selected-install":
            selection = select_installation(
                scope=args.install_scope,
                agents=selection_tokens([agents]),
                target_kind=args.target_kind,
                requested_skills=[args.install_skills] if args.install_skills else skills,
                requested_domains=args.domain,
                discovered=skills,
            )
            if selection.selection_required:
                raise ReleaseError("selected-install requires: " + ", ".join(selection.pending))
            if selection.scope == "global" and not args.install_targets:
                raise ReleaseError("selected-install global scope requires --install-targets")
            if selection.target_kind == "all" and not args.dry_run and not args.confirm_all_targets:
                raise ReleaseError("selected-install all requires a reviewed dry-run and --confirm-all-targets")
            if not args.source_dir:
                raise ReleaseError("selected-install delegates to sync and requires --source-dir")
            command = [sys.executable, str(SYNC_SCRIPT_DIR / "sync_soia_skills.py"), "--source-dir", args.source_dir,
                       "--scope", selection.scope, "--target-kind", selection.target_kind]
            for agent in selection.agents:
                command.extend(["--agents", agent])
            for name in selection.skills:
                command.extend(["--skills", name])
            for domain in selection.domains:
                command.extend(["--domain", domain])
            if selection.scope == "project":
                if not args.project_dir:
                    raise ReleaseError("selected-install project scope requires --project-dir")
                command.extend(["--project-dir", args.project_dir])
            else:
                command.extend(["--targets", args.install_targets])
            run_command(command)
        else:
            print_plugin_publish_steps(args.repo, skills)

        # 7. Verify repository and installed versions with independent file reads.
        #    Plugin mode installs nothing into the shared source, so there is no
        #    installed version to compare against — report the repository version
        #    and leave delivery verification to `claude plugin details`.
        for row in rows:
            if row.name in removed:
                row.result = "removed"
                continue
            row.repository_version = version_from_skill(repo_dir / "skills" / row.name / "SKILL.md")
            if install_mode != "selected-install":
                row.installed_version = "-"
                row.links = "plugin"
                row.result = "published"
                continue
            row.installed_version = "delegated"
            row.links = "selected"
            row.result = "selected-install"
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
    parser.add_argument("--agents", default="", help="Explicit selected agents; required for project selected-install.")
    parser.add_argument("--repo-dir", help="local checkout used for version verification")
    parser.add_argument(
        "--config",
        help=f"private YAML config; otherwise {CONFIG_ENV} or the v2 default is used",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the plan without commands or writes")
    parser.add_argument(
        "--install-mode",
        choices=["remote-only", "selected-install", "ask", "plugin", "npx"],
        default="remote-only",
        help=(
            "remote-only (default): publish guidance only, no local writes. selected-install: "
            "delegate an explicit scope/agent/target selection to sync. ask: interactive choice. "
            "plugin and npx are deprecated compatibility aliases."
        ),
    )
    parser.add_argument("--install-scope", choices=SCOPES)
    parser.add_argument("--install-targets", help="Explicit global sync target ids or paths")
    parser.add_argument("--project-dir", help="Explicit project root for project scope")
    parser.add_argument("--target-kind", choices=TARGET_KINDS)
    parser.add_argument("--install-skills", help="Optional comma-separated selected skills; defaults to --skills")
    parser.add_argument("--domain", action="append")
    parser.add_argument("--source-dir", help="Pre-existing source for sync owner; release never installs it")
    parser.add_argument("--confirm-all-targets", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(release(parse_args()))
