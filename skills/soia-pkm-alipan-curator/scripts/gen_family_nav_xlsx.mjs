#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
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
    if (value === "--help" || value === "-h") args.help = true;
    if (value === "--input") args.input = argv[++index];
    else if (value === "--output") args.output = argv[++index];
    else if (value === "--artifact-runtime") args.artifactRuntime = argv[++index];
    else if (value === "--qa-dir") args.qaDir = argv[++index];
    else if (value === "--soffice") args.soffice = argv[++index];
    else if (value !== "--help" && value !== "-h") throw new Error(`未知参数：${value}`);
  }
  if (args.help) return args;
  if (!args.input || !args.output || !args.artifactRuntime) {
    throw new Error("缺少必填参数。运行 --help 查看用法。");
  }
  return args;
}


function usageText() {
  return `用法：
  gen_family_nav_xlsx.mjs \\
    --input <navigation.json> \\
    --output <file.xlsx> \\
    --artifact-runtime <含 node_modules/@oai/artifact-tool 的目录> \\
    [--qa-dir <预览图片目录>] \\
    [--soffice <LibreOffice/soffice 可执行文件>]

输入 JSON 必填字段：
  title, summary, generatedAt, partition
  guidance[]: {label, text}
  rows[]: {category, name, audience, type, usage, pace, path, url}

输出工作表：
  01_先看这里、02_资源导航

说明：
  资源名称和“打开云盘”都会链接到 row.url。
  row.url 必须是 https://www.alipan.com/drive/file/all/backup/<40位file_id>。
  建议提供 --qa-dir 和 --soffice 完成交付验收。
  完整规范见 references/family-navigation-excel.md。`;
}


function validateInput(input) {
  const requiredText = ["title", "summary", "generatedAt", "partition"];
  for (const field of requiredText) {
    if (typeof input[field] !== "string" || !input[field].trim()) {
      throw new Error(`input.${field} 必须是非空字符串`);
    }
  }
  if (!Array.isArray(input.guidance)) throw new Error("input.guidance 必须是数组");
  input.guidance.forEach((item, index) => {
    for (const field of ["label", "text"]) {
      if (typeof item?.[field] !== "string" || !item[field].trim()) {
        throw new Error(`input.guidance[${index}].${field} 必须是非空字符串`);
      }
    }
  });
  if (!Array.isArray(input.rows) || !input.rows.length) {
    throw new Error("input.rows 必须是非空数组");
  }
  const rowFields = ["category", "name", "audience", "type", "usage", "pace", "path", "url"];
  const driveUrl = /^https:\/\/(?:www\.)?(?:alipan|aliyundrive)\.com\/drive\/file\/all\/backup\/[0-9a-f]{40}(?:[/?#].*)?$/i;
  input.rows.forEach((row, index) => {
    for (const field of rowFields) {
      if (typeof row?.[field] !== "string" || !row[field].trim()) {
        throw new Error(`input.rows[${index}].${field} 必须是非空字符串`);
      }
    }
    if (!driveUrl.test(row.url)) {
      throw new Error(
        `input.rows[${index}].url 必须是 file/all/backup/<40位file_id> 云盘直达链接`
      );
    }
  });
}


async function loadArtifactTool(runtimeRoot) {
  const require = createRequire(import.meta.url);
  const entry = require.resolve("@oai/artifact-tool", { paths: [runtimeRoot] });
  const imported = await import(pathToFileURL(entry).href);
  const api = imported.default ? { ...imported.default, ...imported } : imported;
  if (!api.Workbook || !api.SpreadsheetFile || !api.FileBlob) {
    throw new Error("@oai/artifact-tool 未暴露 Workbook / SpreadsheetFile / FileBlob");
  }
  return api;
}


function matchingFormulaErrors(inspection) {
  return String(inspection.ndjson || "").trim().split("\n").filter(Boolean).filter((line) => {
    try {
      return JSON.parse(line).kind !== "notice";
    } catch {
      return true;
    }
  });
}


async function verifyNoFormulaErrors(workbook) {
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!|#FIELD!|#BLOCKED!|#CONNECT!|#UNKNOWN!|#BUSY!|#GETTING_DATA",
    options: { useRegex: true, maxResults: 100 },
    summary: "final family navigation formula error scan",
  });
  const formulaMatches = matchingFormulaErrors(errors);
  if (formulaMatches.length) {
    throw new Error(`公式错误：${formulaMatches.join("\n")}`);
  }
}


