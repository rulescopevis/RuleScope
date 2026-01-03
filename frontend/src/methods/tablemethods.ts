import { Row, ParsedCSV } from "../types/types";

export function parseCSV(csvContent: string): ParsedCSV {
  const lines = csvContent.split("\n").filter((line) => line.trim() !== "");

  const headers = lines[0].split(",").map((header) => header.trim());

  const csvData = lines.slice(1).map((line, rowIndex) => {
    const values = line.split(",").map((value) => value.trim());
    const row: Row = {};
    headers.forEach((header, columnIndex) => {
      let value: string | number = values[columnIndex];
      if (value && !isNaN(value as any)) {
        value = value.includes(".") ? parseFloat(value) : parseInt(value);
      }
      row[header] = value;
    });
    row["rowIndex"] = rowIndex;
    return row;
  });

  return { csvData, headers };
}
