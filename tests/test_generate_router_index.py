#!/usr/bin/env python3
"""Offline tests for the generated router directory."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_router_index.py"
SPEC = importlib.util.spec_from_file_location("generate_router_index", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GenerateRouterIndexTests(unittest.TestCase):
    def test_build_directory_fetches_descriptions_and_sorts(self) -> None:
        manifest = [
            {"skill_name": "soia-meta-z-skill", "repo": "repo-z", "skillPath": "skills/z"},
            {"skill_name": "soia-meta-a-skill", "repo": "repo-a", "skillPath": "skills/a"},
        ]

        def fetcher(repo: str, _path: str) -> str:
            return f"---\nname: ignored\ndescription: '{repo} description'\n---\n"

        result = MODULE.build_directory(manifest, fetcher=fetcher, workers=2)
        self.assertEqual([item["name"] for item in result], ["soia-meta-a-skill", "soia-meta-z-skill"])
        self.assertEqual(result[0]["description"], "repo-a description")
        self.assertEqual(
            result[0]["install_cmd"],
            "npx skills add soia-team/repo-a -g -a '*' -s soia-meta-a-skill -y",
        )

    def test_check_mode_comparison_does_not_overwrite_stale_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="router-index-") as temp:
            output = Path(temp) / "directory.json"
            output.write_text("stale\n", encoding="utf-8")
            self.assertFalse(MODULE.check_or_write(output, "fresh\n", check=True))
            self.assertEqual(output.read_text(encoding="utf-8"), "stale\n")

    def test_description_requires_scalar_frontmatter_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "description"):
            MODULE.frontmatter_description("---\nname: example\n---\n")


if __name__ == "__main__":
    unittest.main()
