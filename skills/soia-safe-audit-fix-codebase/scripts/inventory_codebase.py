#!/usr/bin/env python3
"""Produce a read-only, content-minimizing inventory of a local codebase."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "target",
    "build",
    "dist",
    "coverage",
    ".next",
    ".nuxt",
    "__pycache__",
}

LANGUAGES = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".php": "PHP",
    ".pl": "Perl",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".scala": "Scala",
    ".sh": "Shell",
    ".sol": "Solidity",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
}

MANIFEST_NAMES = {
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "settings.gradle": "gradle",
    "settings.gradle.kts": "gradle",
    "gradle.lockfile": "gradle-lock",
    "libs.versions.toml": "gradle-version-catalog",
    "package.json": "node",
    "package-lock.json": "node-lock",
    "npm-shrinkwrap.json": "node-lock",
    "pnpm-lock.yaml": "node-lock",
    "yarn.lock": "node-lock",
    "deno.json": "deno",
    "deno.lock": "deno-lock",
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "requirements-dev.txt": "python",
    "poetry.lock": "python-lock",
    "Pipfile": "python",
    "Pipfile.lock": "python-lock",
    "uv.lock": "python-lock",
    "go.mod": "go",
    "go.sum": "go-lock",
    "Cargo.toml": "rust",
    "Cargo.lock": "rust-lock",
    "Gemfile": "ruby",
    "Gemfile.lock": "ruby-lock",
    "composer.json": "php",
    "composer.lock": "php-lock",
    "packages.config": "dotnet",
    "Directory.Packages.props": "dotnet",
    "Podfile": "cocoapods",
    "Podfile.lock": "cocoapods-lock",
    "Package.swift": "swift",
}

RULE_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.rst",
    "SECURITY.md",
    "DEVELOPMENT.md",
}

SENSITIVE_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.yml",
    "secrets.yaml",
}


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def walk_files(root: Path, max_files: int) -> tuple[list[Path], dict[str, Any]]:
    files: list[Path] = []
    skipped_dirs = Counter()
    symlink_files = 0
    symlink_dirs = 0
    truncated = False

    for current_root, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(current_root)
        retained_dirs = []
        for dirname in sorted(dirnames):
            child = current / dirname
            if dirname in IGNORED_DIRS:
                skipped_dirs[dirname] += 1
            elif child.is_symlink():
                symlink_dirs += 1
            else:
                retained_dirs.append(dirname)
        dirnames[:] = retained_dirs

        for filename in sorted(filenames):
            path = current / filename
            if path.is_symlink():
                symlink_files += 1
                continue
            files.append(path)
            if len(files) >= max_files:
                truncated = True
                dirnames[:] = []
                break
        if truncated:
            break

    metadata = {
        "ignored_directory_counts": dict(sorted(skipped_dirs.items())),
        "symlink_files_skipped": symlink_files,
        "symlink_directories_skipped": symlink_dirs,
        "truncated": truncated,
        "max_files": max_files,
    }
    return files, metadata


def is_dockerfile(name: str) -> bool:
    return name == "Dockerfile" or name.startswith("Dockerfile.")


def is_ci_file(path: Path, root: Path) -> bool:
    rel = relative(path, root)
    return (
        rel.startswith(".github/workflows/")
        or rel == ".gitlab-ci.yml"
        or rel == "Jenkinsfile"
        or rel.startswith(".circleci/")
        or rel.startswith(".buildkite/")
    )


def is_iac_file(path: Path) -> bool:
    name = path.name
    return (
        path.suffix == ".tf"
        or name in {"Chart.yaml", "Chart.yml", "kustomization.yaml", "kustomization.yml"}
        or name.endswith(".bicep")
    )


def is_container_or_orchestration_file(path: Path) -> bool:
    name = path.name.lower()
    return (
        is_dockerfile(path.name)
        or name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
        or "kubernetes" in {part.lower() for part in path.parts}
        or "k8s" in {part.lower() for part in path.parts}
        or "helm" in {part.lower() for part in path.parts}
    )


def is_test_file(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    lower_name = path.name.lower()
    return (
        bool(lower_parts & {"test", "tests", "spec", "specs", "__tests__"})
        or lower_name.startswith("test_")
        or lower_name.endswith(("_test.py", "_test.go", ".test.js", ".test.ts", ".spec.js", ".spec.ts"))
    )


def git_command(root: Path, args: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""
    return completed.returncode, completed.stdout.strip()


def git_metadata(root: Path) -> dict[str, Any]:
    code, top = git_command(root, ["rev-parse", "--show-toplevel"])
    if code != 0:
        return {"is_git_repository": False}
    branch_code, branch = git_command(root, ["branch", "--show-current"])
    head_code, head = git_command(root, ["rev-parse", "HEAD"])
    status_code, status = git_command(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    status_lines = [line for line in status.splitlines() if line]
    status_codes = Counter(line[:2] for line in status_lines if len(line) >= 2)
    return {
        "is_git_repository": True,
        "root_matches_target": Path(top).resolve() == root.resolve(),
        "branch": branch if branch_code == 0 else None,
        "commit": head if head_code == 0 else None,
        "dirty": bool(status_lines),
        "status_entry_count": len(status_lines),
        "status_code_counts": dict(sorted(status_codes.items())),
        "status_read_ok": status_code == 0,
    }


def inventory(root: Path, max_files: int) -> dict[str, Any]:
    resolved = root.expanduser().resolve()
    if not resolved.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    files, walk_metadata = walk_files(resolved, max_files)
    language_counts = Counter()
    manifests: list[dict[str, str]] = []
    rule_files = []
    ci_files = []
    container_files = []
    iac_files = []
    artifact_counts = Counter()
    test_files = 0
    sensitive_name_count = 0
    total_bytes = 0

    for path in files:
        suffix = path.suffix.lower()
        if suffix in LANGUAGES:
            language_counts[LANGUAGES[suffix]] += 1
        if path.name in MANIFEST_NAMES:
            manifests.append({"path": relative(path, resolved), "kind": MANIFEST_NAMES[path.name]})
        elif suffix in {".csproj", ".fsproj", ".vbproj", ".sln"}:
            manifests.append({"path": relative(path, resolved), "kind": "dotnet"})
        if path.name in RULE_FILES:
            rule_files.append(relative(path, resolved))
        if is_ci_file(path, resolved):
            ci_files.append(relative(path, resolved))
        if is_container_or_orchestration_file(path):
            container_files.append(relative(path, resolved))
        if is_iac_file(path):
            iac_files.append(relative(path, resolved))
        if suffix in {".jar", ".war", ".ear", ".zip", ".whl", ".gem", ".nupkg"}:
            artifact_counts[suffix.lstrip(".")] += 1
        if is_test_file(path):
            test_files += 1
        if path.name in SENSITIVE_BASENAMES or suffix in {".pem", ".key", ".p12", ".pfx"}:
            sensitive_name_count += 1
        try:
            total_bytes += path.stat().st_size
        except OSError:
            pass

    manifests.sort(key=lambda item: item["path"])
    result = {
        "schema_version": 1,
        "target": {
            "display_name": resolved.name,
            "absolute_path_included": False,
        },
        "git": git_metadata(resolved),
        "walk": walk_metadata,
        "counts": {
            "files": len(files),
            "bytes": total_bytes,
            "test_files": test_files,
            "sensitive_name_candidates": sensitive_name_count,
        },
        "languages": [
            {"name": language, "files": count}
            for language, count in language_counts.most_common()
        ],
        "manifests": manifests,
        "rule_files": sorted(rule_files),
        "ci_files": sorted(ci_files),
        "container_or_orchestration_files": sorted(set(container_files)),
        "iac_files": sorted(set(iac_files)),
        "artifact_counts": dict(sorted(artifact_counts.items())),
        "notes": [
            "Inventory is structural only; it is not a vulnerability verdict.",
            "Sensitive-name candidates were counted but their paths and contents were not emitted.",
            "Ignored, generated, vendored, and symlinked paths require an explicit scope decision.",
        ],
    }
    return result


def safe_write(path: Path, text: str, force: bool) -> None:
    path = path.expanduser()
    if path.exists() and not force:
        raise FileExistsError(f"output exists; pass --force to replace it: {path}")
    if not path.parent.exists():
        raise FileNotFoundError(f"output directory does not exist: {path.parent}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        if path.exists() and force:
            os.replace(temporary_name, path)
        else:
            os.link(temporary_name, path)
            os.unlink(temporary_name)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="soia-codebase-inventory-") as temp_dir:
        root = Path(temp_dir)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "node_modules").mkdir()
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "src" / "App.java").write_text("class App {}\n", encoding="utf-8")
        (root / "tests" / "test_app.py").write_text("def test_ok(): pass\n", encoding="utf-8")
        (root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
        (root / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
        (root / "node_modules" / "ignored.js").write_text("ignored\n", encoding="utf-8")
        (root / ".env").write_text("DO_NOT_READ=this-content\n", encoding="utf-8")

        result = inventory(root, 1000)
        languages = {item["name"]: item["files"] for item in result["languages"]}
        assert languages == {"Java": 1, "Python": 1}
        assert result["counts"]["files"] == 6
        assert result["counts"]["sensitive_name_candidates"] == 1
        assert result["manifests"] == [{"path": "pom.xml", "kind": "maven"}]
        assert result["container_or_orchestration_files"] == ["Dockerfile"]
        assert result["ci_files"] == [".github/workflows/ci.yml"]
        serialized = json.dumps(result)
        assert "DO_NOT_READ" not in serialized
        assert temp_dir not in serialized
    print("self-test: ok")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--max-files", type=int, default=200000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.path is None:
        raise ValueError("path is required unless --self-test is used")
    if not 1 <= args.max_files <= 1_000_000:
        raise ValueError("--max-files must be between 1 and 1000000")

    result = inventory(args.path, args.max_files)
    text = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None) + "\n"
    if args.output:
        safe_write(args.output, text, args.force)
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "files": result["counts"]["files"],
                    "manifests": len(result["manifests"]),
                    "truncated": result["walk"]["truncated"],
                },
                ensure_ascii=False,
            )
        )
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
