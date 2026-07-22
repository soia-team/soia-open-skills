export const COLORS = {
  navy: "#16324F",
  teal: "#0F766E",
  pale: "#E8F3F1",
  blue: "#EAF2F8",
  amber: "#FEF3C7",
  lightGray: "#E2E8F0",
  white: "#FFFFFF",
};

export function titleBand(sheet, range, title) {
  const target = sheet.getRange(range);
  target.merge();
  target.values = [[title]];
  target.format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 16 },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
  target.format.rowHeight = 30;
}

export function noteBand(sheet, range, text, warning = false) {
  const target = sheet.getRange(range);
  target.merge();
  target.values = [[text]];
  target.format = {
    fill: warning ? COLORS.amber : COLORS.pale,
    font: { color: warning ? "#92400E" : COLORS.navy, italic: warning },
    wrapText: true,
    verticalAlignment: "center",
  };
  target.format.rowHeight = warning ? 38 : 30;
}

export function styleHeader(range) {
  range.format = {
    fill: COLORS.teal,
    font: { bold: true, color: COLORS.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.teal },
  };
  range.format.rowHeight = 28;
}

export function setColumnWidths(sheet, widths, lastRow) {
  for (const [column, width] of Object.entries(widths)) {
    sheet.getRange(`${column}1:${column}${lastRow}`).format.columnWidth = width;
  }
}

export function addTable(sheet, range, name) {
  const table = sheet.tables.add(range, true, name);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  table.showBandedRows = true;
  return table;
}

export function prepareSheet(sheet) {
  sheet.showGridLines = false;
}

export function friendlyLocalPath(masterPath, detailPath) {
  // detailPath is undefined for a catalog partition with no matching _全文检索/*.md
  // file (e.g. a currently-empty partition like 80_待探索资源) -- not an error case.
  if (!detailPath) return "";
  const base = masterPath.replace(/\\/g, "/").split("/").slice(0, -1).join("/");
  const target = detailPath.replace(/\\/g, "/");
  return target.startsWith(`${base}/`) ? target.slice(base.length + 1) : target;
}
