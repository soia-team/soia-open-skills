#!/usr/bin/env python3
"""Audit public skill folders for common authoring mistakes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


ALLOWED_FRONTMATTER = {"name", "description", "dependencies", "version", "created_at", "updated_at", "created_by", "updated_by"}
DEPENDENCY_KEYS = {"hard", "optional", "external"}
MAX_SKILL_LINES = 500
DISALLOWED_SKILL_DOCS = {
    "README.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
    "CHANGELOG.md",
}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".txt",
    ".example",
}

ABSOLUTE_PATH_RE = re.compile(r"(/Users/[^ \n`]+|/home/[^/< \n`]+/[^ \n`]+)")
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(?:secret|token|api[_-]?key|session[_-]?string|password|cookie)\b\s*[:=]\s*"
    r"(?!<|\{|YOUR_|EXAMPLE|example|placeholder|\*{4,}|x{4,}|auto\b|prompt\b|never\b|null\b|os\.|resp\.|client\.)"
    r"[^ \n#]{8,}"
)
KNOWN_SECRET_RE = re.compile(
    r"(AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{20,}|ghp_[0-9A-Za-z]{20,})"
)
PRIVATE_CONTEXT_RE = re.compile(r"(老大|二宝|三宝|宝宝|真实家庭结构|孩子昵称|私有 memory|成绩\s*\d{2,3})")
VAULT_SPECIFIC_RE = re.compile(
    r"(40_图书视频馆/10_文章摘抄|40_图书视频馆/40_孩子书库|50_写作与发布/10_草稿|"
    r"50_写作与发布/30_转化输出|10_工作台/00_Inbox)"
)
# Desensitization gate: real private capture data must never reach the public
# skills repo. Placeholders (<...>, 示例*, example, YOUR_) never match these.
CLOUD_REAL_ID_URL_RE = re.compile(
    r"(?:alipan|aliyundrive)\.com/drive/file/[a-z]+/[a-z]+/[0-9a-f]{40}"
    r"|processon\.com/(?:diagraming|mindmap|view|org/teams)/[0-9a-fA-F]{16,}"
    r"|(?:feishu|larksuite)\.[a-z]+/(?:docx|wiki|sheets|base|file|drive)/[A-Za-z0-9]{22,}"
)
REAL_FILE_ID_RE = re.compile(r"(?i)file[_-]?id['\"]?\s*[:=]\s*['\"]?[0-9a-f]{40}\b")
REAL_IDENTITY_FIELD_RE = re.compile(
    r"""["'](?:owner|author|负责人|作者|创建人|所有者)["']\s*:\s*["']([一-鿿]{2,4})["']"""
)
IDENTITY_PLACEHOLDER_PREFIXES = ("示例", "匿名", "测试", "演示", "某", "占位")
IDENTITY_PLACEHOLDER_NAMES = {"张三", "李四", "王五", "学习者", "用户", "作者", "所有者", "负责人"}
LOCAL_NPX_INSTALL_RE = re.compile(r'npx\s+skills\s+add\s+(?:"\$PWD"|\$PWD|\.)(?:\s|$).*(?:-g|--all)')
LOCAL_SOURCE_DIR_RE = re.compile(r"--source-dir\s+skills(?:\s|$)")
DIRECT_SKILL_COPY_RE = re.compile(
    r"\bcp\s+-R\b.*\bskills\b.*(?:~/\.(?:agents|soia|codex|claude)|CODEX_HOME|\$CODEX_HOME)"
)

LINK_TARGET_RE = re.compile(r"\]\(([^)]+)\)")
SRC_TARGET_RE = re.compile(r'src\s*=\s*"([^"]+)"')
# Explicit repo-root docs that skills are allowed to link out to (established usage:
# skills/soia-pkm-clip-wechat-account/SKILL.md links to ../../SKILL_SPEC.md).
ALLOWED_ROOT_DOC_LINKS = {"README.md", "SKILL_SPEC.md", "CONTRIBUTING.md", "LICENSE", "AGENTS.md"}
CUSTOMER_READABLE_RULES = (
    ("customer-readable introduction", ("客户可读说明", "客户可见介绍")),
    ("capability section", ("这个技能可以做什么", "能做什么")),
    ("usage section", ("客户如何使用", "如何使用", "如何运行")),
    ("dependency/install section", ("依赖与安装", "首次安装与配置", "前置依赖", "强依赖")),
    ("log/completion receipt section", ("日志与完成回执", "客户可见日志与总结", "完成后回执", "执行后回执")),
)


