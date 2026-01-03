/**
 * Utility helpers for dynamic multi-column matrix visualization.
 * Supports N columns (N >= 3) with derived matrix layouts.
 */

import {
  Row,
  MultiColumnRule,
  SimpleMultiColumnRule,
  ColumnBasedRule,
  SimpleThreeColumnRule,
  MatrixConfig,
  validRange_Equality_Equality,
  ConflictArea,
} from "@/types/types";

// Type guards
export function isSimpleMultiColumnRule(
  rule: any
): rule is SimpleMultiColumnRule {
  return (
    typeof rule === "object" &&
    rule !== null &&
    "columnValues" in rule &&
    Array.isArray(rule.columnValues)
  );
}

export function isSimpleThreeColumnRule(
  rule: any
): rule is SimpleThreeColumnRule {
  return (
    typeof rule === "object" &&
    rule !== null &&
    "col1Value" in rule &&
    "col2Value" in rule &&
    "col3Value" in rule
  );
}

export function isColumnBasedRule(rule: any): rule is ColumnBasedRule {
  return (
    typeof rule === "object" &&
    rule !== null &&
    !("columnValues" in rule) &&
    !("col1Value" in rule)
  );
}

// Utility helpers
export function toPlainArray<T>(arr: any): T[] {
  if (!arr) return [];
  if (Array.isArray(arr)) return Array.from(arr);
  if (arr && typeof arr === "object" && typeof arr.length === "number")
    return Array.from(arr);
  return [];
}

function generateCombinations(
  arrays: string[][],
  current: string[],
  result: SimpleMultiColumnRule[]
): void {
  if (current.length === arrays.length) {
    result.push({ columnValues: [...current] });
    return;
  }

  const currentIndex = current.length;
  const currentArray = arrays[currentIndex];

  for (const value of currentArray) {
    if (value != null) {
      generateCombinations(arrays, [...current, String(value)], result);
    }
  }
}
export function normalizeMultiColumnRules(
  rules: MultiColumnRule[] | undefined | null,
  columns: string[]
): SimpleMultiColumnRule[] {
  const safeRules = toPlainArray<MultiColumnRule>(rules);
  const numColumns = columns.length;

  if (safeRules.length === 0 || numColumns < 3) {
    console.warn(
      `normalizeMultiColumnRules: invalid input - ${safeRules.length} rules, ${numColumns} columns`
    );
    return [];
  }

  const flatRules: SimpleMultiColumnRule[] = [];

  safeRules.forEach((rule) => {
    if (!rule) return;

    if (isSimpleMultiColumnRule(rule)) {
      if (rule.columnValues.length === numColumns) {
        flatRules.push(rule);
      } else {
        console.warn(
          `Rule has ${rule.columnValues.length} values but expected ${numColumns}`
        );
      }
      return;
    }

    if (isSimpleThreeColumnRule(rule) && numColumns === 3) {
      flatRules.push({
        columnValues: [rule.col1Value, rule.col2Value, rule.col3Value],
      });
      return;
    }

    if (isColumnBasedRule(rule)) {
      const missingColumns = columns.filter(
        (col) => !rule[col] || rule[col].length === 0
      );

      if (missingColumns.length > 0) {
        console.warn(
          `Rule missing columns: ${missingColumns.join(", ")}, skipping`
        );
        return;
      }

      const columnValueArrays = columns.map((col) =>
        toPlainArray<string>(rule[col])
      );
      generateCombinations(columnValueArrays, [], flatRules);
    }
  });
  return flatRules;
}

export function generateMatrixConfigs(
  columns: string[],
  direction: "right" | "top" = "top"
): MatrixConfig[] {
  const numColumns = columns.length;

  if (numColumns < 3) {
    console.warn(
      `generateMatrixConfigs: need at least 3 columns, got ${numColumns}`
    );
    return [];
  }

  const configs: MatrixConfig[] = [];
  const baseColumn = columns[0];
  for (let i = 1; i < numColumns; i++) {
    const matrixId = `matrix${i - 1}`;
    const matrixColumns: [string, string] = [baseColumn, columns[i]];

    let edges: string[];

    if (direction === "top") {
      if (i === 1) {
        edges = ["top", "left", "right"];
      } else if (i === numColumns - 1) {
        edges = ["bottom", "left", "right"];
      } else {
        edges = ["left", "right"];
      }
    } else {
      if (i === 1) {
        edges = ["top", "bottom", "left"];
      } else if (i === numColumns - 1) {
        edges = ["top", "bottom", "right"];
      } else {
        edges = ["top", "bottom"];
      }
    }

    configs.push({
      id: matrixId,
      columns: matrixColumns,
      edges,
      position: { x: 0, y: 0 }, // position resolved later
    });
  }

  return configs;
}

