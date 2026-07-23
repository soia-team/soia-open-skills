#!/usr/bin/env python3
"""Synchronize SOIA-managed skills as symlinks to selected agent directories."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


OPTIONAL_SKILLS: list[str] = []

RETIRED_SKILLS = [
    "soia-dev-project-init",
    "soia-gov-ui-validation",
    "soia-gov-tauri-real-device-test",  # merged into soia-gov-ui-design (2026-04-24)
    "soia-brand-guidelines",  # renamed to soia-design-brand-guidelines (2026-04-24)
    "jiuan-docs-v5-project-structure",
    "jiuan-docs-v5-references",
    "soia-pkm-compose-article-draft",
    "soia-pkm-cover-image",
    "soia-pkm-publish-wechat-draft",
    "soia-pkm-publish-x-thread",
    "soia-pkm-publish-x-article",
    "soia-pkm-publish-rednote-card",
    "soia-dev-sync-skills",
    "soia-dev-skill-release",
    "soia-dev-prompt-clarity",
    "soia-dev-ai-cli-upgrade",
    "soia-dev-run-ops-inspection",
    "soia-safe-audit-fix-codebase",
    "soia-safe-track-vulnerability-intel",
]


@dataclass(frozen=True)
class Target:
    id: str
    label: str
    path: Path


@dataclass
class SyncConfig:
    source_dir: str | None
    targets: list[str]
    excludes: dict[str, list[str]]


TARGETS = {
    "soia": Target("soia", "SOIA AI", Path("~/.soia/skills")),
    "workbuddy": Target("workbuddy", "WorkBuddy", Path("~/.workbuddy/skills")),
    "claude": Target("claude", "Claude Code", Path("~/.claude/skills")),
    "codex": Target("codex", "OpenAI Codex", Path("~/.codex/skills")),
    "agy": Target("agy", "Antigravity CLI", Path("~/.gemini/antigravity-cli/skills")),
    "gemini": Target("gemini", "Gemini CLI (non-consumer lanes)", Path("~/.gemini/skills")),
    "kimi": Target("kimi", "Kimi CLI", Path("~/.kimi/skills")),
    "opencode": Target("opencode", "OpenCode", Path("~/.config/opencode/skill")),
    "qwen": Target("qwen", "Qwen Code", Path("~/.qwen/skills")),
    "cursor": Target("cursor", "Cursor", Path("~/.cursor/skills")),
    "qoder": Target("qoder", "QoderCLI", Path("~/.qoder/skills")),
    "copilot": Target("copilot", "GitHub Copilot", Path("~/.copilot/skills")),
    "windsurf": Target("windsurf", "Windsurf", Path("~/.codeium/windsurf/skills")),
    "trae": Target("trae", "Trae", Path("~/.trae/skills")),
    "openclaw": Target("openclaw", "OpenClaw", Path("~/.openclaw/skills")),
}

DEFAULT_ORDER = [
    "claude",
    "qoder",
    "copilot",
    "cursor",
    "agy",
    "gemini",
    "kimi",
    "codex",
    "opencode",
    "windsurf",
    "trae",
    "qwen",
    "openclaw",
]


def expanded(path: Path) -> Path:
    return path.expanduser()


def display_path(path: Path) -> str:
    resolved = path.expanduser()
    home = Path.home()
    try:
        rel = resolved.relative_to(home)
    except ValueError:
        return str(resolved)
    if str(rel) == ".":
        return "~"
    return f"~/{rel.as_posix()}"


def default_source_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_file() -> Path:
    override = os.environ.get("SOIA_META_SYNC_SKILLS_CONFIG_FILE")
    if override:
        return Path(override).expanduser()
    if os.name == "nt" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"])
    else:
        base = Path.home() / ".config"
    return base / "soia-skills" / "soia-meta-sync-skills" / "config.yml"


def clean_config_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        if value[0] == '"':
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return value[1:-1]
            return parsed if isinstance(parsed, str) else value[1:-1]
        return value[1:-1].replace("''", "'")
    return value


def parse_inline_config_list(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError(f"expected an inline YAML list, got: {value}")
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [clean_config_scalar(item) for item in inner.split(",") if item.strip()]


def split_config_mapping(value: str) -> tuple[str, str] | None:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == ":" and quote is None:
            return value[:index], value[index + 1:]
    return None


def load_config(path: Path) -> SyncConfig:
    if not path.is_file():
        return SyncConfig(None, [], {})
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read config file {display_path(path)}: {exc}") from exc

    source_dir: str | None = None
    targets: list[str] = []
    excludes: dict[str, list[str]] = {}
    section: str | None = None
    exclude_target: str | None = None
    for line_no, raw in enumerate(lines, start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            section = None
            exclude_target = None
            mapping = split_config_mapping(stripped)
            if mapping is None:
                raise ValueError(f"invalid config line {line_no}: expected key: value")
            key, value = mapping
            key = key.strip()
            value = value.strip()
            if key == "source_dir":
                source_dir = clean_config_scalar(value) or None
            elif key in {"targets", "excludes"}:
                section = key
                if value and value != "{}":
                    raise ValueError(f"invalid config line {line_no}: {key} must be a YAML block")
            continue
        if section == "targets" and stripped.startswith("- "):
            target = clean_config_scalar(stripped[2:])
            if target:
                targets.append(target)
            continue
        if section == "excludes":
            mapping = split_config_mapping(stripped)
            if indent == 2 and mapping is not None:
                raw_target, value = mapping
                exclude_target = clean_config_scalar(raw_target)
                if not exclude_target:
                    raise ValueError(f"invalid config line {line_no}: empty exclude target")
                excludes[exclude_target] = parse_inline_config_list(value)
                continue
            if indent >= 4 and stripped.startswith("- ") and exclude_target:
                skill = clean_config_scalar(stripped[2:])
                if skill:
                    excludes[exclude_target].append(skill)
                continue
        raise ValueError(f"invalid config line {line_no}: unsupported YAML shape")

    for target, names in excludes.items():
        invalid = [name for name in names if not is_managed_soia_skill(name)]
        if invalid:
            raise ValueError(
                f"config excludes for {target} contain non-SOIA names: {', '.join(invalid)}"
            )
        excludes[target] = list(dict.fromkeys(names))
    return SyncConfig(source_dir, list(dict.fromkeys(targets)), excludes)


def save_config(path: Path, config: SyncConfig) -> None:
    lines = ["# User-owned defaults. CLI arguments take precedence.", "schema_version: 3"]
    if config.source_dir:
        lines.append(f"source_dir: {json.dumps(config.source_dir, ensure_ascii=False)}")
    if config.targets:
        lines.append("targets:")
        lines.extend(f"  - {json.dumps(target, ensure_ascii=False)}" for target in config.targets)
    lines.append("excludes:")
    if config.excludes:
        for target in sorted(config.excludes):
            lines.append(f"  {json.dumps(target, ensure_ascii=False)}:")
            lines.extend(
                f"    - {json.dumps(skill, ensure_ascii=False)}"
                for skill in sorted(set(config.excludes[target]))
            )
    else:
        lines[-1] = "excludes: {}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Audit log: this sync tool creates/replaces symlinks and removes retired or
# dangling managed entries, i.e. real system-state changes, so a trace belongs in XDG state
# (not TMPDIR, which is for disposable run reports) — see SKILL_SPEC.md "Script
# Disk-Write Destinations" category B.
AUDIT_LOG_RETENTION = 20


def audit_log_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or "~/.local/state"
    return Path(base).expanduser() / "soia-meta-sync-skills"


def rotate_audit_logs(log_dir: Path, keep: int) -> None:
    """Keep at most `keep` existing sync-*.log files, deleting the oldest first."""
    if not log_dir.is_dir():
        return
    logs = sorted(log_dir.glob("sync-*.log"))  # timestamped names sort chronologically
    excess = len(logs) - keep
    if excess <= 0:
        return
    for stale in logs[:excess]:
        try:
            stale.unlink()
        except OSError:
            pass


def parse_target_tokens(values: list[str] | None) -> list[str]:
    if not values:
        return []
    tokens: list[str] = []
    for raw in values:
        tokens.extend(token.strip() for token in raw.split(",") if token.strip())
    return tokens


def target_from_token(token: str) -> Target:
    if token in TARGETS:
        target = TARGETS[token]
        return Target(target.id, target.label, expanded(target.path))
    path = expanded(Path(token))
    if path.is_absolute() or token.startswith((".", "~")):
        return Target("custom", "Custom path", path)
    raise ValueError(f"unknown target id or path: {token}")


def default_targets() -> list[Target]:
    targets: list[Target] = []
    for target_id in DEFAULT_ORDER:
        target = target_from_token(target_id)
        if target.path.exists() or (target.id == "agy" and shutil.which("agy") is not None):
            targets.append(target)
    return targets


def selected_targets(tokens: list[str]) -> list[Target]:
    targets = default_targets() if not tokens else [target_from_token(token) for token in tokens]
    deduped: list[Target] = []
    seen: set[Path] = set()
    for target in targets:
        resolved = target.path.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(target)
    return deduped


def target_config_key(target: Target) -> str:
    target_path = target.path.resolve(strict=False)
    for target_id, known in TARGETS.items():
        if expanded(known.path).resolve(strict=False) == target_path:
            return target_id
    return display_path(target.path)


def ensure_not_source_target(source_dir: Path, targets: list[Target]) -> None:
    source_resolved = source_dir.resolve(strict=False)
    for target in targets:
        if target.path.resolve(strict=False) == source_resolved:
            raise ValueError(f"target must not equal source-dir: {display_path(target.path)}")


def has_skill_md(path: Path) -> bool:
    return path.is_dir() and (path / "SKILL.md").is_file()


def is_managed_soia_skill(name: str) -> bool:
    """Treat every installed `soia-*` skill as managed.

    The shared source may contain skills from both soia-open-skills and
    soia-private-skills. Repository ownership controls publishing, while this
    script controls target links; excluding public PKM names here made a full
    sync silently incomplete and broke explicit --skills requests.
    """
    return name.startswith("soia-")


def discover_skills(source_dir: Path, include_optional: bool) -> list[str]:
    skills: list[str] = []
    for child in sorted(source_dir.iterdir(), key=lambda item: item.name):
        name = child.name
        if not has_skill_md(child):
            continue
        if name in OPTIONAL_SKILLS:
            if include_optional:
                skills.append(name)
            continue
        if is_managed_soia_skill(name):
            skills.append(name)
    return skills


def select_skills(discovered: list[str], requested: list[str]) -> list[str]:
    if not requested:
        return discovered
    available = set(discovered)
    missing = [name for name in requested if name not in available]
    if missing:
        raise ValueError(f"requested skills not found in source-dir: {', '.join(missing)}")
    return list(dict.fromkeys(requested))


def parse_hard_deps(skill_dir: Path) -> list[str]:
    """Read `dependencies.hard` from a skill's SKILL.md frontmatter (stdlib only).

    Supported forms inside the frontmatter block:
        dependencies:
          hard: [a, b]
    and
        dependencies:
          hard:
            - a
            - b
    Everything else in `dependencies` (optional/external) is ignored here:
    optional deps are runtime-reminder territory, not install-closure input.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return []
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if not lines or lines[0].strip() != "---":
        return []

    def clean(token: str) -> str:
        return token.strip().strip("'\"")

    deps: list[str] = []
    in_dependencies = False
    in_hard_list = False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if indent == 0:
            in_dependencies = stripped == "dependencies:"
            in_hard_list = False
            continue
        if not in_dependencies:
            continue
        if in_hard_list:
            if stripped.startswith("- "):
                name = clean(stripped[2:])
                if name:
                    deps.append(name)
                continue
            in_hard_list = False  # dedent or sibling key ends the block list
        if stripped.startswith("hard:"):
            value = stripped[len("hard:"):].strip()
            if value.startswith("[") and value.endswith("]"):
                deps.extend(
                    name for name in (clean(t) for t in value[1:-1].split(",")) if name
                )
            elif not value:
                in_hard_list = True
    return list(dict.fromkeys(deps))


