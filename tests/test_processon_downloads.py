from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "skills"
    / "soia-cwork-processon-diagrams"
    / "scripts"
    / "finalize_processon_download.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("finalize_processon_download", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_pos(path: Path, title: str = "Fixture") -> None:
    path.write_text(
        json.dumps(
            {
                "meta": {
                    "version": "5.0",
                    "diagramInfo": {"title": title, "category": "flow"},
                },
                "diagram": {
                    "elements": {
                        "elements": {
                            "node-1": {"textBlock": [{"text": "hello"}]}
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )


class ProcessOnDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_config_precedence_cli_then_process_env_then_yaml_then_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            config = root / "config.yml"
            config.write_text(
                """schema_version: 1
env:
  SOIA_CWORK_PROCESSON_DIAGRAMS_TEMP_DIR: "<ignored-placeholder>"
  SOIA_CWORK_PROCESSON_DIAGRAMS_OUTPUT_DIR: "yaml-output"
  SOIA_CWORK_PROCESSON_DIAGRAMS_MANIFEST_DIR: "yaml-manifests"
  SOIA_CWORK_PROCESSON_DIAGRAMS_RETENTION_DAYS: "11"
""",
                encoding="utf-8",
            )
            settings = self.module.load_settings(
                config=config,
                temp_dir=root / "cli-temp",
                environ={
                    self.module.OUTPUT_ENV: str(root / "env-output"),
                },
                home=home,
                system_temp=root / "system-temp",
            )

            self.assertEqual(settings.temp_dir, (root / "cli-temp").resolve())
            self.assertEqual(settings.output_dir, (root / "env-output").resolve())
            self.assertEqual(settings.manifest_dir, Path("yaml-manifests").resolve())
            self.assertEqual(settings.retention_days, 11)

    def test_safe_defaults_use_system_temp_downloads_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            settings = self.module.load_settings(
                environ={},
                home=home,
                system_temp=root / "system-temp",
            )

            self.assertEqual(
                settings.temp_dir,
                (root / "system-temp" / self.module.SKILL_NAME).resolve(),
            )
            self.assertEqual(
                settings.output_dir,
                (home / "Downloads" / self.module.SKILL_NAME).resolve(),
            )
            self.assertEqual(
                settings.manifest_dir,
                (
                    home
                    / ".local"
                    / "state"
                    / self.module.SKILL_NAME
                    / "manifests"
                ).resolve(),
            )

    def test_finalize_copy_is_atomic_inspected_and_manifested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "browser-download.pos"
            write_pos(source, "Architecture")
            settings = self.module.Settings(
                temp_dir=root / "temp",
                output_dir=root / "output",
                manifest_dir=root / "manifests",
                retention_days=7,
                config_file=None,
            )
            result = self.module.finalize_download(
                source,
                settings,
                now=datetime(2026, 7, 20, tzinfo=timezone.utc),
            )

            destination = Path(result["destination"])
            manifest = Path(result["manifest"])
            self.assertTrue(source.exists())
            self.assertTrue(destination.exists())
            self.assertTrue(manifest.exists())
            self.assertEqual(result["inspection"]["title"], "Architecture")
            self.assertEqual(
                result["inspection"]["sha256"],
                self.module.inspect_source(source)["sha256"],
            )
            recorded = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(recorded["status"], "completed")
            self.assertEqual(recorded["destination"], str(destination))

    def test_collision_renames_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "diagram.pos"
            write_pos(source)
            output = root / "output"
            output.mkdir()
            existing = output / source.name
            existing.write_text("keep", encoding="utf-8")
            settings = self.module.Settings(
                temp_dir=root / "temp",
                output_dir=output,
                manifest_dir=root / "manifests",
                retention_days=7,
                config_file=None,
            )

            result = self.module.finalize_download(source, settings)

            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")
            self.assertEqual(Path(result["destination"]).name, "diagram (1).pos")

    def test_move_requires_managed_temp_and_removes_source_only_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.module.Settings(
                temp_dir=root / "temp",
                output_dir=root / "output",
                manifest_dir=root / "manifests",
                retention_days=7,
                config_file=None,
            )
            source = settings.temp_dir / "diagram.pos"
            source.parent.mkdir()
            write_pos(source)
            with self.assertRaises(self.module.DownloadError):
                self.module.finalize_download(source, settings, move=True)

            source.unlink()
            settings.temp_dir.rmdir()
            self.module.ensure_paths(settings)
            write_pos(source)
            result = self.module.finalize_download(source, settings, move=True)

            self.assertFalse(source.exists())
            self.assertTrue(Path(result["destination"]).exists())
            self.assertTrue(Path(result["manifest"]).exists())

    def test_cleanup_requires_marker_and_keeps_recent_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.module.Settings(
                temp_dir=root / "temp",
                output_dir=root / "output",
                manifest_dir=root / "manifests",
                retention_days=7,
                config_file=None,
            )
            settings.temp_dir.mkdir()
            with self.assertRaises(self.module.DownloadError):
                self.module.cleanup_temp(settings)

            settings.temp_dir.rmdir()
            self.module.ensure_paths(settings)
            old_file = settings.temp_dir / "old.pos"
            recent_file = settings.temp_dir / "recent.pos"
            write_pos(old_file)
            write_pos(recent_file)
            now = time.time()
            old_time = now - 10 * 24 * 60 * 60
            os.utime(old_file, (old_time, old_time))

            result = self.module.cleanup_temp(settings, now_timestamp=now)

            self.assertFalse(old_file.exists())
            self.assertTrue(recent_file.exists())
            self.assertEqual(result["deleted"], [str(old_file)])
            self.assertTrue(Path(result["manifest"]).exists())

    def test_cleanup_does_not_delete_when_manifest_cannot_be_reserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.module.Settings(
                temp_dir=root / "temp",
                output_dir=root / "output",
                manifest_dir=root / "manifests",
                retention_days=0,
                config_file=None,
            )
            self.module.ensure_paths(settings)
            candidate = settings.temp_dir / "old.pos"
            write_pos(candidate)
            with patch.object(
                self.module,
                "reserve_manifest",
                side_effect=self.module.DownloadError("not writable"),
            ):
                with self.assertRaises(self.module.DownloadError):
                    self.module.cleanup_temp(
                        settings,
                        retention_days=0,
                        now_timestamp=time.time() + 1,
                    )
            self.assertTrue(candidate.exists())

    def test_non_empty_unmanaged_temp_is_not_adopted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = self.module.Settings(
                temp_dir=root / "shared-downloads",
                output_dir=root / "output",
                manifest_dir=root / "manifests",
                retention_days=7,
                config_file=None,
            )
            settings.temp_dir.mkdir()
            (settings.temp_dir / "unrelated.txt").write_text("keep", encoding="utf-8")

            with self.assertRaises(self.module.DownloadError):
                self.module.ensure_paths(settings)

    def test_output_and_manifest_must_not_be_inside_managed_temp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for destination in (root / "temp", root / "temp" / "nested"):
                settings = self.module.Settings(
                    temp_dir=root / "temp",
                    output_dir=destination,
                    manifest_dir=root / "manifests",
                    retention_days=7,
                    config_file=None,
                )
                with self.assertRaises(self.module.DownloadError):
                    self.module.ensure_paths(settings)


if __name__ == "__main__":
    unittest.main()
