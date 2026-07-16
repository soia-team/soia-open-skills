#!/usr/bin/env python3
"""CLI contract tests for the family navigation workbook generator."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "soia-pkm-alipan-curator"
    / "scripts"
    / "gen_family_nav_xlsx.mjs"
)


class FamilyNavigationCliTests(unittest.TestCase):
    @staticmethod
    def payload() -> dict[str, object]:
        return {
            "title": "家庭导航",
            "summary": "说明",
            "generatedAt": "2026-01-01",
            "partition": "10_示例",
            "guidance": [{"label": "先选主线", "text": "一次只选一套。"}],
            "rows": [
                {
                    "category": "10_课程",
                    "name": "示例课程",
                    "audience": "启蒙阶段",
                    "type": "视频",
                    "usage": "亲子观看",
                    "pace": "每次十分钟",
                    "path": "/10_示例/10_课程",
                    "url": "https://www.alipan.com/drive/file/all/backup/0123456789abcdef0123456789abcdef01234567",
                }
            ],
        }

    @staticmethod
    def fake_artifact_tool() -> str:
        return r'''
const fs = require("node:fs");
const state = { workbook: null };
function log(event) { if (process.env.FAKE_ARTIFACT_LOG) fs.appendFileSync(process.env.FAKE_ARTIFACT_LOG, `${event}\n`); }
function columnIndex(label) { return [...label].reduce((result, char) => result * 26 + char.charCodeAt(0) - 64, 0) - 1; }
function parseRange(address) {
  const [start, end = start] = address.split(":");
  const parseCell = (cell) => { const match = /^([A-Z]+)(\d+)$/.exec(cell); return [Number(match[2]) - 1, columnIndex(match[1])]; };
  const [startRow, startCol] = parseCell(start); const [endRow, endCol] = parseCell(end);
  return [startRow, startCol, endRow - startRow + 1, endCol - startCol + 1];
}
class Range {
  constructor(sheet, row, col, rowCount, colCount) { this.sheet = sheet; this.row = row; this.col = col; this.rowCount = rowCount; this.colCount = colCount; this._format = {}; }
  _set(target, matrix) { matrix.forEach((sourceRow, rowOffset) => sourceRow.forEach((value, colOffset) => { const row = this.row + rowOffset; const col = this.col + colOffset; (target[row] ||= [])[col] = value; })); }
  _get(target) { return Array.from({ length: this.rowCount }, (_, rowOffset) => Array.from({ length: this.colCount }, (_, colOffset) => target[this.row + rowOffset]?.[this.col + colOffset] ?? null)); }
  set values(matrix) { this._set(this.sheet.values, matrix); } get values() { return this._get(this.sheet.values); }
  set formulas(matrix) { this._set(this.sheet.formulas, matrix); } get formulas() { return this._get(this.sheet.formulas); }
  set format(value) { this._format = value; } get format() { return this._format; }
  merge() {}
}
class Sheet {
  constructor(name) { this.name = name; this.values = []; this.formulas = []; this.tables = { add: () => ({}) }; this.freezePanes = { freezeRows() {}, freezeColumns() {} }; }
  getRange(address) { return new Range(this, ...parseRange(address)); }
  getRangeByIndexes(row, col, rowCount, colCount) { return new Range(this, row, col, rowCount, colCount); }
  getUsedRange() { const source = [this.values, this.formulas]; let lastRow = 0; let lastCol = 0; source.forEach((grid) => grid.forEach((row, rowIndex) => row?.forEach((value, colIndex) => { if (value !== null && value !== undefined) { lastRow = Math.max(lastRow, rowIndex); lastCol = Math.max(lastCol, colIndex); } }))); return new Range(this, 0, 0, lastRow + 1, lastCol + 1); }
}
class FakeWorkbook {
  constructor() { const items = []; this.worksheets = { items, add(name) { const sheet = new Sheet(name); items.push(sheet); return sheet; }, getItem(name) { return items.find((sheet) => sheet.name === name); } }; }
  async inspect() { log("inspect"); return { ndjson: process.env.FAKE_FORMULA_ERROR ? '{"kind":"match"}\n' : "" }; }
}
const Workbook = { create: () => new FakeWorkbook() };
const SpreadsheetFile = {
  async exportXlsx(workbook) { state.workbook = workbook; log("export"); return { async save(output) { log(`save:${output}`); fs.writeFileSync(output, "fake xlsx"); } }; },
  async importXlsx() { log(`import:${fs.readFileSync(process.env.FINAL_OUTPUT, "utf8")}`); return state.workbook; },
};
const FileBlob = { async load(file) { log(`load:${file}`); return fs.readFileSync(file); } };
module.exports = { Workbook, SpreadsheetFile, FileBlob };
'''

    @staticmethod
    def fake_soffice() -> str:
        return """#!/usr/bin/env python3
