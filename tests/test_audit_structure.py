#!/usr/bin/env python3
"""Regression tests for numbering and exact required chunk groups."""

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


def numbered_rows(*names: str) -> list[dict]:
    return [
        {"path": PARENT, "name": name, "id": f"dir-{index}", "dir": True}
        for index, name in enumerate(names, 1)
    ]


def numbered_rule(**overrides: object) -> dict:
    return {
        "parent": PARENT,
        "pattern": r"^\d{2}_",
        **overrides,
    }


class NumberedLayerTests(unittest.TestCase):
    def test_duplicate_numeric_prefix_is_reported_independently_of_pattern(self) -> None:
        _, violations = audit.audit_numbering(
            numbered_rows("10_Alpha", "10Beta", "20_Gamma"),
            [numbered_rule()],
        )
        self.assertEqual(
            [item["kind"] for item in violations],
            ["unnumbered_directory", "duplicate_directory_number"],
        )
        self.assertEqual(violations[1]["number"], 10)
        self.assertEqual(violations[1]["names"], ["10_Alpha", "10Beta"])

    def test_default_numbered_layer_allows_gaps(self) -> None:
        _, violations = audit.audit_numbering(
            numbered_rows("01_Alpha", "03_Gamma"),
            [numbered_rule()],
        )
        self.assertEqual(violations, [])

    def test_contiguous_numbered_layer_reports_missing_numbers_from_default_start(self) -> None:
        _, violations = audit.audit_numbering(
            numbered_rows("01_Alpha", "03_Gamma"),
            [numbered_rule(contiguous=True)],
        )
        self.assertEqual([item["kind"] for item in violations], ["non_contiguous_directory_numbers"])
        self.assertEqual(violations[0]["missing_numbers"], [2])
        self.assertEqual(violations[0]["start"], 1)

    def test_contiguous_numbered_layer_honors_custom_start(self) -> None:
        _, violations = audit.audit_numbering(
            numbered_rows("10_Alpha", "11_Beta", "13_Gamma"),
            [numbered_rule(contiguous=True, start=10)],
        )
        self.assertEqual(violations[0]["missing_numbers"], [12])

    def test_contiguous_numbered_layer_accepts_a_ten_step_contract(self) -> None:
        _, violations = audit.audit_numbering(
            numbered_rows("10_Alpha", "20_Beta"),
            [numbered_rule(contiguous=True, start=10, step=10)],
        )
        self.assertEqual(violations, [])

    def test_contiguous_numbered_layer_reports_a_gap_at_contract_step(self) -> None:
        _, violations = audit.audit_numbering(
            numbered_rows("10_Alpha", "30_Gamma"),
            [numbered_rule(contiguous=True, start=10, step=10)],
        )
        self.assertEqual([item["kind"] for item in violations], ["non_contiguous_directory_numbers"])
        self.assertEqual(violations[0]["missing_numbers"], [20])
        self.assertEqual(violations[0]["step"], 10)

    def test_contiguous_numbered_layer_rejects_an_off_step_number(self) -> None:
        _, violations = audit.audit_numbering(
            numbered_rows("10_Alpha", "15_Beta"),
            [numbered_rule(contiguous=True, start=10, step=10)],
        )
        self.assertEqual([item["kind"] for item in violations], ["directory_number_off_sequence"])
        self.assertEqual(violations[0]["numbers"], [15])

    def test_contract_rejects_non_positive_numbering_step(self) -> None:
        for value in (0, -10, True):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "step must be a positive integer"
            ):
                audit.validate_contract({"numbered_layers": [numbered_rule(step=value)]})

    def test_excluded_directory_is_not_checked_for_pattern_duplicate_or_continuity(self) -> None:
        checked, violations = audit.audit_numbering(
            numbered_rows("01_Alpha", "02_Beta", "02_Excluded", "notes"),
            [numbered_rule(contiguous=True, exclude=["02_Excluded", "notes"])],
        )
        self.assertEqual(checked, 2)
        self.assertEqual(violations, [])


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
