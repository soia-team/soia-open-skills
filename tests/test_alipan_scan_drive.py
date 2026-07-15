import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-alipan" / "scripts" / "scan_drive.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("scan_drive", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScanDriveTests(unittest.TestCase):
    def test_default_runner_is_resolved_from_this_skill_scripts_directory(self):
        module = load_module()

        with mock.patch.dict(module.os.environ, {}, clear=False):
            module.os.environ.pop(module.RUNNER_ENV, None)
            self.assertEqual(
                module.alipan_runner_path(),
                SCRIPT.with_name("run_with_env.py"),
            )

    def test_runner_override_is_used_and_ll_arguments_are_preserved(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            runner = Path(temporary) / "runner.py"
            runner.write_text("# test runner\n", encoding="utf-8")
            completed = module.subprocess.CompletedProcess([], 0, "当前目录: /资料\n", "")
            with mock.patch.dict(module.os.environ, {module.RUNNER_ENV: str(runner)}, clear=False), mock.patch.object(
                module.subprocess,
                "run",
                return_value=completed,
            ) as run:
                result = module.run_aliyunpan_ll(
                    module.require_alipan_runner(),
                    "drive-1",
                    "/资料/课程  双空格",
                    11,
                )

        self.assertIs(result, completed)
        run.assert_called_once_with(
            [
                sys.executable,
                str(runner),
                "--",
                "aliyunpan",
                "ll",
                "--driveId",
                "drive-1",
                "/资料/课程  双空格",
            ],
            capture_output=True,
            text=True,
            timeout=11,
        )

    def test_missing_runner_fails_closed_without_bare_aliyunpan_fallback(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing-runner.py"
            with mock.patch.dict(module.os.environ, {module.RUNNER_ENV: str(missing)}, clear=False), mock.patch.object(
                module.subprocess,
                "run",
            ) as run:
                with self.assertRaisesRegex(FileNotFoundError, "SOIA_ALIPAN_RUNNER"):
                    module.require_alipan_runner()

        run.assert_not_called()

    def test_row_identity_uses_the_stable_physical_key(self):
        module = load_module()

        self.assertEqual(
            module.row_identity(
                {
                    "path": "/资料",
                    "name": "讲义  最终版.pdf",
                    "id": "file-a",
                    "dir": False,
                    "size": 1024,
                    "sha1": "0123456789ABCDEF0123456789ABCDEF01234567",
                }
            ),
            ("/资料", "讲义  最终版.pdf", "file-a", False),
        )

    def test_parse_ll_output_preserves_repeated_spaces_and_sha1(self):
        module = load_module()
        output = """
当前目录: /资料
----
  1  62773faf37b033a372074651b7ceec718f4a4733  -  -  -  2022-05-08 11:57:35  2022-05-08 11:57:35  31.  课程资料/
  2  6abc  1.00KB  0123456789ABCDEF0123456789ABCDEF01234567  1024  2022-05-08 11:57:36  2022-05-08 11:57:36  讲义  最终版.pdf
                                               总: 1.00KB  文件总数: 1, 目录总数: 1
----
"""

        rows = module.parse_ll_output(output)

        self.assertEqual(
            rows,
            [
                {
                    "id": "62773faf37b033a372074651b7ceec718f4a4733",
                    "name": "31.  课程资料",
                    "dir": True,
                    "size": None,
                    "sha1": None,
                },
                {
                    "id": "6abc",
                    "name": "讲义  最终版.pdf",
                    "dir": False,
                    "size": 1024,
                    "sha1": "0123456789ABCDEF0123456789ABCDEF01234567",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
