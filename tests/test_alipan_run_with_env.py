#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "soia-pkm-alipan" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_with_env  # noqa: E402


TEST_SECRET = "loaded-secret"


class RunWithEnvTests(unittest.TestCase):
    def test_loads_private_env_preserves_arguments_and_propagates_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.yml"
            config.write_text(f"env:\n  ALIPAN_RUN_WITH_ENV_TEST: {TEST_SECRET}\n", encoding="utf-8")
            argument = "left  right; not-a-shell-command"
            completed = mock.Mock(returncode=17)

            with mock.patch.dict(
                os.environ,
                {"SOIA_PKM_ALIPAN_CONFIG_FILE": str(config)},
                clear=False,
            ), mock.patch.object(run_with_env.subprocess, "run", return_value=completed) as run:
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    return_code = run_with_env.main(["aliyunpan", "ls", argument])

                self.assertEqual(return_code, 17)
                self.assertEqual(os.environ["ALIPAN_RUN_WITH_ENV_TEST"], TEST_SECRET)
                run.assert_called_once_with(
                    ["aliyunpan", "ls", argument], check=False, shell=False
                )
                self.assertNotIn(TEST_SECRET, stdout.getvalue() + stderr.getvalue())

    def test_accepts_documented_executable_names(self) -> None:
        for command in (
            ["aliyunpan", "who"],
            ["aliyunpan.exe", "who"],
        ):
            with self.subTest(command=command[0]), mock.patch.object(
                run_with_env, "load_private_env"
            ) as load, mock.patch.object(run_with_env.subprocess, "run") as run:
                run.return_value = mock.Mock(returncode=0)
                self.assertEqual(run_with_env.main(command), 0)
                load.assert_called_once_with(required=False)
                run.assert_called_once_with(command, check=False, shell=False)

    def test_rejects_absolute_aliyunpan_path_before_loading_private_env(
        self,
    ) -> None:
        private_argument = f"--config={TEST_SECRET}"
        for executable in ("/tmp/aliyunpan", "/tmp/aliyunpan.exe"):
            with self.subTest(executable=executable), mock.patch.object(
                run_with_env, "load_private_env"
            ) as load, mock.patch.object(run_with_env.subprocess, "run") as run:
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    return_code = run_with_env.main([executable, private_argument])

                self.assertEqual(return_code, 2)
                load.assert_not_called()
                run.assert_not_called()
                self.assertNotIn(TEST_SECRET, stdout.getvalue() + stderr.getvalue())

    def test_rejects_non_aliyunpan_commands_before_loading_private_env(self) -> None:
        secret_command = f"env=ALIPAN_RUN_WITH_ENV_TEST={TEST_SECRET}"
        for command in (
            ["env", "aliyunpan", "who"],
            ["/bin/sh", "-c", "aliyunpan who"],
            ["./aliyunpan", "who"],
            [secret_command],
        ):
            with self.subTest(command=command[0]), mock.patch.object(
                run_with_env, "load_private_env"
            ) as load, mock.patch.object(run_with_env.subprocess, "run") as run:
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    return_code = run_with_env.main(command)

                self.assertEqual(return_code, 2)
                load.assert_not_called()
                run.assert_not_called()
                self.assertNotIn(TEST_SECRET, stdout.getvalue() + stderr.getvalue())

    def test_missing_command_returns_usage_error_without_loading_private_env(self) -> None:
        with mock.patch.object(run_with_env, "load_private_env") as load:
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = run_with_env.main(["--"])

        self.assertEqual(return_code, 2)
        load.assert_not_called()
        self.assertIn("usage:", stderr.getvalue())

    def test_startup_error_does_not_echo_private_arguments(self) -> None:
        private_argument = f"--config={TEST_SECRET}"
        with mock.patch.object(run_with_env, "load_private_env"), mock.patch.object(
            run_with_env.subprocess, "run", side_effect=OSError("private failure")
        ):
            stderr = StringIO()
            with redirect_stderr(stderr):
                return_code = run_with_env.main(["aliyunpan", private_argument])

        self.assertEqual(return_code, 127)
        self.assertNotIn(TEST_SECRET, stderr.getvalue())

    def test__env_cli_is_silent_with_private_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.yml"
            config.write_text(f"env:\n  ALIPAN_RUN_WITH_ENV_TEST: {TEST_SECRET}\n", encoding="utf-8")
            environment = os.environ.copy()
            environment["SOIA_PKM_ALIPAN_CONFIG_FILE"] = str(config)

            import subprocess

            completed = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "alipan_env.py")],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

        self.assertEqual(completed.returncode, 0)
        self.assertNotIn(TEST_SECRET, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
