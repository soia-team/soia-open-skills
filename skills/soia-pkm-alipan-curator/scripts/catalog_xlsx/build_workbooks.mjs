import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

import {
  COLORS,
  addTable,
  friendlyLocalPath,
  noteBand,
  prepareSheet,
  setColumnWidths,
  styleHeader,
  titleBand,
} from "./workbook_style.mjs";


const MB = 1024 ** 2;
const GB = 1024 ** 3;

const TYPE_NOTES = {
  视频: "常见视频容器",
  音频: "音乐、课程音频与有声书",
  电子书: "PDF/EPUB/MOBI 等",
  Office文档: "Word/Excel/PPT/CSV",
  文本与网页: "TXT/MD/HTML/JSON 等",
  图片: "常见位图与矢量图",
  压缩包: "ZIP/RAR/7Z/ISO 等",
  字幕: "SRT/ASS/VTT 等",
  软件与安装包: "EXE/DMG/APK/DLL 等",
  代码与数据: "源码、脚本、数据库与数据文件",
  其他: "未命中已知扩展名规则",
};


function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--plan") result.plan = argv[++index];
    else if (value === "--artifact-runtime") result.artifactRuntime = argv[++index];
    else throw new Error(`未知参数：${value}`);
  }
  if (!result.plan || !result.artifactRuntime) {
    throw new Error("用法：build_workbooks.mjs --plan <build-plan.json> --artifact-runtime <含 node_modules 的目录>");
  }
  return result;
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


function writeRowsInChunks(sheet, startRow, startColumn, rows, columnCount, chunkSize = 4000) {
  for (let offset = 0; offset < rows.length; offset += chunkSize) {
    const chunk = rows.slice(offset, offset + chunkSize);
    sheet.getRangeByIndexes(startRow + offset, startColumn, chunk.length, columnCount).values = chunk;
  }
}


function typeStatsFromFiles(files) {
  const stats = new Map();
  for (const row of files) {
    const current = stats.get(row.type) || { type: row.type, count: 0, bytes: 0 };
    current.count += 1;
    current.bytes += row.sizeBytes;
    stats.set(row.type, current);
  }
  return [...stats.values()].sort((a, b) => a.type.localeCompare(b.type, "zh-CN"));
}


function extensionStatsFromFiles(files) {
  const stats = new Map();
  for (const row of files) {
    const current = stats.get(row.ext) || { ext: row.ext, type: row.type, count: 0, bytes: 0 };
    current.count += 1;
    current.bytes += row.sizeBytes;
    stats.set(row.ext, current);
  }
  return [...stats.values()].sort((a, b) => b.count - a.count || a.ext.localeCompare(b.ext));
}


function excelText(value) {
  return String(value ?? "").replaceAll('"', '""');
}


function excelColumn(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(65 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
}


async function inspectAndRender(workbook, outputPath, verify, cacheDir, previewSpecs) {
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  const previews = [];
  if (verify) {
    const workbookName = path.basename(outputPath, ".xlsx");
    const previewDir = path.join(cacheDir, "qa", workbookName);
    await fs.mkdir(previewDir, { recursive: true });
    for (const [sheetName, range, filename] of previewSpecs) {
      const blob = await workbook.render({ sheetName, range, scale: 1, format: "png" });
      const previewPath = path.join(previewDir, filename);
      await fs.writeFile(previewPath, new Uint8Array(await blob.arrayBuffer()));
      previews.push(previewPath);
    }
  }
  return { formulaErrorScan: errors.ndjson, previews };
}


async function exportWorkbook(SpreadsheetFile, workbook, outputPath) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(outputPath);
}


function releaseMetadataRows(releaseMetadata) {
  return [
    ["catalog_release_id", releaseMetadata.catalog_release_id],
    ["index_updated_at", releaseMetadata.index_updated_at],
    ["snapshot_at", releaseMetadata.snapshot_at],
    ["catalog_schema_version", releaseMetadata.catalog_schema_version],
    ["source_fingerprint", releaseMetadata.source_fingerprint],
  ];
}


