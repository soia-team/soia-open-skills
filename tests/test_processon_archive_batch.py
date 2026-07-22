import argparse
import asyncio
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-cwork-processon-diagrams" / "scripts" / "processon_archive_batch.py"
RUNNER_DIR = SCRIPT.parent
import sys

sys.path.insert(0, str(RUNNER_DIR))
SPEC = importlib.util.spec_from_file_location("processon_archive_batch", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MenuLocator:
    def __init__(self, visible):
        self.visible = visible

    def filter(self, **_kwargs):
        return self

    def nth(self, _index):
        return self

    async def count(self):
        return 1 if self.visible else 0

    async def is_visible(self):
        return self.visible


class MenuPage:
    def __init__(self, visible_labels):
        self.visible_labels = set(visible_labels)

    def get_by_text(self, label, *, exact):
        assert exact is True
        return MenuLocator(label in self.visible_labels)

    async def wait_for_timeout(self, _milliseconds):
        return None


class ProcessOnArchiveBatchTests(unittest.TestCase):
    def entry(self, artifact_id="a", collision="none_detected"):
        return {
            "artifact_id": artifact_id,
            "confirmation_required": False,
            "type": "flowchart",
            "collision_risk": collision,
            "source_directory": "root/folder",
            "source_path": f"root/folder/{artifact_id}",
            "title": artifact_id,
            "primary_format": "vsdx",
            "primary_menu": "VISIO文件",
        }

    def test_parallel_selection_skips_collision_risk(self):
        plan = {"entries": [self.entry("safe"), self.entry("collision", "duplicate_title")]}
        progress = {"completed": [], "failed": [], "blocked": []}
        selected = MODULE.choose_entries(plan, progress, 10, workers=2)
        self.assertEqual([item["artifact_id"] for item in selected], ["safe"])
        serial = MODULE.choose_entries(plan, progress, 10, workers=1)
        self.assertEqual([item["artifact_id"] for item in serial], ["safe"])
        deferred = MODULE.deferred_collision_entries(plan, progress)
        self.assertEqual([item["artifact_id"] for item in deferred], ["collision"])

    def test_vsdx_download_menu_prefers_all_canvases(self):
        label, _locator = asyncio.run(
            MODULE.find_download_menu(
                MenuPage({"VISIO文件", "导出全部画布 (.vsdx)"}),
                self.entry("multi-canvas"),
                timeout_ms=100,
            )
        )
        self.assertEqual(label, "导出全部画布 (.vsdx)")

    def test_vsdx_download_menu_falls_back_to_legacy_plan_label(self):
        label, _locator = asyncio.run(
            MODULE.find_download_menu(
                MenuPage({"VISIO文件"}),
                self.entry("single-canvas"),
                timeout_ms=100,
            )
        )
        self.assertEqual(label, "VISIO文件")

    def test_vsdx_semantic_title_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "数据服务平台.vsdx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("visio/document.xml", "<VisioDocument />")
                archive.writestr(
                    "visio/pages/page1.xml",
                    "<PageContents><Shapes><Shape><Text>数据服务平台 exchange</Text></Shape></Shapes></PageContents>",
                )
            inspected = MODULE.inspect_vsdx(
                path, "《斛斗4.0数据服务平台&保单验真(exchange)部署架构图-生产环境》"
            )
            self.assertEqual(inspected["semantic_status"], "matched")
            self.assertIn("exchange", inspected["matched_title_signals"])
            with self.assertRaises(MODULE.BatchError):
                MODULE.inspect_vsdx(path, "《风险管理系统-测试环境-部署图》")

    def test_vsdx_requires_short_chinese_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "订单系统部署架构图.vsdx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("visio/document.xml", "<VisioDocument />")
                archive.writestr(
                    "visio/pages/page1.xml",
                    "<PageContents><Shapes><Shape><Text>完全无关内容</Text></Shape></Shapes></PageContents>",
                )
            self.assertEqual(MODULE.title_signals("订单系统部署架构图"), ["订单"])
            with self.assertRaises(MODULE.BatchError):
                MODULE.inspect_vsdx(path, "订单系统部署架构图")

    def test_vsdx_accepts_two_non_overlapping_chinese_bigram_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "数字化柜面状态流传.vsdx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("visio/document.xml", "<VisioDocument />")
                archive.writestr(
                    "visio/pages/page1.xml",
                    "<PageContents><Shapes><Shape><Text>任务状态</Text></Shape>"
                    "<Shape><Text>柜面视频身份核验标识</Text></Shape></Shapes></PageContents>",
                )
            inspected = MODULE.inspect_vsdx(path, "数字化柜面状态流传")
            self.assertEqual(inspected["semantic_status"], "matched")
            self.assertEqual(inspected["semantic_match_method"], "chinese_bigram_pair")
            self.assertEqual(inspected["matched_title_signals"], ["柜面", "状态"])

    def test_vsdx_rejects_one_or_overlapping_chinese_bigram_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "compound.vsdx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("visio/document.xml", "<VisioDocument />")
                archive.writestr(
                    "visio/pages/page1.xml",
                    "<PageContents><Shapes><Shape><Text>柜面服务</Text></Shape></Shapes></PageContents>",
                )
            with self.assertRaises(MODULE.BatchError):
                MODULE.inspect_vsdx(path, "数字化柜面状态流传")
            self.assertEqual(MODULE.matched_chinese_bigram_pair("数字化", "数字字化"), [])

    def test_vsdx_blocks_plaintext_credentials_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "MongoDB使用关系图.vsdx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("visio/document.xml", "<VisioDocument />")
                archive.writestr(
                    "visio/pages/page1.xml",
                    "<PageContents><Shapes><Shape><Text>MongoDB 密码：do-not-log-this</Text></Shape>"
                    "<Shape><Text>password=also-secret</Text></Shape></Shapes></PageContents>",
                )
            with self.assertRaises(MODULE.BatchError) as caught:
                MODULE.inspect_vsdx(path, "MongoDB使用关系图")
            message = str(caught.exception)
            self.assertIn("security review required", message)
            self.assertIn("chinese_password_assignment=1", message)
            self.assertIn("english_password_assignment=1", message)
            self.assertNotIn("do-not-log-this", message)
            self.assertNotIn("also-secret", message)

    def test_secret_scan_does_not_block_non_assignment_security_terms(self):
        self.assertEqual(
            MODULE.sensitive_text_findings(["token验证", "password policy", "修改密码"]),
            [],
        )

    def test_dotted_release_number_separates_chinese_title_signals(self):
        self.assertEqual(
            MODULE.title_signals("《磐石4.0短信系统部署架构图-生产环境》"),
            ["磐石", "短信"],
        )

    def test_concurrency_requires_matching_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = {
                "entries": [
                    {
                        "artifact_id": "a",
                        "title": "Alpha",
                        "source_url": "https://www.processon.com/diagraming/a",
                        "remote_id": "a",
                        "primary_format": "vsdx",
                    },
                    {
                        "artifact_id": "b",
                        "title": "Beta",
                        "source_url": "https://www.processon.com/diagraming/b",
                        "remote_id": "b",
                        "primary_format": "vsdx",
                    },
                ]
            }
            completed = []
            samples = []
            for artifact_id, title in (("a", "Alpha"), ("b", "Beta")):
                folder = root / artifact_id
                folder.mkdir()
                destination = folder / f"{title}.vsdx"
                with zipfile.ZipFile(destination, "w") as archive:
                    archive.writestr("visio/document.xml", "<VisioDocument />")
                    archive.writestr(
                        "visio/pages/page1.xml",
                        f"<PageContents><Shapes><Shape><Text>{title}</Text></Shape></Shapes></PageContents>",
                    )
                digest = MODULE.sha256(destination)
                source_url = f"https://www.processon.com/diagraming/{artifact_id}"
                (folder / "metadata.yml").write_text(
                    "\n".join(
                        [
                            f'artifact_id: "{artifact_id}"',
                            f'title: "{title}"',
                            f'source_url: "{source_url}"',
                            f'remote_id: "{artifact_id}"',
                            f'sha256: "{digest}"',
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                completed.append(
                    {
                        "artifact_id": artifact_id,
                        "archive_destination": str(destination),
                        "sha256": digest,
                    }
                )
                samples.append(
                    {
                        "artifact_id": artifact_id,
                        "title": title,
                        "source_url": source_url,
                        "remote_id": artifact_id,
                        "sha256": digest,
                        "semantic_status": "matched",
                    }
                )
            progress = {"plan": {"sha256": "abc"}, "completed": completed}
            with self.assertRaises(MODULE.BatchError):
                MODULE.validate_concurrency_proof(
                    None, workers=2, plan=plan, progress=progress
                )
            proof = root / "proof.json"
            proof.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "passed",
                        "plan_sha256": "abc",
                        "max_workers": 2,
                        "samples": samples,
                        "lifecycle": {
                            "scoped_pages_opened": 2,
                            "scoped_pages_closed": 2,
                            "worker_pages_opened": 2,
                            "worker_pages_closed": 2,
                            "pages_remaining": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = MODULE.validate_concurrency_proof(
                proof, workers=2, plan=plan, progress=progress
            )
            self.assertEqual(result["max_workers"], 2)
            payload = json.loads(proof.read_text(encoding="utf-8"))
            payload["samples"][0]["source_url"] = "https://www.processon.com/diagraming/evil"
            payload["samples"][0]["remote_id"] = "evil"
            proof.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(MODULE.BatchError):
                MODULE.validate_concurrency_proof(
                    proof, workers=2, plan=plan, progress=progress
                )
            payload["samples"][0]["source_url"] = "https://www.processon.com/diagraming/a"
            payload["samples"][0]["remote_id"] = "a"
            payload["lifecycle"]["worker_pages_opened"] = 1
            proof.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(MODULE.BatchError):
                MODULE.validate_concurrency_proof(
                    proof, workers=2, plan=plan, progress=progress
                )
            payload["lifecycle"]["worker_pages_opened"] = 2
            proof.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(MODULE.BatchError):
                MODULE.validate_concurrency_proof(
                    proof, workers=3, plan=plan, progress=progress
                )

    def test_concurrency_rejects_duplicate_samples(self):
        progress = {"plan": {"sha256": "abc"}}
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "proof.json"
            sample = {
                "artifact_id": "same",
                "source_url": "https://www.processon.com/diagraming/same",
                "sha256": "same-sha",
                "semantic_status": "matched",
            }
            proof.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "passed",
                        "plan_sha256": "abc",
                        "max_workers": 2,
                        "samples": [sample, sample],
                        "lifecycle": {
                            "scoped_pages_opened": 2,
                            "scoped_pages_closed": 2,
                            "worker_pages_closed": 2,
                            "pages_remaining": 0,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(MODULE.BatchError):
                MODULE.validate_concurrency_proof(
                    proof, workers=2, plan={"entries": []}, progress=progress
                )

    def test_source_popup_identity_must_match_plan(self):
        entry = self.entry("a")
        entry["remote_id"] = "remote-a"
        entry["source_url"] = "https://www.processon.com/diagraming/remote-a"
        observed = "https://www.processon.com/diagraming/remote-a/"
        self.assertEqual(MODULE.verify_source_identity(entry, observed), "remote-a")
        with self.assertRaises(MODULE.BatchError):
            MODULE.verify_source_identity(
                entry, "https://www.processon.com/diagraming/remote-b"
            )

    def test_zip_member_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unsafe.vsdx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape", "no")
                archive.writestr("visio/document.xml", "<VisioDocument />")
                archive.writestr("visio/pages/page1.xml", "<PageContents />")
            with self.assertRaises(MODULE.BatchError):
                MODULE.inspect_vsdx(path, "订单系统部署架构图")

    @unittest.skipIf(os.name == "nt", "symlink privileges vary on Windows")
    def test_lock_rejects_symlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "victim.txt"
            victim.write_text("KEEP-ME", encoding="utf-8")
            lock = root / "lock"
            lock.symlink_to(victim)
            with self.assertRaises(MODULE.BatchError):
                with MODULE.exclusive_lock(lock):
                    pass
            self.assertEqual(victim.read_text(encoding="utf-8"), "KEEP-ME")

    @unittest.skipIf(os.name == "nt", "hard-link semantics vary on Windows")
    def test_lock_rejects_hardlink_without_touching_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            victim = root / "victim.txt"
            victim.write_text("KEEP-ME", encoding="utf-8")
            lock = root / "lock"
            os.link(victim, lock)
            with self.assertRaises(MODULE.BatchError):
                with MODULE.exclusive_lock(lock):
                    pass
            self.assertEqual(victim.read_text(encoding="utf-8"), "KEEP-ME")

    def test_progress_mirror_reports_complete_and_waiting_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.yml"
            plan = {"entries": [], "counts": {"total_entries": 0}}
            progress = {
                "plan": {"sha256": "abc"},
                "counts": {
                    "planned_known": 1,
                    "completed": 1,
                    "failed": 0,
                    "blocked": 0,
                    "remaining_known": 0,
                    "unknown_pending_confirmation": 0,
                },
                "completed": [],
                "blocked": [],
            }
            MODULE.write_progress_mirror(path, plan=plan, progress=progress, run_id="run")
            self.assertIn('status: "asset_archive_completed"', path.read_text(encoding="utf-8"))
            progress["counts"].update(
                {"blocked": 1, "remaining_known": 1, "unknown_pending_confirmation": 1}
            )
            MODULE.write_progress_mirror(path, plan=plan, progress=progress, run_id="run")
            self.assertIn('status: "asset_archive_running"', path.read_text(encoding="utf-8"))

    def test_source_link_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source-links.yml"
            path.write_text(
                'schema_version: 1\nentries:\n  - artifact_id: "a"\n    source_url: "https://www.processon.com/diagraming/one"\n',
                encoding="utf-8",
            )
            entry = self.entry("a")
            with self.assertRaises(MODULE.BatchError):
                MODULE.append_source_link(
                    path,
                    entry,
                    {
                        "source_url": "https://www.processon.com/diagraming/two",
                        "remote_id": "two",
                    },
                )

    def test_output_folder_contains_collision_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = self.entry("abcdef012345", "duplicate_title")
            target = MODULE.output_folder(Path(tmp), entry)
            self.assertEqual(target.name, "abcdef012345--abcdef01")

    def test_output_folder_treats_title_separator_as_one_escaped_component(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = self.entry("abcdef012345")
            entry["source_directory"] = "team/system"
            entry["source_path"] = "team/system/中介/银保手续费"
            entry["title"] = "中介/银保手续费"
            entry["collision_risk"] = "none_detected"
            target = MODULE.output_folder(Path(tmp), entry)
            self.assertEqual(target.parent.name, "system")
            self.assertEqual(target.name, "中介_银保手续费--abcdef01")

    def test_same_download_name_uses_artifact_specific_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = MODULE.safe_download_path(Path(tmp), "artifact-a", "未命名文件.vsdx")
            second = MODULE.safe_download_path(Path(tmp), "artifact-b", "未命名文件.vsdx")
            self.assertNotEqual(first.parent, second.parent)
            self.assertEqual(first.name, second.name)
            self.assertEqual(first.parent.name, "artifact-a")
            self.assertEqual(second.parent.name, "artifact-b")

    def test_finalize_result_moves_from_managed_staging_without_payload_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            managed = root / "staging"
            output = root / "output"
            manifests = root / "manifests"
            plan_path = root / "archive-plan.json"
            progress_path = root / "download-progress.json"
            entry = self.entry("deployment")
            archive_plan = {
                "schema_version": 1,
                "plan_type": "processon-artifact-archive",
                "archive_status": "known_ready",
                "ready_for_known_artifacts": True,
                "ready_for_archive": True,
                "counts": {
                    "total": 1,
                    "flowchart": 1,
                    "mindmap": 0,
                    "unknown": 0,
                    "pending_confirmation": 0,
                },
                "entries": [entry],
            }
            plan_path.write_text(json.dumps(archive_plan), encoding="utf-8")
            MODULE.run_json(
                [
                    sys.executable,
                    str(MODULE.FINALIZER),
                    "paths",
                    "--temp-dir",
                    str(managed),
                    "--output-dir",
                    str(output),
                    "--manifest-dir",
                    str(manifests),
                    "--ensure",
                ]
            )
            MODULE.run_json(
                [
                    sys.executable,
                    str(MODULE.ARCHIVE_STATE),
                    "init",
                    "--plan",
                    str(plan_path),
                    "--progress",
                    str(progress_path),
                ]
            )
            source = managed / "run" / entry["artifact_id"] / "deployment.vsdx"
            source.parent.mkdir(parents=True)
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("visio/document.xml", "<VisioDocument />")
                archive.writestr("visio/pages/pages.xml", "<Pages />")
                archive.writestr(
                    "visio/pages/page1.xml",
                    "<PageContents><Shapes><Shape><Text>deployment</Text></Shape></Shapes></PageContents>",
                )
            source_inode = source.stat().st_ino
            args = argparse.Namespace(
                output_root=output,
                manifest_dir=manifests,
                managed_temp_root=managed,
                team_url="https://www.processon.com/org/teams/team-id",
                source_links=None,
                plan=plan_path,
                progress=progress_path,
            )
            result = MODULE.finalize_result(
                {
                    "download": {"path": str(source)},
                    "source_url": "https://www.processon.com/diagraming/remote-id",
                    "remote_id": "remote-id",
                    "download_menu": "导出全部画布 (.vsdx)",
                },
                entry,
                args=args,
            )
            destination = Path(result["destination"])
            self.assertFalse(source.exists())
            self.assertTrue(destination.is_file())
            self.assertEqual(destination.stat().st_ino, source_inode)
            self.assertTrue(Path(result["metadata"]).is_file())
            self.assertIn(
                'download_menu: "导出全部画布 (.vsdx)"',
                Path(result["metadata"]).read_text(encoding="utf-8"),
            )
            manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["operation"], "move")
            self.assertEqual(manifest["transfer_mode"], "hardlink_then_unlink")
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            self.assertEqual(progress["counts"]["completed"], 1)
            self.assertEqual(progress["completed"][0]["download_source"], str(source.resolve()))

    def test_legacy_flat_download_review_revalidates_every_flat_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            downloads = home / "Downloads"
            downloads.mkdir()
            progress = {
                "completed": [
                    {
                        "artifact_id": "a",
                        "source_path": "root/a",
                        "download_source": str(downloads / "未命名文件 (2).vsdx"),
                        "archive_destination": "/archive/a",
                    },
                    {
                        "artifact_id": "b",
                        "source_path": "root/b",
                        "download_source": str(downloads / "唯一名称.vsdx"),
                        "archive_destination": "/archive/b",
                    },
                    {
                        "artifact_id": "c",
                        "source_path": "root/c",
                        "download_source": str(home / "managed" / "同名.vsdx"),
                        "archive_destination": "/archive/c",
                    },
                ]
            }
            with patch.object(Path, "home", return_value=home):
                review = MODULE.legacy_flat_download_review(progress)
            self.assertEqual(review["flat_downloads_completed_count"], 2)
            self.assertEqual(review["revalidation_required_count"], 2)
            self.assertEqual(review["numbered_suffix_review_count"], 1)
            self.assertEqual(review["trusted_completed_count"], 1)
            self.assertEqual(review["claim_status"], "revalidation_required")
            self.assertEqual(
                [item["artifact_id"] for item in review["revalidation_items"]], ["a", "b"]
            )
            self.assertEqual(review["numbered_suffix_items"][0]["artifact_id"], "a")

    def test_progress_mirror_excludes_legacy_numbered_download_from_trusted_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            downloads = home / "Downloads"
            downloads.mkdir()
            mirror = home / "archive-progress.yml"
            plan = {"entries": [], "counts": {"total_entries": 2}}
            progress = {
                "plan": {"sha256": "abc"},
                "counts": {
                    "planned_known": 2,
                    "completed": 2,
                    "failed": 0,
                    "blocked": 0,
                    "remaining_known": 0,
                    "unknown_pending_confirmation": 0,
                },
                "completed": [
                    {
                        "artifact_id": "unsafe",
                        "source_path": "root/unsafe",
                        "actual_format": "vsdx",
                        "download_source": str(downloads / "未命名文件 (2).vsdx"),
                        "archive_destination": str(home / "archive" / "unsafe.vsdx"),
                    },
                    {
                        "artifact_id": "safe",
                        "source_path": "root/safe",
                        "actual_format": "vsdx",
                        "download_source": str(home / "managed" / "safe" / "同名.vsdx"),
                        "archive_destination": str(home / "archive" / "safe.vsdx"),
                    },
                ],
                "blocked": [],
            }
            with patch.object(Path, "home", return_value=home):
                MODULE.write_progress_mirror(mirror, plan=plan, progress=progress, run_id="run")
            text = mirror.read_text(encoding="utf-8")
            self.assertIn("completed: 1", text)
            self.assertIn("completed_recorded: 2", text)
            self.assertIn("revalidation_pending: 1", text)
            self.assertIn("legacy_flat_revalidation_pending: 1", text)
            self.assertIn("remaining_known: 1", text)
            self.assertIn("remaining_known_recorded: 0", text)
            self.assertIn('artifact_id: "unsafe"', text)

    def test_progress_mirror_does_not_double_count_explicit_revalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mirror = root / "archive-progress.yml"
            plan = {"entries": [], "counts": {"total_entries": 2}}
            progress = {
                "plan": {"sha256": "abc"},
                "counts": {
                    "planned_known": 2,
                    "completed": 1,
                    "failed": 0,
                    "blocked": 0,
                    "revalidation_pending": 1,
                    "remaining_known": 1,
                    "unknown_pending_confirmation": 0,
                },
                "completed": [
                    {
                        "artifact_id": "safe",
                        "source_path": "root/safe",
                        "actual_format": "vsdx",
                        "download_source": str(root / "staging" / "safe" / "safe.vsdx"),
                        "archive_destination": str(root / "archive" / "safe.vsdx"),
                    }
                ],
                "revalidation_pending": [
                    {
                        "artifact_id": "reopen",
                        "source_path": "root/reopen",
                        "reason": "legacy flat source",
                        "prior_completion": {
                            "download_source": str(root / "Downloads" / "same.vsdx")
                        },
                    }
                ],
                "blocked": [],
            }
            MODULE.write_progress_mirror(mirror, plan=plan, progress=progress, run_id="run")
            text = mirror.read_text(encoding="utf-8")
            self.assertIn("completed: 1", text)
            self.assertIn("revalidation_pending: 1", text)
            self.assertIn("explicit_revalidation_pending: 1", text)
            self.assertIn("legacy_flat_revalidation_pending: 0", text)
            self.assertIn("remaining_known: 1", text)

    def test_provider_title_suffix_is_deliberately_narrow(self):
        title = "企业知识库"
        self.assertTrue(MODULE.source_title_matches(title, title))
        self.assertTrue(MODULE.source_title_matches(title, f"{title}-ProcessOn"))
        self.assertFalse(MODULE.source_title_matches(title, f"{title}-副本"))

    def test_provider_filename_sanitization_is_deliberately_narrow(self):
        title = "《蚁窠-中介/银保手续费/可用费用-系统交互图》"
        self.assertEqual(
            MODULE.provider_safe_filename_stem(title),
            "《蚁窠-中介_银保手续费_可用费用-系统交互图》",
        )
        self.assertNotEqual(
            MODULE.provider_safe_filename_stem(title), title.replace("中介", "中介平台")
        )


if __name__ == "__main__":
    unittest.main()
