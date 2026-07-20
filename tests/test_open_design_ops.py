#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
import urllib.error
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "soia-dev-open-design-ops" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import check_env  # noqa: E402
import daemon_ctl  # noqa: E402
import list_skills  # noqa: E402


def load_run_with_env():
    name = "open_design_ops_run_with_env"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / "run_with_env.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load run_with_env.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_with_env = load_run_with_env()


class CheckEnvTests(unittest.TestCase):
    def test_missing_node_fails_closed(self) -> None:
        def which(name: str) -> str | None:
            return None if name == "node" else "/tool/pnpm"

        with mock.patch.dict(os.environ, {"OPEN_DESIGN_HOME": "/checkout"}, clear=True), mock.patch.object(
            check_env, "load_private_env"
        ), mock.patch.object(check_env.shutil, "which", side_effect=which), mock.patch.object(
            check_env, "executable_version", return_value="10.33.2"
        ), mock.patch.object(check_env.os.path, "isdir", return_value=True), mock.patch.object(
            check_env.os.path, "isfile", return_value=True
        ):
            result = check_env.check_environment()

        self.assertEqual(result["status"], "error")
        self.assertIn("node", result["missing"])
        self.assertFalse(result["checks"]["node"]["found"])

    def test_missing_open_design_home_fails_closed(self) -> None:
        def which(name: str) -> str:
            return f"/tool/{name}"

        def version(executable: str) -> str:
            return "v24.1.0" if executable.endswith("node") else "10.33.2"

        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            check_env, "load_private_env"
        ), mock.patch.object(check_env.shutil, "which", side_effect=which), mock.patch.object(
            check_env, "executable_version", side_effect=version
        ), mock.patch.object(check_env.os.path, "isdir", return_value=False):
            result = check_env.check_environment()

        self.assertEqual(result["status"], "error")
        self.assertIn("OPEN_DESIGN_HOME", result["missing"])
        self.assertFalse(result["checks"]["open_design_home"]["configured"])


class FakeResponse:
    def __init__(self, payload: dict[str, object], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class DaemonHealthTests(unittest.TestCase):
    def test_health_reachable_skills_response(self) -> None:
        response = FakeResponse({"skills": [{"name": "one"}, {"name": "two"}]})
        with mock.patch.object(daemon_ctl.urllib.request, "urlopen", return_value=response) as urlopen:
            result = daemon_ctl.health_request("http://127.0.0.1:7456")

        self.assertTrue(result["reachable"])
        self.assertEqual(result["skills_count"], 2)
        urlopen.assert_called_once()

    def test_health_unreachable(self) -> None:
        with mock.patch.object(
            daemon_ctl.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            result = daemon_ctl.health_request("http://127.0.0.1:7456")

        self.assertFalse(result["reachable"])
        self.assertEqual(result["error"], "URLError")


class ListSkillsTests(unittest.TestCase):
    def test_parse_sample_payload_and_category_filter(self) -> None:
        fixture = {
            "skills": [
                {
                    "id": "pptx-generator",
                    "name": "pptx-generator",
                    "description": "Create editable decks.",
                    "mode": "deck",
                    "category": "slides",
                },
                {
                    "id": "web-clone",
                    "description": "Clone a web design.",
                    "mode": "prototype",
                    "category": "web-artifacts",
                },
            ]
        }

        parsed = list_skills.parse_skill_payload(fixture, category="slides")

        self.assertEqual(
            parsed,
            [
                {
                    "name": "pptx-generator",
                    "description": "Create editable decks.",
                    "od": {"mode": "deck"},
                    "category": "slides",
                }
            ],
        )


class RunWithEnvAllowlistTests(unittest.TestCase):
    def test_rejects_arbitrary_commands_before_loading_config(self) -> None:
        for command in (
            ["env"],
            ["/bin/sh", "-c", "pnpm tools-dev status"],
            ["pnpm", "exec", "arbitrary-tool"],
            ["pnpm", "dlx", "arbitrary-package"],
            ["node", "arbitrary.js"],
        ):
            with self.subTest(command=command), mock.patch.object(
                run_with_env, "load_private_env"
            ) as load, mock.patch.object(run_with_env.subprocess, "run") as run:
                stderr = StringIO()
                with redirect_stderr(stderr):
                    return_code = run_with_env.main(command)

                self.assertEqual(return_code, 2)
                load.assert_not_called()
                run.assert_not_called()
                self.assertIn("allowlist", stderr.getvalue())

    def test_accepts_documented_commands(self) -> None:
        accepted = (
            ["pnpm", "install"],
            ["pnpm", "tools-dev", "status"],
            ["pnpm", "--filter", "@open-design/daemon", "build"],
            ["corepack", "enable"],
            ["corepack", "pnpm", "--version"],
        )
        for command in accepted:
            with self.subTest(command=command):
                self.assertTrue(run_with_env.is_allowed_command(command))


if __name__ == "__main__":
    unittest.main()
