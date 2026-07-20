import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-alipan-drive-ops" / "scripts" / "scan_drive.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("scan_drive", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScanDriveTests(unittest.TestCase):
    @staticmethod
    def ll_output(path, entries=()):
        lines = [f"当前目录: {path}", "----"]
        for index, (id_, sha1, size, name) in enumerate(entries, 1):
            lines.append(
                f"  {index}  {id_}  -  {sha1}  {size}  "
                f"2022-05-08 11:57:35  2022-05-08 11:57:35  {name}"
            )
        lines.append("----")
        return "\n".join(lines) + "\n"

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

    def test_ambiguous_sibling_names_are_marked_and_not_descended(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / "runner.py"
            runner.write_text("# test runner\n", encoding="utf-8")
            output = root / "scan.jsonl"
            calls = []

            def fake_run(args, **kwargs):
                path = args[-1]
                calls.append(path)
                if path == "/root":
                    stdout = self.ll_output(
                        path,
                        [
                            ("dup-a", "-", "-", "same/"),
                            ("dup-b", "-", "-", "same/"),
                            ("unique-id", "-", "-", "unique/"),
                        ],
                    )
                elif path == "/root/unique":
                    stdout = self.ll_output(path, [("file-1", "ABC", "7", "child.txt")])
                else:
                    self.fail(f"unexpected ll path: {path}")
                return subprocess.CompletedProcess(args, 0, stdout, "")

            stdout = io.StringIO()
            argv = [
                str(SCRIPT),
                "--driveId", "drive-1",
                "--root", "/root",
                "--out", str(output),
                "--workers", "1", "--attempts", "1",
                "--no-descend", "same",
            ]
            with mock.patch.dict(module.os.environ, {module.RUNNER_ENV: str(runner)}, clear=False), \
                    mock.patch.object(module.subprocess, "run", side_effect=fake_run), \
                    mock.patch.object(module.sys, "argv", argv), \
                    mock.patch.object(module.sys, "stdout", stdout):
                module.main()

            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            duplicate_rows = [row for row in rows if row.get("name") == "same"]
            self.assertEqual(len(duplicate_rows), 2)
            self.assertTrue(all(row.get("ambiguous_name") is True for row in duplicate_rows))
            unique_row = next(row for row in rows if row.get("name") == "unique")
            self.assertNotIn("ambiguous_name", unique_row)
            self.assertIn("/root/unique", calls)
            self.assertNotIn("/root/same", calls)

            errors = output.with_suffix(".jsonl.errors").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(errors), 2)
            self.assertTrue(
                all(
                    "AMBIGUOUS_NAME '/root/same' ids=[dup-a,dup-b] not_descended" in line
                    for line in errors
                ),
                errors,
            )
            done = output.with_suffix(".jsonl.done").read_text(encoding="utf-8").splitlines()
            self.assertNotIn("/root/same", done)
            self.assertIn("/root/unique", done)
            self.assertIn("ambig=2", output.with_suffix(".jsonl.progress").read_text(encoding="utf-8"))
            self.assertIn("ambig=2", stdout.getvalue())

    def test_completed_directories_are_not_relisted_within_run(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / "runner.py"
            runner.write_text("# test runner\n", encoding="utf-8")
            output = root / "scan.jsonl"

            completed = subprocess.CompletedProcess(
                [], 0, self.ll_output("/root"), ""
            )
            argv = [
                str(SCRIPT),
                "--driveId", "drive-1",
                "--root", "/root",
                "--root", "/root",
                "--out", str(output),
                "--workers", "1", "--attempts", "1",
            ]
            stdout = io.StringIO()
            with mock.patch.dict(module.os.environ, {module.RUNNER_ENV: str(runner)}, clear=False), \
                    mock.patch.object(module.subprocess, "run", return_value=completed) as run, \
                    mock.patch.object(module.sys, "argv", argv), \
                    mock.patch.object(module.sys, "stdout", stdout):
                module.main()

            run.assert_called_once()
            self.assertEqual(
                output.with_suffix(".jsonl.done").read_text(encoding="utf-8").splitlines(),
                ["/root"],
            )


    def test_resume_reenqueues_unscanned_frontier(self):
        """Resume must rescan dirs discovered in the JSONL but never listed.

        Interrupted state: "/root" and "/root/a" were both listed (their child
        rows are in the JSONL, so both are in the derived done set), but the
        grandchild dir "/root/a/b" was queued and never scanned. A naive resume
        skips "/root/a" (in done) and so never rediscovers "/root/a/b" — the
        whole subtree is silently lost with exit code 0.

        Also covers the exclusions: no_descend dirs ("private") and aggregated
        dirs (rows carrying "agg_files") must not be re-enqueued.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            call_log = root / "calls.log"
            call_log.write_text("", encoding="utf-8")
            runner = root / "fake_runner.py"
            runner.write_text(
                textwrap.dedent(
                    """
                    import sys
                    path = sys.argv[-1]
                    with open(%r, "a") as f:
                        f.write(path + "\\n")
                    def row(idx, id_, sha, size, name):
                        return (f"  {idx}  {id_}  -  {sha}  {size}  "
                                f"2022-05-08 11:57:35  2022-05-08 11:57:35  {name}")
                    lines = [f"当前目录: {path}", "----"]
                    if path == "/root/a/b":
                        lines.append(row(1, "f3", "ABC123", 7, "c.txt"))
                    elif path == "/root":
                        lines.append(row(1, "d1", "-", "-", "a/"))
                        lines.append(row(2, "f1", "AA", 5, "x.txt"))
                        lines.append(row(3, "d9", "-", "-", "private/"))
                    elif path == "/root/a":
                        lines.append(row(1, "d2", "-", "-", "b/"))
                        lines.append(row(2, "f2", "BB", 6, "y.txt"))
                        lines.append(row(3, "d3", "-", "-", "agg/"))
                    lines.append("----")
                    print("\\n".join(lines))
                    """
                ).strip()
                % str(call_log)
                + "\n",
                encoding="utf-8",
            )
            output = root / "scan.jsonl"
            interrupted = [
                {"path": "/root", "name": "a", "id": "d1", "dir": True, "size": None, "sha1": None},
                {"path": "/root", "name": "x.txt", "id": "f1", "dir": False, "size": 5, "sha1": "AA"},
                {"path": "/root", "name": "private", "id": "d9", "dir": True, "size": None, "sha1": None},
                {"path": "/root/a", "name": "b", "id": "d2", "dir": True, "size": None, "sha1": None},
                {"path": "/root/a", "name": "y.txt", "id": "f2", "dir": False, "size": 6, "sha1": "BB"},
                {"path": "/root/a", "name": "agg", "id": "d3", "dir": True, "size": None, "sha1": None},
                {"path": "/root/a", "name": "agg", "id": None, "dir": True, "size": None,
                 "agg_files": 5, "agg_size": 100},
            ]
            output.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in interrupted),
                encoding="utf-8",
            )

            env = dict(os.environ, SOIA_ALIPAN_RUNNER=str(runner))
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--driveId", "drive-1",
                    "--root", "/root",
                    "--out", str(output),
                    "--workers", "1", "--attempts", "1",
                    "--resume",
                    "--no-descend", "private",
                ],
                check=False, capture_output=True, text=True, env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            # (a) exactly one ll call, for the lost frontier dir — done dirs,
            # no_descend dirs and aggregated dirs must not be re-listed
            calls = [
                l for l in call_log.read_text(encoding="utf-8").splitlines() if l.strip()
            ]
            self.assertEqual(
                calls, ["/root/a/b"],
                f"Expected exactly one call for '/root/a/b', got: {calls}",
            )

            # (b) the rescued subtree's content is now in the output
            lines = output.read_text(encoding="utf-8").splitlines()
            rows = [json.loads(l) for l in lines]
            self.assertIn(
                ("/root/a/b", "c.txt"),
                [(r.get("path"), r.get("name")) for r in rows],
                f"c.txt missing from resumed output: {rows}",
            )

            # (c) nothing was re-emitted: exactly one new line
            self.assertEqual(
                len(lines), len(interrupted) + 1,
                f"resume duplicated rows: before={len(interrupted)} after={len(lines)}",
            )


    def test_resume_rescans_torn_directory_with_sidecar(self):
        """With a done sidecar, a torn directory listing must be rescanned.

        New-format interrupted state: the sidecar records only "/root" as fully
        listed. The JSONL contains root's complete listing plus a PARTIAL
        listing of "/root/d" (d has two children but only one row was written
        before the kill). The JSONL heuristic would wrongly treat "/root/d" as
        done; the sidecar is authoritative and says it is not — so resume must
        re-list it and recover the missing child row.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            call_log = root / "calls.log"
            call_log.write_text("", encoding="utf-8")
            runner = root / "fake_runner.py"
            runner.write_text(
                textwrap.dedent(
                    """
                    import sys
                    path = sys.argv[-1]
                    with open(%r, "a") as f:
                        f.write(path + "\\n")
                    def row(idx, id_, sha, size, name):
                        return (f"  {idx}  {id_}  -  {sha}  {size}  "
                                f"2022-05-08 11:57:35  2022-05-08 11:57:35  {name}")
                    lines = [f"当前目录: {path}", "----"]
                    if path == "/root/d":
                        lines.append(row(1, "f2", "PP", 3, "p.txt"))
                        lines.append(row(2, "f3", "QQ", 4, "q.txt"))
                    elif path == "/root":
                        lines.append(row(1, "d1", "-", "-", "d/"))
                        lines.append(row(2, "f1", "AA", 5, "x.txt"))
                    lines.append("----")
                    print("\\n".join(lines))
                    """
                ).strip()
                % str(call_log)
                + "\n",
                encoding="utf-8",
            )
            output = root / "scan.jsonl"
            torn_state = [
                {"path": "/root", "name": "d", "id": "d1", "dir": True, "size": None, "sha1": None},
                {"path": "/root", "name": "x.txt", "id": "f1", "dir": False, "size": 5, "sha1": "AA"},
                # torn: /root/d has two children, only one row made it to disk
                {"path": "/root/d", "name": "p.txt", "id": "f2", "dir": False, "size": 3, "sha1": "PP"},
            ]
            output.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in torn_state),
                encoding="utf-8",
            )
            sidecar = root / "scan.jsonl.done"
            sidecar.write_text("/root\n", encoding="utf-8")

            env = dict(os.environ, SOIA_ALIPAN_RUNNER=str(runner))
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--driveId", "drive-1",
                    "--root", "/root",
                    "--out", str(output),
                    "--workers", "1", "--attempts", "1",
                    "--resume",
                ],
                check=False, capture_output=True, text=True, env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            # (a) the torn dir is re-listed, and only it
            calls = [
                l for l in call_log.read_text(encoding="utf-8").splitlines() if l.strip()
            ]
            self.assertEqual(
                calls, ["/root/d"],
                f"Expected exactly one call for the torn dir '/root/d', got: {calls}",
            )

            # (b) the child row lost in the tear is recovered
            rows = [json.loads(l) for l in output.read_text(encoding="utf-8").splitlines()]
            self.assertIn(
                ("/root/d", "q.txt"),
                [(r.get("path"), r.get("name")) for r in rows],
                f"q.txt not recovered after resume: {rows}",
            )

            # (c) the sidecar now records the torn dir as fully listed
            done_after = sidecar.read_text(encoding="utf-8").splitlines()
            self.assertIn("/root/d", done_after, f"'/root/d' missing from sidecar: {done_after}")


    def test_resume_seeds_sidecar_for_legacy_scans(self):
        """Resuming a legacy scan (no sidecar) migrates the heuristic done set.

        The heuristic done set derived from the JSONL must be written to a
        newly created sidecar, and the resume behavior itself must match the
        legacy frontier semantics (discovered-but-unlisted dirs are rescanned).
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            call_log = root / "calls.log"
            call_log.write_text("", encoding="utf-8")
            runner = root / "fake_runner.py"
            runner.write_text(
                textwrap.dedent(
                    """
                    import sys
                    path = sys.argv[-1]
                    with open(%r, "a") as f:
                        f.write(path + "\\n")
                    def row(idx, id_, sha, size, name):
                        return (f"  {idx}  {id_}  -  {sha}  {size}  "
                                f"2022-05-08 11:57:35  2022-05-08 11:57:35  {name}")
                    lines = [f"当前目录: {path}", "----"]
                    if path == "/root/a":
                        lines.append(row(1, "f2", "YY", 6, "y.txt"))
                    lines.append("----")
                    print("\\n".join(lines))
                    """
                ).strip()
                % str(call_log)
                + "\n",
                encoding="utf-8",
            )
            output = root / "scan.jsonl"
            legacy_state = [
                {"path": "/root", "name": "a", "id": "d1", "dir": True, "size": None, "sha1": None},
                {"path": "/root", "name": "x.txt", "id": "f1", "dir": False, "size": 5, "sha1": "AA"},
            ]
            output.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in legacy_state),
                encoding="utf-8",
            )
            sidecar = root / "scan.jsonl.done"
            self.assertFalse(sidecar.exists())

            env = dict(os.environ, SOIA_ALIPAN_RUNNER=str(runner))
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--driveId", "drive-1",
                    "--root", "/root",
                    "--out", str(output),
                    "--workers", "1", "--attempts", "1",
                    "--resume",
                ],
                check=False, capture_output=True, text=True, env=env,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            # behavior matches legacy frontier semantics: only "/root/a" rescanned
            calls = [
                l for l in call_log.read_text(encoding="utf-8").splitlines() if l.strip()
            ]
            self.assertEqual(calls, ["/root/a"], f"Expected exactly ['/root/a'], got: {calls}")

            # sidecar created: heuristic done ("/root") seeded + new completion ("/root/a")
            self.assertTrue(sidecar.exists(), "sidecar was not created on legacy resume")
            done_after = {
                l for l in sidecar.read_text(encoding="utf-8").splitlines() if l.strip()
            }
            self.assertEqual(
                done_after, {"/root", "/root/a"},
                f"sidecar should hold seeded + new completions, got: {done_after}",
            )


if __name__ == "__main__":
    unittest.main()
