from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "skills"
    / "soia-cwork-processon-diagrams"
    / "scripts"
    / "processon_archive_state.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("processon_archive_state", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def plan() -> dict:
    return {
        "schema_version": 1,
        "plan_type": "processon-artifact-archive",
        "archive_status": "known_ready_pending_confirmation",
        "ready_for_known_artifacts": True,
        "ready_for_archive": False,
        "counts": {
            "total": 3,
            "flowchart": 1,
            "mindmap": 1,
            "unknown": 1,
            "pending_confirmation": 1,
        },
        "entries": [
            {
                "artifact_id": "flow-1",
                "source_directory": "team/system",
                "source_path": "team/system/deployment",
                "title": "deployment",
                "type": "flowchart",
                "primary_format": "vsdx",
                "primary_menu": "VISIO文件",
                "selection_rule": "VISIO文件",
                "confirmation_required": False,
                "status": "planned",
            },
            {
                "artifact_id": "mind-1",
                "source_directory": "team/system",
                "source_path": "team/system/topics",
                "title": "topics",
                "type": "mindmap",
                "primary_format": "xmind",
                "primary_menu": "Xmind文件",
                "selection_rule": "Xmind文件",
                "confirmation_required": False,
                "status": "planned",
            },
            {
                "artifact_id": "unknown-1",
                "source_directory": "team/system",
                "source_path": "team/system/unknown",
                "title": "unknown",
                "type": "unknown",
                "primary_format": None,
                "primary_menu": None,
                "selection_rule": "人工确认",
                "confirmation_required": True,
                "status": "pending_confirmation",
            },
        ],
    }


def write_vsdx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("visio/document.xml", "<VisioDocument/>")
        package.writestr("visio/pages/page1.xml", "<PageContents/>")


def write_manifest(path: Path, destination: Path, sha256: str, size: int) -> None:
    path.write_text(
        json.dumps(
            {
                "status": "completed",
                "operation": "copy",
                "source": str(destination.resolve()),
                "destination": str(destination.resolve()),
                "inspection": {"sha256": sha256, "bytes": size},
            }
        ),
        encoding="utf-8",
    )


class ProcessOnArchiveStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_init_next_record_and_audit_are_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            destination = root / "deployment.vsdx"
            manifest = root / "manifest.json"
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")

            state = self.module.initialize_state(plan_path, progress_path)
            self.assertEqual(state["counts"]["planned_known"], 2)
            self.assertEqual(state["counts"]["unknown_pending_confirmation"], 1)
            self.assertEqual(progress_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                [item["artifact_id"] for item in self.module.next_items(plan(), state, 10, None, False, False)],
                ["flow-1", "mind-1"],
            )

            write_vsdx(destination)
            inspection = self.module.inspect_artifact(destination, "vsdx")
            write_manifest(manifest, destination, inspection["sha256"], inspection["bytes"])
            recorded, outcome = self.module.record_completed(
                plan_path,
                progress_path,
                "flow-1",
                destination,
                destination,
                manifest,
                "vsdx",
                "vsdx",
                "not_observed_verified_file",
            )
            self.assertEqual(outcome, "completed")
            self.assertEqual(recorded["counts"]["completed"], 1)
            self.assertEqual(recorded["counts"]["remaining_known"], 1)
            self.assertEqual(
                [item["artifact_id"] for item in self.module.next_items(plan(), recorded, 10, None, False, False)],
                ["mind-1"],
            )
            replayed, outcome = self.module.record_completed(
                plan_path,
                progress_path,
                "flow-1",
                destination,
                destination,
                manifest,
                "vsdx",
                "vsdx",
                "not_observed_verified_file",
            )
            self.assertEqual(outcome, "already_completed")
            self.assertEqual(replayed["counts"]["completed"], 1)
            self.assertEqual(self.module.audit_state(plan_path, progress_path)["status"], "passed")

    def test_failed_and_blocked_are_persisted_and_skipped_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")
            self.module.initialize_state(plan_path, progress_path)
            failed = self.module.mark_outcome(
                plan_path, progress_path, "flow-1", "failed", "download missing"
            )
            blocked = self.module.mark_outcome(
                plan_path, progress_path, "mind-1", "blocked", "membership restriction"
            )
            self.assertEqual(failed["counts"]["failed"], 1)
            self.assertEqual(blocked["counts"]["blocked"], 1)
            self.assertEqual(self.module.next_items(plan(), blocked, 10, None, False, False), [])
            retried = self.module.next_items(plan(), blocked, 10, None, True, True)
            self.assertEqual([item["prior_outcome"] for item in retried], ["failed", "blocked"])

    def test_blocked_diagnostic_is_copied_and_replayed_by_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            diagnostic = root / "mindmap.md"
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")
            diagnostic.write_text("# diagnostic export\n", encoding="utf-8")
            self.module.initialize_state(plan_path, progress_path)

            blocked = self.module.mark_outcome(
                plan_path,
                progress_path,
                "mind-1",
                "blocked",
                "native export produced no file",
                [diagnostic],
            )
            evidence = blocked["blocked"][0]["evidence_files"][0]
            archived = Path(evidence["archived_path"])
            self.assertTrue(archived.is_file())
            self.assertEqual(archived.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(archived, diagnostic)
            self.assertEqual(self.module.audit_state(plan_path, progress_path)["status"], "passed")

            updated = self.module.mark_outcome(
                plan_path,
                progress_path,
                "mind-1",
                "blocked",
                "same blocker after restart",
            )
            self.assertEqual(updated["blocked"][0]["evidence_files"], [evidence])

            archived.write_text("tampered\n", encoding="utf-8")
            result = self.module.audit_state(plan_path, progress_path)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("evidence" in error for error in result["errors"]))

    def test_plan_drift_and_unknown_record_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")
            self.module.initialize_state(plan_path, progress_path)
            with self.assertRaises(self.module.ArchiveStateError):
                self.module.get_plan_item(plan(), "unknown-1")

            changed = plan()
            changed["entries"][0]["title"] = "changed"
            plan_path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(self.module.ArchiveStateError):
                self.module.initialize_state(plan_path, progress_path)

    def test_tampered_archive_fails_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            destination = root / "deployment.vsdx"
            manifest = root / "manifest.json"
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")
            self.module.initialize_state(plan_path, progress_path)
            write_vsdx(destination)
            inspection = self.module.inspect_artifact(destination, "vsdx")
            write_manifest(manifest, destination, inspection["sha256"], inspection["bytes"])
            self.module.record_completed(
                plan_path,
                progress_path,
                "flow-1",
                destination,
                destination,
                manifest,
                "vsdx",
                "vsdx",
                "observed",
            )
            destination.write_bytes(b"tampered")
            result = self.module.audit_state(plan_path, progress_path)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["errors"])

    def test_record_rejects_every_file_from_flat_personal_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            downloads = home / "Downloads"
            downloads.mkdir()
            for filename in ("未命名文件.vsdx", "未命名文件 (2).vsdx"):
                source = downloads / filename
                write_vsdx(source)
                with patch.object(Path, "home", return_value=home):
                    self.assertTrue(self.module.is_unsafe_flat_personal_download(source))
                    with self.assertRaisesRegex(
                        self.module.ArchiveStateError, "artifact_id-scoped managed staging"
                    ):
                        self.module.record_completed(
                            home / "unused-plan.json",
                            home / "unused-progress.json",
                            "flow-1",
                            source,
                            source,
                            home / "unused-manifest.json",
                            "vsdx",
                            "vsdx",
                            "observed",
                        )

    def test_reopen_completed_is_resumable_audited_and_cleared_by_redownload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            destination = root / "archive" / "deployment" / "deployment.vsdx"
            metadata = destination.parent / "metadata.yml"
            manifest = root / "manifest.json"
            quarantine = root / "archive" / "_staging" / "legacy-quarantine"
            destination.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")
            self.module.initialize_state(plan_path, progress_path)
            write_vsdx(destination)
            metadata.write_text("artifact_id: flow-1\n", encoding="utf-8")
            inspection = self.module.inspect_artifact(destination, "vsdx")
            write_manifest(manifest, destination, inspection["sha256"], inspection["bytes"])
            self.module.record_completed(
                plan_path,
                progress_path,
                "flow-1",
                destination,
                destination,
                manifest,
                "vsdx",
                "vsdx",
                "not_observed_verified_file",
            )

            reopened, outcome = self.module.reopen_completed(
                plan_path,
                progress_path,
                ["flow-1"],
                "legacy flat download requires source revalidation",
                quarantine,
            )
            self.assertEqual(outcome, "reopened")
            self.assertEqual(reopened["counts"]["completed"], 0)
            self.assertEqual(reopened["counts"]["revalidation_pending"], 1)
            self.assertEqual(reopened["counts"]["remaining_known"], 2)
            self.assertFalse(destination.exists())
            self.assertFalse(metadata.exists())
            evidence = reopened["revalidation_pending"][0]["quarantine_files"]
            self.assertEqual(len(evidence), 2)
            self.assertTrue(all(Path(item["quarantine_path"]).is_file() for item in evidence))
            next_item = self.module.next_items(plan(), reopened, 1, None, False, False)[0]
            self.assertEqual(next_item["artifact_id"], "flow-1")
            self.assertEqual(next_item["prior_outcome"], "revalidation_pending")
            self.assertEqual(self.module.audit_state(plan_path, progress_path)["status"], "passed")

            destination.parent.mkdir(parents=True, exist_ok=True)
            write_vsdx(destination)
            replacement = self.module.inspect_artifact(destination, "vsdx")
            write_manifest(manifest, destination, replacement["sha256"], replacement["bytes"])
            recorded, record_outcome = self.module.record_completed(
                plan_path,
                progress_path,
                "flow-1",
                destination,
                destination,
                manifest,
                "vsdx",
                "vsdx",
                "observed",
            )
            self.assertEqual(record_outcome, "completed")
            self.assertEqual(recorded["counts"]["completed"], 1)
            self.assertEqual(recorded["counts"]["revalidation_pending"], 0)

    def test_reopen_rolls_files_back_when_state_commit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            destination = root / "archive" / "deployment" / "deployment.vsdx"
            metadata = destination.parent / "metadata.yml"
            manifest = root / "manifest.json"
            quarantine = root / "archive" / "_staging" / "legacy-quarantine"
            destination.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(plan()), encoding="utf-8")
            self.module.initialize_state(plan_path, progress_path)
            write_vsdx(destination)
            metadata.write_text("artifact_id: flow-1\n", encoding="utf-8")
            inspection = self.module.inspect_artifact(destination, "vsdx")
            write_manifest(manifest, destination, inspection["sha256"], inspection["bytes"])
            self.module.record_completed(
                plan_path,
                progress_path,
                "flow-1",
                destination,
                destination,
                manifest,
                "vsdx",
                "vsdx",
                "observed",
            )
            before = progress_path.read_bytes()

            with patch.object(self.module, "atomic_write_json", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    self.module.reopen_completed(
                        plan_path,
                        progress_path,
                        ["flow-1"],
                        "test rollback",
                        quarantine,
                    )
            self.assertTrue(destination.is_file())
            self.assertTrue(metadata.is_file())
            self.assertEqual(progress_path.read_bytes(), before)
            self.assertFalse((quarantine / "flow-1").exists())

    def test_reopen_artifact_id_file_is_bounded_and_rejects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact_ids = root / "reopen.txt"
            artifact_ids.write_text("# migration set\nflow-1\n\nmind-1\n", encoding="utf-8")
            self.assertEqual(
                self.module.reopen_artifact_ids([], artifact_ids), ["flow-1", "mind-1"]
            )
            with self.assertRaisesRegex(self.module.ArchiveStateError, "unique"):
                self.module.reopen_artifact_ids(["flow-1"], artifact_ids)
            if hasattr(artifact_ids, "symlink_to"):
                symlink = root / "ids-link.txt"
                try:
                    symlink.symlink_to(artifact_ids)
                except OSError:
                    return
                with self.assertRaisesRegex(self.module.ArchiveStateError, "non-symlink"):
                    self.module.reopen_artifact_ids([], symlink)


if __name__ == "__main__":
    unittest.main()
