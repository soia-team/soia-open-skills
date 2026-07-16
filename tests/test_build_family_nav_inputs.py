#!/usr/bin/env python3
"""Contract tests for family-navigation input construction from scan JSONL."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "soia-pkm-alipan-curator"
    / "scripts"
    / "build_family_nav_inputs.py"
)
URL_PREFIX = "https://www.alipan.com/drive/file/all/backup/"


def identifier(number: int) -> str:
    return f"{number:040x}"


def directory(parent: str, name: str, number: int | None) -> dict[str, object]:
    return {"path": parent, "name": name, "id": identifier(number) if number else None, "dir": True}


def file(parent: str, name: str, number: int) -> dict[str, object]:
    return {"path": parent, "name": name, "id": identifier(number), "dir": False, "size": 1}


def guide_spec(
    *,
    roots: list[dict[str, str]] | None = None,
    exclude_paths: list[str] | None = None,
    exclude_name_patterns: list[str] | None = None,
    selection_mode: str | None = "deepest_leaves",
) -> dict[str, object]:
    guide: dict[str, object] = {
        "guides": [
            {
                "id": "family-learning",
                "scope_root": "/family",
                "title": "家庭学习导航",
                "summary": "从一套资源开始，持续使用后再评估。",
                "generatedAt": "2026-07-15",
                "partition": "家庭学习",
                "guidance": [{"label": "先选主线", "text": "每次只启用一套课程。"}],
                "row_defaults": {
                    "category": "学习资源",
                    "audience": "待家长确认",
                    "type": "待确认",
                    "usage": "按课程说明使用",
                    "pace": "待家长确认",
                },
                "resource_roots": roots or [],
            }
        ]
    }
    if selection_mode is not None:
        guide["guides"][0]["selection_mode"] = selection_mode
    if exclude_paths is not None:
        guide["guides"][0]["exclude_paths"] = exclude_paths
    if exclude_name_patterns is not None:
        guide["guides"][0]["exclude_name_patterns"] = exclude_name_patterns
    return guide


class BuildFamilyNavigationInputsTests(unittest.TestCase):
    def run_builder(
        self,
        root: Path,
        rows: list[dict[str, object]],
        spec: dict[str, object],
        *,
        scan_errors: str | None = "",
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        scan = root / "fresh-scan.jsonl"
        guide = root / "guide.json"
        scan.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        if scan_errors is not None:
            Path(f"{scan}.errors").write_text(scan_errors, encoding="utf-8")
        guide.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--scan",
                str(scan),
                "--guide-spec",
                str(guide),
                "--out-dir",
                str(root / "out"),
                "--url-prefix",
                URL_PREFIX,
                *(extra_args or []),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_selects_directory_units_and_keeps_file_id_evidence(self) -> None:
        rows = [
            directory("/family", "10_数学", 1),
            directory("/family/10_数学", "数学启蒙课", 2),
            file("/family/10_数学/数学启蒙课", "第01集.mp4", 3),
            file("/family/10_数学/数学启蒙课", "第01集.srt", 4),
            directory("/family", "20_语言", 5),
            directory("/family", "30_完整课程", 6),
            directory("/family/30_完整课程", "第01章", 7),
            file("/family/30_完整课程/第01章", "第01集.mp4", 8),
        ]
        spec = guide_spec(
            roots=[
                {
                    "path": "/family/30_完整课程",
                    "category": "完整课程",
                    "type": "视频课程包",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(root, rows, spec)
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads(result.stdout)
            self.assertEqual(status["outputs"][0]["rows"], 3)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        selected = {row["name"]: row for row in document["rows"]}
        self.assertEqual(set(selected), {"数学启蒙课", "20_语言", "30_完整课程"})
        self.assertNotIn("第01集.mp4", selected)
        self.assertNotIn("第01集.srt", selected)
        self.assertEqual(selected["30_完整课程"]["category"], "完整课程")
        self.assertEqual(selected["30_完整课程"]["type"], "视频课程包")
        self.assertEqual(selected["数学启蒙课"]["file_id"], identifier(2))
        self.assertEqual(selected["数学启蒙课"]["url"], f"{URL_PREFIX}{identifier(2)}")

    def test_empty_resource_roots_without_selection_mode_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(
                Path(temporary),
                [directory("/family", "数学课程", 1)],
                guide_spec(selection_mode=None),
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resource_roots must contain at least one directory", result.stderr)

    def test_explicit_resource_roots_select_only_declared_roots(self) -> None:
        rows = [
            directory("/family", "数学课程", 1),
            directory("/family", "英语课程", 2),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(
                root,
                rows,
                guide_spec(
                    roots=[{"path": "/family/数学课程", "category": "数学"}],
                    selection_mode="explicit_roots",
                ),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        self.assertEqual([row["name"] for row in document["rows"]], ["数学课程"])

    def test_explicit_deepest_leaves_mode_preserves_automatic_selection(self) -> None:
        rows = [
            directory("/family", "数学", 1),
            directory("/family/数学", "启蒙课", 2),
            file("/family/数学/启蒙课", "第01集.mp4", 3),
            directory("/family", "英语", 4),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(
                root, rows, guide_spec(selection_mode="deepest_leaves")
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        self.assertEqual([row["name"] for row in document["rows"]], ["启蒙课", "英语"])

    def test_unknown_selection_mode_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(
                Path(temporary),
                [directory("/family", "数学课程", 1)],
                guide_spec(selection_mode="all_directories"),
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("selection_mode", result.stderr)
        self.assertIn("unsupported", result.stderr)

    def test_rejects_duplicate_file_ids(self) -> None:
        rows = [
            directory("/family", "课程A", 1),
            file("/family/课程A", "第01集.mp4", 1),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(Path(temporary), rows, guide_spec())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate file_id", result.stderr)

    def test_requires_scan_error_sidecar_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(
                root,
                [directory("/family", "数学课程", 1)],
                guide_spec(),
                scan_errors=None,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scan error sidecar is missing", result.stderr)

    def test_missing_sidecar_override_is_recorded_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(
                root,
                [directory("/family", "数学课程", 1)],
                guide_spec(),
                scan_errors=None,
                extra_args=["--allow-missing-scan-errors"],
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads(result.stdout)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        expected = {
            "status": "missing-overridden",
            "override": "allow-missing-scan-errors",
            "error_count": 0,
            "listing_failure_paths": [],
            "sha256": None,
        }
        self.assertEqual({key: status["scan_errors"][key] for key in expected}, expected)
        self.assertEqual(document["scan_errors"], status["scan_errors"])

    def test_nonempty_sidecar_fails_closed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(
                Path(temporary),
                [directory("/family", "数学课程", 1)],
                guide_spec(),
                scan_errors="[12:00:00] LIST_FAIL '/family/数学课程' rc=1\n",
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contains 1 failed listing", result.stderr)

    def test_scan_error_override_rejects_unparseable_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(
                Path(temporary),
                [directory("/family", "数学课程", 1)],
                guide_spec(),
                scan_errors="unstructured scanner failure\n",
                extra_args=["--allow-scan-errors"],
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported scan error entry", result.stderr)

    def test_scan_error_override_audits_and_excludes_failed_leaf(self) -> None:
        rows = [
            directory("/family", "数学课程", 1),
            directory("/family", "损坏课程", 2),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(
                root,
                rows,
                guide_spec(),
                scan_errors="[12:00:00] LIST_FAIL '/family/损坏课程' rc=1\n",
                extra_args=["--allow-scan-errors"],
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads(result.stdout)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        self.assertEqual([row["name"] for row in document["rows"]], ["数学课程"])
        self.assertEqual(status["scan_errors"]["status"], "errors-overridden")
        self.assertEqual(status["scan_errors"]["override"], "allow-scan-errors")
        self.assertEqual(status["scan_errors"]["listing_failure_paths"], ["/family/损坏课程"])
        self.assertEqual(document["scan_errors"], status["scan_errors"])

    def test_scan_error_override_rejects_resource_root_with_failed_listing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(
                Path(temporary),
                [directory("/family", "损坏课程", 1)],
                guide_spec(roots=[{"path": "/family/损坏课程"}]),
                scan_errors="[12:00:00] LIST_FAIL '/family/损坏课程' rc=1\n",
                extra_args=["--allow-scan-errors"],
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("overlaps a failed scan listing", result.stderr)

    def test_rejects_selected_resource_without_file_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(
                Path(temporary), [directory("/family", "课程A", None)], guide_spec()
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing file_id", result.stderr)

    def test_rejects_resource_root_outside_guide_scope(self) -> None:
        rows = [
            directory("/family", "课程A", 1),
            directory("/other", "课程B", 2),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_builder(
                Path(temporary),
                rows,
                guide_spec(roots=[{"path": "/other/课程B"}]),
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside scope_root", result.stderr)

    def test_default_excludes_empty_guide_leaf_and_audits_it(self) -> None:
        rows = [
            directory("/family", "01_先看这里", 1),
            directory("/family", "01_先看这里课程", 2),
            directory("/family", "数学课程", 3),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(root, rows, guide_spec())
            self.assertEqual(result.returncode, 0, result.stderr)
            status = json.loads(result.stdout)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        self.assertEqual({row["name"] for row in document["rows"]}, {"01_先看这里课程", "数学课程"})
        self.assertEqual(document["excluded_directories"], [
            {
                "path": "/family/01_先看这里",
                "name": "01_先看这里",
                "matched_by": [{
                    "field": "exclude_name_patterns",
                    "value": "^01_先看这里$",
                    "source": "default",
                    "matched_path": "/family/01_先看这里",
                }],
            }
        ])
        self.assertEqual(status["outputs"][0]["excluded_directories"], document["excluded_directories"])

    def test_exclude_paths_excludes_a_directory_tree_and_audits_all_affected_paths(self) -> None:
        rows = [
            directory("/family", "导航资料", 1),
            directory("/family/导航资料", "内部说明", 2),
            directory("/family", "数学课程", 3),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(
                root, rows, guide_spec(exclude_paths=["/family/导航资料"])
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        self.assertEqual([row["name"] for row in document["rows"]], ["数学课程"])
        self.assertEqual(
            [item["path"] for item in document["excluded_directories"]],
            ["/family/导航资料", "/family/导航资料/内部说明"],
        )
        self.assertEqual(
            document["excluded_directories"][1]["matched_by"][0]["matched_path"],
            "/family/导航资料",
        )

    def test_exclude_name_patterns_uses_regular_expression_without_harming_resources(self) -> None:
        rows = [
            directory("/family", "说明-内部", 1),
            directory("/family", "英语课程", 2),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.run_builder(
                root,
                rows,
                guide_spec(exclude_name_patterns=[r"^说明(?:-|_).+$"]),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads((root / "out" / "family-learning.json").read_text(encoding="utf-8"))

        self.assertEqual([row["name"] for row in document["rows"]], ["英语课程"])
        self.assertEqual(document["excluded_directories"][0]["matched_by"][0]["value"], r"^说明(?:-|_).+$")


if __name__ == "__main__":
    unittest.main()
