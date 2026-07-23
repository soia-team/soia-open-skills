#!/usr/bin/env python3
"""Generate pinned Claude and Codex marketplace manifests for SOIA plugins."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, NamedTuple, Sequence


OWNER = "soia-team"
PORTAL_REPOSITORY = "soia-open-skills"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class PluginDefinition(NamedTuple):
    repository: str
    name: str
    description: str
    category: str


# Keep this ordered table aligned with the public spoke topology. Descriptions
# mirror the repositories' GitHub descriptions so generation stays deterministic
# and only main-branch revisions require live GitHub lookups.
PLUGIN_DEFINITIONS = (
    PluginDefinition(
        "soia-open-dev-coding-skills",
        "soia-dev-coding",
        "开发编码技能：工程协议、代码审查、缺陷修复、任务执行与 AI 派发",
        "Developer Tools",
    ),
    PluginDefinition(
        "soia-open-dev-design-skills",
        "soia-dev-design",
        "设计与文档产线技能：Open Design、Archify、draw.io/Visio、OfficeCLI",
        "Creativity",
    ),
    PluginDefinition(
        "soia-open-dev-product-skills",
        "soia-dev-product",
        "产品需求技能：PRD 起草、用户故事与验收标准",
        "Productivity",
    ),
    PluginDefinition(
        "soia-open-dev-testing-skills",
        "soia-dev-testing",
        "测试技能：测试计划、用例设计与回归清单",
        "Developer Tools",
    ),
    PluginDefinition(
        "soia-open-dev-release-skills",
        "soia-dev-release",
        "发布技能：发布清单、灰度验证与回滚预案",
        "Developer Tools",
    ),
    PluginDefinition(
        "soia-open-dev-infra-skills",
        "soia-dev-infra",
        "基础设施与运维技能：终端长任务诊断、系统巡检",
        "Developer Tools",
    ),
    PluginDefinition(
        "soia-open-safe-skills",
        "soia-safe",
        "安全技能：代码安全审计与漏洞情报跟踪",
        "Developer Tools",
    ),
    PluginDefinition(
        "soia-open-cwork-office-skills",
        "soia-cwork-office",
        "办公协作技能：飞书知识库与云盘、ProcessOn 图表",
        "Productivity",
    ),
    PluginDefinition(
        "soia-open-pkm-clip-skills",
        "soia-pkm-clip",
        "知识剪藏与网盘技能：网页、公众号、X、抖音、小红书、GitHub 归档与云盘操作",
        "Productivity",
    ),
    PluginDefinition(
        "soia-open-pkm-vault-skills",
        "soia-pkm-vault",
        "知识库技能：初始化、整理、提炼、翻译、转换与书库",
        "Productivity",
    ),
    PluginDefinition(
        "soia-open-media-content-skills",
        "soia-media-content",
        "新媒体内容技能：文章成文、封面图与公众号、X、小红书发布",
        "Creativity",
    ),
    PluginDefinition(
        "soia-open-edu-course-skills",
        "soia-edu-course",
        "教育课程技能：课程大纲设计与教案编写",
        "Education & Research",
    ),
    PluginDefinition(
        "soia-open-env-skills",
        "soia-env",
        "环境技能：AI CLI 与运行时安装、网络诊断、系统维护",
        "Developer Tools",
    ),
    PluginDefinition(
        PORTAL_REPOSITORY,
        "soia-meta",
        "SOIA 技能生态门户：规范真源、技能目录与跨仓路由清单",
        "Developer Tools",
    ),
)


def run_gh_json(arguments: Sequence[str]) -> Any:
    """Run gh and decode one JSON response."""
    command = ["gh", *arguments]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return json.loads(result.stdout)


def fetch_main_sha(repository: str) -> str:
    """Fetch and validate the current 40-character main-branch revision."""
    payload = run_gh_json(["api", f"repos/{OWNER}/{repository}/commits/main"])
    sha = payload.get("sha") if isinstance(payload, Mapping) else None
    if not isinstance(sha, str) or SHA_PATTERN.fullmatch(sha) is None:
        raise ValueError(f"invalid main SHA returned for {OWNER}/{repository}: {sha!r}")
    return sha


def load_routed_repositories(manifest_path: Path) -> set[str]:
    """Return repositories that currently publish at least one routed skill."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("routing manifest must contain a JSON array")

    repositories: set[str] = set()
    for index, entry in enumerate(payload):
        if not isinstance(entry, Mapping):
            raise ValueError(f"routing manifest entry {index} must be an object")
        repository = entry.get("repo")
        if not isinstance(repository, str) or not repository:
            raise ValueError(f"routing manifest entry {index} has no valid repo")
        repositories.add(repository)

    known = {definition.repository for definition in PLUGIN_DEFINITIONS}
    unknown = sorted(repositories - known)
    if unknown:
        raise ValueError(f"missing plugin definitions for repositories: {', '.join(unknown)}")
    return repositories