def expand_with_hard_deps(
    selected: list[str], source_dir: Path, discovered: list[str]
) -> tuple[list[str], dict[str, str], list[tuple[str, str]]]:
    """Expand a skill selection with its transitive hard-dependency closure.

    Returns (expanded selection, {added_dep: first_requirer}, [(missing_dep, requirer)]).
    Deps absent from the source-dir are reported, not linked: they usually live
    in the sibling repo and need `npx skills add` first.
    """
    available = set(discovered)
    expanded = list(selected)
    seen = set(selected)
    added: dict[str, str] = {}
    missing: list[tuple[str, str]] = []
    queue = list(selected)
    while queue:
        current = queue.pop(0)
        for dep in parse_hard_deps(source_dir / current):
            if dep in seen:
                continue
            seen.add(dep)
            if dep in available:
                expanded.append(dep)
                added[dep] = current
                queue.append(dep)
            else:
                missing.append((dep, current))
    return expanded, added, missing


def existing_path(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def remove_path(path: Path, dry_run: bool) -> bool:
    if not existing_path(path):
        return False
    if not dry_run:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
    return True


def symlink_target(source: Path, dest: Path) -> Path:
    target = os.path.relpath(source.resolve(strict=False), dest.parent.resolve(strict=False))
    return Path(target)


def link_skill(source: Path, dest: Path, dry_run: bool) -> Path:
    target = symlink_target(source, dest)
    if not dry_run:
        dest.symlink_to(target, target_is_directory=True)
    return target


def prune_dangling_soia_symlinks(
    target_dir: Path, dry_run: bool, planned_names: set[str]
) -> list[Path]:
    """Remove first-level dangling symlinks not already repaired by this sync."""
    if not target_dir.is_dir():
        return []

    pruned: list[Path] = []
    for entry in sorted(target_dir.iterdir(), key=lambda item: item.name):
        if entry.name in planned_names or not entry.name.startswith("soia-"):
            continue
        if not entry.is_symlink() or entry.exists():
            continue
        if not dry_run:
            entry.unlink()
        pruned.append(entry)
    return pruned


def sync(
    source_dir: Path,
    targets: list[Target],
    skills: list[str],
    dry_run: bool,
    cleanup_retired: bool = True,
    prune: bool = True,
    excludes_by_target: dict[str, set[str]] | None = None,
) -> int:
    linked = 0
    cleaned = 0
    overwritten = 0
    created_targets = 0
    excluded_unlinked = 0
    excludes_by_target = excludes_by_target or {}

    # Audit log setup happens before any stdout output; log content is additive
    # and never changes what already gets printed below.
    log_dir = audit_log_dir()
    rotate_audit_logs(log_dir, keep=AUDIT_LOG_RETENTION - 1)
    audit_lines: list[str] = [
        f"run_time: {datetime.now().isoformat(timespec='seconds')}",
        f"mode: {'dry-run' if dry_run else 'write'}",
        f"source_dir: {source_dir}",
    ]

    print(f"Mode: {'DRY-RUN' if dry_run else 'WRITE'}")
    print(f"Source: {display_path(source_dir)}")
    retired_count = len(RETIRED_SKILLS) if cleanup_retired else 0
    print(f"Skills: {len(skills)} selected, {retired_count} retired cleanup names")
    print("Install mode: symlink")
    print(f"Targets: {len(targets)}")

    for target in targets:
        print(f"\n[{target.id}] {target.label}: {display_path(target.path)}")
        audit_lines.append(f"target {target.id}: {target.path}")
        target_excludes = excludes_by_target.get(target_config_key(target), set())
        target_skills = [skill for skill in skills if skill not in target_excludes]
        if target_excludes:
            print(f"  excludes: {', '.join(sorted(target_excludes))}")
            audit_lines.append(f"  excludes: {', '.join(sorted(target_excludes))}")
        if not target.path.exists():
            created_targets += 1
            print("  create target directory")
            if not dry_run:
                target.path.mkdir(parents=True, exist_ok=True)
            audit_lines.append(f"  created target directory: {target.path}")

        if cleanup_retired:
            for retired in RETIRED_SKILLS:
                retired_path = target.path / retired
                if remove_path(retired_path, dry_run):
                    cleaned += 1
                    print(f"  remove retired: {retired}")
                    audit_lines.append(f"  removed retired entry: {retired_path}")

        for skill in sorted(target_excludes):
            excluded_path = target.path / skill
            if excluded_path.is_symlink():
                if not dry_run:
                    excluded_path.unlink()
                excluded_unlinked += 1
                print(f"  unlink excluded: {skill}")
                audit_lines.append(f"  unlinked excluded symlink: {excluded_path}")
            elif existing_path(excluded_path):
                print(f"  keep excluded non-symlink: {skill}")
                audit_lines.append(f"  kept excluded non-symlink: {excluded_path}")

        for skill in target_skills:
            source = source_dir / skill
            dest = target.path / skill
            replaced = remove_path(dest, dry_run)
            if replaced:
                overwritten += 1
                action = "relink"
            else:
                action = "link"
            target_path = link_skill(source, dest, dry_run)
            print(f"  {action}: {skill} -> {target_path}")
            audit_lines.append(
                f"  {'replaced' if replaced else 'created'} symlink: {dest} -> {target_path}"
            )
            linked += 1

        if prune:
            planned_names = set(target_skills) | target_excludes
            if cleanup_retired:
                planned_names.update(RETIRED_SKILLS)
            for dangling_path in prune_dangling_soia_symlinks(
                target.path, dry_run, planned_names
            ):
                cleaned += 1
                print(f"  prune dangling symlink: {dangling_path.name}")
                audit_lines.append(f"  unlinked dangling symlink: {dangling_path}")

    print("\nSummary:")
    print(f"- target dirs created: {created_targets}")
    print(f"- retired dirs cleaned: {cleaned}")
    print(f"- overwritten skill entries: {overwritten}")
    print(f"- symlinked skill entries: {linked}")
    print(f"- excluded symlinks removed: {excluded_unlinked}")
    print("- unrelated target entries: untouched")

    audit_lines.append(
        "summary: "
        f"target_dirs_created={created_targets} "
        f"retired_dirs_cleaned={cleaned} "
        f"overwritten_skill_entries={overwritten} "
        f"symlinked_skill_entries={linked} "
        f"excluded_symlinks_removed={excluded_unlinked}"
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    # Microseconds prevent a dry-run followed immediately by write mode from
    # silently overwriting the first audit record in the same second.
    log_path = log_dir / f"sync-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')}.log"
    log_path.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Symlink SOIA skills to selected targets, clean retired names, and prune dangling "
            "soia-* symlinks."
        )
    )
    parser.add_argument(
        "--source-dir",
        help=(
            "Directory containing SOIA skill folders. CLI overrides config; otherwise defaults "
            "to the installed shared skill directory inferred from this script."
        ),
    )
    parser.add_argument(
        "--targets",
        action="append",
        help="Comma-separated target ids or custom paths. Defaults to 'soia' plus existing known target dirs.",
    )
    parser.add_argument(
        "--skills",
        action="append",
        help="Comma-separated managed skill names to sync. Omit for the full discovered set.",
    )
    parser.add_argument(
        "--exclude-skills",
        action="append",
        help=(
            "Comma-separated soia-* skill names to skip and unlink for every selected target "
            "in this run."
        ),
    )
    parser.add_argument(
        "--save-excludes",
        action="store_true",
        help="Merge --exclude-skills into the private config for each selected target.",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        help="Private config path; overrides SOIA_META_SYNC_SKILLS_CONFIG_FILE and the default.",
    )
    parser.add_argument(
        "--optional",
        action="store_true",
        help="Include optional non-SOIA skills. No optional entries are currently bundled.",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Skip hard-dependency closure when --skills is given; sync exactly the named skills.",
    )
    parser.add_argument(
        "--no-prune",
        action="store_true",
        help="Keep dangling soia-* symlinks in target directories instead of pruning them.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned creates, removes, and symlinks without writing.",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="List supported target ids and paths, then exit.",
    )
    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="List discovered managed skills from source-dir, then exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config_path = (args.config_file or default_config_file()).expanduser()
    try:
        config = load_config(config_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list_targets:
        for target_id in DEFAULT_ORDER:
            target = target_from_token(target_id)
            exists = "exists" if target.path.exists() else "missing"
            print(f"{target.id:10} {display_path(target.path):34} {exists}  {target.label}")
        return 0

    source_value = args.source_dir or config.source_dir or str(default_source_dir())
    source_dir = expanded(Path(source_value))
    if not source_dir.is_dir():
        print(f"error: source-dir is not a directory: {source_dir}", file=sys.stderr)
        return 2

    discovered_skills = discover_skills(source_dir, args.optional)
    requested_skill_tokens = parse_target_tokens(args.skills)
    cli_excludes = parse_target_tokens(args.exclude_skills)
    invalid_excludes = [name for name in cli_excludes if not is_managed_soia_skill(name)]
    if invalid_excludes:
        print(
            f"error: --exclude-skills accepts only soia-* names: {', '.join(invalid_excludes)}",
            file=sys.stderr,
        )
        return 2
    if args.save_excludes and not cli_excludes:
        print("error: --save-excludes requires --exclude-skills", file=sys.stderr)
        return 2
    if args.save_excludes and args.dry_run:
        print("error: --save-excludes cannot be combined with --dry-run", file=sys.stderr)
        return 2
    try:
        skills = select_skills(discovered_skills, requested_skill_tokens)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not skills:
        print(f"error: no SOIA skills found in source-dir: {source_dir}", file=sys.stderr)
        return 2

    # Hard-dependency closure: single-skill sync pulls in declared hard deps so a
    # customer never gets a skill without the skills it cannot run without.
    if requested_skill_tokens and not args.no_deps:
        skills, added_deps, missing_deps = expand_with_hard_deps(
            skills, source_dir, discovered_skills
        )
        for dep, requirer in added_deps.items():
            print(f"note: auto-including hard dependency: {dep} (required by {requirer})")
    else:
        # Full sync links everything discovered anyway; still surface cross-repo
        # gaps where a skill declares a hard dep the shared source doesn't have.
        _, _, missing_deps = expand_with_hard_deps(skills, source_dir, discovered_skills)
    for dep, requirer in missing_deps:
        print(
            f"warning: hard dependency not in source-dir: {dep} (required by {requirer}). "
            f"Install it first, e.g. `npx skills add soia-team/soia-open-skills -g -a '*' -s {dep} -y` "
            "(or the soia-private-skills package), then re-run this sync.",
            file=sys.stderr,
        )

    if args.list_skills:
        for skill in skills:
            print(skill)
        return 0

    cli_target_tokens = parse_target_tokens(args.targets)
    tokens = cli_target_tokens or config.targets
    try:
        targets = selected_targets(tokens)
        ensure_not_source_target(source_dir, targets)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    excludes_by_target: dict[str, set[str]] = {}
    for target in targets:
        key = target_config_key(target)
        persistent = set(config.excludes.get(key, []))
        excludes_by_target[key] = persistent | set(cli_excludes)

    if args.save_excludes:
        for target in targets:
            key = target_config_key(target)
            config.excludes[key] = sorted(excludes_by_target[key])
        try:
            save_config(config_path, config)
        except OSError as exc:
            print(f"error: cannot save config file {display_path(config_path)}: {exc}", file=sys.stderr)
            return 2
        print(f"saved excludes: {display_path(config_path)}")

    return sync(
        source_dir,
        targets,
        skills,
        args.dry_run,
        cleanup_retired=not bool(requested_skill_tokens),
        prune=not args.no_prune,
        excludes_by_target=excludes_by_target,
    )


if __name__ == "__main__":
    raise SystemExit(main())
