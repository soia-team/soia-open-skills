#!/usr/bin/env python3
"""Regression tests for the verified-ledger catalog snapshot materializer."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/soia-pkm-alipan-curator/scripts/materialize_catalog_snapshot.py"
SPEC = importlib.util.spec_from_file_location("materialize_catalog_snapshot", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
materializer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = materializer
SPEC.loader.exec_module(materializer)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def result(action: dict, status: str = "verified", **values: object) -> dict:
    return {**action, "status": status, **values}


class MaterializeCatalogSnapshotTests(unittest.TestCase):
    def write_bundle(self, root: Path, initial: list[dict], batches: list[tuple[list[dict], list[dict]]]) -> Path:
        scan = root / "inventory/initial.jsonl"
        write_jsonl(scan, initial)
        declarations = []
        for index, (plan, ledger) in enumerate(batches, 1):
            plan_member = f"actions/{index:02d}.plan.jsonl"
            ledger_member = f"actions/{index:02d}.result.jsonl"
            write_jsonl(root / plan_member, plan)
            write_jsonl(root / ledger_member, ledger)
            declarations.append({"plan": plan_member, "result": ledger_member})
        write_json(root / "run.json", {
            "files": {"initial_scan": "inventory/initial.jsonl"},
            "batches": declarations,
        })
        return scan

    def run_materializer(
        self,
        root: Path,
        scan: Path,
        *,
        root_id: str = "target-id",
        directory_identities: Path | None = None,
    ) -> tuple[Path, Path, Path]:
        output = root / "snapshot/target.jsonl"
        errors = Path(f"{output}.errors")
        provenance = Path(f"{output}.provenance.json")
        args = [
            "--run-dir", str(root), "--initial-scan", str(scan),
            "--target-root", "/target", "--target-root-file-id", root_id,
            "--out", str(output),
        ]
        if directory_identities is not None:
            args.extend(["--directory-identities", str(directory_identities)])
        code = materializer.main(args)
        self.assertEqual(code, 0)
        return output, errors, provenance

    def test_parent_cross_partition_move_relinks_every_descendant(self) -> None:
        initial = [
            {"path": "/", "name": "source", "id": "source-id", "dir": True},
            {"path": "/", "name": "target", "id": "target-id", "dir": True},
            {"path": "/source", "name": "package", "id": "package-id", "dir": True},
            {"path": "/source/package", "name": "lesson.pdf", "id": "lesson-id", "dir": False, "size": 7},
        ]
        move = {"action_id": "MOVE-PACKAGE", "op": "mv", "from": "/source/package", "to": "/target", "file_id": "package-id"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [([move], [result(move)])])
            output, errors, provenance = self.run_materializer(root, scan)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            paths = {row["id"]: materializer.child_path(row["path"], row["name"]) for row in rows}
            evidence = json.loads(provenance.read_text(encoding="utf-8"))
            plan_sha256 = materializer.sha256_file(root / "actions/01.plan.jsonl")
            errors_bytes = errors.read_bytes()

        self.assertEqual(paths, {
            "target-id": "/target",
            "package-id": "/target/package",
            "lesson-id": "/target/package/lesson.pdf",
        })
        self.assertEqual(errors_bytes, b"")
        self.assertEqual(evidence["statistics"], {"entities": 3, "files": 1, "directories": 2, "bytes": 7})
        self.assertEqual(evidence["inputs"]["base_scan"]["path"], "inventory/initial.jsonl")
        self.assertEqual(evidence["inputs"]["plans"], [{
            "batch": 1,
            "path": "actions/01.plan.jsonl",
            "sha256": plan_sha256,
        }])

    def test_mkdir_then_mv_then_rename_uses_executor_path_semantics(self) -> None:
        initial = [
            {"path": "/", "name": "source", "id": "source-id", "dir": True},
            {"path": "/", "name": "target", "id": "target-id", "dir": True},
            {"path": "/source", "name": "readme.txt", "id": "readme-id", "dir": False, "size": 3},
        ]
        make = {"action_id": "MAKE", "op": "mkdir", "to": "/target/incoming"}
        move = {"action_id": "MOVE", "op": "mv", "from": "/source/readme.txt", "to": "/target/incoming", "file_id": "readme-id"}
        rename = {"action_id": "RENAME", "op": "rename", "from": "/target/incoming/readme.txt", "to": "/target/incoming/001_readme.txt", "file_id": "readme-id"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [
                ([make], [result(make, created_file_id="incoming-id")]),
                ([move, rename], [result(move), result(rename, status="completed")]),
            ])
            output, _, _ = self.run_materializer(root, scan)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(
            {row["id"]: materializer.child_path(row["path"], row["name"]) for row in rows},
            {
                "target-id": "/target",
                "incoming-id": "/target/incoming",
                "readme-id": "/target/incoming/001_readme.txt",
            },
        )

    def test_shallow_directory_identity_evidence_closes_historic_mkdir(self) -> None:
        initial = [
            {"path": "/", "name": "source", "id": "source-id", "dir": True},
            {"path": "/source", "name": "lesson.pdf", "id": "lesson-id", "dir": False, "size": 5},
        ]
        make_root = {"action_id": "MAKE-ROOT", "op": "mkdir", "to": "/target"}
        make_child = {"action_id": "MAKE-CHILD", "op": "mkdir", "to": "/target/course"}
        move = {
            "action_id": "MOVE",
            "op": "mv",
            "from": "/source/lesson.pdf",
            "to": "/target/course",
            "file_id": "lesson-id",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(
                root,
                initial,
                [([make_root, make_child, move], [result(make_root), result(make_child), result(move)])],
            )
            identities = root / "verification/directory-identities.jsonl"
            write_jsonl(identities, [
                {"path": "/target", "id": "target-id", "dir": True},
                {"path": "/target/course", "id": "course-id", "dir": True},
            ])
            output, _, provenance = self.run_materializer(
                root,
                scan,
                directory_identities=identities,
            )
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            evidence = json.loads(provenance.read_text(encoding="utf-8"))

        self.assertEqual(
            {row["id"]: materializer.child_path(row["path"], row["name"]) for row in rows},
            {
                "target-id": "/target",
                "course-id": "/target/course",
                "lesson-id": "/target/course/lesson.pdf",
            },
        )
        self.assertIn("directory_identities", evidence["inputs"])
        self.assertEqual(
            evidence["inputs"]["directory_identities"]["path"],
            "verification/directory-identities.jsonl",
        )

    def test_directory_identity_conflicts_fail_closed(self) -> None:
        initial = [{"path": "/", "name": "source", "id": "source-id", "dir": True}]
        make_root = {"action_id": "MAKE-ROOT", "op": "mkdir", "to": "/target"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [([make_root], [result(make_root)])])
            identities = root / "verification/directory-identities.jsonl"
            write_jsonl(identities, [
                {"path": "/target", "id": "wrong-id", "dir": True},
            ])
            with self.assertRaisesRegex(
                materializer.MaterializationError,
                "target root identity conflicts",
            ):
                materializer.materialize(
                    scan,
                    root,
                    "/target",
                    "target-id",
                    identities,
                )

    def test_rejects_destination_name_conflict(self) -> None:
        initial = [
            {"path": "/", "name": "source", "id": "source-id", "dir": True},
            {"path": "/", "name": "target", "id": "target-id", "dir": True},
            {"path": "/source", "name": "same.txt", "id": "source-file", "dir": False, "size": 1},
            {"path": "/target", "name": "same.txt", "id": "target-file", "dir": False, "size": 1},
        ]
        move = {"action_id": "MOVE", "op": "mv", "from": "/source/same.txt", "to": "/target", "file_id": "source-file"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [([move], [result(move)])])
            with self.assertRaisesRegex(materializer.MaterializationError, "path conflict"):
                materializer.materialize(scan, root, "/target", "target-id")

    def test_rejects_unverified_latest_result_and_wrong_identity(self) -> None:
        initial = [
            {"path": "/", "name": "source", "id": "source-id", "dir": True},
            {"path": "/", "name": "target", "id": "target-id", "dir": True},
            {"path": "/source", "name": "one.txt", "id": "one-id", "dir": False, "size": 1},
        ]
        move = {"action_id": "MOVE", "op": "mv", "from": "/source/one.txt", "to": "/target", "file_id": "one-id"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [([move], [result(move, status="failed")])])
            with self.assertRaisesRegex(materializer.MaterializationError, "not materializable"):
                materializer.materialize(scan, root, "/target", "target-id")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad_identity = {**move, "file_id": "other-id"}
            scan = self.write_bundle(root, initial, [([move], [result(bad_identity)])])
            with self.assertRaisesRegex(materializer.MaterializationError, "not registered"):
                materializer.materialize(scan, root, "/target", "target-id")

    def test_rejects_cleanup_in_an_ordinary_batch(self) -> None:
        initial = [{"path": "/", "name": "target", "id": "target-id", "dir": True}]
        cleanup = {"action_id": "CLEAN", "op": "trash", "from": "/target", "to": "/target", "file_id": "target-id"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [([cleanup], [result(cleanup)])])
            with self.assertRaisesRegex(materializer.MaterializationError, "cleanup op"):
                materializer.materialize(scan, root, "/target", "target-id")

    def test_cleanup_batches_are_not_read_as_migration_input(self) -> None:
        initial = [{"path": "/", "name": "target", "id": "target-id", "dir": True}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [])
            write_json(root / "run.json", {
                "files": {"initial_scan": "inventory/initial.jsonl"},
                "batches": [],
                "cleanup_batches": [{
                    "plan": "cleanup/not-read.plan.jsonl",
                    "result": "cleanup/not-read.result.jsonl",
                }],
            })
            output, _, provenance = self.run_materializer(root, scan)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            evidence = json.loads(provenance.read_text(encoding="utf-8"))

        self.assertEqual([row["id"] for row in rows], ["target-id"])
        self.assertEqual(evidence["inputs"]["plans"], [])
        self.assertEqual(evidence["inputs"]["result_ledgers"], [])

    def test_rejects_unclosed_plan_actions_and_extra_ledger_keys(self) -> None:
        initial = [
            {"path": "/", "name": "source", "id": "source-id", "dir": True},
            {"path": "/", "name": "target", "id": "target-id", "dir": True},
            {"path": "/source", "name": "one.txt", "id": "one-id", "dir": False, "size": 1},
        ]
        move = {"action_id": "MOVE", "op": "mv", "from": "/source/one.txt", "to": "/target", "file_id": "one-id"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [([move], [])])
            with self.assertRaisesRegex(materializer.MaterializationError, "unclosed action"):
                materializer.materialize(scan, root, "/target", "target-id")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extra = {**move, "action_id": "EXTRA"}
            scan = self.write_bundle(root, initial, [([move], [result(move), result(extra)])])
            with self.assertRaisesRegex(materializer.MaterializationError, "not registered"):
                materializer.materialize(scan, root, "/target", "target-id")

    def test_repeated_materialization_is_byte_identical(self) -> None:
        initial = [
            {"path": "/", "name": "target", "id": "target-id", "dir": True},
            {"path": "/target", "name": "old.txt", "id": "old-id", "dir": False, "size": 11},
        ]
        rename = {"action_id": "RENAME", "op": "rename", "from": "/target/old.txt", "to": "/target/new.txt", "file_id": "old-id"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan = self.write_bundle(root, initial, [([rename], [result(rename)])])
            output, errors, provenance = self.run_materializer(root, scan)
            first = (output.read_bytes(), errors.read_bytes(), provenance.read_bytes())
            output, errors, provenance = self.run_materializer(root, scan)
            second = (output.read_bytes(), errors.read_bytes(), provenance.read_bytes())

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