export function generateValidRulesForMatrices(
  flatRules: SimpleMultiColumnRule[],
  columns: string[],
  matrixConfigs: MatrixConfig[]
): Map<string, validRange_Equality_Equality[]> {
  const matrixRulesMap = new Map<string, validRange_Equality_Equality[]>();

  matrixConfigs.forEach((config) => {
    const [col1, col2] = config.columns;
    const col1Index = columns.indexOf(col1);
    const col2Index = columns.indexOf(col2);

    if (col1Index === -1 || col2Index === -1) {
      console.warn(`Matrix ${config.id} has invalid columns: ${col1}, ${col2}`);
      return;
    }

    const groupedRules = new Map<string, Set<string>>();

    flatRules.forEach((rule) => {
      const key = rule.columnValues[col1Index];
      const constraint = rule.columnValues[col2Index];

      if (!groupedRules.has(key)) {
        groupedRules.set(key, new Set());
      }
      groupedRules.get(key)!.add(constraint);
    });

    const validRules: validRange_Equality_Equality[] = [];
    groupedRules.forEach((constraints, condition) => {
      validRules.push({
        conditionValue: condition,
        constraintValue: Array.from(constraints),
      });
    });

    matrixRulesMap.set(config.id, validRules);
  });
  return matrixRulesMap;
}

export function analyzeConflictAreasForMatrices(
  csvData: Row[],
  columns: string[],
  flatRules: SimpleMultiColumnRule[],
  invalidIndices: number[],
  matrixConfigs: MatrixConfig[]
): Map<string, ConflictArea[]> {
  const matrixConflictsMap = new Map<string, ConflictArea[]>();

  matrixConfigs.forEach((config) => {
    const [col1, col2] = config.columns;
    const conflicts: ConflictArea[] = [];

    const combinations = new Map<
      string,
      { validExists: boolean; invalidExists: boolean }
    >();

    csvData.forEach((row, index) => {
      const val1 = String(row[col1] || "").toLowerCase();
      const val2 = String(row[col2] || "").toLowerCase();

      if (!val1 || !val2) return;

      const key = `${val1}-${val2}`;
      if (!combinations.has(key)) {
        combinations.set(key, { validExists: false, invalidExists: false });
      }

      const col1Index = columns.indexOf(col1);
      const col2Index = columns.indexOf(col2);

      const matchesRule = flatRules.some((rule) => {
        return columns.every((colName, idx) => {
          const ruleValue = rule.columnValues[idx].toLowerCase();
          const rowValue = String(row[colName] || "").toLowerCase();
          return ruleValue === rowValue;
        });
      });

      const isInvalid = invalidIndices.includes(index);

      if (matchesRule && !isInvalid) {
        combinations.get(key)!.validExists = true;
      } else if (isInvalid) {
        combinations.get(key)!.invalidExists = true;
      }
    });

    combinations.forEach((status, key) => {
      if (status.validExists && status.invalidExists) {
        const [cat1, cat2] = key.split("-");
        conflicts.push({
          category1: cat1,
          category2: cat2,
          conflictType: "both",
        });
      }
    });

    matrixConflictsMap.set(config.id, conflicts);
  });
  return matrixConflictsMap;
}

export function calculateMultipleMatrixLayout(
  matrixInstances: Map<string, any>,
  matrixConfigs: MatrixConfig[],
  direction: "right" | "top" = "top",
  gap = 10,
  edgeChartHeight = 220
): {
  positions: Map<string, { x: number; y: number }>;
  totalBounds: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
    width: number;
    height: number;
  };
} {
  const positions = new Map<string, { x: number; y: number }>();

  let currentX = 0;
  let currentY = 0;
  let minX = 0;
  let minY = 0;
  let maxX = 0;
  let maxY = 0;

  matrixConfigs.forEach((config, index) => {
    const instance = matrixInstances.get(config.id);
    if (!instance?.getDimensions) {
      console.warn(`Matrix ${config.id} instance not found or invalid`);
      return;
    }

    const dimensions = instance.getDimensions();

    let matrixMinX = currentX;
    let matrixMinY = currentY;
    let matrixMaxX = currentX + dimensions.matrixWidth;
    let matrixMaxY = currentY + dimensions.matrixHeight;

    if (config.edges.includes("left")) matrixMinX -= edgeChartHeight + gap;
    if (config.edges.includes("right")) matrixMaxX += edgeChartHeight + gap;
    if (config.edges.includes("top")) matrixMinY -= edgeChartHeight + gap;
    if (config.edges.includes("bottom")) matrixMaxY += edgeChartHeight + gap;

    positions.set(config.id, { x: currentX, y: currentY });

    minX = Math.min(minX, matrixMinX);
    minY = Math.min(minY, matrixMinY);
    maxX = Math.max(maxX, matrixMaxX);
    maxY = Math.max(maxY, matrixMaxY);

    if (index < matrixConfigs.length - 1) {
      if (direction === "right") {
        currentX = matrixMaxX + gap;
      } else {
        currentY = matrixMaxY + gap;
      }
    }
  });

  return {
    positions,
    totalBounds: {
      minX,
      minY,
      maxX,
      maxY,
      width: maxX - minX,
      height: maxY - minY,
    },
  };
}