def selected_definitions(manifest_path: Path) -> list[PluginDefinition]:
    repositories = load_routed_repositories(manifest_path)
    return [
        definition
        for definition in PLUGIN_DEFINITIONS
        if definition.repository in repositories
    ]


def build_marketplaces(
    definitions: Sequence[PluginDefinition],
    sha_fetcher: Callable[[str], str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Build both marketplace payloads and return external repository SHAs."""
    if sha_fetcher is None:
        sha_fetcher = fetch_main_sha
    revisions: dict[str, str] = {}
    for definition in definitions:
        if definition.repository != PORTAL_REPOSITORY:
            sha = sha_fetcher(definition.repository)
            if SHA_PATTERN.fullmatch(sha) is None:
                raise ValueError(
                    f"invalid main SHA returned for {OWNER}/{definition.repository}: {sha!r}"
                )
            revisions[definition.repository] = sha

    claude_plugins: list[dict[str, Any]] = []
    codex_plugins: list[dict[str, Any]] = []
    for definition in definitions:
        if definition.repository == PORTAL_REPOSITORY:
            claude_source: str | dict[str, str] = "./"
            codex_source = {"source": "local", "path": "./"}
        else:
            sha = revisions[definition.repository]
            claude_source = {
                "source": "github",
                "repo": f"{OWNER}/{definition.repository}",
                "sha": sha,
            }
            codex_source = {
                "source": "url",
                "url": f"https://github.com/{OWNER}/{definition.repository}.git",
                "ref": sha,
            }

        claude_plugins.append(
            {
                "name": definition.name,
                "description": definition.description,
                "source": claude_source,
            }
        )
        codex_plugins.append(
            {
                "name": definition.name,
                "description": definition.description,
                "source": codex_source,
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": definition.category,
            }
        )

    claude = {
        "name": "soia",
        "owner": {"name": OWNER},
        "description": "SOIA Skills 双格式插件市场，按领域分发可复用 AI 工作流。",
        "plugins": claude_plugins,
    }
    codex = {
        "name": "soia",
        "interface": {"displayName": "SOIA"},
        "plugins": codex_plugins,
    }
    return claude, codex, revisions


def format_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def check_or_write(path: Path, content: str, check: bool) -> bool:
    """Return True when the file is current; write it when not checking."""
    if check:
        if not path.is_file():
            print(f"out of date: {path} does not exist", file=sys.stderr)
            return False
        if path.read_text(encoding="utf-8") != content:
            print(f"out of date: {path}", file=sys.stderr)
            return False
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path}")
    return True


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("routing/routing-manifest.json"),
        help="Routing manifest path",
    )
    parser.add_argument(
        "--claude-output",
        type=Path,
        default=Path(".claude-plugin/marketplace.json"),
        help="Claude marketplace output path",
    )
    parser.add_argument(
        "--codex-output",
        type=Path,
        default=Path(".agents/plugins/marketplace.json"),
        help="Codex marketplace output path",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when either generated marketplace differs from disk",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        definitions = selected_definitions(args.manifest)
        claude, codex, _ = build_marketplaces(definitions)
        results = (
            check_or_write(args.claude_output, format_json(claude), args.check),
            check_or_write(args.codex_output, format_json(codex), args.check),
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if not all(results):
            return 1
        print(f"marketplaces are current ({len(definitions)} plugins)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