function buildMasterWorkbook(Workbook, aggregate, plan, generatedAt) {
  const workbook = Workbook.create();
  const usage = workbook.worksheets.add("00_使用说明");
  const directoriesSheet = workbook.worksheets.add("01_目录索引");
  const entrySheet = workbook.worksheets.add("02_明细入口");
  const typeSheet = workbook.worksheets.add("03_类型统计");
  const partitionSheet = workbook.worksheets.add("04_分区统计");
  const extensionSheet = workbook.worksheets.add("05_扩展名统计");
  for (const sheet of [usage, directoriesSheet, entrySheet, typeSheet, partitionSheet, extensionSheet]) prepareSheet(sheet);

  const { catalog, directories, typeStats, extensionStats, partitionStats, indexedFiles, indexedBytes } = aggregate;
  const partitionEnd = partitionStats.length + 4;

  titleBand(usage, "A1:J1", "阿里云盘馆藏总索引");
  noteBand(usage, "A2:J2", "轻量总入口：目录与统计保留在本工作簿，单文件明细按分区拆到相邻工作簿。以后只重建发生变化的分区，不再全量生成 6.8 万行。" );
  usage.getRange("A3:J3").values = [["全盘文件", "", "已展开明细", "", "明细覆盖率", "", "目录索引行", "", "明细估算体量(GB)", ""]];
  usage.getRange("A3:J3").format = { fill: COLORS.blue, font: { bold: true, color: COLORS.navy }, horizontalAlignment: "center" };
  usage.getRange("A4").values = [[catalog.totalFiles]];
  usage.getRange("C4").formulas = [[`=SUM('02_明细入口'!$D$5:$D$${partitionEnd})`]];
  usage.getRange("E4").formulas = [["=C4/A4"]];
  usage.getRange("G4").formulas = [[`=COUNTA('01_目录索引'!$A$5:$A$${directories.length + 4})`]];
  usage.getRange("I4").formulas = [[`=SUM('02_明细入口'!$F$5:$F$${partitionEnd})/$B$23`]];
  for (const range of ["A4:B4", "C4:D4", "E4:F4", "G4:H4", "I4:J4"]) usage.getRange(range).merge();
  usage.getRange("A4:J4").format = { fill: COLORS.white, font: { bold: true, color: COLORS.teal, size: 15 }, horizontalAlignment: "center", borders: { preset: "outside", style: "thin", color: COLORS.lightGray } };
  usage.getRange("A4:D4").format.numberFormat = "#,##0";
  usage.getRange("E4:F4").format.numberFormat = "0.0%";
  usage.getRange("G4:H4").format.numberFormat = "#,##0";
  usage.getRange("I4:J4").format.numberFormat = "#,##0.0";

  usage.getRange("A7:J7").merge();
  usage.getRange("A7:J7").values = [["怎么用"]];
  usage.getRange("A7:J7").format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
  usage.getRange("A8:J12").values = [
    ["1", "找目录", "打开 01_目录索引，按完整路径或主要类型筛选；点击链接直接进入阿里云盘。", "", "", "", "", "", "", ""],
    ["2", "找文件", "打开 02_明细入口，选择分区并点击“打开明细”；在分区工作簿按文件类型、扩展名或大小筛选。", "", "", "", "", "", "", ""],
    ["3", "看全盘分布", `03_类型统计、04_分区统计、05_扩展名统计由 ${partitionStats.length} 份分区缓存聚合，可快速判断资源所在区域。`, "", "", "", "", "", "", ""],
    ["4", "增量更新", "生成器比较 Markdown SHA-256；只重建变化分区及本总入口，未变化分区工作簿直接复用。", "", "", "", "", "", "", ""],
    ["5", "强制全量", "仅在生成规则或样式整体变化时使用 --force；普通索引刷新不要全量重建。", "", "", "", "", "", "", ""],
  ];
  for (let row = 8; row <= 12; row += 1) usage.getRange(`C${row}:J${row}`).merge();
  usage.getRange("A8:J12").format = { wrapText: true, verticalAlignment: "center", borders: { preset: "inside", style: "thin", color: COLORS.lightGray } };
  usage.getRange("A8:A12").format = { fill: COLORS.pale, font: { bold: true, color: COLORS.teal }, horizontalAlignment: "center" };
  usage.getRange("B8:B12").format.font = { bold: true, color: COLORS.navy };

  usage.getRange("A15:J15").merge();
  usage.getRange("A15:J15").values = [["口径与限制"]];
  usage.getRange("A15:J15").format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
  noteBand(usage, "A16:J17", `馆藏总览口径：${catalog.totalDirs.toLocaleString()} 个目录 / ${catalog.totalFiles.toLocaleString()} 个文件 / ${catalog.totalSize}。全文检索 Markdown 展开 ${indexedFiles.toLocaleString()} 个文件，覆盖率 ${(indexedFiles / catalog.totalFiles * 100).toFixed(1)}%。未展开差额主要来自采用聚合索引的分区。`, true);
  usage.getRange("A19:B23").values = [["字段", "值"], ["生成时间", generatedAt], ["云盘入口", "见目录索引与分区统计中的链接"], ["Bytes/MB", MB], ["Bytes/GB", GB]];
  styleHeader(usage.getRange("A19:B19"));
  usage.getRange("B22:B23").format.numberFormat = "#,##0";
  const sourceStart = plan.releaseMetadata ? 32 : 25;
  if (plan.releaseMetadata) {
    usage.getRange("A25:J25").merge();
    usage.getRange("A25:J25").values = [["发布元数据（调用方提供）"]];
    usage.getRange("A25:J25").format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
    usage.getRange("A26:B30").values = releaseMetadataRows(plan.releaseMetadata);
    styleHeader(usage.getRange("A26:A30"));
    usage.getRange("B26:B30").format = { wrapText: true };
  }
  usage.getRange(`A${sourceStart}:J${sourceStart}`).merge();
  usage.getRange(`A${sourceStart}:J${sourceStart}`).values = [["数据源"]];
  usage.getRange(`A${sourceStart}:J${sourceStart}`).format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
  const sourceRows = [[catalog.sourceName, "馆藏总览"], ...plan.partitions.map((item) => [path.basename(item.source), "分区全文检索"] )];
  usage.getRange(`A${sourceStart + 1}:B${sourceStart + sourceRows.length}`).values = sourceRows;
  usage.freezePanes.freezeRows(2);
  setColumnWidths(usage, { A: 24, B: 42, C: 22, D: 15, E: 15, F: 15, G: 15, H: 15, I: 15, J: 15 }, sourceStart + sourceRows.length + 1);

  titleBand(directoriesSheet, "A1:P1", "目录索引");
  noteBand(directoriesSheet, "A2:P2", `共 ${directories.length.toLocaleString()} 行：由 ${partitionStats.length} 份分区缓存反推目录树；可按分区、层级、主要类型、完整路径组合筛选。`);
  const directoryHeaders = ["序号", "分区", "层级", "课程/目录名（点击直达）", "完整路径", "父目录", "主要类型", "直接文件数", "子树文件数", "直接大小(Bytes)", "子树大小(Bytes)", "子树大小(GB)", "直接子目录数", "文件夹URL", "快捷打开", "来源"];
  directoriesSheet.getRange("A4:P4").values = [directoryHeaders];
  const directoryValues = directories.map((row, index) => [index + 1, row.partition, row.depth, null, row.path, row.parent, row.dominantType, row.directFiles, row.subtreeFiles, row.directBytes, row.subtreeBytes, null, row.childDirCount, row.url, null, row.source]);
  writeRowsInChunks(directoriesSheet, 4, 0, directoryValues, directoryHeaders.length);
  if (directories.length) {
    directoriesSheet.getRangeByIndexes(4, 3, directories.length, 1).formulas = directories.map((row, index) => {
      const label = excelText(row.name);
      return [row.url ? `=HYPERLINK(N${index + 5},"${label}")` : `="${label}"`];
    });
    directoriesSheet.getRange("L5").formulas = [["=K5/'00_使用说明'!$B$23"]];
    directoriesSheet.getRange(`L5:L${directories.length + 4}`).fillDown();
    directoriesSheet.getRange("O5").formulas = [['=IF(N5="","",HYPERLINK(N5,"🔗 打开云盘"))']];
    directoriesSheet.getRange(`O5:O${directories.length + 4}`).fillDown();
    addTable(directoriesSheet, `A4:P${directories.length + 4}`, "DirectoryIndexTable");
    directoriesSheet.getRange(`A5:C${directories.length + 4}`).format.numberFormat = "#,##0";
    directoriesSheet.getRange(`H5:K${directories.length + 4}`).format.numberFormat = "#,##0";
    directoriesSheet.getRange(`L5:L${directories.length + 4}`).format.numberFormat = "#,##0.000";
    directoriesSheet.getRange(`M5:M${directories.length + 4}`).format.numberFormat = "#,##0";
    directoriesSheet.getRange(`D5:D${directories.length + 4}`).format.font = { color: "#0563C1" };
    directoriesSheet.getRange(`O5:O${directories.length + 4}`).format.font = { color: "#0563C1" };
  }
  styleHeader(directoriesSheet.getRange("A4:P4"));
  directoriesSheet.freezePanes.freezeRows(4);
  directoriesSheet.freezePanes.freezeColumns(2);
  setColumnWidths(directoriesSheet, { A: 9, B: 20, C: 8, D: 38, E: 58, F: 45, G: 16, H: 13, I: 13, J: 18, K: 18, L: 15, M: 14, N: 46, O: 18, P: 20 }, directories.length + 4);

  titleBand(entrySheet, "A1:M1", "分区文件明细入口");
  noteBand(entrySheet, "A2:M2", `文件明细拆成 ${partitionStats.length} 个独立工作簿。点击“打开明细”进入对应文件；点击“打开云盘”直接进入该分区。相对路径便于整套复制或上传。` );
  const entryHeaders = ["分区", "全盘口径目录数", "全盘口径文件数", "已展开明细", "明细覆盖率", "明细估算大小(Bytes)", "明细估算大小(GB)", "全盘口径体量", "分区URL", "打开云盘", "明细工作簿相对路径", "打开明细", "来源Markdown"];
  entrySheet.getRange("A4:M4").values = [entryHeaders];
  const detailByPartition = new Map(plan.partitions.map((item) => [item.partition, item.output]));
  const entryValues = partitionStats.map((row) => {
    const detailOutput = detailByPartition.get(row.partition);
    const relative = friendlyLocalPath(plan.outputPath, detailOutput);
    return [row.partition, row.dirs, row.files, row.indexedFiles, null, row.indexedBytes, null, row.volume, row.url, null, relative, null, `${row.partition}.md`];
  });
  entrySheet.getRangeByIndexes(4, 0, entryValues.length, entryHeaders.length).values = entryValues;
  for (let index = 0; index < entryValues.length; index += 1) {
    const row = index + 5;
    entrySheet.getRange(`E${row}`).formulas = [[`=IFERROR(D${row}/C${row},0)`]];
    entrySheet.getRange(`G${row}`).formulas = [[`=F${row}/'00_使用说明'!$B$23`]];
    entrySheet.getRange(`J${row}`).formulas = [[`=HYPERLINK(I${row},"🔗 打开云盘")`]];
    entrySheet.getRange(`L${row}`).formulas = [[`=HYPERLINK(K${row},"📄 打开明细")`]];
  }
  styleHeader(entrySheet.getRange("A4:M4"));
  addTable(entrySheet, `A4:M${partitionEnd}`, "DetailEntryTable");
  entrySheet.freezePanes.freezeRows(4);
  entrySheet.getRange(`B5:D${partitionEnd}`).format.numberFormat = "#,##0";
  entrySheet.getRange(`E5:E${partitionEnd}`).format.numberFormat = "0.0%";
  entrySheet.getRange(`F5:F${partitionEnd}`).format.numberFormat = "#,##0";
  entrySheet.getRange(`G5:G${partitionEnd}`).format.numberFormat = "#,##0.00";
  entrySheet.getRange(`J5:J${partitionEnd}`).format.font = { color: "#0563C1" };
  entrySheet.getRange(`L5:L${partitionEnd}`).format.font = { color: "#0563C1" };
  setColumnWidths(entrySheet, { A: 22, B: 18, C: 18, D: 16, E: 14, F: 22, G: 18, H: 16, I: 48, J: 16, K: 48, L: 16, M: 22 }, partitionEnd);

  titleBand(typeSheet, "A1:G1", "按文件类型统计");
  noteBand(typeSheet, "A2:G2", `由 ${partitionStats.length} 份分区缓存聚合；文件数和体量是生成器实算值，占比、GB 与平均大小使用工作表公式。` );
  const typeHeaders = ["文件类型", "文件数", "明细占比", "估算大小(Bytes)", "估算大小(GB)", "平均大小(MB)", "说明"];
  typeSheet.getRange("A4:G4").values = [typeHeaders];
  typeSheet.getRangeByIndexes(4, 0, typeStats.length, 7).values = typeStats.map((row) => [row.type, row.count, null, row.bytes, null, null, TYPE_NOTES[row.type] || ""]);
  for (let index = 0; index < typeStats.length; index += 1) {
    const row = index + 5;
    typeSheet.getRange(`C${row}`).formulas = [[`=B${row}/'00_使用说明'!$C$4`]];
    typeSheet.getRange(`E${row}`).formulas = [[`=D${row}/'00_使用说明'!$B$23`]];
    typeSheet.getRange(`F${row}`).formulas = [[`=IFERROR(D${row}/B${row}/'00_使用说明'!$B$22,0)`]];
  }
  styleHeader(typeSheet.getRange("A4:G4"));
  addTable(typeSheet, `A4:G${typeStats.length + 4}`, "TypeSummaryTable");
  typeSheet.freezePanes.freezeRows(4);
  typeSheet.getRange(`B5:B${typeStats.length + 4}`).format.numberFormat = "#,##0";
  typeSheet.getRange(`C5:C${typeStats.length + 4}`).format.numberFormat = "0.0%";
  typeSheet.getRange(`D5:D${typeStats.length + 4}`).format.numberFormat = "#,##0";
  typeSheet.getRange(`E5:F${typeStats.length + 4}`).format.numberFormat = "#,##0.00";
  setColumnWidths(typeSheet, { A: 20, B: 14, C: 14, D: 20, E: 16, F: 16, G: 38 }, typeStats.length + 4);

  titleBand(partitionSheet, "A1:J1", "按分区统计与明细覆盖率");
  noteBand(partitionSheet, "A2:J2", "全盘口径来自馆藏总览输入；明细口径来自各分区缓存。覆盖率低表示该分区在 Markdown 中采用聚合索引，不代表文件丢失。", true);
  const partitionHeaders = ["分区", "全盘口径目录数", "全盘口径文件数", "Markdown明细文件数", "明细覆盖率", "明细估算大小(Bytes)", "明细估算大小(GB)", "全盘口径体量", "分区URL", "点击直达云盘"];
  partitionSheet.getRange("A4:J4").values = [partitionHeaders];
  partitionSheet.getRangeByIndexes(4, 0, partitionStats.length, 10).values = partitionStats.map((row) => [row.partition, row.dirs, row.files, row.indexedFiles, null, row.indexedBytes, null, row.volume, row.url, null]);
  for (let index = 0; index < partitionStats.length; index += 1) {
    const row = index + 5;
    partitionSheet.getRange(`E${row}`).formulas = [[`=IFERROR(D${row}/C${row},0)`]];
    partitionSheet.getRange(`G${row}`).formulas = [[`=F${row}/'00_使用说明'!$B$23`]];
    partitionSheet.getRange(`J${row}`).formulas = [[`=HYPERLINK(I${row},"🔗 打开分区")`]];
  }
  styleHeader(partitionSheet.getRange("A4:J4"));
  addTable(partitionSheet, `A4:J${partitionEnd}`, "PartitionSummaryTable");
  partitionSheet.freezePanes.freezeRows(4);
  partitionSheet.getRange(`B5:D${partitionEnd}`).format.numberFormat = "#,##0";
  partitionSheet.getRange(`E5:E${partitionEnd}`).format.numberFormat = "0.0%";
  partitionSheet.getRange(`F5:F${partitionEnd}`).format.numberFormat = "#,##0";
  partitionSheet.getRange(`G5:G${partitionEnd}`).format.numberFormat = "#,##0.00";
  partitionSheet.getRange(`J5:J${partitionEnd}`).format.font = { color: "#0563C1" };
  setColumnWidths(partitionSheet, { A: 22, B: 18, C: 18, D: 20, E: 16, F: 22, G: 18, H: 16, I: 48, J: 18 }, partitionEnd);

  titleBand(extensionSheet, "A1:G1", "按扩展名统计");
  noteBand(extensionSheet, "A2:G2", `共识别 ${extensionStats.length} 种扩展名；按出现次数排序。文件数和体量来自分区缓存，占比与 GB 使用工作表公式。`);
  const extensionHeaders = ["扩展名", "文件类型", "文件数", "明细占比", "估算大小(Bytes)", "估算大小(GB)", "筛选提示"];
  extensionSheet.getRange("A4:G4").values = [extensionHeaders];
  extensionSheet.getRangeByIndexes(4, 0, extensionStats.length, 7).values = extensionStats.map((row) => [row.ext, row.type, row.count, null, row.bytes, null, row.ext === "(无扩展名)" ? "文件名没有后缀" : `在分区明细筛选：${row.ext}`]);
  for (let index = 0; index < extensionStats.length; index += 1) {
    const row = index + 5;
    extensionSheet.getRange(`D${row}`).formulas = [[`=C${row}/'00_使用说明'!$C$4`]];
    extensionSheet.getRange(`F${row}`).formulas = [[`=E${row}/'00_使用说明'!$B$23`]];
  }
  styleHeader(extensionSheet.getRange("A4:G4"));
  addTable(extensionSheet, `A4:G${extensionStats.length + 4}`, "ExtensionSummaryTable");
  extensionSheet.freezePanes.freezeRows(4);
  extensionSheet.getRange(`C5:C${extensionStats.length + 4}`).format.numberFormat = "#,##0";
  extensionSheet.getRange(`D5:D${extensionStats.length + 4}`).format.numberFormat = "0.0%";
  extensionSheet.getRange(`E5:E${extensionStats.length + 4}`).format.numberFormat = "#,##0";
  extensionSheet.getRange(`F5:F${extensionStats.length + 4}`).format.numberFormat = "#,##0.00";
  setColumnWidths(extensionSheet, { A: 18, B: 20, C: 14, D: 14, E: 22, F: 18, G: 34 }, extensionStats.length + 4);

  return {
    workbook,
    previews: [
      ["00_使用说明", "A1:J40", "00_usage.png"],
      ["01_目录索引", "A1:P18", "01_directories.png"],
      ["02_明细入口", "A1:M10", "02_entries.png"],
      ["03_类型统计", `A1:G${typeStats.length + 4}`, "03_types.png"],
      ["04_分区统计", "A1:J10", "04_partitions.png"],
      ["05_扩展名统计", "A1:G22", "05_extensions.png"],
    ],
    metrics: { indexedFiles, indexedBytes, directories: directories.length, types: typeStats.length, extensions: extensionStats.length },
  };
}


