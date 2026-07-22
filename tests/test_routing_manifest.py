#!/usr/bin/env python3
"""Offline tests for public routing-manifest normalization and formatting."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_routing_manifest.py"
FIXTURE = ROOT / "tests/fixtures/routing_contents.json"

SPEC = importlib.util.spec_from_file_location("generate_routing_manifest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RoutingManifestTests(unittest.TestCase):
    def test_fixture_builds_stable_public_entries_without_network(self) -> None:
        payloads = json.loads(FIXTURE.read_text(encoding="utf-8"))
        repositories = ("soia-open-example-a", "soia-open-example-b")

        entries = MODULE.build_manifest(payloads, repositories)
        rendered = MODULE.format_manifest(entries)

        self.assertTrue(rendered.endswith("\n"))
        self.assertEqual(
            json.loads(rendered),
            [
                {
                    "skill_name": "soia-alpha-example-skill",
                    "repo": "soia-open-example-b",
                    "skillPath": "skills/soia-alpha-example-skill",
                    "visibility": "public",
                },
                {
                    "skill_name": "soia-zeta-example-skill",
                    "repo": "soia-open-example-a",
                    "skillPath": "skills/soia-zeta-example-skill",
                    "visibility": "public",
                },
            ],
        )

    def test_duplicate_skill_names_are_rejected(self) -> None:
        payloads = {
            "repo-a": [{"name": "soia-duplicate-skill-name", "type": "dir"}],
            "repo-b": [{"name": "soia-duplicate-skill-name", "type": "dir"}],
        }
        with self.assertRaisesRegex(ValueError, "duplicate public skill names"):
            MODULE.build_manifest(payloads, ("repo-a", "repo-b"))


if __name__ == "__main__":
    unittest.main()
