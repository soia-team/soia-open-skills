#!/usr/bin/env python3
"""Regression tests for the local catalog-publication manifest auditor."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "soia-pkm-alipan-curator" / "scripts" / "audit_catalog_publish.py"
SPEC = importlib.util.spec_from_file_location("audit_catalog_publish_under_test", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def write_artifact(run_dir: Path, relative_path: str, data: bytes) -> dict:
    path = run_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": relative_path, "size": len(data), "sha1": sha1(data)}


def artifact(
    logical_name: str,
    path: str,
    data: bytes,
    file_id: str,
    *,
    role: str,
    partition: str | None = None,
) -> dict:
    value = {
        "logical_name": logical_name,
        "path": path,
        "size": len(data),
        "sha1": sha1(data),
        "file_id": file_id,
        "role": role,
    }
    if partition is not None:
        value["partition"] = partition
    return value


class CatalogPublicationAuditTests(unittest.TestCase):
    def build_passing_bundle(self, root: Path) -> tuple[Path, dict]:
        run_dir = root / "run"
        run_dir.mkdir()
        release = {
            "catalog_release_id": "catalog-20260721-a",
            "index_updated_at": "2026-07-21T09:00:00+08:00",
            "snapshot_at": "2026-07-21T08:55:00+08:00",
            "catalog_schema_version": "1",
            "source_fingerprint": "source-sha256:abc123",
        }
        release_text = json.dumps(release, ensure_ascii=False).encode("utf-8")
        entry_data = b"catalog entry\n" + release_text
        alpha_data = b"alpha detail\n" + release_text
        beta_data = b"beta detail\n" + release_text
        local_entry = artifact(
            "catalog-entry", "out/catalog.txt", entry_data, "entry-id", role="catalog_entry"
        )
        local_alpha = artifact(
            "partition-alpha", "out/alpha.txt", alpha_data, "alpha-id",
            role="partition_detail", partition="alpha",
        )
        local_beta = artifact(
            "partition-beta", "out/beta.txt", beta_data, "beta-id",
            role="partition_detail", partition="beta",
        )
        for item, data in ((local_entry, entry_data), (local_alpha, alpha_data), (local_beta, beta_data)):
            write_artifact(run_dir, item["path"], data)

        remote_entry = {**local_entry, "path": "/catalog/catalog.xlsx"}
        remote_alpha = {**local_alpha, "path": "/catalog/alpha.xlsx"}
        remote_beta = {**local_beta, "path": "/catalog/beta.xlsx"}
        consumer = run_dir / "consumers" / "resource-map.md"
        consumer.parent.mkdir(parents=True)
        consumer.write_text("new links only\n" + json.dumps(release, ensure_ascii=False), encoding="utf-8")
        manifest = {
            "publication_status": "passed",
            "idempotence_status": "unchanged",
            **release,
            "expected_partitions": ["alpha", "beta"],
            "artifacts": {
                "local": [local_entry, local_alpha, local_beta],
                "remote": [remote_entry, remote_alpha, remote_beta],
            },
            "remote_inventory": [remote_entry, remote_alpha, remote_beta],
            "consumer_audits": [{
                "path": "consumers/resource-map.md",
                "old_file_ids": ["retired-entry-id"],
                "old_file_id_references": 0,
            }],
        }
        manifest_path = run_dir / "catalog-publication.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return run_dir, manifest

    def test_passing_final_manifest_verifies_local_remote_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, _ = self.build_passing_bundle(Path(temp))
            result = audit.audit_catalog_publication(run_dir, "catalog-publication.json", final=True)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["checked"]["expected_partitions"], 2)
        self.assertEqual(result["checked"]["consumer_old_file_id_references"], 0)

    def test_final_rejects_naive_timestamps_and_non_passing_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, manifest = self.build_passing_bundle(Path(temp))
            manifest["index_updated_at"] = "2026-07-21T09:00:00"
            manifest["publication_status"] = "published"
            (run_dir / "catalog-publication.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = audit.audit_catalog_publication(run_dir, "catalog-publication.json", final=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(
            {item["kind"] for item in result["violations"]},
            {"timestamp_missing_timezone", "publication_status_not_passed"},
        )

    def test_final_requires_unchanged_replay_and_snapshot_not_after_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, manifest = self.build_passing_bundle(Path(temp))
            manifest["snapshot_at"] = "2026-07-21T09:01:00+08:00"
            manifest["idempotence_status"] = "rebuilt"
            (run_dir / "catalog-publication.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = audit.audit_catalog_publication(run_dir, "catalog-publication.json", final=True)
        self.assertTrue({
            "snapshot_after_index_update",
            "idempotence_status_not_unchanged",
        }.issubset({item["kind"] for item in result["violations"]}))

    def test_rejects_partition_coverage_metadata_mismatch_and_duplicate_remote_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, manifest = self.build_passing_bundle(Path(temp))
            manifest["artifacts"]["remote"][1]["file_id"] = "wrong-alpha-id"
            manifest["remote_inventory"].append({
                **manifest["remote_inventory"][1],
                "file_id": "alpha-copy-id",
                "path": "/catalog/alpha (1).xlsx",
            })
            manifest["expected_partitions"].append("missing")
            (run_dir / "catalog-publication.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = audit.audit_catalog_publication(run_dir, "catalog-publication.json", final=True)
        kinds = {item["kind"] for item in result["violations"]}
        self.assertTrue({
            "local_remote_artifact_mismatch",
            "missing_partition_detail",
            "remote_duplicate_name_suffix",
            "remote_name_not_unique",
        }.issubset(kinds))

    def test_rejects_old_id_references_and_consumer_path_outside_run_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir, manifest = self.build_passing_bundle(root)
            consumer = run_dir / "consumers" / "resource-map.md"
            consumer.write_text("retired-entry-id\n", encoding="utf-8")
            old_reference_result = audit.audit_catalog_publication(
                run_dir, "catalog-publication.json", final=True
            )
            manifest["consumer_audits"][0]["path"] = "../outside.md"
            (run_dir / "catalog-publication.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = audit.audit_catalog_publication(run_dir, "catalog-publication.json", final=True)
        self.assertIn(
            "consumer_old_file_id_references_not_zero",
            {item["kind"] for item in old_reference_result["violations"]},
        )
        kinds = {item["kind"] for item in result["violations"]}
        self.assertIn("consumer_path_outside_run_bundle", kinds)

    def test_cli_outputs_json_and_nonzero_for_violations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, manifest = self.build_passing_bundle(Path(temp))
            manifest["publication_status"] = "pending"
            (run_dir / "catalog-publication.json").write_text(json.dumps(manifest), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--run-dir", str(run_dir), "--final"],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["status"], "failed")

    def test_malformed_artifact_is_a_structured_failure_not_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir, manifest = self.build_passing_bundle(Path(temp))
            del manifest["artifacts"]["local"][0]["path"]
            (run_dir / "catalog-publication.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = audit.audit_catalog_publication(run_dir, "catalog-publication.json", final=True)
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "invalid_artifact_field",
            {item["kind"] for item in result["violations"]},
        )


if __name__ == "__main__":
    unittest.main()