function buildPartitionWorkbook(Workbook, partitionCache, generatedAt) {
  const workbook = Workbook.create();
  const usage = workbook.worksheets.add("00_使用说明");
  const filesSheet = workbook.worksheets.add("01_文件明细");
  const typeSheet = workbook.worksheets.add("02_类型统计");
  const extensionSheet = workbook.worksheets.add("03_扩展名统计");
  for (const sheet of [usage, filesSheet, typeSheet, extensionSheet]) prepareSheet(sheet);

  const { partition, files, sourceName } = partitionCache;
  const typeStats = typeStatsFromFiles(files);
  const extensionStats = extensionStatsFromFiles(files);
  const fileEnd = files.length + 4;
  const categoryDepth = Math.max(0, ...files.map((row) => (row.categories || []).length));
  const categoryHeaders = Array.from({ length: categoryDepth }, (_, index) => `分类层级${index + 1}`);
  const typeIndex = 2 + categoryDepth;
  const extensionIndex = typeIndex + 1;
  const sizeBytesIndex = typeIndex + 4;
  const sizeMbIndex = typeIndex + 5;
  const folderUrlIndex = typeIndex + 8;
  const linkIndex = typeIndex + 9;

  titleBand(usage, "A1:H1", `${partition} · 文件明细索引`);
  noteBand(usage, "A2:H2", `本工作簿只对应一个分区；可按文件类型、扩展名、${categoryDepth || 0} 层分类和大小组合筛选。分类列根据真实目录深度动态生成；源 Markdown 未变化时，增量生成器不会重建本文件。` );
  usage.getRange("A4:H4").values = [["分区", "文件数", "估算体量(GB)", "文件类型数", "扩展名数", "生成时间", "来源Markdown", "缓存策略"]];
  styleHeader(usage.getRange("A4:H4"));
  usage.getRange("A5:H5").values = [[partition, files.length, null, typeStats.length, extensionStats.length, generatedAt, sourceName, "SHA-256 未变则复用"]];
  usage.getRange("C5").formulas = [[`=SUM('01_文件明细'!$${excelColumn(sizeBytesIndex)}$5:$${excelColumn(sizeBytesIndex)}$${fileEnd})/$B$9`]];
  usage.getRange("B5").format.numberFormat = "#,##0";
  usage.getRange("C5").format.numberFormat = "#,##0.00";
  usage.getRange("D5:E5").format.numberFormat = "#,##0";
  usage.getRange("A8:B9").values = [["Bytes/MB", MB], ["Bytes/GB", GB]];
  usage.getRange("A12:H12").merge();
  usage.getRange("A12:H12").values = [["使用建议：先在 02_类型统计或 03_扩展名统计判断资源分布，再回到 01_文件明细筛选；“点击直达云盘”进入文件所在文件夹。"]];
  usage.getRange("A12:H12").format = { fill: COLORS.pale, font: { color: COLORS.navy }, wrapText: true };
  usage.getRange("A15:B16").values = [["源文件", sourceName], ["云盘入口", "见文件明细中的文件夹URL"]];
  if (partitionCache.releaseMetadata) {
    usage.getRange("A18:H18").merge();
    usage.getRange("A18:H18").values = [["发布元数据（调用方提供）"]];
    usage.getRange("A18:H18").format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
    usage.getRange("A19:B23").values = releaseMetadataRows(partitionCache.releaseMetadata);
    styleHeader(usage.getRange("A19:A23"));
    usage.getRange("B19:B23").format = { wrapText: true };
  }
  usage.freezePanes.freezeRows(2);
  setColumnWidths(usage, { A: 24, B: 42, C: 18, D: 16, E: 16, F: 20, G: 24, H: 22 }, partitionCache.releaseMetadata ? 23 : 16);

  const fileHeaders = ["序号", "分区", ...categoryHeaders, "文件类型", "扩展名", "文件名", "大小原文", "估算大小(Bytes)", "估算大小(MB)", "文件夹路径", "完整文件路径", "文件夹URL", "点击直达云盘", "来源Markdown"];
  const lastFileColumn = excelColumn(fileHeaders.length - 1);
  titleBand(filesSheet, `A1:${lastFileColumn}1`, `${partition} · 文件明细（可筛选）`);
  noteBand(filesSheet, `A2:${lastFileColumn}2`, `共 ${files.length.toLocaleString()} 个 Markdown 已展开文件。分类层级按实际目录深度动态展开；估算大小由 Markdown 显示值换算；点击链接进入文件所在云盘文件夹。`);
  filesSheet.getRange(`A4:${lastFileColumn}4`).values = [fileHeaders];
  const fileValues = files.map((row, index) => {
    const categories = [...(row.categories || [])];
    while (categories.length < categoryDepth) categories.push("");
    return [index + 1, row.partition, ...categories, row.type, row.ext, row.name, row.sizeText, row.sizeBytes, null, row.folder, row.fullPath, row.folderUrl, null, row.source];
  });
  writeRowsInChunks(filesSheet, 4, 0, fileValues, fileHeaders.length);
  if (files.length) {
    const sizeBytesColumn = excelColumn(sizeBytesIndex);
    const sizeMbColumn = excelColumn(sizeMbIndex);
    const folderUrlColumn = excelColumn(folderUrlIndex);
    const linkColumn = excelColumn(linkIndex);
    filesSheet.getRange(`${sizeMbColumn}5`).formulas = [[`=${sizeBytesColumn}5/'00_使用说明'!$B$8`]];
    filesSheet.getRange(`${sizeMbColumn}5:${sizeMbColumn}${fileEnd}`).fillDown();
    filesSheet.getRange(`${linkColumn}5`).formulas = [[`=IF(${folderUrlColumn}5="","",HYPERLINK(${folderUrlColumn}5,"🔗 打开文件夹"))`]];
    filesSheet.getRange(`${linkColumn}5:${linkColumn}${fileEnd}`).fillDown();
    addTable(filesSheet, `A4:${lastFileColumn}${fileEnd}`, "FileDetailTable");
    filesSheet.getRange(`A5:A${fileEnd}`).format.numberFormat = "#,##0";
    filesSheet.getRange(`${sizeBytesColumn}5:${sizeBytesColumn}${fileEnd}`).format.numberFormat = "#,##0";
    filesSheet.getRange(`${sizeMbColumn}5:${sizeMbColumn}${fileEnd}`).format.numberFormat = "#,##0.00";
    filesSheet.getRange(`${linkColumn}5:${linkColumn}${fileEnd}`).format.font = { color: "#0563C1" };
  }
  styleHeader(filesSheet.getRange(`A4:${lastFileColumn}4`));
  filesSheet.freezePanes.freezeRows(4);
  filesSheet.freezePanes.freezeColumns(2);
  const fileWidths = { A: 9, B: 20 };
  for (let index = 0; index < categoryDepth; index += 1) fileWidths[excelColumn(2 + index)] = 28;
  Object.assign(fileWidths, {
    [excelColumn(typeIndex)]: 15,
    [excelColumn(extensionIndex)]: 13,
    [excelColumn(typeIndex + 2)]: 48,
    [excelColumn(typeIndex + 3)]: 13,
    [excelColumn(sizeBytesIndex)]: 18,
    [excelColumn(sizeMbIndex)]: 16,
    [excelColumn(typeIndex + 6)]: 55,
    [excelColumn(typeIndex + 7)]: 62,
    [excelColumn(folderUrlIndex)]: 46,
    [excelColumn(linkIndex)]: 18,
    [excelColumn(typeIndex + 10)]: 22,
  });
  setColumnWidths(filesSheet, fileWidths, Math.max(fileEnd, 5));

  titleBand(typeSheet, "A1:G1", `${partition} · 按文件类型统计`);
  noteBand(typeSheet, "A2:G2", "文件数、占比和体量均由本分区文件明细公式计算，可追溯到 01_文件明细。" );
  const typeHeaders = ["文件类型", "文件数", "明细占比", "估算大小(Bytes)", "估算大小(GB)", "平均大小(MB)", "说明"];
  typeSheet.getRange("A4:G4").values = [typeHeaders];
  typeSheet.getRangeByIndexes(4, 0, typeStats.length, 7).values = typeStats.map((row) => [row.type, null, null, null, null, null, TYPE_NOTES[row.type] || ""]);
  for (let index = 0; index < typeStats.length; index += 1) {
    const row = index + 5;
    typeSheet.getRange(`B${row}`).formulas = [[`=COUNTIF('01_文件明细'!$${excelColumn(typeIndex)}$5:$${excelColumn(typeIndex)}$${fileEnd},A${row})`]];
    typeSheet.getRange(`C${row}`).formulas = [[`=B${row}/'00_使用说明'!$B$5`]];
    typeSheet.getRange(`D${row}`).formulas = [[`=SUMIF('01_文件明细'!$${excelColumn(typeIndex)}$5:$${excelColumn(typeIndex)}$${fileEnd},A${row},'01_文件明细'!$${excelColumn(sizeBytesIndex)}$5:$${excelColumn(sizeBytesIndex)}$${fileEnd})`]];
    typeSheet.getRange(`E${row}`).formulas = [[`=D${row}/'00_使用说明'!$B$9`]];
    typeSheet.getRange(`F${row}`).formulas = [[`=IFERROR(D${row}/B${row}/'00_使用说明'!$B$8,0)`]];
  }
  styleHeader(typeSheet.getRange("A4:G4"));
  addTable(typeSheet, `A4:G${typeStats.length + 4}`, "TypeSummaryTable");
  typeSheet.freezePanes.freezeRows(4);
  typeSheet.getRange(`B5:B${typeStats.length + 4}`).format.numberFormat = "#,##0";
  typeSheet.getRange(`C5:C${typeStats.length + 4}`).format.numberFormat = "0.0%";
  typeSheet.getRange(`D5:D${typeStats.length + 4}`).format.numberFormat = "#,##0";
  typeSheet.getRange(`E5:F${typeStats.length + 4}`).format.numberFormat = "#,##0.00";
  setColumnWidths(typeSheet, { A: 20, B: 14, C: 14, D: 20, E: 16, F: 16, G: 38 }, typeStats.length + 4);

  titleBand(extensionSheet, "A1:G1", `${partition} · 按扩展名统计`);
  noteBand(extensionSheet, "A2:G2", `共识别 ${extensionStats.length} 种扩展名；文件数、占比和体量均由本分区文件明细公式计算。`);
  const extensionHeaders = ["扩展名", "文件类型", "文件数", "明细占比", "估算大小(Bytes)", "估算大小(GB)", "筛选提示"];
  extensionSheet.getRange("A4:G4").values = [extensionHeaders];
  extensionSheet.getRangeByIndexes(4, 0, extensionStats.length, 7).values = extensionStats.map((row) => [row.ext, row.type, null, null, null, null, row.ext === "(无扩展名)" ? "文件名没有后缀" : `在文件明细筛选：${row.ext}`]);
  for (let index = 0; index < extensionStats.length; index += 1) {
    const row = index + 5;
    extensionSheet.getRange(`C${row}`).formulas = [[`=COUNTIF('01_文件明细'!$${excelColumn(extensionIndex)}$5:$${excelColumn(extensionIndex)}$${fileEnd},A${row})`]];
    extensionSheet.getRange(`D${row}`).formulas = [[`=C${row}/'00_使用说明'!$B$5`]];
    extensionSheet.getRange(`E${row}`).formulas = [[`=SUMIF('01_文件明细'!$${excelColumn(extensionIndex)}$5:$${excelColumn(extensionIndex)}$${fileEnd},A${row},'01_文件明细'!$${excelColumn(sizeBytesIndex)}$5:$${excelColumn(sizeBytesIndex)}$${fileEnd})`]];
    extensionSheet.getRange(`F${row}`).formulas = [[`=E${row}/'00_使用说明'!$B$9`]];
  }
  styleHeader(extensionSheet.getRange("A4:G4"));
  addTable(extensionSheet, `A4:G${extensionStats.length + 4}`, "ExtensionSummaryTable");
  extensionSheet.freezePanes.freezeRows(4);
  extensionSheet.getRange(`C5:C${extensionStats.length + 4}`).format.numberFormat = "#,##0";
  extensionSheet.getRange(`D5:D${extensionStats.length + 4}`).format.numberFormat = "0.0%";
  extensionSheet.getRange(`E5:E${extensionStats.length + 4}`).format.numberFormat = "#,##0";
  extensionSheet.getRange(`F5:F${extensionStats.length + 4}`).format.numberFormat = "#,##0.00";
  setColumnWidths(extensionSheet, { A: 18, B: 20, C: 14, D: 14, E: 22, F: 18, G: 34 }, extensionStats.length + 4);

  return {
    workbook,
    previews: [
      ["00_使用说明", "A1:H25", "00_usage.png"],
      ["01_文件明细", `A1:${lastFileColumn}18`, "01_files.png"],
      ["02_类型统计", `A1:G${typeStats.length + 4}`, "02_types.png"],
      ["03_扩展名统计", "A1:G22", "03_extensions.png"],
    ],
    metrics: { partition, files: files.length, types: typeStats.length, extensions: extensionStats.length },
  };
}


