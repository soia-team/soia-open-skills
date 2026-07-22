#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "soia-dev-officecli-ops" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import check_env  # noqa: E402
import officecli_safe  # noqa: E402


class CheckEnvironmentTests(unittest.TestCase):
    def test_missing_binary_fails_closed(self) -> None:
        with mock.patch.object(check_env.shutil, "which", return_value=None):
            result = check_env.check_environment({})

        self.assertEqual(result["status"], "error")
        self.assertFalse(result["available"])

    def test_compatible_version_is_accepted(self) -> None:
        completed = mock.Mock(returncode=0, stdout="1.0.140\n", stderr="")
        with mock.patch.object(check_env, "resolve_binary", return_value="/tool/officecli"), mock.patch.object(
            check_env.subprocess, "run", return_value=completed
        ):
            result = check_env.check_environment({})

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["compatible"])
        self.assertEqual(result["version"], "1.0.140")

    def test_old_version_is_rejected_for_writes(self) -> None:
        completed = mock.Mock(returncode=0, stdout="1.0.136\n", stderr="")
        with mock.patch.object(check_env, "resolve_binary", return_value="/tool/officecli"), mock.patch.object(
            check_env.subprocess, "run", return_value=completed
        ):
            result = check_env.check_environment({})

        self.assertEqual(result["status"], "error")
        self.assertFalse(result["compatible"])


class SafeMutationTests(unittest.TestCase):
    def test_rejects_in_place_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "deck.pptx"
            source.write_bytes(b"fixture")
            with self.assertRaisesRegex(ValueError, "in-place"):
                officecli_safe.build_plan(
                    input_path=source,
                    output_path=source,
                    office_args=["set", "/slide[1]", "--prop", "name=Title"],
                    overwrite=False,
                )

    def test_rejects_unapproved_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.docx"
            output = Path(directory) / "result.docx"
            source.write_bytes(b"source")
            output.write_bytes(b"existing")
            with self.assertRaisesRegex(ValueError, "--overwrite"):
                officecli_safe.build_plan(
                    input_path=source,
                    output_path=output,
                    office_args=["set", "/body/p[1]", "--prop", "bold=true"],
                    overwrite=False,
                )

    def test_rejects_non_mutation_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.xlsx"
            source.write_bytes(b"source")
            with self.assertRaisesRegex(ValueError, "allowlist"):
                officecli_safe.build_plan(
                    input_path=source,
                    output_path=Path(directory) / "result.xlsx",
                    office_args=["install"],
                    overwrite=False,
                )

    def test_executes_copy_mutation_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pptx"
            output = Path(directory) / "result.pptx"
            source.write_bytes(b"source")
            plan = officecli_safe.build_plan(
                input_path=source,
                output_path=output,
                office_args=["set", "/slide[1]", "--prop", "name=Title"],
                overwrite=False,
            )
            completed = mock.Mock(returncode=0, stdout="{}", stderr="")
            with mock.patch.object(officecli_safe.subprocess, "run", return_value=completed) as run:
                result = officecli_safe.execute_plan(plan, binary="/tool/officecli", timeout=30)

            self.assertTrue(result["success"])
            self.assertEqual(output.read_bytes(), b"source")
            self.assertEqual(run.call_count, 4)
            commands = [call.args[0][1] for call in run.call_args_list]
            self.assertEqual(commands, ["set", "close", "validate", "view"])


if __name__ == "__main__":
    unittest.main()