function assertFinalWorkbook(finalWorkbook, input) {
  const expectedSheetNames = ["01_先看这里", "02_资源导航"];
  const actualSheetNames = finalWorkbook.worksheets.items.map((sheet) => sheet.name);
  if (
    actualSheetNames.length !== expectedSheetNames.length ||
    actualSheetNames.some((name, index) => name !== expectedSheetNames[index])
  ) {
    throw new Error(`最终 XLSX 工作表不符合预期：${actualSheetNames.join(" / ")}`);
  }

  const navigation = finalWorkbook.worksheets.getItem("02_资源导航");
  const usedValues = navigation.getUsedRange().values;
  const actualDataRows = usedValues.length - 4;
  if (actualDataRows !== input.rows.length) {
    throw new Error(`最终 XLSX 数据行数不匹配：期望 ${input.rows.length}，实际 ${actualDataRows}`);
  }

  const dataRows = navigation.getRangeByIndexes(4, 0, input.rows.length, 10).values;
  const nameFormulas = navigation.getRangeByIndexes(4, 2, input.rows.length, 1).formulas;
  const openFormulas = navigation.getRangeByIndexes(4, 9, input.rows.length, 1).formulas;
  input.rows.forEach((row, index) => {
    const excelRow = index + 5;
    if (dataRows[index]?.[0] !== index + 1) {
      throw new Error(`最终 XLSX 第 ${excelRow} 行序号不匹配`);
    }
    if (dataRows[index]?.[8] !== row.url) {
      throw new Error(`最终 XLSX 第 ${excelRow} 行 URL 与输入不一致`);
    }
    const expectedNameFormula = `=HYPERLINK(I${excelRow},"${excelText(row.name)}")`;
    const expectedOpenFormula = `=HYPERLINK(I${excelRow},"🔗 打开")`;
    if (nameFormulas[index]?.[0] !== expectedNameFormula) {
      throw new Error(`最终 XLSX 第 ${excelRow} 行资源名称 HYPERLINK 公式不符合输入 URL`);
    }
    if (openFormulas[index]?.[0] !== expectedOpenFormula) {
      throw new Error(`最终 XLSX 第 ${excelRow} 行打开云盘 HYPERLINK 公式不符合输入 URL`);
    }
  });
  return navigation;
}


async function verifyFinalXlsx(SpreadsheetFile, FileBlob, output, input) {
  const finalFile = await FileBlob.load(output);
  const finalWorkbook = await SpreadsheetFile.importXlsx(finalFile);
  assertFinalWorkbook(finalWorkbook, input);
  await verifyNoFormulaErrors(finalWorkbook);
  return finalWorkbook;
}


async function renderPreviews(workbook, qaDir, usageLastRow, navigationLastRow) {
  if (!qaDir) return [];
  await fs.mkdir(qaDir, { recursive: true });
  const specs = [
    ["01_先看这里", `A1:J${Math.min(usageLastRow, 35)}`, "01_先看这里.png"],
    ["02_资源导航", `A1:J${Math.min(navigationLastRow, 35)}`, "02_资源导航.png"],
  ];
  const previews = [];
  for (const [sheetName, range, filename] of specs) {
    const blob = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    const preview = path.join(qaDir, filename);
    await fs.writeFile(preview, new Uint8Array(await blob.arrayBuffer()));
    previews.push(preview);
  }
  return previews;
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


function temporaryOutputPath(output) {
  const parsed = path.parse(output);
  return path.join(
    parsed.dir,
    `.${parsed.name}.tmp-${process.pid}-${randomUUID()}${parsed.ext}`
  );
}


async function run() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usageText());
    return;
  }
  const input = JSON.parse(await fs.readFile(args.input, "utf8"));
  validateInput(input);
  const { Workbook, SpreadsheetFile, FileBlob } = await loadArtifactTool(args.artifactRuntime);
  const built = buildWorkbook(Workbook, input);
  built.navigation.getRangeByIndexes(4, 2, input.rows.length, 1).formulas = input.rows.map((row, index) => [
    `=HYPERLINK(I${index + 5},"${excelText(row.name)}")`
  ]);
  built.navigation.getRangeByIndexes(4, 9, input.rows.length, 1).formulas = input.rows.map((_, index) => [
    `=HYPERLINK(I${index + 5},"🔗 打开")`
  ]);
  const output = path.resolve(args.output);
  await fs.mkdir(path.dirname(output), { recursive: true });
  let temporaryOutput = temporaryOutputPath(output);
  let previews;
  try {
    const xlsx = await SpreadsheetFile.exportXlsx(built.workbook);
    await xlsx.save(temporaryOutput);
    if (args.soffice) await recalculateWithLibreOffice(temporaryOutput, args.soffice);
    const finalWorkbook = await verifyFinalXlsx(SpreadsheetFile, FileBlob, temporaryOutput, input);
    previews = await renderPreviews(
      finalWorkbook,
      args.qaDir,
      built.usageLastRow,
      built.navigationLastRow
    );
    await fs.rm(`${temporaryOutput}.inspect.ndjson`, { force: true });
    await fs.rename(temporaryOutput, output);
    temporaryOutput = undefined;
  } finally {
    if (temporaryOutput) {
      await fs.rm(temporaryOutput, { force: true });
      await fs.rm(`${temporaryOutput}.inspect.ndjson`, { force: true });
    }
  }

  console.log(JSON.stringify({
    status: "updated",
    output,
    rows: input.rows.length,
    recalculated: Boolean(args.soffice),
    verified: true,
    previews,
  }));
}


run().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