@dataclass
class Finding:
    severity: str
    path: str
    message: str
    line: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "path": self.path,
            "line": self.line,
            "message": self.message,
        }


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    lines = text.replace("\r\n", "\n").splitlines()
    if not lines or lines[0] != "---":
        return {}, ["missing YAML frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, ["unterminated YAML frontmatter"]
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        return {}, [f"invalid YAML frontmatter: {exc}"]
    if not isinstance(data, dict):
        return {}, ["YAML frontmatter must be a mapping"]
    errors: list[str] = []
    for key in ("name", "description"):
        if key in data and not isinstance(data[key], str):
            errors.append(f"frontmatter {key} must be a string")
    return data, errors


def parse_openai_interface(path: Path) -> tuple[dict[str, str], list[str]]:
    try:
        document = yaml.safe_load(read_text(path))
    except yaml.YAMLError as exc:
        return {}, [f"invalid YAML metadata: {exc}"]
    if not isinstance(document, dict) or not isinstance(document.get("interface"), dict):
        return {}, ["missing interface mapping"]
    interface = document["interface"]
    data: dict[str, str] = {}
    errors: list[str] = []
    for key in ("display_name", "short_description", "default_prompt"):
        value = interface.get(key, "")
        if not isinstance(value, str):
            errors.append(f"interface.{key} must be a string")
        else:
            data[key] = value
    return data, errors


def add_line_finding(findings: list[Finding], severity: str, root: Path, path: Path, line_no: int, message: str) -> None:
    findings.append(Finding(severity, rel(path, root), message, line_no))


VALID_DOMAINS = ("pkm", "dev", "cwork", "design", "env", "meta", "safe", "gov")


def audit_skill_name(root: Path, skill_dir: Path, findings: list[Finding]) -> None:
    """Naming contract: soia-<domain>-<kebab-name>, no repeated tokens, known domain."""
    name = skill_dir.name
    import re as _re
    if not _re.fullmatch(r"soia-[a-z0-9]+(-[a-z0-9]+)+", name):
        findings.append(Finding("ERROR", rel(skill_dir, root),
            f"skill name must match soia-<domain>-<kebab-name>: {name!r}"))
        return
    parts = name.split("-")
    domain = parts[1]
    if domain not in VALID_DOMAINS:
        findings.append(Finding("ERROR", rel(skill_dir, root),
            f"unknown domain {domain!r}; valid: {', '.join(VALID_DOMAINS)}"))
    for i in range(len(parts) - 1):
        if parts[i] == parts[i + 1]:
            findings.append(Finding("ERROR", rel(skill_dir, root),
                f"repeated token {parts[i]!r} in skill name (e.g. the soia-dev-soia-* anti-pattern)"))
            break
    if "soia" in parts[2:]:
        findings.append(Finding("ERROR", rel(skill_dir, root),
            "'soia' must not reappear after the domain segment; product-only governance skills belong to the gov domain"))


def audit_skill(root: Path, skill_dir: Path, findings: list[Finding]) -> None:
    skill_name = skill_dir.name
    audit_skill_name(root, skill_dir, findings)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        findings.append(Finding("ERROR", rel(skill_dir, root), "missing SKILL.md"))
        return

    text = read_text(skill_md)
    line_count = len(text.splitlines())
    if line_count > MAX_SKILL_LINES:
        findings.append(
            Finding(
                "INFO",
                rel(skill_md, root),
                f"SKILL.md is long ({line_count} lines); split durable detail into references/ (target <= {MAX_SKILL_LINES})",
            )
        )
    if (skill_dir / "scripts").is_dir() or (skill_dir / "references").is_dir():
        if not re.search(r"(?i)(forward[- ]?test|前向测试|真实输出|端到端|e2e|验收)", text):
            findings.append(
                Finding(
                    "INFO",
                    rel(skill_md, root),
                    "complex skill should document a fixture or realistic forward test that verifies the output",
                )
            )
    fm, errors = parse_frontmatter(text)
    for error in errors:
        findings.append(Finding("ERROR", rel(skill_md, root), error))

    if fm.get("name") != skill_name:
        findings.append(Finding("ERROR", rel(skill_md, root), f"frontmatter name must match folder name: {skill_name!r}"))
    description = fm.get("description")
    if not isinstance(description, str) and description is not None:
        pass  # parse_frontmatter already emitted the type error
    elif not description:
        findings.append(Finding("ERROR", rel(skill_md, root), "missing frontmatter description"))
    elif len(description) > 220:
        findings.append(Finding("WARN", rel(skill_md, root), f"description is long ({len(description)} chars); keep trigger metadata concise"))

    extras = sorted(set(fm) - ALLOWED_FRONTMATTER)
    if extras:
        findings.append(Finding("WARN", rel(skill_md, root), f"extra frontmatter fields: {', '.join(extras)}"))

    deps = fm.get("dependencies")
    if deps is not None:
        if not isinstance(deps, dict) or not set(deps) <= DEPENDENCY_KEYS:
            findings.append(
                Finding("ERROR", rel(skill_md, root), "dependencies must be a mapping with only hard/optional/external keys")
            )
        else:
            for key in ("hard", "optional"):
                names = deps.get(key)
                if names is not None and not (
                    isinstance(names, list) and names and all(isinstance(n, str) and n for n in names)
                ):
                    findings.append(
                        Finding("ERROR", rel(skill_md, root), f"dependencies.{key} must be a non-empty list of skill names")
                    )
            externals = deps.get("external")
            if externals is not None and not (
                isinstance(externals, list)
                and externals
                and all(isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"] for e in externals)
            ):
                findings.append(
                    Finding("ERROR", rel(skill_md, root), "dependencies.external must be a non-empty list of mappings with a string name")
                )

    for label, markers in CUSTOMER_READABLE_RULES:
        if not any(marker in text for marker in markers):
            findings.append(Finding("ERROR", rel(skill_md, root), f"missing customer-readable {label}"))

    for path in skill_dir.rglob("*"):
        if path.is_dir():
            continue
        if path.name in DISALLOWED_SKILL_DOCS:
            findings.append(Finding("WARN", rel(path, root), "auxiliary docs inside skill; prefer SKILL.md + references/"))
        if path.name == ".env" or path.suffix == ".session":
            findings.append(Finding("ERROR", rel(path, root), "private auth/session file must not be committed"))
        if "references" in path.parts:
            try:
                idx = path.parts.index("references")
            except ValueError:
                idx = -1
            if idx >= 0 and len(path.parts) - idx > 2:
                findings.append(Finding("WARN", rel(path, root), "nested references should stay one level below references/"))

    audit_skill_links(root, skill_dir, findings)
    audit_openai_metadata(root, skill_dir, findings)


def audit_openai_metadata(root: Path, skill_dir: Path, findings: list[Finding]) -> None:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.is_file():
        return
    _, errors = parse_openai_interface(path)
    for error in errors:
        findings.append(Finding("ERROR", rel(path, root), error))


def check_link_target(root: Path, skill_dir: Path, source_file: Path, target: str) -> str | None:
    """Return an error when a relative link escapes the skill directory or is missing."""
    target = target.strip()
    if not target or target.startswith("#") or target in {"...", "…"}:
        return None
    if "://" in target or target.startswith("mailto:"):
        return None
    if target.startswith("<") or "{{" in target or "TODO" in target:
        return None  # placeholder text, not a concrete path
    if re.search(r"\s", target):
        # `](path "title")` → keep the path token only.
        target = target.split(None, 1)[0]

    path_part = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not path_part or path_part.startswith("/"):
        return None  # absolute paths are covered by the hardcoded-path check
    if any(char in path_part for char in "<>{}*$"):
        return None  # placeholder or glob, not a concrete packaged path

    resolved = (source_file.parent / path_part).resolve()
    skill_root = skill_dir.resolve()
    try:
        resolved.relative_to(skill_root)
    except ValueError:
        root_resolved = root.resolve()
        if resolved.parent == root_resolved and resolved.name in ALLOWED_ROOT_DOC_LINKS:
            if not resolved.exists():
                return f"relative link target not found: {target}"
            return None  # explicit repo-level doc link, established usage
        return f"relative link escapes skill directory: {target}"

    if not resolved.exists():
        return f"relative link target not found: {target}"
    return None


def iter_non_fenced_lines(text: str):
    """Yield (line_no, line) outside fenced code blocks; fences hold examples, not real links."""
    fence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = not fence
            continue
        if not fence:
            yield line_no, line


def audit_skill_links(root: Path, skill_dir: Path, findings: list[Finding]) -> None:
    md_files = [skill_dir / "SKILL.md"]
    references_dir = skill_dir / "references"
    if references_dir.is_dir():
        md_files.extend(sorted(references_dir.rglob("*.md")))

    for md_file in md_files:
        if not md_file.is_file():
            continue
        for i, line in iter_non_fenced_lines(read_text(md_file)):
            for match in LINK_TARGET_RE.finditer(line):
                message = check_link_target(root, skill_dir, md_file, match.group(1))
                if message:
                    add_line_finding(findings, "ERROR", root, md_file, i, message)
            for match in SRC_TARGET_RE.finditer(line):
                message = check_link_target(root, skill_dir, md_file, match.group(1))
                if message:
                    add_line_finding(findings, "ERROR", root, md_file, i, message)


def audit_text_file(root: Path, path: Path, findings: list[Finding]) -> None:
    if path.suffix not in TEXT_SUFFIXES and path.name not in {"SKILL.md", "config.example.yml"}:
        return
    text = read_text(path)
    for i, line in enumerate(text.splitlines(), start=1):
        placeholder_path = any(marker in line for marker in ("/Users/xxx", "/home/xxx", "/Users/<", "/home/<"))
        secret_is_env_read = "os.environ" in line or "getenv(" in line
        secret_is_placeholder_expr = "{" in line and "}" in line
        secret_is_function_call = re.search(r"[:=]\s*[A-Za-z_][A-Za-z0-9_.]*\(", line) is not None
        # Public documentation URLs can legitimately contain `/home/` (for
        # example, Feishu's `/document/home/...` routes). Remove URLs only for
        # the local absolute-path check; keep the original line for all other
        # safety checks.
        path_scan_line = re.sub(r"https?://[^ \n`]+", "", line)
        if ABSOLUTE_PATH_RE.search(path_scan_line) and not placeholder_path:
            add_line_finding(findings, "ERROR", root, path, i, "hardcoded absolute user path")
        if KNOWN_SECRET_RE.search(line) or (
            SECRET_VALUE_RE.search(line)
            and not secret_is_env_read
            and not secret_is_placeholder_expr
            and not secret_is_function_call
        ):
            add_line_finding(findings, "ERROR", root, path, i, "possible committed secret or credential value")
        if PRIVATE_CONTEXT_RE.search(line):
            add_line_finding(findings, "WARN", root, path, i, "possible private family/profile context")
        if VAULT_SPECIFIC_RE.search(line):
            add_line_finding(findings, "WARN", root, path, i, "vault-specific public default; prefer placeholder, env, CLI arg, or config")
        if LOCAL_NPX_INSTALL_RE.search(line):
            add_line_finding(findings, "ERROR", root, path, i, "install acceptance must use remote npx repo, not local $PWD or .")
        if LOCAL_SOURCE_DIR_RE.search(line):
            add_line_finding(findings, "ERROR", root, path, i, "install acceptance must sync from ~/.agents/skills after npx, not repository-local skills/")
        if DIRECT_SKILL_COPY_RE.search(line):
            add_line_finding(findings, "ERROR", root, path, i, "do not copy local skill directories into AI skill targets; install via npx and symlink sync")
        if CLOUD_REAL_ID_URL_RE.search(line):
            add_line_finding(findings, "ERROR", root, path, i, "real cloud/drive/diagram URL with a literal id; use a <placeholder> instead of real private data")
        if REAL_FILE_ID_RE.search(line):
            add_line_finding(findings, "ERROR", root, path, i, "real 40-hex cloud file_id committed; use a <placeholder>")
        identity_match = REAL_IDENTITY_FIELD_RE.search(line)
        if identity_match:
            captured_name = identity_match.group(1)
            if not captured_name.startswith(IDENTITY_PLACEHOLDER_PREFIXES) and captured_name not in IDENTITY_PLACEHOLDER_NAMES:
                add_line_finding(findings, "WARN", root, path, i, "possible real personal name in an example identity field; use a placeholder like 示例用户/张三")


def collect_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    skills_root = root / "skills"
    if not skills_root.is_dir():
        return [Finding("ERROR", "skills", "missing skills/ directory")]

    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir() and not path.name.startswith(".")):
        audit_skill(root, skill_dir, findings)

    # SKILL_SPEC.md intentionally contains forbidden examples; scanning it would create false positives.
    scan_roots = [
        root / "AGENTS.md",
        root / "README.md",
        root / "README.en.md",
        root / "CONTRIBUTING.md",
        skills_root,
    ]
    for scan_root in scan_roots:
        if scan_root.is_file():
            audit_text_file(root, scan_root, findings)
        elif scan_root.is_dir():
            for path in scan_root.rglob("*"):
                if path.is_file():
                    audit_text_file(root, path, findings)
    return sorted(findings, key=lambda f: (f.severity != "ERROR", f.path, f.line or 0, f.message))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit public skills for authoring-rule drift.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--json", action="store_true", help="Print JSON findings.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on WARN as well as ERROR.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings = collect_findings(root)

    if args.json:
        print(json.dumps([f.as_dict() for f in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("No findings.")
        for finding in findings:
            loc = finding.path if finding.line is None else f"{finding.path}:{finding.line}"
            print(f"{finding.severity}: {loc}: {finding.message}")

    has_error = any(f.severity == "ERROR" for f in findings)
    has_warn = any(f.severity == "WARN" for f in findings)
    return 1 if has_error or (args.strict and has_warn) else 0


if __name__ == "__main__":
    raise SystemExit(main())
