#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { promisify } from "node:util";

import {
  COLORS,
  addTable,
  noteBand,
  prepareSheet,
  setColumnWidths,
  styleHeader,
  titleBand,
} from "./catalog_xlsx/workbook_style.mjs";


function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--input") args.input = argv[++index];
    else if (value === "--output") args.output = argv[++index];
    else if (value === "--artifact-runtime") args.artifactRuntime = argv[++index];
    else if (value === "--qa-dir") args.qaDir = argv[++index];
    else if (value === "--soffice") args.soffice = argv[++index];
    else throw new Error(`未知参数：${value}`);
  }
  if (!args.input || !args.output || !args.artifactRuntime) {
    throw new Error(
      "用法：gen_family_nav_xlsx.mjs --input <navigation.json> --output <file.xlsx> " +
      "--artifact-runtime <含 node_modules 的目录> [--qa-dir <目录>] [--soffice <可执行文件>]"
    );
  }
  return args;
}


async function loadArtifactTool(runtimeRoot) {
  const require = createRequire(import.meta.url);
  const entry = require.resolve("@oai/artifact-tool", { paths: [runtimeRoot] });
  const imported = await import(pathToFileURL(entry).href);
  const api = imported.default ? { ...imported.default, ...imported } : imported;
  if (!api.Workbook || !api.SpreadsheetFile) {
    throw new Error("@oai/artifact-tool 未暴露 Workbook / SpreadsheetFile");
  }
  return api;
}


function excelText(value) {
  return String(value ?? "").replaceAll('"', '""');
}


function categoryStats(rows) {
  const stats = new Map();
  for (const row of rows) stats.set(row.category, (stats.get(row.category) || 0) + 1);
  return [...stats.entries()].sort((a, b) => a[0].localeCompare(b[0], "zh-CN", { numeric: true }));
}


async function recalculateWithLibreOffice(output, soffice) {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "soia-family-nav-"));
  try {
    await promisify(execFile)(soffice, [
      "--headless",
      "--convert-to", "xlsx",
      "--outdir", tempDir,
      output,
    ]);
    const recalculated = path.join(tempDir, path.basename(output));
    await fs.copyFile(recalculated, output);
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}


function buildWorkbook(Workbook, input) {
  const workbook = Workbook.create();
  const usage = workbook.worksheets.add("01_先看这里");
  const navigation = workbook.worksheets.add("02_资源导航");
  prepareSheet(usage);
  prepareSheet(navigation);

  const rows = input.rows || [];
  const stats = categoryStats(rows);

  titleBand(usage, "A1:J1", input.title);
  noteBand(usage, "A2:J3", input.summary, false);
  usage.getRange("A5:J5").values = [[
    "收录资源", "", "分类数", "", "生成日期", "", "云盘分区", "", "使用原则", ""
  ]];
  usage.getRange("A5:J5").format = {
    fill: COLORS.blue,
    font: { bold: true, color: COLORS.navy },
    horizontalAlignment: "center",
  };
  usage.getRange("A6").values = [[rows.length]];
  usage.getRange("C6").values = [[stats.length]];
  usage.getRange("E6").values = [[input.generatedAt]];
  usage.getRange("G6").values = [[input.partition]];
  usage.getRange("I6").values = [["先选一项、少量开始、观察反馈"]];
  for (const range of ["A6:B6", "C6:D6", "E6:F6", "G6:H6", "I6:J6"]) usage.getRange(range).merge();
  usage.getRange("A6:J6").format = {
    fill: COLORS.white,
    font: { bold: true, color: COLORS.teal, size: 13 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.lightGray },
  };
  usage.getRange("A6:D6").format.numberFormat = "#,##0";

  usage.getRange("A8:J8").merge();
  usage.getRange("A8:J8").values = [["家庭使用建议"]];
  usage.getRange("A8:J8").format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
  const guidance = (input.guidance || []).slice(0, 6);
  const guidanceRows = guidance.map((item, index) => [
    index + 1,
    item.label,
    item.text,
    "", "", "", "", "", "", "",
  ]);
  if (guidanceRows.length) {
    usage.getRangeByIndexes(8, 0, guidanceRows.length, 10).values = guidanceRows;
    for (let row = 9; row < 9 + guidanceRows.length; row += 1) usage.getRange(`C${row}:J${row}`).merge();
    usage.getRange(`A9:J${8 + guidanceRows.length}`).format = {
      wrapText: true,
      verticalAlignment: "center",
      borders: { preset: "inside", style: "thin", color: COLORS.lightGray },
    };
    usage.getRange(`A9:A${8 + guidanceRows.length}`).format = {
      fill: COLORS.pale,
      font: { bold: true, color: COLORS.teal },
      horizontalAlignment: "center",
    };
    usage.getRange(`B9:B${8 + guidanceRows.length}`).format.font = { bold: true, color: COLORS.navy };
  }

  const statsStart = 11 + guidanceRows.length;
  usage.getRange(`A${statsStart}:D${statsStart}`).values = [["分类", "资源数", "占比", "说明"]];
  styleHeader(usage.getRange(`A${statsStart}:D${statsStart}`));
  if (stats.length) {
    usage.getRangeByIndexes(statsStart, 0, stats.length, 4).values =
      stats.map(([category, count]) => [category, count, null, "在“02_资源导航”中筛选此分类"]);
    for (let index = 0; index < stats.length; index += 1) {
      const row = statsStart + 1 + index;
      usage.getRange(`C${row}`).formulas = [[`=B${row}/$A$6`]];
    }
    addTable(usage, `A${statsStart}:D${statsStart + stats.length}`, "FamilyCategoryTable");
    usage.getRange(`B${statsStart + 1}:B${statsStart + stats.length}`).format.numberFormat = "#,##0";
    usage.getRange(`C${statsStart + 1}:C${statsStart + stats.length}`).format.numberFormat = "0.0%";
  }
  usage.freezePanes.freezeRows(3);
  setColumnWidths(usage, { A: 10, B: 24, C: 22, D: 34, E: 16, F: 16, G: 18, H: 18, I: 25, J: 20 }, statsStart + stats.length);

  titleBand(navigation, "A1:J1", `${input.partition} · 资源导航`);
  noteBand(
    navigation,
    "A2:J2",
    "按分类、适龄/阶段、资源形态筛选；资源名称和“打开云盘”均可点击。URL 列保留完整链接，复制到浏览器也能直达。"
  );
  const headers = [
    "序号", "分类", "资源名称（点击直达）", "适合谁/阶段", "资源形态",
    "怎么用", "建议节奏", "云盘路径", "完整URL", "打开云盘"
  ];
  navigation.getRange("A4:J4").values = [headers];
  styleHeader(navigation.getRange("A4:J4"));
  if (rows.length) {
    navigation.getRangeByIndexes(4, 0, rows.length, headers.length).values = rows.map((row, index) => [
      index + 1,
      row.category,
      row.name,
      row.audience,
      row.type,
      row.usage,
      row.pace,
      row.path,
      row.url,
      "🔗 打开",
    ]);
    addTable(navigation, `A4:J${rows.length + 4}`, "FamilyResourceTable");
    navigation.getRange(`A5:A${rows.length + 4}`).format.numberFormat = "#,##0";
    navigation.getRange(`C5:C${rows.length + 4}`).format.font = { color: "#0563C1" };
    navigation.getRange(`J5:J${rows.length + 4}`).format.font = { color: "#0563C1" };
    navigation.getRange(`D5:H${rows.length + 4}`).format.wrapText = true;
  }
  navigation.freezePanes.freezeRows(4);
  navigation.freezePanes.freezeColumns(2);
  setColumnWidths(
    navigation,
    { A: 8, B: 22, C: 42, D: 20, E: 16, F: 32, G: 24, H: 64, I: 48, J: 14 },
    rows.length + 4
  );
  return { workbook, navigation, usageLastRow: statsStart + stats.length, navigationLastRow: rows.length + 4 };
}


