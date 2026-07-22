#!/usr/bin/env python3
"""Generate skill catalog docs and optional SOIA registry manifests."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


GROUPS = [
    ("soia-pkm-", "PKM", "content"),
    ("soia-cwork-", "CWork", "cwork"),
    ("soia-dev-", "Development", "development"),
    ("soia-gov-", "Governance", "governance"),
    ("soia-design-", "Design", "design"),
    ("soia-meta-", "Meta", "development"),
]


@dataclass(frozen=True)
class SkillEntry:
    name: str
    description: str
    path: Path
    display_name: str = ""
    short_description: str = ""
    default_prompt: str = ""
    version: str = "1.0.0"
    tags: tuple[str, ...] = ()
    category: str = "general"
    activate: str = ""
    compatibility: tuple[str, ...] = ()


def clean_scalar(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def split_inline_list(raw: str) -> tuple[str, ...]:
    value = clean_scalar(raw)
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if not value:
        return ()
    return tuple(clean_scalar(part) for part in value.split(",") if clean_scalar(part))


def parse_frontmatter(skill_md: Path) -> dict[str, object]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, object] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value.startswith("["):
            data[key] = split_inline_list(value)
        else:
            data[key] = clean_scalar(value)
    return data


def parse_openai_yaml(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data: dict[str, str] = {}
    in_interface = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\S", line):
            in_interface = line.strip() == "interface:"
            continue
        if not in_interface:
            continue
        match = re.match(r"\s+([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if match:
            data[match.group(1)] = clean_scalar(match.group(2))
    return data


def is_placeholder(value: str) -> bool:
    return not value or "<" in value or "your-skill" in value or "TODO" in value


def infer_group(name: str) -> tuple[str, str]:
    for prefix, group, category in GROUPS:
        if name.startswith(prefix):
            return group, category
    return "Other", "general"


def infer_tags(name: str, category: str, raw_tags: tuple[str, ...]) -> tuple[str, ...]:
    if raw_tags:
        return raw_tags
    parts = [part for part in name.split("-") if part and part != "soia"]
    tags = [category]
    tags.extend(part for part in parts if part not in tags)
    return tuple(tags)


def load_skills(root: Path) -> list[SkillEntry]:
    skills_dir = root / "skills"
    entries: list[SkillEntry] = []
    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        fm = parse_frontmatter(skill_md)
        ui = parse_openai_yaml(skill_dir / "agents" / "openai.yaml")
        name = str(fm.get("name") or skill_dir.name)
        _, inferred_category = infer_group(name)
        description = str(fm.get("description") or "").strip()
        short_description = ui.get("short_description", "").strip()
        if is_placeholder(short_description):
            short_description = ""
        display_name = ui.get("display_name", "").strip()
        if is_placeholder(display_name):
            display_name = ""
        default_prompt = ui.get("default_prompt", "").strip()
        if is_placeholder(default_prompt):
            default_prompt = ""
        raw_tags = fm.get("tags")
        tags = raw_tags if isinstance(raw_tags, tuple) else ()
        category = str(fm.get("category") or inferred_category)
        compatibility = fm.get("compatibility")
        entries.append(
            SkillEntry(
                name=name,
                description=description,
                path=skill_dir,
                display_name=display_name,
                short_description=short_description,
                default_prompt=default_prompt,
                version=str(fm.get("version") or "1.0.0"),
                tags=infer_tags(name, category, tags),
                category=category,
                activate=str(fm.get("activate") or ""),
                compatibility=compatibility if isinstance(compatibility, tuple) else (),
            )
        )
    return entries


def markdown_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip()


def catalog_description(entry: SkillEntry, limit: int = 220) -> str:
    value = entry.short_description or entry.description
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\b(?:\d{2}_[^/\s，。；|`]+/)+[^\s，。；|`]*/?", "<vault-path>", value)
    for marker in ("覆盖 PROPOSAL-", "PROPOSAL-", "Triggers:", "Triggers：", "Trigger:", "触发："):
        index = value.find(marker)
        if index > 0:
            value = value[:index].rstrip(" ，。.;；")
    if len(value) > limit:
        value = value[:limit].rstrip(" ，。.;；") + "..."
    return value


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def infer_display_name(name: str) -> str:
    labels = {
        "ai": "AI",
        "api": "API",
        "cli": "CLI",
        "git": "Git",
        "github": "GitHub",
        "gzh": "GZH",
        "pkm": "PKM",
        "ui": "UI",
        "x": "X",
    }
    parts = [part for part in name.split("-") if part and part != "soia"]
    return " ".join(labels.get(part, part.capitalize()) for part in parts)


def openai_yaml_for(entry: SkillEntry) -> str:
    short_description = catalog_description(entry, limit=160)
    default_prompt = f"Use {entry.name}: {short_description}"
    return "\n".join(
        [
            "interface:",
            f"  display_name: {yaml_string(infer_display_name(entry.name))}",
            f"  short_description: {yaml_string(short_description)}",
            f"  default_prompt: {yaml_string(default_prompt)}",
            "",
        ]
    )


def write_missing_openai(entries: list[SkillEntry]) -> int:
    written = 0
    for entry in entries:
        target = entry.path / "agents" / "openai.yaml"
        if target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(openai_yaml_for(entry), encoding="utf-8")
        written += 1
    return written


def resolve_repo_name(root: Path) -> str:
    """Repo name used in catalog labels.

    Prefer the git `origin` remote so the generated output is identical no
    matter what the checkout directory is called — a worktree or a clone into
    an arbitrarily-named directory must not bake the wrong name into
    skills/README.md (which would then read as "stale" in CI, whose checkout
    dir is always the real repo name). Fall back to the directory name only
    when git or an origin remote is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return root.name
    if result.returncode != 0:
        return root.name
    url = result.stdout.strip()
    if not url:
        return root.name
    # Take the last path component of either an https or scp-style remote URL:
    # https://github.com/soia-team/soia-open-skills.git  -> soia-open-skills
    # git@github.com:soia-team/soia-open-skills.git       -> soia-open-skills
    tail = url.rstrip("/")
    for sep in ("/", ":"):
        if sep in tail:
            tail = tail.rsplit(sep, 1)[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail or root.name


def repo_title(repo: str) -> str:
    if "private" in repo:
        return "SOIA Private Skills Catalog"
    if "open" in repo:
        return "SOIA Open Skills Catalog"
    return "SOIA Skills Catalog"


def render_readme(root: Path, entries: list[SkillEntry]) -> str:
    repo = resolve_repo_name(root)
    lines = [
        f"# {repo_title(repo)}",
        "",
        "> Generated from `skills/*/SKILL.md` and optional `agents/openai.yaml`.",
        "> Do not edit by hand. Run `python3 scripts/generate_skill_catalog.py`.",
        f"> Discoverable by `npx skills add soia-team/{repo} -l`: {len(entries)} skills.",
        "",
        "## Source Fields",
        "",
        "- `SKILL.md` is the canonical cross-agent instruction file. Capabilities, dependencies, setup, workflow steps, logs, and completion summaries must live there.",
        "- `agents/openai.yaml` is optional UI/catalog metadata for OpenAI/Codex-style surfaces and SOIA registry display: `display_name`, `short_description`, and `default_prompt`.",
        "- Claude Code and generic skills.sh-compatible agents must be assumed to consume `SKILL.md`; do not put required workflow steps only in `agents/openai.yaml`.",
        "- Legacy `metadata.json` files are not used to generate this catalog.",
        "",
    ]
    grouped: dict[str, list[SkillEntry]] = {}
    for entry in entries:
        group, _ = infer_group(entry.name)
        grouped.setdefault(group, []).append(entry)
    ordered_groups = [group for _, group, _ in GROUPS if group in grouped]
    ordered_groups.extend(group for group in sorted(grouped) if group not in ordered_groups)
    for group in ordered_groups:
        lines.extend(
            [
                f"## {group}",
                "",
                "| Skill | Description | Default Prompt |",
                "|---|---|---|",
            ]
        )
        for entry in sorted(grouped[group], key=lambda item: item.name):
            description = catalog_description(entry)
            prompt = entry.default_prompt
            lines.append(
                f"| [`{entry.name}`](./{entry.name}/) | {markdown_cell(description)} | {markdown_cell(prompt)} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Registry Export",
            "",
            "Generate v7 SOIA registry manifests from the same sources when needed:",
            "",
            "```bash",
            "python3 scripts/generate_skill_catalog.py --registry-out <soia-repo>/runtime/registry/skills",
            "```",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def registry_manifest(entry: SkillEntry) -> dict[str, object]:
    manifest: dict[str, object] = {
        "name": entry.name,
        "description": catalog_description(entry),
        "version": entry.version,
        "category": entry.category,
        "tags": list(entry.tags),
        "compatibility": list(entry.compatibility or ("codex", "claude")),
        "maintainer": "soia-team",
        "source": "skills-dir",
    }
    if entry.activate:
        manifest["activate"] = entry.activate
    if entry.display_name:
        manifest["display_name"] = entry.display_name
    if entry.default_prompt:
        manifest["default_prompt"] = entry.default_prompt
    return manifest


def write_registry(out_dir: Path, entries: list[SkillEntry]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        target = out_dir / f"{entry.name}.json"
        target.write_text(
            json.dumps(registry_manifest(entry), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SOIA skill catalog files.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--check", action="store_true", help="Fail if skills/README.md is stale.")
    parser.add_argument("--json", action="store_true", help="Print the discovered skill entries as JSON.")
    parser.add_argument("--write-missing-openai", action="store_true", help="Create missing agents/openai.yaml files from SKILL.md.")
    parser.add_argument("--registry-out", help="Optional directory for v7 runtime registry JSON manifests.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    entries = load_skills(root)
    if args.write_missing_openai:
        written = write_missing_openai(entries)
        if written:
            entries = load_skills(root)
        print(f"Wrote {written} missing agents/openai.yaml file(s).")
    rendered = render_readme(root, entries)
    readme = root / "skills" / "README.md"

    if args.json:
        print(json.dumps([registry_manifest(entry) for entry in entries], ensure_ascii=False, indent=2))

    if args.check:
        current = readme.read_text(encoding="utf-8") if readme.is_file() else ""
        if current != rendered:
            print(f"{readme} is stale; run python3 scripts/generate_skill_catalog.py", file=sys.stderr)
            return 1
    else:
        readme.write_text(rendered, encoding="utf-8")

    if args.registry_out:
        write_registry(Path(args.registry_out), entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