async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { SpreadsheetFile, Workbook } = await loadArtifactTool(path.resolve(args.artifactRuntime));
  const plan = JSON.parse(await fs.readFile(path.resolve(args.plan), "utf8"));
  const aggregate = JSON.parse(await fs.readFile(plan.aggregatePath, "utf8"));
  const dateTimeOptions = { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false };
  const configuredTimeZone = process.env.SOIA_CATALOG_TIME_ZONE?.trim();
  if (configuredTimeZone) dateTimeOptions.timeZone = configuredTimeZone;
  const generatedAt = plan.releaseMetadata?.index_updated_at
    || new Intl.DateTimeFormat("sv-SE", dateTimeOptions).format(new Date());
  const results = [];

  if (plan.buildMaster) {
    const built = buildMasterWorkbook(Workbook, aggregate, plan, generatedAt);
    const qa = await inspectAndRender(built.workbook, plan.outputPath, plan.verify, plan.cacheDir, built.previews);
    await exportWorkbook(SpreadsheetFile, built.workbook, plan.outputPath);
    results.push({ output: plan.outputPath, kind: "master", ...built.metrics, ...qa });
  }

  for (const partitionPlan of plan.partitions.filter((item) => item.changed)) {
    const partitionCache = JSON.parse(await fs.readFile(partitionPlan.cache, "utf8"));
    const built = buildPartitionWorkbook(Workbook, partitionCache, generatedAt);
    const qa = await inspectAndRender(built.workbook, partitionPlan.output, plan.verify, plan.cacheDir, built.previews);
    await exportWorkbook(SpreadsheetFile, built.workbook, partitionPlan.output);
    results.push({ output: partitionPlan.output, kind: "partition", ...built.metrics, ...qa });
  }

  const payload = { generatedAt, outputs: results };
  await fs.writeFile(path.join(plan.cacheDir, "build-result.json"), JSON.stringify(payload, null, 2));
  console.log(JSON.stringify(payload));
}


await main();
