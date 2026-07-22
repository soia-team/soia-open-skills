#!/usr/bin/env python3
"""Scaffold baseline files for repositories split from soia-open-skills."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import stat
import subprocess
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SHARED_FILES = (
    "SKILL_SPEC.md",
    "DATA_STORAGE_SPEC.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".gitignore",
    "requirements-dev.txt",
    "scripts/audit_skills.py",
    "scripts/generate_skill_catalog.py",
    ".github/workflows/audit.yml",
)
WHOLE_DIRECTORIES = ("templates/skill-template",)
REPO_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DOMAIN_RE = re.compile(r"^[a-z0-9]+$")


@dataclass(frozen=True)
class RepoSpec:
    name: str
    visibility: str
    domain: str
    title_zh: str
    desc: str
    incubator: bool
    readme_note: str = ""
    note: str = ""
    license: str = ""


@dataclass(frozen=True)
class GeneratedFile:
    content: bytes
    mode: int = 0o644


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Generate local baseline directories for split SOIA skill repositories."
    )
    parser.add_argument("--manifest", required=True, type=Path, help="JSON repository manifest.")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=script_root,
        help="Source soia-open-skills checkout (default: this script's repository).",
    )
    parser.add_argument("--output-root", required=True, type=Path, help="Parent directory for generated repositories.")
    parser.add_argument("--check", action="store_true", help="Report baseline differences without writing files.")
    return parser.parse_args()


def require_string(item: dict[str, Any], key: str, index: int, *, optional: bool = False) -> str:
    value = item.get(key, "" if optional else None)
    if not isinstance(value, str) or (not optional and not value.strip()):
        raise ValueError(f"manifest item {index}: {key!r} must be a non-empty string")
    return value.strip()


def load_manifest(path: Path) -> list[RepoSpec]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read manifest {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON manifest {path}: {exc}") from exc

    if isinstance(document, dict):
        for key in ("repositories", "repos"):
            if key in document:
                document = document[key]
                break
    if not isinstance(document, list) or not document:
        raise ValueError("manifest must be a non-empty list or contain a non-empty 'repositories'/'repos' list")

    specs: list[RepoSpec] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(document, start=1):
        if not isinstance(raw_item, dict):
            raise ValueError(f"manifest item {index}: expected an object")
        name = require_string(raw_item, "name", index)
        visibility = require_string(raw_item, "visibility", index)
        domain = require_string(raw_item, "domain", index)
        if not REPO_NAME_RE.fullmatch(name):
            raise ValueError(f"manifest item {index}: invalid repository name {name!r}")
        if name in seen:
            raise ValueError(f"manifest item {index}: duplicate repository name {name!r}")
        if visibility not in {"public", "private"}:
            raise ValueError(f"manifest item {index}: visibility must be 'public' or 'private'")
        if not DOMAIN_RE.fullmatch(domain):
            raise ValueError(f"manifest item {index}: invalid domain {domain!r}")
        incubator = raw_item.get("incubator")
        if not isinstance(incubator, bool):
            raise ValueError(f"manifest item {index}: 'incubator' must be a boolean")
        license_value = require_string(raw_item, "license", index, optional=True)
        specs.append(
            RepoSpec(
                name=name,
                visibility=visibility,
                domain=domain,
                title_zh=require_string(raw_item, "title_zh", index),
                desc=require_string(raw_item, "desc", index),
                incubator=incubator,
                readme_note=require_string(raw_item, "readme_note", index, optional=True),
                note=require_string(raw_item, "note", index, optional=True),
                license=license_value,
            )
        )
        seen.add(name)
    return specs


def source_commit(source_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    sha = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        detail = result.stderr.strip() or "not a Git checkout"
        raise ValueError(f"cannot resolve source commit for {source_root}: {detail}")
    return sha


def replace_repo_name(text: str, repo_name: str) -> str:
    return text.replace("soia-open-skills", repo_name)


def derive_agents(source: str, spec: RepoSpec) -> str:
    text = replace_repo_name(source, spec.name)
    purpose = (
        "## Repository Purpose\n\n"
        f"`{spec.name}` publishes reusable `soia-{spec.domain}-*` skills for the {spec.domain} domain. "
        "Every committed skill must be safe for users who do not share the maintainer's machine, "
        "accounts, private data, or internal workspace.\n"
    )
    text = re.sub(
        r"## Repository Purpose\n.*?(?=\n## )",
        purpose.rstrip(),
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace("in this public repo", "in this repository")
    text = text.replace("Public examples", "Repository examples")
    return text.rstrip() + "\n"


def derive_workflow(source: str, repo_name: str) -> str:
    text = replace_repo_name(source, repo_name)
    unavailable_steps = {
        "Run WeChat archive regression tests",
        "Run AI CLI upgrade regression tests",
        "Check top-level README skill coverage",
    }
    lines = text.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)- name: (.+)$", lines[index])
        if match and match.group(2) in unavailable_steps:
            indent = len(match.group(1))
            index += 1
            while index < len(lines):
                next_match = re.match(r"^(\s*)- (?:name:|uses:)", lines[index])
                if next_match and len(next_match.group(1)) == indent:
                    break
                index += 1
            continue
        kept.append(lines[index])
        index += 1
    return "\n".join(kept).rstrip() + "\n"


def derive_catalog_generator(source: str, repo_name: str) -> str:
    text = replace_repo_name(source, repo_name)
    marker = "    grouped: dict[str, list[SkillEntry]] = {}\n"
    empty_state = (
        "    if not entries:\n"
        "        lines.extend([\"## Skills\", \"\", \"暂无技能。运行生成器后，此页会自动列出 `skills/*/SKILL.md`。\", \"\"])\n"
    )
    if marker not in text:
        raise ValueError("catalog generator does not contain the expected render marker")
    return text.replace(marker, empty_state + marker, 1)


def derive_audit(source: str, spec: RepoSpec) -> str:
    text = replace_repo_name(source, spec.name)
    marker = re.compile(r'^VALID_DOMAINS = \([^\n]+\)$', re.MULTILINE)
    if not marker.search(text):
        raise ValueError("audit script does not contain the expected VALID_DOMAINS contract")
    return marker.sub(f'VALID_DOMAINS = ("{spec.domain}",)', text, count=1)


def render_readme(spec: RepoSpec) -> str:
    lines = [f"# {spec.title_zh}", ""]
    notices: list[str] = []
    if spec.readme_note:
        notices.append(spec.readme_note)
    if spec.visibility == "private":
        notices.extend(["**Proprietary - internal use only.**", "**本仓永不开源；不进入公开 catalog 与路由清单。**"])
    if notices:
        lines.extend(["  \n".join(f"> {notice}" for notice in notices), ""])
    lines.extend([spec.desc, ""])
    if spec.note:
        lines.extend([spec.note, ""])
    if spec.incubator:
        lines.extend(["## 孵化中", "", "本仓处于孵化阶段，技能和接口可能继续调整。", ""])
    lines.extend(
        [
            "## 域说明",
            "",
            f"本仓负责 `{spec.domain}` 域，技能名称统一使用 `soia-{spec.domain}-*` 前缀。",
            "",
            "## 安装",
            "",
            "```bash",
            f"npx skills add soia-team/{spec.name} -g -a '*' -s <skill> -y",
            "```",
            "",
            "本仓属于 SOIA 技能生态，规范真源见 [soia-team/soia-open-skills](https://github.com/soia-team/soia-open-skills)。",
            "",
        ]
    )
    return "\n".join(lines)


def render_readme_en(spec: RepoSpec) -> str:
    lines = [f"# {spec.name}", ""]
    notices: list[str] = []
    if spec.readme_note:
        notices.append(spec.readme_note)
    if spec.visibility == "private":
        notices.extend(
            [
                "**Proprietary - internal use only.**",
                "**This repository will remain private and is excluded from public catalogs and routing manifests.**",
            ]
        )
    if notices:
        lines.extend(["  \n".join(f"> {notice}" for notice in notices), ""])
    lines.extend([spec.desc, ""])
    if spec.note:
        lines.extend([spec.note, ""])
    if spec.incubator:
        lines.extend(["## Incubating", "", "This repository is incubating; skills and interfaces may continue to change.", ""])
    lines.extend(
        [
            "## Domain",
            "",
            f"This repository owns the `{spec.domain}` domain. Skill names use the `soia-{spec.domain}-*` prefix.",
            "",
            "## Install",
            "",
            "```bash",
            f"npx skills add soia-team/{spec.name} -g -a '*' -s <skill> -y",
            "```",
            "",
            "This repository is part of the SOIA skill ecosystem. The canonical specifications live in "
            "[soia-team/soia-open-skills](https://github.com/soia-team/soia-open-skills).",
            "",
        ]
    )
    return "\n".join(lines)


def baseline_test() -> str:
    return '''"""Smoke tests for a freshly scaffolded skill repository."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BaselineTest(unittest.TestCase):
    def run_tool(self, script: str, *args: str) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), "--root", str(ROOT), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_strict_audit(self) -> None:
        self.run_tool("audit_skills.py", "--strict")

    def test_catalog_is_current(self) -> None:
        self.run_tool("generate_skill_catalog.py", "--check")