async function run() {
  const args = parseArgs(process.argv.slice(2));
  const input = JSON.parse(await fs.readFile(args.input, "utf8"));
  if (!Array.isArray(input.rows) || !input.rows.length) throw new Error("input.rows 必须是非空数组");
  const { Workbook, SpreadsheetFile } = await loadArtifactTool(args.artifactRuntime);
  const built = buildWorkbook(Workbook, input);
  const errors = await built.workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "family navigation formula error scan",
  });
  const inspectionLines = String(errors.ndjson || "").trim().split("\n").filter(Boolean);
  const formulaMatches = inspectionLines.filter((line) => {
    try {
      return JSON.parse(line).kind !== "notice";
    } catch {
      return true;
    }
  });
  if (formulaMatches.length) {
    throw new Error(`公式错误：${formulaMatches.join("\n")}`);
  }

  const previews = [];
  if (args.qaDir) {
    await fs.mkdir(args.qaDir, { recursive: true });
    const specs = [
      ["01_先看这里", `A1:J${Math.min(built.usageLastRow, 35)}`, "01_先看这里.png"],
      ["02_资源导航", `A1:J${Math.min(built.navigationLastRow, 35)}`, "02_资源导航.png"],
    ];
    for (const [sheetName, range, filename] of specs) {
      const blob = await built.workbook.render({ sheetName, range, scale: 1, format: "png" });
      const preview = path.join(args.qaDir, filename);
      await fs.writeFile(preview, new Uint8Array(await blob.arrayBuffer()));
      previews.push(preview);
    }
  }
  built.navigation.getRangeByIndexes(4, 2, input.rows.length, 1).formulas = input.rows.map((row, index) => [
    `=HYPERLINK(I${index + 5},"${excelText(row.name)}")`
  ]);
  built.navigation.getRangeByIndexes(4, 9, input.rows.length, 1).formulas = input.rows.map((_, index) => [
    `=HYPERLINK(I${index + 5},"🔗 打开")`
  ]);
  await fs.mkdir(path.dirname(args.output), { recursive: true });
  const xlsx = await SpreadsheetFile.exportXlsx(built.workbook);
  await xlsx.save(args.output);
  if (args.soffice) await recalculateWithLibreOffice(args.output, args.soffice);
  await fs.rm(`${args.output}.inspect.ndjson`, { force: true });

  console.log(JSON.stringify({
    status: "updated",
    output: path.resolve(args.output),
    rows: input.rows.length,
    recalculated: Boolean(args.soffice),
    previews,
  }));
}


run().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
