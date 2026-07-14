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

    def test_guide_closure_can_require_a_real_navigation_file(self) -> None:
        checked, violations = audit.audit_guides(
            ROWS,
            [{
                "parent": "/learning",
                "child_pattern": r"^10_",
                "guide_name": "01_guide",
                "file_pattern": r"\.xlsx$",
            }],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations[0]["kind"], "missing_guide_file")

    def test_guide_layer_does_not_require_a_guide_inside_the_guide_directory(self) -> None:
        rows = [
            {"path": "/learning", "name": "01_guide", "id": "root-guide", "dir": True},
            {"path": "/learning", "name": "10_course", "id": "course", "dir": True},
            {"path": "/learning/10_course", "name": "01_guide", "id": "course-guide", "dir": True},
        ]
        checked, violations = audit.audit_guides(
            rows,
            [{"parent": "/learning", "child_pattern": r"^\d{2}_", "guide_name": "01_guide"}],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations, [])

    def test_guide_layer_rejects_no_matching_children_by_default(self) -> None:
        checked, violations = audit.audit_guides(
            ROWS,
            [{
                "parent": "/learning",
                "child_pattern": r"^90_",
                "guide_name": "01_guide",
                "file_pattern": r"\.xlsx$",
            }],
        )
        self.assertEqual(checked, 0)
        self.assertEqual(violations[0]["kind"], "guide_scope_has_no_matching_children")

        _, allowed = audit.audit_guides(
            ROWS,
            [{
                "parent": "/learning",
                "child_pattern": r"^90_",
                "guide_name": "01_guide",
                "file_pattern": r"\.xlsx$",
                "allow_empty": True,
            }],
        )
        self.assertEqual(allowed, [])

    def test_required_guide_checks_the_learning_root_and_file(self) -> None:
        rows = [
            {"path": "/learning", "name": "01_guide", "id": "guide", "dir": True},
            {
                "path": "/learning/01_guide",
                "name": "start-here.xlsx",
                "id": "file",
                "dir": False,
                "size": 128,
            },
        ]
        checked, violations = audit.audit_required_guides(
            rows,
            [{"parent": "/learning", "guide_name": "01_guide", "file_pattern": r"\.xlsx$"}],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations, [])

        checked, violations = audit.audit_required_guides(
            rows[:1],
            [{"parent": "/learning", "guide_name": "01_guide", "file_pattern": r"\.xlsx$"}],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations[0]["kind"], "missing_required_guide_file")

    def test_required_guide_rejects_a_zero_byte_placeholder(self) -> None:
        rows = [
            {"path": "/learning", "name": "01_guide", "id": "guide", "dir": True},
            {
                "path": "/learning/01_guide",
                "name": "start-here.xlsx",
                "id": "file",
                "dir": False,
                "size": 0,
            },
        ]
        _, violations = audit.audit_required_guides(
            rows,
            [{"parent": "/learning", "guide_name": "01_guide", "file_pattern": r"\.xlsx$"}],
        )
        self.assertEqual(violations[0]["kind"], "required_guide_file_too_small")

    def test_required_artifact_verifies_exact_cloud_identity(self) -> None:
        rows = [{
            "path": "/learning/01_guide",
            "name": "start-here.xlsx",
            "id": "file-id",
            "dir": False,
            "size": 128,
            "sha1": "A" * 40,
        }]
        checked, violations = audit.audit_required_artifacts(
            rows,
            [{
                "path": "/learning/01_guide/start-here.xlsx",
                "id": "file-id",
                "size": 128,
                "sha1": "a" * 40,
            }],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations, [])

        _, violations = audit.audit_required_artifacts(
            rows,
            [{
                "path": "/learning/01_guide/start-here.xlsx",
                "id": "other-id",
                "size": 129,
                "sha1": "B" * 40,
            }],
        )
        self.assertEqual(
            {item["kind"] for item in violations},
            {
                "required_artifact_id_mismatch",
                "required_artifact_size_mismatch",
                "required_artifact_sha1_mismatch",
            },
        )

    def test_required_artifact_reports_missing_and_duplicate_paths(self) -> None:
        rule = [{"path": "/learning/file.xlsx", "size": 1, "sha1": "A" * 40}]
        _, missing = audit.audit_required_artifacts([], rule)
        self.assertEqual(missing[0]["kind"], "required_artifact_missing")
        duplicate_rows = [
            {"path": "/learning", "name": "file.xlsx", "dir": False},
            {"path": "/learning", "name": "file.xlsx", "dir": False},
        ]
        _, duplicate = audit.audit_required_artifacts(duplicate_rows, rule)
        self.assertEqual(duplicate[0]["kind"], "required_artifact_duplicate_path")

    def test_resource_map_requires_clickable_markdown_cloud_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path = root / "map.md"
            prefix = "https://drive.example/files/"
            map_path.write_text(
                "Claims it is clickable: https://drive.example/files/root-id\n",
                encoding="utf-8",
            )
            rule = [{
                "path": "map.md",
                "url_prefix": prefix,
                "required_ids": ["root-id", "course-id"],
                "min_links": 2,
            }]
            checked, violations = audit.audit_resource_maps(rule, root)
            self.assertEqual(checked, 1)
            self.assertEqual(
                {item["kind"] for item in violations},
                {
                    "resource_map_has_too_few_cloud_links",
                    "resource_map_missing_required_link",
                },
            )

            map_path.write_text(
                "[root](https://drive.example/files/root-id)\n"
                "[course](https://drive.example/files/course-id)\n",
                encoding="utf-8",
            )
            _, violations = audit.audit_resource_maps(rule, root)
            self.assertEqual(violations, [])

    def test_contract_rejects_incomplete_artifact_and_map_rules(self) -> None:
        with self.assertRaisesRegex(ValueError, "sha1 must be 40 hexadecimal"):
            audit.validate_contract({
                "required_artifacts": [{"path": "/file.xlsx", "size": 1, "sha1": "bad"}],
            })
        with self.assertRaisesRegex(ValueError, "required_ids must be a non-empty array"):
            audit.validate_contract({
                "resource_maps": [{"path": "map.md", "url_prefix": "https://example/"}],
            })

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

    def test_unclear_item_can_be_an_intact_directory_package(self) -> None:
        checked, violations = audit.audit_unclear_manifest(
            [{
                "source": "/learning/ambiguous-package",
                "reason": "package contents are incomplete",
                "target": "/review/incomplete/ambiguous-package",
                "status": "verified",
            }],
            "/review",
            final=True,
            scan_rows=[{
                "path": "/review/incomplete",
                "name": "ambiguous-package",
                "id": "package-dir",
                "dir": True,
            }],
        )
        self.assertEqual(checked, 1)
        self.assertEqual(violations, [])

    def test_contract_requires_explicit_guide_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "guide_name is required"):
            audit.validate_contract({
                "numbered_layers": [],
                "guide_layers": [
                    {"parent": "/learning", "child_pattern": r"^\d{2}_"},
                ],
            })

    def test_contract_requires_explicit_guide_file_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "file_pattern is required"):
            audit.validate_contract({
                "required_guides": [{"parent": "/learning", "guide_name": "01_guide"}],
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

    def test_flat_series_discovery_finds_an_undeclared_course(self) -> None:
        rows = [
            {"path": "/learning/course-a", "name": f"{number:03}.mp4", "dir": False}
            for number in range(1, 9)
        ]
        stats, violations = audit.audit_flat_series_discovery(
            rows,
            [{"root": "/learning", "max_items": 7, "file_pattern": r"\.mp4$"}],
            chunk_rules=[],
        )
        self.assertEqual(stats["matching_parents"], 1)
        self.assertEqual(stats["violating_parents"], 1)
        self.assertEqual(violations[0]["kind"], "undeclared_flat_series")
        self.assertEqual(violations[0]["parent"], "/learning/course-a")

    def test_flat_series_discovery_supports_the_drive_root(self) -> None:
        rows = [
            {"path": "/nested/course", "name": f"{number:03}.mp4", "dir": False}
            for number in range(1, 9)
        ]
        stats, violations = audit.audit_flat_series_discovery(
            rows,
            [{"root": "/", "max_items": 7, "file_pattern": r"\.mp4$"}],
            chunk_rules=[],
        )
        self.assertEqual(stats["matching_parents"], 1)
        self.assertEqual(violations[0]["parent"], "/nested/course")

    def test_flat_series_discovery_rejects_aggregate_scan_rows(self) -> None:
        rows = [{
            "path": "/learning",
            "name": "course-a",
            "dir": True,
            "agg_files": 200,
            "agg_size": 1000,
        }]
        stats, violations = audit.audit_flat_series_discovery(
            rows,
            [{"root": "/learning", "max_items": 7, "allow_empty": True}],
            chunk_rules=[],
        )
        self.assertEqual(stats["aggregate_rows"], 1)
        self.assertEqual(violations[0]["kind"], "aggregate_scan_rows_in_discovery_scope")

    def test_flat_series_discovery_rejects_a_missing_scope_by_default(self) -> None:
        _, violations = audit.audit_flat_series_discovery(
            [],
            [{"root": "/learning", "max_items": 7}],
            chunk_rules=[],
        )
        self.assertEqual(violations[0]["kind"], "discovery_scope_has_no_file_rows")

    def test_flat_series_discovery_rejects_a_path_filter_matching_no_parent(self) -> None:
        rows = [{"path": "/learning/course-a", "name": "001.mp4", "dir": False}]
        _, violations = audit.audit_flat_series_discovery(
            rows,
            [{"root": "/learning", "max_items": 7, "path_pattern": r"/missing$"}],
            chunk_rules=[],
        )
        self.assertEqual(violations[0]["kind"], "discovery_scope_has_no_file_rows")

    def test_flat_series_discovery_rejects_file_pattern_matching_no_file(self) -> None:
        rows = [{"path": "/learning/course-a", "name": "001.mp3", "dir": False}]
        stats, violations = audit.audit_flat_series_discovery(
            rows,
            [{"root": "/learning", "max_items": 7, "file_pattern": r"\.mp4$"}],
            chunk_rules=[],
        )
        self.assertEqual(stats["matching_parents"], 0)
        self.assertEqual(violations[0]["kind"], "discovery_scope_has_no_matching_files")

    def test_flat_series_discovery_honors_explicit_semantic_bucket_exception(self) -> None:
        rows = [
            {"path": "/learning/podcast/2026-07", "name": f"day-{number:02}.mp3", "dir": False}
            for number in range(1, 10)
        ]
        stats, violations = audit.audit_flat_series_discovery(
            rows,
            [{
                "root": "/learning",
                "max_items": 7,
                "file_pattern": r"\.mp3$",
                "exclude_path_patterns": [r"/\d{4}-\d{2}$"],
            }],
            chunk_rules=[],
        )
        self.assertEqual(stats["matching_parents"], 1)
        self.assertEqual(stats["skipped_by_exception"], 1)
        self.assertEqual(violations, [])

    def test_flat_series_discovery_skips_explicit_chunk_contracts(self) -> None:
        rows = [
            {"path": "/learning/course-a", "name": f"{number:03}.mp4", "dir": False}
            for number in range(1, 9)
        ]
        stats, violations = audit.audit_flat_series_discovery(
            rows,
            [{"root": "/learning", "max_items": 7}],
            chunk_rules=[{
                "parent": "/learning/course-a",
                "child_pattern": r"^\d{2}_",
                "max_items": 7,
            }],
        )
        self.assertEqual(stats["matching_parents"], 1)
        self.assertEqual(stats["skipped_by_chunk"], 1)
        self.assertEqual(violations, [])

    def test_flat_series_discovery_does_not_skip_a_looser_chunk_contract(self) -> None:
        rows = [
            {"path": "/learning/course-a", "name": f"{number:03}.mp4", "dir": False}
            for number in range(1, 9)
        ]
        stats, violations = audit.audit_flat_series_discovery(
            rows,
            [{"root": "/learning", "max_items": 7, "file_pattern": r"\.mp4$"}],
            chunk_rules=[{
                "parent": "/learning/course-a",
                "child_pattern": r"^\d{2}_",
                "max_items": 100,
            }],
        )
        self.assertEqual(stats["skipped_by_chunk"], 0)
        self.assertEqual(violations[0]["kind"], "undeclared_flat_series")

    def test_contract_requires_positive_discovery_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_items must be a positive integer"):
            audit.validate_contract({
                "flat_series_discovery": [{"root": "/learning", "max_items": 0}],
            })

    def test_contract_rejects_an_empty_discovery_exception(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a non-empty string"):
            audit.validate_contract({
                "flat_series_discovery": [{
                    "root": "/learning",
                    "max_items": 7,
                    "exclude_path_patterns": [""],
                }],
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
        self.assertIn("flat_series_matching_parents", process.stdout)
        self.assertIn("flat_series_skipped_by_exception", process.stdout)
        self.assertNotIn("flat_series_candidates", process.stdout)

    def test_cli_final_fails_when_scan_error_sidecar_is_nonempty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = root / "scan.jsonl"
            contract = root / "contract.json"
            scan.write_text(
                json.dumps({"path": "/learning", "name": "file.mp4", "dir": False}) + "\n",
                encoding="utf-8",
            )
            Path(str(scan) + ".errors").write_text("LIST_FAIL /learning/course\n", encoding="utf-8")
            contract.write_text(json.dumps({}), encoding="utf-8")
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--scan",
                    str(scan),
                    "--contract",
                    str(contract),
                    "--final",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(process.returncode, 1)
        self.assertIn("scan_errors_present", process.stdout)

    def test_cli_final_fails_when_scan_error_sidecar_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = root / "scan.jsonl"
            contract = root / "contract.json"
            scan.write_text(
                json.dumps({"path": "/learning", "name": "file.mp4", "dir": False}) + "\n",
                encoding="utf-8",
            )
            contract.write_text(json.dumps({}), encoding="utf-8")
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--scan",
                    str(scan),
                    "--contract",
                    str(contract),
                    "--final",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(process.returncode, 1)
        self.assertIn("scan_error_sidecar_missing", process.stdout)

    def test_cli_explicit_missing_scan_error_sidecar_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = root / "scan.jsonl"
            contract = root / "contract.json"
            scan.write_text(
                json.dumps({"path": "/learning", "name": "file.mp4", "dir": False}) + "\n",
                encoding="utf-8",
            )
            contract.write_text(json.dumps({}), encoding="utf-8")
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--scan",
                    str(scan),
                    "--contract",
                    str(contract),
                    "--scan-errors",
                    str(root / "missing.errors"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(process.returncode, 1)
        self.assertIn("scan_error_sidecar_missing", process.stdout)

    def test_cli_final_can_explicitly_allow_missing_scan_error_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = root / "scan.jsonl"
            contract = root / "contract.json"
            scan.write_text(
                json.dumps({"path": "/learning", "name": "file.mp4", "dir": False}) + "\n",
                encoding="utf-8",
            )
            contract.write_text(json.dumps({}), encoding="utf-8")
            process = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--scan",
                    str(scan),
                    "--contract",
                    str(contract),
                    "--final",
                    "--allow-missing-scan-errors",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