if __name__ == "__main__":
    unittest.main()
'''


def source_file(source_root: Path, relative: str) -> tuple[bytes, int]:
    path = source_root / relative
    if not path.is_file():
        raise ValueError(f"required source file is missing: {path}")
    return path.read_bytes(), stat.S_IMODE(path.stat().st_mode)


def build_files(source_root: Path, spec: RepoSpec, sha: str, utc_date: str) -> dict[str, GeneratedFile]:
    files: dict[str, GeneratedFile] = {}
    for relative in SHARED_FILES:
        content, mode = source_file(source_root, relative)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            transformed = content
        else:
            if relative == ".github/workflows/audit.yml":
                text = derive_workflow(text, spec.name)
            elif relative == "scripts/audit_skills.py":
                text = derive_audit(text, spec)
            elif relative == "scripts/generate_skill_catalog.py":
                text = derive_catalog_generator(text, spec.name)
            else:
                text = replace_repo_name(text, spec.name)
            transformed = text.encode("utf-8")
        files[relative] = GeneratedFile(transformed, mode)

    for directory in WHOLE_DIRECTORIES:
        source_dir = source_root / directory
        if not source_dir.is_dir():
            raise ValueError(f"required source directory is missing: {source_dir}")
        for path in sorted(item for item in source_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(source_root).as_posix()
            content = path.read_bytes()
            try:
                content = replace_repo_name(content.decode("utf-8"), spec.name).encode("utf-8")
            except UnicodeDecodeError:
                pass
            files[relative] = GeneratedFile(content, stat.S_IMODE(path.stat().st_mode))

    agents, agents_mode = source_file(source_root, "AGENTS.md")
    files["AGENTS.md"] = GeneratedFile(derive_agents(agents.decode("utf-8"), spec).encode("utf-8"), agents_mode)
    files["README.md"] = GeneratedFile(render_readme(spec).encode("utf-8"))
    files["README.en.md"] = GeneratedFile(render_readme_en(spec).encode("utf-8"))
    files["tests/test_baseline.py"] = GeneratedFile(baseline_test().encode("utf-8"))
    files["BASELINE_VERSION"] = GeneratedFile(f"{sha} {utc_date} baseline-v1\n".encode("utf-8"))

    generator = files["scripts/generate_skill_catalog.py"].content.decode("utf-8")
    module_name = "_scaffold_catalog_renderer"
    module = types.ModuleType(module_name)
    sys.modules[module_name] = module
    try:
        exec(compile(generator, "scripts/generate_skill_catalog.py", "exec"), module.__dict__)
        rendered_catalog = module.render_readme(
            # The renderer uses the directory name when the generated directory is not a Git checkout.
            source_root.parent / spec.name,
            [],
        )
    finally:
        sys.modules.pop(module_name, None)
    files["skills/README.md"] = GeneratedFile(rendered_catalog.encode("utf-8"))

    if spec.visibility == "public" and spec.license != "none":
        license_content, license_mode = source_file(source_root, "LICENSE")
        files["LICENSE"] = GeneratedFile(license_content, license_mode)
    return files


def text_diff(relative: str, actual: bytes, expected: bytes) -> list[str]:
    try:
        actual_text = actual.decode("utf-8").splitlines(keepends=True)
        expected_text = expected.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return [f"binary content differs: {relative}"]
    return list(
        difflib.unified_diff(
            actual_text,
            expected_text,
            fromfile=f"actual/{relative}",
            tofile=f"expected/{relative}",
        )
    )


def check_repo(target: Path, files: dict[str, GeneratedFile], should_have_license: bool) -> list[str]:
    differences: list[str] = []
    if not target.is_dir():
        return [f"missing repository directory: {target}"]
    for relative, generated in sorted(files.items()):
        path = target / relative
        if not path.is_file():
            differences.append(f"missing: {relative}")
            continue
        actual = path.read_bytes()
        if actual != generated.content:
            differences.extend(text_diff(relative, actual, generated.content))
    if not should_have_license and (target / "LICENSE").exists():
        differences.append("unexpected: LICENSE")
    for directory in WHOLE_DIRECTORIES:
        expected = {relative for relative in files if relative.startswith(f"{directory}/")}
        actual_dir = target / directory
        if actual_dir.is_dir():
            actual = {
                path.relative_to(target).as_posix()
                for path in actual_dir.rglob("*")
                if path.is_file()
            }
            differences.extend(f"unexpected: {relative}" for relative in sorted(actual - expected))
    return differences


def write_repo(target: Path, files: dict[str, GeneratedFile], should_have_license: bool) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for directory in WHOLE_DIRECTORIES:
        managed = target / directory
        if managed.exists():
            shutil.rmtree(managed)
    if not should_have_license:
        license_path = target / "LICENSE"
        if license_path.is_file() or license_path.is_symlink():
            license_path.unlink()
    for relative, generated in sorted(files.items()):
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(generated.content)
        path.chmod(generated.mode)


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    try:
        specs = load_manifest(args.manifest.resolve())
        sha = source_commit(source_root)
        utc_date = datetime.now(timezone.utc).date().isoformat()
        all_differences: list[str] = []
        for spec in specs:
            files = build_files(source_root, spec, sha, utc_date)
            target = output_root / spec.name
            should_have_license = "LICENSE" in files
            if args.check:
                differences = check_repo(target, files, should_have_license)
                if differences:
                    all_differences.append(f"[{spec.name}]")
                    all_differences.extend(differences)
            else:
                write_repo(target, files, should_have_license)
                print(f"generated {target}")
        if args.check:
            if all_differences:
                print("\n".join(all_differences))
                return 1
            print(f"baseline is current for {len(specs)} repository/repositories")
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
