from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "skills/soia-cwork-feishu-cli/scripts/setup_app_credentials.py"
SPEC = importlib.util.spec_from_file_location("setup_app_credentials", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SetupAppCredentialsTests(unittest.TestCase):
    def test_replace_removes_existing_profile_before_readding_same_app_id(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_profile_operation(_argv: list[str], *args: str) -> CompletedProcess[bytes]:
            calls.append(args)
            return CompletedProcess(args, 0, b"", b"")

        def fake_existing_profile(_argv: list[str], name: str) -> dict | None:
            if name == "feishu-reader":
                return {"name": name, "active": True}
            return None

        def fake_list_profiles(_argv: list[str]) -> list[dict]:
            return [{"name": "feishu-reader", "active": True}]

        config = {
            "env": {
                "LARK_APP_ID": "cli_test",
                "LARK_APP_SECRET": "secret-test",
                "LARK_PROFILE": "feishu-reader",
                "LARK_BRAND": "feishu",
            }
        }

        with (
            patch.object(MODULE, "config_candidates", return_value=[Path("fixture.yml")]),
            patch.object(Path, "is_file", return_value=True),
            patch.object(MODULE, "load_config", return_value=config),
            patch.object(MODULE.shutil, "which", return_value="/usr/local/bin/lark-cli"),
            patch.object(MODULE, "existing_profile", side_effect=fake_existing_profile),
            patch.object(MODULE, "list_profiles", side_effect=fake_list_profiles),
            patch.object(MODULE, "profile_operation", side_effect=fake_profile_operation),
            patch.object(
                MODULE.subprocess,
                "run",
                side_effect=[
                    CompletedProcess(["lark-cli", "profile", "add", "helper"], 0, b"", b""),
                    CompletedProcess(["lark-cli", "profile", "add"], 0, b"", b""),
                ],
            ) as run,
            patch.object(sys, "argv", ["setup_app_credentials.py", "--replace"]),
        ):
            self.assertEqual(MODULE.main(), 0)

        self.assertEqual(calls[0][0], "remove")
        self.assertEqual(calls[-1][0], "remove")
        add_argv = run.call_args_list[-1].args[0]
        self.assertIn("--app-secret-stdin", add_argv)
        self.assertIn("--use", add_argv)

    def test_failed_replace_reports_that_old_profile_was_removed(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_profile_operation(_argv: list[str], *args: str) -> CompletedProcess[bytes]:
            calls.append(args)
            return CompletedProcess(args, 0, b"", b"")

        def fake_existing_profile(_argv: list[str], name: str) -> dict | None:
            return {"name": name, "active": True} if name == "feishu-reader" else None

        config = {
            "env": {
                "LARK_APP_ID": "cli_test",
                "LARK_APP_SECRET": "secret-test",
                "LARK_PROFILE": "feishu-reader",
                "LARK_BRAND": "feishu",
            }
        }

        with (
            patch.object(MODULE, "config_candidates", return_value=[Path("fixture.yml")]),
            patch.object(Path, "is_file", return_value=True),
            patch.object(MODULE, "load_config", return_value=config),
            patch.object(MODULE.shutil, "which", return_value="/usr/local/bin/lark-cli"),
            patch.object(MODULE, "existing_profile", side_effect=fake_existing_profile),
            patch.object(MODULE, "profile_operation", side_effect=fake_profile_operation),
            patch.object(
                MODULE.subprocess,
                "run",
                return_value=CompletedProcess(["lark-cli", "profile", "add"], 7, b"", b""),
            ),
            patch.object(sys, "argv", ["setup_app_credentials.py", "--replace"]),
        ):
            self.assertEqual(MODULE.main(), 7)

        self.assertEqual(calls, [("remove", "feishu-reader")])


if __name__ == "__main__":
    unittest.main()
