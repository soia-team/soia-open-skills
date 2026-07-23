#!/usr/bin/env python3
"""Offline tests for dual Claude/Codex marketplace generation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_marketplaces.py"

SPEC = importlib.util.spec_from_file_location("generate_marketplaces", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MarketplaceGenerationTests(unittest.TestCase):
    SHA = "0123456789abcdef0123456789abcdef01234567"

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.manifest = self.root / "routing.json"
        self.claude_output = self.root / ".claude-plugin" / "marketplace.json"
        self.codex_output = self.root / ".agents" / "plugins" / "marketplace.json"
        self.manifest.write_text(
            json.dumps(
                [
                    {
                        "skill_name": "soia-dev-task-execute",
                        "repo": "soia-open-dev-coding-skills",
                    },
                    {
                        "skill_name": "soia-meta-prompt-clarity",
                        "repo": "soia-open-skills",
                    },
                ]
            ),
            encoding="utf-8",
        )

    def arguments(self, *extra: str) -> list[str]:
        return [
            "--manifest",
            str(self.manifest),
            "--claude-output",
            str(self.claude_output),
            "--codex-output",
            str(self.codex_output),
            *extra,
        ]

    def test_fixture_builds_both_marketplace_structures(self) -> None:
        definitions = MODULE.selected_definitions(self.manifest)
        claude, codex, revisions = MODULE.build_marketplaces(
            definitions, sha_fetcher=lambda _repository: self.SHA
        )

        self.assertEqual(claude["name"], "soia")
        self.assertEqual(claude["owner"], {"name": "soia-team"})
        self.assertEqual(len(claude["plugins"]), 2)
        external = claude["plugins"][0]
        self.assertEqual(external["name"], "soia-dev-coding")
        self.assertEqual(external["source"]["source"], "github")
        self.assertEqual(external["source"]["sha"], self.SHA)
        self.assertRegex(external["source"]["sha"], r"^[0-9a-f]{40}$")
        self.assertEqual(claude["plugins"][1]["source"], "./")

        self.assertEqual(codex["interface"], {"displayName": "SOIA"})
        codex_external = codex["plugins"][0]
        self.assertEqual(codex_external["source"]["source"], "url")
        self.assertEqual(codex_external["source"]["ref"], self.SHA)
        self.assertEqual(
            codex_external["interface"],
            {
                "displayName": "开发编码技能库",
                "shortDescription": "开发编码技能：工程协议、代码审查、缺陷修复、任务执行、终端操作与 AI 派发",
                "category": "Developer Tools",
            },
        )
        self.assertEqual(
            codex_external["policy"],
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        )
        self.assertEqual(codex["plugins"][1]["source"], {"source": "local", "path": "./"})
        self.assertEqual(codex["plugins"][1]["interface"]["displayName"], "SOIA 元技能库")
        self.assertEqual(revisions, {"soia-open-dev-coding-skills": self.SHA})

    def test_fetch_main_sha_uses_gh_and_rejects_non_full_sha(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"sha": self.SHA}), stderr=""
        )
        with mock.patch.object(MODULE.subprocess, "run", return_value=completed) as run:
            self.assertEqual(MODULE.fetch_main_sha("soia-open-example-skills"), self.SHA)
        run.assert_called_once_with(
            ["gh", "api", "repos/soia-team/soia-open-example-skills/commits/main"],
            check=False,
            capture_output=True,
            text=True,
        )

        with self.assertRaisesRegex(ValueError, "invalid main SHA"):
            MODULE.build_marketplaces(
                MODULE.selected_definitions(self.manifest),
                sha_fetcher=lambda _repository: "abc123",
            )

    def test_check_succeeds_when_outputs_match(self) -> None:
        with mock.patch.object(MODULE, "fetch_main_sha", return_value=self.SHA):
            self.assertEqual(MODULE.main(self.arguments()), 0)
            self.assertEqual(MODULE.main(self.arguments("--check")), 0)

    def test_check_fails_without_overwriting_stale_output(self) -> None:
        with mock.patch.object(MODULE, "fetch_main_sha", return_value=self.SHA):
            self.assertEqual(MODULE.main(self.arguments()), 0)
            self.claude_output.write_text("stale\n", encoding="utf-8")
            self.assertEqual(MODULE.main(self.arguments("--check")), 1)
        self.assertEqual(self.claude_output.read_text(encoding="utf-8"), "stale\n")


if __name__ == "__main__":
    unittest.main()
