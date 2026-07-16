import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-baidu-netdisk-ops" / "scripts" / "scan_drive.py"


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


    def test_resume_skips_done_directories_without_reemitting(self):
        """Resuming must not re-scan or re-emit entries for directories in the done set."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_cli = root / "fake-bdpan"
            # The fake CLI logs every invocation to a sidecar so we can count API calls.
            call_log = root / "calls.log"
            fake_cli.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env python3
                    import json, sys
                    paths = [arg for arg in sys.argv[1:] if arg not in {{"ls", "--json"}}]
                    path = paths[0] if paths else ""
                    with open({str(call_log)!r}, "a") as f:
                        f.write(path + "\\n")
                    if path == "":
                        rows = [
                            {{"fs_id": 1, "server_filename": "sub", "isdir": True, "size": 0}},
                            {{"fs_id": 2, "server_filename": "a.txt", "isdir": False, "size": 5}},
                        ]
                    elif path == "sub":
                        rows = [
                            {{"fs_id": 3, "server_filename": "b.txt", "isdir": False, "size": 10}},
                        ]
                    else:
                        rows = []
                    print(json.dumps(rows, ensure_ascii=False))
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            output = root / "scan.jsonl"

            # --- First run (no resume) ------------------------------------------
            r1 = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--root", "/",
                    "--out", str(output),
                    "--binary", str(fake_cli),
                    "--workers", "1", "--attempts", "1",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            first_lines = output.read_text(encoding="utf-8").splitlines()
            first_names = [json.loads(l)["name"] for l in first_lines]
            self.assertIn("sub", first_names)
            self.assertIn("b.txt", first_names)

            # --- Resume run: pretend "/" and "/sub" are already done --------------
            done_file = root / "scan.jsonl.done"
            # done file already has "/" and "/sub" from the first run; verify
            done_contents = done_file.read_text(encoding="utf-8").splitlines()
            self.assertIn("/", done_contents)
            self.assertIn("/sub", done_contents)

            call_log.write_text("")  # reset call counter
            r2 = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--root", "/",
                    "--out", str(output),
                    "--binary", str(fake_cli),
                    "--workers", "1", "--attempts", "1",
                    "--resume",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)

            # The resume run should NOT have called the CLI at all (both dirs done)
            resume_calls = [
                l for l in call_log.read_text(encoding="utf-8").splitlines() if l.strip()
            ]
            self.assertEqual(
                resume_calls, [],
                f"Expected zero API calls on full resume, got: {resume_calls}",
            )

            # The output file should have no new lines appended beyond the first run
            all_lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                len(all_lines), len(first_lines),
                f"Resume appended duplicate rows: first={len(first_lines)} total={len(all_lines)}",
            )


    def test_resume_reenqueues_unscanned_frontier(self):
        """Resume must rescan dirs discovered but never listed (in JSONL, not in done).

        Simulates an interrupted scan: "/" was listed (its rows are in the JSONL,
        "/" is in the done file) but the child dir "/sub" was never scanned. A
        naive resume drops the whole "/sub" subtree silently.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_cli = root / "fake-bdpan"
            call_log = root / "calls.log"
            fake_cli.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env python3
                    import json, sys
                    paths = [arg for arg in sys.argv[1:] if arg not in {{"ls", "--json"}}]
                    path = paths[0] if paths else ""
                    with open({str(call_log)!r}, "a") as f:
                        f.write(path + "\\n")
                    if path == "sub":
                        rows = [
                            {{"fs_id": 3, "server_filename": "b.txt", "isdir": False, "size": 10}},
                        ]
                    else:
                        rows = [
                            {{"fs_id": 1, "server_filename": "sub", "isdir": True, "size": 0}},
                            {{"fs_id": 2, "server_filename": "a.txt", "isdir": False, "size": 5}},
                        ]
                    print(json.dumps(rows, ensure_ascii=False))
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            call_log.write_text("", encoding="utf-8")
            output = root / "scan.jsonl"

            # Handcraft the interrupted state: "/" fully listed, "/sub" never scanned.
            interrupted_rows = [
                {"path": "/", "name": "sub", "id": "1", "dir": True,
                 "size": None, "sha1": None, "md5": None, "mtime": None},
                {"path": "/", "name": "a.txt", "id": "2", "dir": False,
                 "size": 5, "sha1": None, "md5": None, "mtime": None},
            ]
            output.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in interrupted_rows),
                encoding="utf-8",
            )
            done_file = root / "scan.jsonl.done"
            done_file.write_text("/\n", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--root", "/",
                    "--out", str(output),
                    "--binary", str(fake_cli),
                    "--workers", "1", "--attempts", "1",
                    "--resume",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            # (a) exactly one CLI call, for "sub" — "/" must not be re-listed
            calls = [
                l for l in call_log.read_text(encoding="utf-8").splitlines() if l.strip()
            ]
            self.assertEqual(calls, ["sub"], f"Expected exactly one call for 'sub', got: {calls}")

            # (b) output gained the b.txt row
            names = [
                json.loads(l)["name"]
                for l in output.read_text(encoding="utf-8").splitlines()
            ]
            self.assertIn("b.txt", names, f"b.txt missing from resumed output: {names}")

            # (c) done file now records "/sub"
            done_after = done_file.read_text(encoding="utf-8").splitlines()
            self.assertIn("/sub", done_after, f"'/sub' missing from done file: {done_after}")


if __name__ == "__main__":
    unittest.main()
