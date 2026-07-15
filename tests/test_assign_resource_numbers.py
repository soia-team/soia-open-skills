#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/soia-pkm-alipan-curator/scripts/assign_resource_numbers.py"
SPEC = importlib.util.spec_from_file_location("assign_resource_numbers", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {SCRIPT}")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class AssignResourceNumbersTests(unittest.TestCase):
    def run_main(self, *arguments: str | Path) -> int:
        argv = sys.argv
        try:
            sys.argv = [str(SCRIPT), *(str(argument) for argument in arguments)]
            return module.main()
        finally:
            sys.argv = argv

    def test_assigns_smallest_free_number_only_to_directories(self) -> None:
        inventory = {
            "d1": {"id": "d1", "dir": True},
            "d2": {"id": "d2", "dir": True},
            "f1": {"id": "f1", "dir": False},
            "skip": {"id": "skip", "dir": True},
            "pseudo": {"id": "pseudo", "dir": True},
            "reserve": {"id": "reserve", "dir": True},
        }
        rows = [
            {"file_id": "d1", "target_parent": "/A", "normalized_name": "Course A"},
            {"file_id": "d2", "target_parent": "/A", "normalized_name": "003_Course B"},
            {"file_id": "f1", "target_parent": "/A", "normalized_name": "Book.pdf"},
            {"file_id": "skip", "target_parent": "/Archive", "normalized_name": "10_Risk"},
            {"file_id": "pseudo", "target_parent": "<split-by-course>", "normalized_name": "Old shell"},
        ]
        reserves = [{"file_id": "reserve", "final_target": "/A", "final_name": "001_Existing"}]
        editable = [(Path("map.tsv"), ["file_id", "target_parent", "normalized_name"], rows)]
        reserve_inputs = [(Path("reserve.tsv"), reserves)]

        report = module.assign_numbers(
            inventory,
            editable,
            reserve_inputs,
            id_column="file_id",
            target_column="target_parent",
            name_column="normalized_name",
            reserve_id_column="file_id",
            reserve_target_column="final_target",
            reserve_name_column="final_name",
            exclude_targets=["/Archive"],
            width=3,
            start=1,
            step=1,
        )

        self.assertEqual(rows[0]["normalized_name"], "002_Course A")
        self.assertEqual(rows[1]["normalized_name"], "003_Course B")
        self.assertEqual(rows[2]["normalized_name"], "Book.pdf")
        self.assertEqual(rows[3]["normalized_name"], "10_Risk")
        self.assertEqual(rows[4]["normalized_name"], "Old shell")
        self.assertEqual(report["changed"], 1)

    def test_main_is_idempotent_after_first_in_place_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inventory = root / "inventory.jsonl"
            mapping = root / "map.tsv"
            inventory.write_text(json.dumps({"id": "d1", "dir": True}) + "\n", encoding="utf-8")
            mapping.write_text("file_id\ttarget_parent\tnormalized_name\n" "d1\t/A\tCourse\n", encoding="utf-8")
            arguments = ("--inventory", inventory, "--input", mapping, "--in-place")
            self.assertEqual(self.run_main(*arguments), 0)
            first = mapping.read_text(encoding="utf-8")
            self.assertEqual(self.run_main(*arguments), 0)
            second = mapping.read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertIn("001_Course", first)

    def test_multi_input_replace_failure_restores_all_maps_and_cleans_temporaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inventory = root / "inventory.jsonl"
            first_map = root / "first.tsv"
            second_map = root / "second.tsv"
            inventory.write_text(
                "\n".join(
                    json.dumps(item)
                    for item in [
                        {"id": "d1", "dir": True},
                        {"id": "d2", "dir": True},
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            first_original = "file_id\ttarget_parent\tnormalized_name\n" "d1\t/A\tFirst course\n"
            second_original = "file_id\ttarget_parent\tnormalized_name\n" "d2\t/B\tSecond course\n"
            first_map.write_text(first_original, encoding="utf-8")
            second_map.write_text(second_original, encoding="utf-8")

            original_replace = module.os.replace
            failed = False

            def fail_second_replace(source: str | Path, destination: str | Path) -> None:
                nonlocal failed
                if Path(destination) == second_map and not failed:
                    failed = True
                    raise OSError("injected replacement failure")
                original_replace(source, destination)

            arguments = (
                "--inventory",
                inventory,
                "--input",
                first_map,
                "--input",
                second_map,
                "--in-place",
            )
            with patch.object(module.os, "replace", side_effect=fail_second_replace):
                self.assertEqual(self.run_main(*arguments), 2)

            self.assertTrue(failed)
            self.assertEqual(first_map.read_text(encoding="utf-8"), first_original)
            self.assertEqual(second_map.read_text(encoding="utf-8"), second_original)
            self.assertEqual(list(root.glob(".*.tmp")), [])

    def test_multi_input_prepare_failure_does_not_replace_any_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inventory = root / "inventory.jsonl"
            first_map = root / "first.tsv"
            second_map = root / "second.tsv"
            inventory.write_text(
                "\n".join(
                    json.dumps(item)
                    for item in [
                        {"id": "d1", "dir": True},
                        {"id": "d2", "dir": True},
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            first_original = "file_id\ttarget_parent\tnormalized_name\n" "d1\t/A\tFirst course\n"
            second_original = "file_id\ttarget_parent\tnormalized_name\n" "d2\t/B\tSecond course\n"
            first_map.write_text(first_original, encoding="utf-8")
            second_map.write_text(second_original, encoding="utf-8")

            original_write = module._write_tsv_temporary
            attempts = 0

            def fail_second_temporary(
                path: Path,
                fieldnames: list[str],
                rows: list[dict[str, str]],
            ) -> Path:
                nonlocal attempts
                attempts += 1
                if attempts == 2:
                    raise OSError("injected temporary write failure")
                return original_write(path, fieldnames, rows)

            arguments = (
                "--inventory",
                inventory,
                "--input",
                first_map,
                "--input",
                second_map,
                "--in-place",
            )
            with patch.object(module, "_write_tsv_temporary", side_effect=fail_second_temporary):
                with patch.object(module.os, "replace") as replace:
                    self.assertEqual(self.run_main(*arguments), 2)
                    replace.assert_not_called()

            self.assertEqual(first_map.read_text(encoding="utf-8"), first_original)
            self.assertEqual(second_map.read_text(encoding="utf-8"), second_original)
            self.assertEqual(list(root.glob(".*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
