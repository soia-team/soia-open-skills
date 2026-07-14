#!/usr/bin/env python3
"""Regression tests for exact required chunk groups."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts" / "audit_structure.py"
SPEC = importlib.util.spec_from_file_location("required_chunk_structure_audit", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


PARENT = "/learning/course"
CHILD_PATTERN = r"^\d{2}_\d{3}(?:-\d{3})?$"


def chunk_rows(*names: str) -> list[dict]:
    rows: list[dict] = []
    for index, name in enumerate(names, 1):
        rows.extend([
            {"path": PARENT, "name": name, "id": f"dir-{index}", "dir": True},
            {"path": f"{PARENT}/{name}", "name": f"{index:03}.mp4", "dir": False},
        ])
    return rows


def chunk_rule(required_children: list[str]) -> dict:
    return {
        "parent": PARENT,
        "child_pattern": CHILD_PATTERN,
        "count_pattern": r"\.mp4$",
        "max_items": 20,
        "required_children": required_children,
    }


class RequiredChunkStructureTests(unittest.TestCase):
    def test_missing_required_chunk_is_reported(self) -> None:
        _, violations = audit.audit_chunks(
            chunk_rows("10_001-020"),
            [chunk_rule(["10_001-020", "20_021-035"])],
        )
        self.assertEqual([item["kind"] for item in violations], ["missing_required_chunk"])
        self.assertEqual(violations[0]["name"], "20_021-035")

    def test_extra_matching_chunk_is_reported(self) -> None:
        _, violations = audit.audit_chunks(
            chunk_rows("10_001-020", "20_021-035", "30_036-040"),
            [chunk_rule(["10_001-020", "20_021-035"])],
        )
        self.assertEqual([item["kind"] for item in violations], ["unexpected_chunk"])
        self.assertEqual(violations[0]["name"], "30_036-040")

    def test_exact_required_chunks_pass_and_exclude_is_not_required(self) -> None:
        rows = chunk_rows("10_001-020", "20_021-035")
        rows.append({"path": PARENT, "name": "assets", "id": "assets", "dir": True})
        rule = chunk_rule(["10_001-020", "20_021-035"])
        rule["exclude"] = ["assets"]
        checked, violations = audit.audit_chunks(rows, [rule])
        self.assertEqual(checked, 2)
        self.assertEqual(violations, [])

    def test_contract_rejects_invalid_required_children(self) -> None:
        invalid_values = (
            "10_001-020",
            [],
            [""],
            ["   "],
            [10],
        )
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "required_children"
            ):
                rule = chunk_rule(["10_001-020"])
                rule["required_children"] = value
                audit.validate_contract({"chunk_layers": [rule]})

    def test_contract_rejects_duplicate_required_children(self) -> None:
        with self.assertRaisesRegex(ValueError, "required_children must be unique"):
            audit.validate_contract({
                "chunk_layers": [chunk_rule(["10_001-020", "10_001-020"])],
            })

    def test_contract_rejects_required_child_not_matching_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "must match child_pattern"):
            audit.validate_contract({
                "chunk_layers": [chunk_rule(["10_001-020", "chapter-two"])],
            })


if __name__ == "__main__":
    unittest.main()