import json
import os
import shutil
import sys
from pathlib import Path

args = sys.argv[1:]
source = Path(args[-1])
outdir = Path(args[args.index('--outdir') + 1])
shutil.copyfile(source, outdir / source.name)
Path(os.environ['FAKE_SOFFICE_LOG']).write_text(
    json.dumps({'source': str(source), 'outdir': str(outdir)}), encoding='utf-8'
)
"""

    def prepare_runtime(self, root: Path) -> Path:
        runtime = root / "runtime"
        package = runtime / "node_modules" / "@oai" / "artifact-tool"
        package.mkdir(parents=True)
        (package / "index.js").write_text(self.fake_artifact_tool(), encoding="utf-8")
        return runtime

    def run_generator(
        self, source: Path, output_dir: Path | None, runtime: Path, env: dict[str, str], *extra_args: str
    ) -> subprocess.CompletedProcess[str]:
        command = ["node", str(SCRIPT), "--input", str(source)]
        if output_dir is not None:
            command.extend(["--output-dir", str(output_dir)])
        command.extend(["--artifact-runtime", str(runtime), *extra_args])
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_recalculates_and_validates_temp_xlsx_before_replacing_final_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "navigation.json"
            output_dir = root / "deliverables"
            output = output_dir / "01_家庭学习导航.xlsx"
            runtime = self.prepare_runtime(root)
            source.write_text(json.dumps(self.payload(), ensure_ascii=False), encoding="utf-8")
            output_dir.mkdir()
            output.write_text("known-good xlsx", encoding="utf-8")
            lifecycle_log = root / "artifact-lifecycle.log"
            soffice_log = root / "soffice.json"
            soffice = root / "fake-soffice"
            soffice.write_text(self.fake_soffice(), encoding="utf-8")
            soffice.chmod(0o755)
            result = self.run_generator(
                source,
                output_dir,
                runtime,
                {
                    **os.environ,
                    "FAKE_ARTIFACT_LOG": str(lifecycle_log),
                    "FAKE_SOFFICE_LOG": str(soffice_log),
                    "FINAL_OUTPUT": str(output),
                },
                "--soffice",
                str(soffice),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "fake xlsx")
            self.assertTrue(json.loads(result.stdout)["verified"])
            lifecycle = lifecycle_log.read_text(encoding="utf-8").splitlines()
            temporary_output = Path(lifecycle[1].removeprefix("save:"))
            self.assertEqual(lifecycle[0], "export")
            self.assertEqual(temporary_output.parent, output.parent)
            self.assertNotEqual(temporary_output, output)
            self.assertTrue(temporary_output.name.startswith(".01_家庭学习导航.tmp-"))
            self.assertEqual(lifecycle[2], f"load:{temporary_output}")
            self.assertEqual(lifecycle[3], "import:known-good xlsx")
            self.assertEqual(lifecycle[4], "inspect")
            self.assertFalse(temporary_output.exists())
            self.assertEqual(
                json.loads(soffice_log.read_text(encoding="utf-8"))["source"],
                str(temporary_output),
            )

    def test_validation_failure_preserves_existing_output_and_cleans_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "navigation.json"
            output_dir = root / "deliverables"
            output = output_dir / "01_家庭学习导航.xlsx"
            runtime = self.prepare_runtime(root)
            source.write_text(json.dumps(self.payload(), ensure_ascii=False), encoding="utf-8")
            output_dir.mkdir()
            output.write_text("known-good xlsx", encoding="utf-8")
            lifecycle_log = root / "artifact-lifecycle.log"
            result = self.run_generator(
                source,
                output_dir,
                runtime,
                {
                    **os.environ,
                    "FAKE_ARTIFACT_LOG": str(lifecycle_log),
                    "FAKE_FORMULA_ERROR": "1",
                    "FINAL_OUTPUT": str(output),
                },
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("公式错误", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "known-good xlsx")
            self.assertFalse(list(output_dir.glob(".01_家庭学习导航.tmp-*.xlsx")))
            self.assertEqual(
                lifecycle_log.read_text(encoding="utf-8").splitlines()[2:],
                ["load:" + lifecycle_log.read_text(encoding="utf-8").splitlines()[1][5:], "import:known-good xlsx", "inspect"],
            )

    def test_help_is_available_without_artifact_runtime(self) -> None:
        result = subprocess.run(
            ["node", str(SCRIPT), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("navigation.json", result.stdout)
        self.assertIn("family-navigation-excel.md", result.stdout)
        self.assertIn("file/all/backup", result.stdout)

    def test_missing_output_dir_uses_home_downloads_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "navigation.json"
            runtime = self.prepare_runtime(root)
            source.write_text(json.dumps(self.payload(), ensure_ascii=False), encoding="utf-8")
            home = root / "home"
            output = home / "Downloads" / "soia-pkm-alipan-curator" / "01_家庭学习导航.xlsx"
            reference = root / "reference.xlsx"
            reference.write_text("known-good xlsx", encoding="utf-8")
            env = {**os.environ, "HOME": str(home), "FINAL_OUTPUT": str(reference)}
            for name in ("ALIPAN_CURATOR_OUTPUT_DIR", "SOIA_PKM_ALIPAN_CURATOR_CONFIG_FILE"):
                env.pop(name, None)
            result = self.run_generator(source, None, runtime, env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertIn(
                f"输出到默认目录 {output.parent}（可用 --output-dir 或 config ALIPAN_CURATOR_OUTPUT_DIR 覆盖）",
                result.stderr,
            )

    def test_config_output_dir_overrides_home_downloads_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "navigation.json"
            runtime = self.prepare_runtime(root)
            source.write_text(json.dumps(self.payload(), ensure_ascii=False), encoding="utf-8")
            configured = root / "configured-output"
            config = root / "config.yml"
            config.write_text(
                "env:\n  ALIPAN_CURATOR_OUTPUT_DIR: " + str(configured) + "\n",
                encoding="utf-8",
            )
            output = configured / "01_家庭学习导航.xlsx"
            reference = root / "reference.xlsx"
            reference.write_text("known-good xlsx", encoding="utf-8")
            env = {
                **os.environ,
                "HOME": str(root / "home"),
                "SOIA_PKM_ALIPAN_CURATOR_CONFIG_FILE": str(config),
                "FINAL_OUTPUT": str(reference),
            }
            env.pop("ALIPAN_CURATOR_OUTPUT_DIR", None)
            result = self.run_generator(source, None, runtime, env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertNotIn("输出到默认目录", result.stderr)

    def test_missing_required_args_points_to_help(self) -> None:
        result = subprocess.run(
            ["node", str(SCRIPT), "--input", "missing.json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--artifact-runtime", result.stderr)

    def test_invalid_drive_url_fails_before_loading_artifact_tool(self) -> None:
        payload = {
            "title": "家庭导航",
            "summary": "说明",
            "generatedAt": "2026-01-01",
            "partition": "10_示例",
            "guidance": [{"label": "先选主线", "text": "一次只选一套。"}],
            "rows": [
                {
                    "category": "10_课程",
                    "name": "示例课程",
                    "audience": "启蒙阶段",
                    "type": "视频",
                    "usage": "亲子观看",
                    "pace": "每次十分钟",
                    "path": "/10_示例/10_课程",
                    "url": "https://www.alipan.com/drive/folder/wrong",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "navigation.json"
            source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    "node",
                    str(SCRIPT),
                    "--input",
                    str(source),
                    "--output-dir",
                    str(root),
                    "--artifact-runtime",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("file/all/backup", result.stderr)
        self.assertNotIn("artifact-tool", result.stderr)


if __name__ == "__main__":
    unittest.main()
