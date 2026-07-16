import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "soia-pkm-alipan-drive-ops" / "scripts" / "compact_scan_jsonl.py"


def write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class CompactScanJsonlTests(unittest.TestCase):
    def test_output_mode_compacts_by_physical_key_without_merging_distinct_ids(self):
        first = {
            "path": "/资料",
            "name": "讲义.pdf",
            "id": "file-a",
            "dir": False,
            "size": 1024,
            "sha1": "A" * 40,
        }
        duplicate_with_new_metadata = {**first, "size": 2048, "sha1": "B" * 40}
        distinct_physical_row = {**first, "id": "file-b"}

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "scan.jsonl"
            destination = directory / "compact.jsonl"
            write_jsonl(source, [first, duplicate_with_new_metadata, distinct_physical_row])

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(destination)],
                capture_output=True,
                check=False,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["duplicate_rows"], 1)
            self.assertEqual(
                [json.loads(line) for line in destination.read_text(encoding="utf-8").splitlines()],
                [first, distinct_physical_row],
            )
            self.assertTrue(source.exists())

    def test_in_place_mode_replaces_input_and_keeps_default_backup(self):
        row = {
            "path": "/资料",
            "name": "讲义.pdf",
            "id": "file-a",
            "dir": False,
            "size": 1024,
            "sha1": "A" * 40,
        }

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scan.jsonl"
            write_jsonl(source, [row, row])
            original = source.read_text(encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(source), "--in-place"],
                capture_output=True,
                check=False,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["duplicate_rows"], 1)
            self.assertEqual(
                [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()],
                [row],
            )
            self.assertEqual(source.with_name("scan.jsonl.pre-compact").read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
