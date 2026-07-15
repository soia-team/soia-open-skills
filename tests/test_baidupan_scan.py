import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-baidupan" / "scripts" / "scan_drive.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("baidupan_scan", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BaidupanScanTests(unittest.TestCase):
    def test_parse_official_json_uses_virtual_parent_not_display_path(self):
        module = load_module()
        output = json.dumps(
            [
                {
                    "fs_id": 11,
                    "path": "我的应用数据/bdpan/资料",
                    "server_filename": "资料",
                    "isdir": True,
                    "size": 0,
                    "server_mtime": 1700000000,
                },
                {
                    "fs_id": 12,
                    "path": "我的应用数据/bdpan/资料/讲义.pdf",
                    "server_filename": "讲义.pdf",
                    "isdir": False,
                    "size": 1024,
                    "server_mtime": 1700000001,
                    "md5": "abc123",
                },
            ],
            ensure_ascii=False,
        )

        rows = module.parse_json_output(output, "/")

        self.assertEqual(rows[0]["path"], "/")
        self.assertEqual(rows[0]["name"], "资料")
        self.assertTrue(rows[0]["dir"])
        self.assertEqual(rows[1]["path"], "/")
        self.assertEqual(rows[1]["name"], "讲义.pdf")
        self.assertEqual(rows[1]["size"], 1024)
        self.assertEqual(rows[1]["md5"], "abc123")

        child_output = json.dumps(
            [{"fs_id": 12, "server_filename": "讲义.pdf", "isdir": False, "size": 1024}],
            ensure_ascii=False,
        )
        child_rows = module.parse_json_output(child_output, "/资料")
        self.assertEqual(child_rows[0]["path"], "/资料")
        self.assertEqual(child_rows[0]["_remote_path"], "/资料/讲义.pdf")

    def test_rejects_remote_path_traversal(self):
        module = load_module()
        with self.assertRaises(ValueError):
            module.parse_json_output("[]", "/资料/../私密")

    def test_forward_scan_writes_clean_jsonl_and_resume_sidecars(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_cli = root / "fake-bdpan"
            fake_cli.write_text(
                textwrap.dedent(
                    """
                    #!/usr/bin/env python3
                    import json
                    import sys

                    paths = [arg for arg in sys.argv[1:] if arg not in {"ls", "--json"}]
                    path = paths[0] if paths else ""
                    if path == "":
                        rows = [
                            {"fs_id": 1, "path": "我的应用数据/bdpan/资料", "server_filename": "资料", "isdir": True, "size": 0},
                            {"fs_id": 2, "path": "我的应用数据/bdpan/readme.txt", "server_filename": "readme.txt", "isdir": False, "size": 7},
                        ]
                    else:
                        rows = [
                            {"fs_id": 3, "path": "我的应用数据/bdpan/资料/讲义.pdf", "server_filename": "讲义.pdf", "isdir": False, "size": 1024},
                        ]
                    print(json.dumps(rows, ensure_ascii=False))
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            output = root / "scan.jsonl"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    "/",
                    "--out",
                    str(output),
                    "--binary",
                    str(fake_cli),
                    "--workers",
                    "1",
                    "--attempts",
                    "1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["name"] for row in rows], ["资料", "readme.txt", "讲义.pdf"])
            self.assertTrue(all("_remote_path" not in row for row in rows))
            self.assertEqual(
                (root / "scan.jsonl.done").read_text(encoding="utf-8").splitlines(),
                ["/", "/资料"],
            )
            self.assertEqual((root / "scan.jsonl.errors").read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
