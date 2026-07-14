#!/usr/bin/env python3
"""Regression tests for curator structure closure checks."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts" / "audit_structure.py"
SPEC = importlib.util.spec_from_file_location("curator_structure_audit", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


ROWS = [
    {"path": "/learning", "name": "10_business", "id": "a", "dir": True},
    {"path": "/learning", "name": "20_communication", "id": "b", "dir": True},
    {"path": "/learning/10_business", "name": "01_guide", "id": "c", "dir": True},
    {"path": "/learning/10_business", "name": "economics", "id": "d", "dir": True},
    {"path": "/learning/20_communication", "name": "01_guide", "id": "e", "dir": True},
    {"path": "/learning/20_communication", "name": "10_speaking", "id": "f", "dir": True},
]


class StructureAuditTests(unittest.TestCase):
    def test_numbering_reports_unprefixed_business_directory(self) -> None:
        checked, violations = audit.audit_numbering(
            ROWS,
            [{"parent": "/learning/10_business", "pattern": r"^\d{2}_"}],
        )
        self.assertEqual(checked, 2)
        self.assertEqual([item["name"] for item in violations], ["economics"])

    def test_guide_closure_reports_missing_guide(self) -> None:
        rows = [row for row in ROWS if row.get("id") != "e"]
        checked, violations = audit.audit_guides(
            rows,
            [{
                "parent": "/learning",
                "child_pattern": r"^\d{2}_",
                "guide_name": "01_guide",
            }],
        )
        self.assertEqual(checked, 2)
        self.assertEqual(violations[0]["parent"], "/learning/20_communication")

    def test_unclear_items_must_be_inside_review_root_and_verified(self) -> None:
        checked, violations = audit.audit_unclear_manifest(
            [
                {
                    "source": "/learning/unknown.pdf",
                    "reason": "topic unclear",
                    "target": "/review/topic/unknown.pdf",
                    "status": "verified",
                },
                {
                    "source": "/learning/pending.pdf",
                    "reason": "content unreadable",
                    "target": "/elsewhere/pending.pdf",
                    "status": "planned",
                },
            ],
            "/review",
            final=True,
            scan_rows=[
                {"path": "/review/topic", "name": "unknown.pdf", "id": "g", "dir": False},
            ],
        )
        self.assertEqual(checked, 2)
        self.assertEqual(
            {item["kind"] for item in violations},
            {
                "unclear_outside_review_root",
                "unclear_not_verified",
                "unclear_target_missing",
            },
        )

    def test_contract_requires_explicit_guide_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "guide_name is required"):
            audit.validate_contract({
                "numbered_layers": [],
                "guide_layers": [
                    {"parent": "/learning", "child_pattern": r"^\d{2}_"},
                ],
            })

    def test_chunking_reports_flat_series_over_configured_limit(self) -> None:
        rows = [
            {"path": "/learning/course", "name": f"{number:03}.mp3", "dir": False}
            for number in range(1, 22)
        ]
        checked, violations = audit.audit_chunks(
            rows,
            [{"parent": "/learning/course", "child_pattern": r"^\d{2}_", "max_items": 20}],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations[0]["kind"], "series_exceeds_chunk_limit")
        self.assertEqual(violations[0]["item_count"], 21)

    def test_chunking_reports_loose_files_and_oversized_chunk(self) -> None:
        rows = [
            {"path": "/learning/course", "name": "10_001-020", "id": "a", "dir": True},
            {"path": "/learning/course", "name": "20_021-041", "id": "b", "dir": True},
            {"path": "/learning/course", "name": "loose.mp3", "id": "c", "dir": False},
        ]
        rows.extend(
            {"path": "/learning/course/10_001-020", "name": f"{number:03}.mp3", "dir": False}
            for number in range(1, 21)
        )
        rows.extend(
            {"path": "/learning/course/20_021-041", "name": f"{number:03}.mp3", "dir": False}
            for number in range(21, 42)
        )
        checked, violations = audit.audit_chunks(
            rows,
            [{"parent": "/learning/course", "child_pattern": r"^\d{2}_", "max_items": 20}],
        )
        self.assertEqual(checked, 2)
        self.assertEqual(
            {item["kind"] for item in violations},
            {"direct_items_outside_chunks", "chunk_exceeds_limit"},
        )

    def test_chunking_accepts_bounded_groups(self) -> None:
        rows = [
            {"path": "/learning/course", "name": "10_001-020", "id": "a", "dir": True},
            {"path": "/learning/course", "name": "20_021-035", "id": "b", "dir": True},
        ]
        rows.extend(
            {"path": "/learning/course/10_001-020", "name": f"{number:03}.mp3", "dir": False}
            for number in range(1, 21)
        )
        rows.extend(
            {"path": "/learning/course/20_021-035", "name": f"{number:03}.mp3", "dir": False}
            for number in range(21, 36)
        )
        checked, violations = audit.audit_chunks(
            rows,
            [{"parent": "/learning/course", "child_pattern": r"^\d{2}_", "max_items": 20}],
        )
        self.assertEqual(checked, 2)
        self.assertEqual(violations, [])

    def test_contract_requires_positive_chunk_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_items must be a positive integer"):
            audit.validate_contract({
                "chunk_layers": [
                    {"parent": "/learning/course", "child_pattern": r"^\d{2}_", "max_items": 0},
                ],
            })

    def test_chunking_rejects_undeclared_sibling_directory(self) -> None:
        rows = [
            {"path": "/learning/course", "name": "10_001-020", "id": "a", "dir": True},
            {"path": "/learning/course", "name": "attachments", "id": "b", "dir": True},
            {"path": "/learning/course/10_001-020", "name": "001.mp3", "dir": False},
            {"path": "/learning/course/attachments", "name": "021.mp3", "dir": False},
        ]
        checked, violations = audit.audit_chunks(
            rows,
            [{"parent": "/learning/course", "child_pattern": r"^\d{2}_", "max_items": 20}],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations[0]["kind"], "unexpected_non_chunk_directory")

    def test_chunking_allows_explicitly_excluded_technical_directory(self) -> None:
        rows = [
            {"path": "/learning/course", "name": "10_001-020", "id": "a", "dir": True},
            {"path": "/learning/course", "name": "assets", "id": "b", "dir": True},
            {"path": "/learning/course/10_001-020", "name": "001.mp3", "dir": False},
            {"path": "/learning/course/assets", "name": "cover.jpg", "dir": False},
        ]
        _, violations = audit.audit_chunks(
            rows,
            [{
                "parent": "/learning/course",
                "child_pattern": r"^\d{2}_",
                "max_items": 20,
                "exclude": ["assets"],
            }],
        )
        self.assertEqual(violations, [])

    def test_cli_fails_for_undeclared_sibling_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = root / "scan.jsonl"
            contract = root / "contract.json"
            scan.write_text(
                "\n".join([
                    json.dumps({"path": "/course", "name": "10_001-020", "dir": True}),
                    json.dumps({"path": "/course", "name": "attachments", "dir": True}),
                    json.dumps({"path": "/course/10_001-020", "name": "001.mp3", "dir": False}),
                ]) + "\n",
                encoding="utf-8",
            )
            contract.write_text(json.dumps({
                "chunk_layers": [{
                    "parent": "/course",
                    "child_pattern": r"^\d{2}_",
                    "max_items": 20,
                }],
            }), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(SCRIPT), "--scan", str(scan), "--contract", str(contract)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(process.returncode, 1)
        self.assertIn("unexpected_non_chunk_directory", process.stdout)


if __name__ == "__main__":
    unittest.main()
