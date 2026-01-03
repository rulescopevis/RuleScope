import * as d3 from "d3";
import { discrete_matrix, renderMatrixCore } from "./discrete_matrix";
import {
  validRange_Equality_Equality,
  Row,
  ConflictArea,
  MatrixEventBus,
  MatrixRenderConfig,
  HighlightState,
  ThreeColumnRule,
  ColumnBasedRule,
  SimpleThreeColumnRule,
  MultiColumnRule,
  SimpleMultiColumnRule,
  MatrixConfig,
} from "@/types/types";
import { MultipleMatrixManager } from "./multiple-matrix-manager";
import { createTooltip } from "@/utils/tootips";
import { createLoadingAnimation } from "@/utils/utils";

// === Configuration ===
const CONFIG = {
  MULTIPLE_MATRIX: {
    spacing: 40,
    rotationAngle: 45,
    edgeChartHeight: 220,
    minScale: 0.6, // Allow moderate zoom out
    maxScale: 6, // Increase upper bound to allow small matrices to appear larger
  },
  COLORS: {
    highlight: "#fd8d3c",
    valid: "#4570b6",
    invalid: "#fd8d3c",
    conflict: "#FBDE71",
  },
  TOOLTIP: {
    stroke: "black",
    strokeWidth: "2",
  },
  ANIMATION: {
    duration: 500,
  },
  TOOLTIPS: {
    getValidTemplate: (validDataStr: string, ruleType: string): string => {
      switch (ruleType.toLowerCase()) {
        case "mapping":
          return `${validDataStr} <strong style="color: ${CONFIG.COLORS.valid};">is valid</strong> for mapping rules`;
        case "multiplecondition":
        default:
          return `${validDataStr} <strong style="color: ${CONFIG.COLORS.valid};">is valid</strong> for logical and condition rules`;
      }
    },
    getInvalidTemplate: (invalidDataStr: string, ruleType: string): string => {
      switch (ruleType.toLowerCase()) {
        case "mapping":
          return `${invalidDataStr} <strong style="color: ${CONFIG.COLORS.invalid};">is invalid</strong> for mapping rules`;
        case "multiplecondition":
        default:
          return `${invalidDataStr} <strong style="color: ${CONFIG.COLORS.invalid};">is invalid</strong> for logical and condition rules`;
      }
    },
    getConflictTemplate: (parts: string[], ruleType: string): string => {
      const template = parts.join(", ");
      switch (ruleType.toLowerCase()) {
        case "mapping":
          return `${template} for mapping rules`;
        case "multiplecondition":
        default:
          return `${template} for logical and condition rules`;
      }
    },
    getNoValidData: (ruleType: string): string => {
      switch (ruleType.toLowerCase()) {
        case "mapping":
          return "No data matching mapping rules";
        case "multiplecondition":
        default:
          return "No data matching logical and condition rules";
      }
    },
    getNoInvalidData: (ruleType: string): string => {
      switch (ruleType.toLowerCase()) {
        case "mapping":
          return "No data violating mapping rules";
        case "multiplecondition":
        default:
          return "No data violating logical and condition rules";
      }
    },
    getNoData: (ruleType: string): string => {
      switch (ruleType.toLowerCase()) {
        case "mapping":
          return "No mapping rule data";
        case "multiplecondition":
        default:
          return "No logical and condition rule data";
      }
    },
  },
};

// Global variables to track the currently displayed tooltip
let currentTooltip: any = null;
let currentTooltipCell: { category1: string; category2: string } | null = null;

// === Utility Functions ===

/**
 * Safely convert Vue Proxy array to plain array
 */
function toPlainArray<T>(arr: any): T[] {
  if (!arr) return [];
  if (Array.isArray(arr)) return Array.from(arr);
  if (arr && typeof arr === "object" && typeof arr.length === "number")
    return Array.from(arr);
  return [];
}

/**
 * Safely get array length
 */
function getSafeLength(arr: any): number {
  if (!arr) return 0;
  if (typeof arr.length === "number") return arr.length;
  if (Array.isArray(arr)) return arr.length;
  return 0;
}

/**
 * Type Guard: Check if it is a simple three-column rule format
 */
function isSimpleThreeColumnRule(
  rule: ThreeColumnRule | MultiColumnRule
): rule is SimpleThreeColumnRule {
  return (
    typeof rule === "object" &&
    rule !== null &&
    "col1Value" in rule &&
    "col2Value" in rule &&
    "col3Value" in rule &&
    typeof rule.col1Value === "string" &&
    typeof rule.col2Value === "string" &&
    typeof rule.col3Value === "string"
  );
}

/**
 * Type Guard: Check if it is a simple multi-column rule format
 */
function isSimpleMultiColumnRule(
  rule: ThreeColumnRule | MultiColumnRule
): rule is SimpleMultiColumnRule {
  return (
    typeof rule === "object" &&
    rule !== null &&
    "columnValues" in rule &&
    Array.isArray(rule.columnValues)
  );
}

/**
 * Type Guard: Check if it is a column-name based rule format
 */
function isColumnBasedRule(
  rule: ThreeColumnRule | MultiColumnRule
): rule is ColumnBasedRule {
  return (
    typeof rule === "object" &&
    rule !== null &&
    !("col1Value" in rule) &&
    !("col2Value" in rule) &&
    !("col3Value" in rule) &&
    !("columnValues" in rule)
  );
}

/**
 * Calculate matrix extended bounds
 */
function getMatrixExtendedBounds(
  dimensions: any,
  edges: string[],
  baseX: number,
  baseY: number,
  edgeChartHeight: number,
  gap: number
) {
  let minX = baseX;
  let minY = baseY;
  let maxX = baseX + dimensions.matrixWidth;
  let maxY = baseY + dimensions.matrixHeight;

  if (edges.includes("left")) minX -= edgeChartHeight + gap;
  if (edges.includes("right")) maxX += edgeChartHeight + gap;
  if (edges.includes("top")) minY -= edgeChartHeight + gap;
  if (edges.includes("bottom")) maxY += edgeChartHeight + gap;

  return {
    minX,
    minY,
    maxX,
    maxY,
    totalWidth: maxX - minX,
    totalHeight: maxY - minY,
    coreX: baseX,
    coreY: baseY,
    coreWidth: dimensions.matrixWidth,
    coreHeight: dimensions.matrixHeight,
  };
}

/**
 * Calculate matrix layout - supports different directions
 */
function calculateMatrixLayout(
  matrix1Instance: any,
  matrix2Instance: any,
  matrix1Config: MatrixRenderConfig,
  matrix2Config: MatrixRenderConfig,
  direction: "right" | "top" = "right",
  gap = 10
) {
  const edgeChartHeight = CONFIG.MULTIPLE_MATRIX.edgeChartHeight;

  if (!matrix1Instance?.getDimensions || !matrix2Instance?.getDimensions) {
    return null;
  }

  const matrix1Dimensions = matrix1Instance.getDimensions();
  const matrix2Dimensions = matrix2Instance.getDimensions();

  const matrix1BaseX = 0;
  const matrix1BaseY = 0;
  const matrix1Bounds = getMatrixExtendedBounds(
    matrix1Dimensions,
    matrix1Config.edges,
    matrix1BaseX,
    matrix1BaseY,
    edgeChartHeight,
    gap
  );

  let matrix2BaseX, matrix2BaseY;

  // Calculate position of the second matrix based on direction
  if (direction === "right") {
    // Second matrix on the right
    matrix2BaseX = matrix1Bounds.maxX + gap;
    matrix2BaseY = matrix1BaseY;

    // Consider the left edge chart of the second matrix
    if (matrix2Config.edges.includes("left")) {
      matrix2BaseX += edgeChartHeight + gap;
    }
  } else if (direction === "top") {
    // Second matrix on top
    matrix2BaseX = matrix1BaseX;
    matrix2BaseY = matrix1Bounds.minY - matrix2Dimensions.matrixHeight - gap;

    // Consider the bottom edge chart of the second matrix
    if (matrix2Config.edges.includes("bottom")) {
      matrix2BaseY -= edgeChartHeight + gap;
    }
  } else {
    // Default (keep right)
    matrix2BaseX = matrix1Bounds.maxX + gap;
    matrix2BaseY = matrix1BaseY;
  }

  const matrix2Bounds = getMatrixExtendedBounds(
    matrix2Dimensions,
    matrix2Config.edges,
    matrix2BaseX,
    matrix2BaseY,
    edgeChartHeight,
    gap
  );

  // Calculate system bounds
  const systemMinX = Math.min(matrix1Bounds.minX, matrix2Bounds.minX);
  const systemMinY = Math.min(matrix1Bounds.minY, matrix2Bounds.minY);
  const systemMaxX = Math.max(matrix1Bounds.maxX, matrix2Bounds.maxX);
  const systemMaxY = Math.max(matrix1Bounds.maxY, matrix2Bounds.maxY);

  return {
    matrix1: { x: matrix1BaseX, y: matrix1BaseY, bounds: matrix1Bounds },
    matrix2: { x: matrix2BaseX, y: matrix2BaseY, bounds: matrix2Bounds },
    system: {
      minX: systemMinX,
      minY: systemMinY,
      maxX: systemMaxX,
      maxY: systemMaxY,
      totalWidth: systemMaxX - systemMinX,
      totalHeight: systemMaxY - systemMinY,
      centerX: systemMinX + (systemMaxX - systemMinX) / 2,
      centerY: systemMinY + (systemMaxY - systemMinY) / 2,
    },
  };
}

/**
 * Normalize rule format - supports any number of columns (N >= 3)
 * @param rules - Original rules array
 * @param columns - Array of column names, length N
 * @returns Normalized simple rule array (each rule is a columnValues array)
 */
function normalizeRules(
  rules: (ThreeColumnRule | MultiColumnRule)[] | undefined | null,
  columns: string[]
): SimpleMultiColumnRule[] {
  const safeRules = toPlainArray<ThreeColumnRule | MultiColumnRule>(rules);
  const safeColumns = toPlainArray<string>(columns);

  if (getSafeLength(safeRules) === 0) {
    return [];
  }

  if (getSafeLength(safeColumns) < 3) {
    console.warn(
      `normalizeRules: columns parameter must have at least 3 elements, got ${safeColumns.length}`
    );
    return [];
  }

  const numColumns = safeColumns.length;
  const flatRules: SimpleMultiColumnRule[] = [];

  safeRules.forEach((rule) => {
    if (!rule) {
      return;
    }

    // Case 1: Already in SimpleMultiColumnRule format
    if (isSimpleMultiColumnRule(rule)) {
      if (rule.columnValues.length === numColumns) {
        flatRules.push(rule);
      } else {
        console.warn(
          `normalizeRules: SimpleMultiColumnRule has ${rule.columnValues.length} values but expected ${numColumns}, skipping`
        );
      }
      return;
    }

    // Case 2: Backwards compatible with SimpleThreeColumnRule format
    if (isSimpleThreeColumnRule(rule) && numColumns === 3) {
      flatRules.push({
        columnValues: [rule.col1Value, rule.col2Value, rule.col3Value],
      });
      return;
    }

    // Case 3: ColumnBasedRule format - needs verification that all columns exist
    if (isColumnBasedRule(rule)) {
      const columnBasedRule = rule;

      // Verify all columns are defined in the rule
      const missingColumns = safeColumns.filter(
        (col) => !columnBasedRule[col] || columnBasedRule[col].length === 0
      );

      if (missingColumns.length > 0) {
        console.warn(
          `normalizeRules: rule missing columns [${missingColumns.join(
            ", "
          )}], skipping:`,
          rule
        );
        return;
      }

      // Get value arrays for each column
      const columnValueArrays = safeColumns.map((col) =>
        toPlainArray<string>(columnBasedRule[col])
      );

      // Generate all possible combinations
      generateCombinations(columnValueArrays, [], flatRules);
    }
  });

  return flatRules;
}

/**
 * Recursively generate Cartesian product combinations of all column values
 */
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

// ===== Dynamic Multi-Column Matrix Helper Functions =====

/**
 * Generate configuration for multiple matrices - generate N-1 matrices for N columns
 * Strategy: Alternating shared column "chain" pattern to ensure matrix edge connections
 */
function generateMatrixConfigsForMultipleMatrix(
  columns: string[],
  direction: "right" | "top" = "top"
): Array<{ id: string; columns: [string, string]; edges: string[] }> {
  const numColumns = columns.length;

  if (numColumns < 3) {
    console.warn(
      `generateMatrixConfigs: need at least 3 columns, got ${numColumns}`
    );
    return [];
  }

  const configs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }> = [];

  let matrixIndex = 0;

  // Iterate over all possible shared columns (odd indices: 1, 3, 5, ...)
  for (let sharedIdx = 1; sharedIdx < numColumns; sharedIdx += 2) {
    const sharedColumn = columns[sharedIdx];

    // Create matrix for this shared column
    // First matrix: Paired with previous column
    if (sharedIdx > 0) {
      const matrixId = `matrix${matrixIndex}`;
      const matrixColumns: [string, string] = [
        sharedColumn,
        columns[sharedIdx - 1],
      ];

      // Determine which edges to display based on position and direction
      let edges: string[];

      if (direction === "top") {
        // Vertical arrangement
        // matrix0 at bottom, show bottom and right
        if (matrixIndex === 0) {
          edges = ["bottom", "right"];
        } else if (sharedIdx === numColumns - 1) {
          edges = ["top"];
        } else {
          edges = ["left", "right"];
        }
      } else {
        // Horizontal arrangement
        if (matrixIndex === 0) {
          edges = ["top", "bottom", "left"];
        } else if (sharedIdx === numColumns - 1) {
          edges = ["top", "bottom", "right"];
        } else {
          edges = ["top", "bottom"];
        }
      }

      configs.push({
        id: matrixId,
        columns: matrixColumns,
        edges,
      });

      matrixIndex++;
    }

    // Second matrix: Paired with next column (if exists)
    if (sharedIdx + 1 < numColumns) {
      const matrixId = `matrix${matrixIndex}`;
      const matrixColumns: [string, string] = [
        sharedColumn,
        columns[sharedIdx + 1],
      ];

      // Determine edges
      let edges: string[];

      if (direction === "top") {
        // Vertical arrangement
        // matrix1 top left, show left
        // matrix2+ top right, show top
        if (matrixIndex === 1) {
          edges = ["left"];
        } else if (matrixIndex === 2) {
          // matrix2 right of matrix1, show top
          edges = ["top"];
        } else if (matrixIndex > 2) {
          // matrix3+ continues on right
          edges = ["top"];
        } else {
          edges = ["left", "right"];
        }
      } else {
        // Horizontal arrangement
        if (matrixIndex === 0) {
          edges = ["top", "bottom", "left"];
        } else if (sharedIdx + 1 === numColumns - 1) {
          edges = ["top", "bottom", "right"];
        } else {
          edges = ["top", "bottom"];
        }
      }

      configs.push({
        id: matrixId,
        columns: matrixColumns,
        edges,
      });

      matrixIndex++;
    }
  }

  return configs;
}

/**
 * Generate valid rules for each matrix
 */
function generateValidRulesForMultipleMatrices(
  flatRules: SimpleMultiColumnRule[],
  columns: string[],
  matrixConfigs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }>
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

    // Group by first column
    const groupedRules = new Map<string, Set<string>>();

    flatRules.forEach((rule) => {
      const key = rule.columnValues[col1Index];
      const constraint = rule.columnValues[col2Index];

      if (!groupedRules.has(key)) {
        groupedRules.set(key, new Set());
      }
      groupedRules.get(key)!.add(constraint);
    });

    // Convert to validRange_Equality_Equality format
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

/**
 * Analyze conflict areas for each matrix
 */
function analyzeConflictAreasForMultipleMatrices(
  csvData: Row[],
  columns: string[],
  flatRules: SimpleMultiColumnRule[],
  invalidIndices: number[],
  matrixConfigs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }>
): Map<string, ConflictArea[]> {
  const matrixConflictsMap = new Map<string, ConflictArea[]>();

  matrixConfigs.forEach((config) => {
    const [col1, col2] = config.columns;
    const conflicts: ConflictArea[] = [];

    // Track validity of each combination
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

      // Check against rules
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

    // Identify conflicting combinations
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

/**
 * Calculate layout positions for multiple matrices
 */
function calculateMultipleMatricesLayout(
  matrixInstances: Map<string, any>,
  matrixConfigs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }>,
  direction: "right" | "top" = "top",
  gap = CONFIG.MULTIPLE_MATRIX.spacing,
  edgeChartHeight = CONFIG.MULTIPLE_MATRIX.edgeChartHeight
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
} | null {
  const positions = new Map<string, { x: number; y: number }>();

  let minX = 0;
  let minY = 0;
  let maxX = 0;
  let maxY = 0;

  // Place first matrix at origin
  const firstConfig = matrixConfigs[0];
  const firstInstance = matrixInstances.get(firstConfig.id);

  if (!firstInstance?.getDimensions) {
    console.warn(`Matrix ${firstConfig.id} instance not found or invalid`);
    return null;
  }

  const firstDimensions = firstInstance.getDimensions();
  const firstBaseX = 0;
  const firstBaseY = 0;

  // Calculate first matrix extended bounds
  const firstBounds = getMatrixExtendedBounds(
    firstDimensions,
    firstConfig.edges,
    firstBaseX,
    firstBaseY,
    edgeChartHeight,
    gap
  );

  positions.set(firstConfig.id, { x: firstBaseX, y: firstBaseY });

  minX = firstBounds.minX;
  minY = firstBounds.minY;
  maxX = firstBounds.maxX;
  maxY = firstBounds.maxY;

  // Process subsequent matrices
  for (let i = 1; i < matrixConfigs.length; i++) {
    const config = matrixConfigs[i];
    const instance = matrixInstances.get(config.id);

    if (!instance?.getDimensions) {
      console.warn(`Matrix ${config.id} instance not found or invalid`);
      return null;
    }

    const dimensions = instance.getDimensions();

    let currentX: number;
    let currentY: number;

    if (direction === "right") {
      // Horizontal: All matrices to the right of the previous one
      const prevConfig = matrixConfigs[i - 1];
      const prevPos = positions.get(prevConfig.id)!;
      const prevInstance = matrixInstances.get(prevConfig.id);

      if (!prevInstance?.getDimensions) {
        console.warn(`Previous matrix instance not found`);
        return null;
      }

      const prevDimensions = prevInstance.getDimensions();
      const prevBounds = getMatrixExtendedBounds(
        prevDimensions,
        prevConfig.edges,
        prevPos.x,
        prevPos.y,
        edgeChartHeight,
        gap
      );

      currentX = prevBounds.maxX + gap;
      currentY = prevPos.y;

      if (config.edges.includes("left")) {
        currentX += edgeChartHeight + gap;
      }
    } else {
      // Vertical: Layout depends on matrix index
      if (i === 1) {
        // matrix1: Above matrix0
        const prevConfig = matrixConfigs[0];
        const prevPos = positions.get(prevConfig.id)!;
        const prevInstance = matrixInstances.get(prevConfig.id);

        if (!prevInstance?.getDimensions) {
          console.warn(`Matrix ${prevConfig.id} instance not found`);
          return null;
        }

        const prevDimensions = prevInstance.getDimensions();
        const prevBounds = getMatrixExtendedBounds(
          prevDimensions,
          prevConfig.edges,
          prevPos.x,
          prevPos.y,
          edgeChartHeight,
          gap
        );

        currentX = prevPos.x;
        currentY = prevBounds.minY - dimensions.matrixHeight - gap;

        if (config.edges.includes("bottom")) {
          currentY -= edgeChartHeight + gap;
        }
      } else if (i === 2) {
        // matrix2: To the right of matrix1
        const matrix1Config = matrixConfigs[1];
        const matrix1Pos = positions.get(matrix1Config.id)!;
        const matrix1Instance = matrixInstances.get(matrix1Config.id);

        if (!matrix1Instance?.getDimensions) {
          console.warn(`Matrix ${matrix1Config.id} instance not found`);
          return null;
        }

        const matrix1Dimensions = matrix1Instance.getDimensions();
        const matrix1Bounds = getMatrixExtendedBounds(
          matrix1Dimensions,
          matrix1Config.edges,
          matrix1Pos.x,
          matrix1Pos.y,
          edgeChartHeight,
          gap
        );

        currentX = matrix1Bounds.maxX + gap;
        currentY = matrix1Pos.y;

        if (config.edges.includes("left")) {
          currentX += edgeChartHeight + gap;
        }
      } else {
        // matrix3+: Continue to the right of the previous matrix
        const prevConfig = matrixConfigs[i - 1];
        const prevPos = positions.get(prevConfig.id)!;
        const prevInstance = matrixInstances.get(prevConfig.id);

        if (!prevInstance?.getDimensions) {
          console.warn(`Previous matrix instance not found`);
          return null;
        }

        const prevDimensions = prevInstance.getDimensions();
        const prevBounds = getMatrixExtendedBounds(
          prevDimensions,
          prevConfig.edges,
          prevPos.x,
          prevPos.y,
          edgeChartHeight,
          gap
        );

        currentX = prevBounds.maxX + gap;
        currentY = prevPos.y;

        if (config.edges.includes("left")) {
          currentX += edgeChartHeight + gap;
        }
      }
    }

    positions.set(config.id, { x: currentX, y: currentY });

    // Calculate current matrix extended bounds and update global bounds
    const currentBounds = getMatrixExtendedBounds(
      dimensions,
      config.edges,
      currentX,
      currentY,
      edgeChartHeight,
      gap
    );

    minX = Math.min(minX, currentBounds.minX);
    minY = Math.min(minY, currentBounds.minY);
    maxX = Math.max(maxX, currentBounds.maxX);
    maxY = Math.max(maxY, currentBounds.maxY);
  }

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

/**
 * Set up dynamic multi-matrix tooltips
 */
function setupMultipleMatrixTooltipsForDynamic(
  containerGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  columns: string[],
  invalidIndices: number[],
  flatRules: SimpleMultiColumnRule[],
  matrixInstances: Map<string, any>,
  matrixConfigs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }>,
  ruleType: string,
  scale: number
): void {
  const safeCsvData = toPlainArray<Row>(csvData);
  const safeColumns = toPlainArray<string>(columns);
  const safeInvalidIndices = toPlainArray<number>(invalidIndices);
  const safeFlatRules = toPlainArray<SimpleMultiColumnRule>(flatRules);

  if (safeCsvData.length === 0 || safeColumns.length < 2) {
    return;
  }

  // Ensure previous tooltips are cleared
  hideAllMultipleMatrixTooltips();

  // Create or get global tooltip layer, ensuring it renders above all matrices
  let tooltipLayer = containerGroup.select<SVGGElement>(".tooltip-layer");
  if (tooltipLayer.empty()) {
    tooltipLayer = containerGroup.append("g").attr("class", "tooltip-layer");
  }
  tooltipLayer.raise();

  // Scale up tooltip moderately when layout is compressed to maintain readability
  const tooltipScaleRatio =
    scale < 1 ? Math.max(1, Math.min(1.6, 0.8 / scale)) : 1;

  matrixConfigs.forEach((config) => {
    const matrixGroup = containerGroup.select<SVGGElement>(
      `.matrix-group.${config.id}`
    );
    if (matrixGroup.empty()) return;

    const matrixColumns: [string, string] = config.columns;
    const matrixCells = matrixGroup.selectAll("rect[id='matrix']");

    matrixCells.each(function () {
      const cell = d3.select(this);
      const category1 = cell.attr("data-category1");
      const category2 = cell.attr("data-category2");
      const cellType = cell.attr("data-cell-type") || "invalid";

      if (!category1 || !category2) return;

      const rectX = parseFloat(cell.attr("x"));
      const rectY = parseFloat(cell.attr("y"));
      const rectWidth = parseFloat(cell.attr("width"));
      const rectHeight = parseFloat(cell.attr("height"));

      // Transform rectangle local coordinates to containerGroup coordinates
      const toContainerPoint = (x: number, y: number) => {
        const cellNode = cell.node() as SVGRectElement | null;
        const containerNode = containerGroup.node() as SVGGElement | null;
        if (!cellNode || !containerNode) return { x, y };

        const cellCTM = cellNode.getCTM();
        const containerCTM = containerNode.getCTM();
        if (!cellCTM || !containerCTM) return { x, y };

        const containerInv = containerCTM.inverse();
        const domPoint = new DOMPoint(x, y);
        const globalPoint = domPoint.matrixTransform(cellCTM);
        const localToContainer = globalPoint.matrixTransform(containerInv);
        return { x: localToContainer.x, y: localToContainer.y };
      };

      // Calculate top-left position in container coordinates
      const { x: anchorX, y: anchorY } = toContainerPoint(rectX, rectY);

      // Calculate actual width of cell in container coordinates
      const pRight = toContainerPoint(rectX + rectWidth, rectY);
      const scaledWidth = Math.hypot(pRight.x - anchorX, pRight.y - anchorY);
      // Fallback to original width if scaling calculation fails
      const finalWidth =
        isFinite(scaledWidth) && scaledWidth > 0 ? scaledWidth : rectWidth;

      const cellData = analyzeCellMultiColumnData(
        safeCsvData,
        safeColumns,
        matrixColumns,
        category1,
        category2,
        safeInvalidIndices,
        safeFlatRules
      );

      const tooltipTemplate = generateDynamicTooltipTemplate(
        cellData,
        safeColumns,
        cellType,
        ruleType
      );

      const tooltip = createTooltip(
        tooltipLayer,
        anchorX,
        anchorY,
        0,
        0,
        finalWidth,
        tooltipTemplate,
        safeColumns,
        ruleType,
        `${category1}-${category2}`,
        tooltipScaleRatio
      );

      const originalClickHandler = cell.on("click");
      const originalContextMenuHandler = cell.on("contextmenu");

      cell.on("click", function (event, d) {
        if (originalClickHandler) {
          originalClickHandler.call(this, event, d);
        }

        setTimeout(() => {
          handleTooltipInteraction(
            tooltip,
            category1,
            category2,
            cellType === "valid",
            cellType === "conflict"
          );
        }, 50);
      });

      cell.on("contextmenu", function (event, d) {
        event.preventDefault();

        if (originalContextMenuHandler) {
          originalContextMenuHandler.call(this, event, d);
        }

        setTimeout(() => {
          handleTooltipInteraction(
            tooltip,
            category1,
            category2,
            cellType === "valid",
            cellType === "conflict"
          );
        }, 50);
      });
    });
  });
}

// ===== Original Three-Column Matrix Functions (Kept for backward compatibility) =====

/**
 * Generate valid rules from three-column rules - Fix: Generate rules based on actual matrix columns
 */
function generateValidRulesFromThreeColumn(
  threeColumnRules: ThreeColumnRule[],
  columns: string[],
  matrix1Columns: [string, string],
  matrix2Columns: [string, string]
): {
  matrix1ValidRules: validRange_Equality_Equality[];
  matrix2ValidRules: validRange_Equality_Equality[];
} {
  const matrix1ValidRules: validRange_Equality_Equality[] = [];
  const matrix2ValidRules: validRange_Equality_Equality[] = [];

  const safeRules = toPlainArray<ThreeColumnRule>(threeColumnRules);
  const safeColumns = toPlainArray<string>(columns);
  const flatRules = normalizeRules(safeRules, safeColumns);

  if (flatRules.length === 0) {
    return { matrix1ValidRules, matrix2ValidRules };
  }

  // Fix: Dynamically analyze mapping between matrix columns and global columns
  const matrix1Col1Index = safeColumns.indexOf(matrix1Columns[0]);
  const matrix1Col2Index = safeColumns.indexOf(matrix1Columns[1]);
  const matrix2Col1Index = safeColumns.indexOf(matrix2Columns[0]);
  const matrix2Col2Index = safeColumns.indexOf(matrix2Columns[1]);

  if (
    matrix1Col1Index === -1 ||
    matrix1Col2Index === -1 ||
    matrix2Col1Index === -1 ||
    matrix2Col2Index === -1
  ) {
    return { matrix1ValidRules, matrix2ValidRules };
  }

  // Group rules for matrix 1
  const matrix1Groups = new Map<string, Set<string>>();
  // Group rules for matrix 2
  const matrix2Groups = new Map<string, Set<string>>();

  flatRules.forEach((rule) => {
    // Get values for matrix 1
    const matrix1Key = rule[
      ["col1Value", "col2Value", "col3Value"][
        matrix1Col1Index
      ] as keyof SimpleThreeColumnRule
    ] as string;

    const matrix1Constraint = rule[
      ["col1Value", "col2Value", "col3Value"][
        matrix1Col2Index
      ] as keyof SimpleThreeColumnRule
    ] as string;

    if (!matrix1Groups.has(matrix1Key))
      matrix1Groups.set(matrix1Key, new Set());
    matrix1Groups.get(matrix1Key)!.add(matrix1Constraint);

    // Get values for matrix 2
    const matrix2Key = rule[
      ["col1Value", "col2Value", "col3Value"][
        matrix2Col1Index
      ] as keyof SimpleThreeColumnRule
    ] as string;

    const matrix2Constraint = rule[
      ["col1Value", "col2Value", "col3Value"][
        matrix2Col2Index
      ] as keyof SimpleThreeColumnRule
    ] as string;

    if (!matrix2Groups.has(matrix2Key))
      matrix2Groups.set(matrix2Key, new Set());
    matrix2Groups.get(matrix2Key)!.add(matrix2Constraint);
  });

  // Convert to validRange_Equality_Equality format
  matrix1Groups.forEach((col2Values, col1Value) => {
    matrix1ValidRules.push({
      conditionValue: col1Value,
      constraintValue: Array.from(col2Values),
    });
  });

  matrix2Groups.forEach((col2Values, col1Value) => {
    matrix2ValidRules.push({
      conditionValue: col1Value,
      constraintValue: Array.from(col2Values),
    });
  });

  return { matrix1ValidRules, matrix2ValidRules };
}

/**
 * Analyze cell data for three columns
 */
function analyzeCellThreeColumnData(
  csvData: Row[],
  allColumns: [string, string, string],
  matrixColumns: [string, string],
  category1: string,
  category2: string,
  invalidIndices: number[],
  flatRules: SimpleThreeColumnRule[]
): {
  validData: { [key: string]: Set<string> };
  invalidData: { [key: string]: Set<string> };
} {
  const [col1, col2, col3] = allColumns;
  const [matrixCol1, matrixCol2] = matrixColumns;

  const validData: { [key: string]: Set<string> } = {
    [col1]: new Set(),
    [col2]: new Set(),
    [col3]: new Set(),
  };

  const invalidData: { [key: string]: Set<string> } = {
    [col1]: new Set(),
    [col2]: new Set(),
    [col3]: new Set(),
  };

  csvData.forEach((row, index) => {
    const val1 = String(row[col1] || "")
      .toLowerCase()
      .trim();
    const val2 = String(row[col2] || "")
      .toLowerCase()
      .trim();
    const val3 = String(row[col3] || "")
      .toLowerCase()
      .trim();

    const isMatching =
      String(row[matrixCol1] || "")
        .toLowerCase()
        .trim() === category1.toLowerCase() &&
      String(row[matrixCol2] || "")
        .toLowerCase()
        .trim() === category2.toLowerCase();

    if (!isMatching || !val1 || !val2 || !val3) return;

    const isValidByRule = flatRules.some(
      (rule) =>
        rule.col1Value.toLowerCase() === val1 &&
        rule.col2Value.toLowerCase() === val2 &&
        rule.col3Value.toLowerCase() === val3
    );

    const isInvalidData = invalidIndices.includes(index);

    if (isValidByRule && !isInvalidData) {
      validData[col1].add(val1);
      validData[col2].add(val2);
      validData[col3].add(val3);
    } else if (isInvalidData || !isValidByRule) {
      invalidData[col1].add(val1);
      invalidData[col2].add(val2);
      invalidData[col3].add(val3);
    }
  });

  return { validData, invalidData };
}

/**
 * Analyze cell data for dynamic multi-column matrix
 */
function analyzeCellMultiColumnData(
  csvData: Row[],
  allColumns: string[],
  matrixColumns: [string, string],
  category1: string,
  category2: string,
  invalidIndices: number[],
  flatRules: SimpleMultiColumnRule[]
): {
  validData: { [key: string]: Set<string> };
  invalidData: { [key: string]: Set<string> };
} {
  const validData: { [key: string]: Set<string> } = {};
  const invalidData: { [key: string]: Set<string> } = {};

  allColumns.forEach((col) => {
    validData[col] = new Set();
    invalidData[col] = new Set();
  });

  const [matrixCol1, matrixCol2] = matrixColumns;

  csvData.forEach((row, index) => {
    const val1 = String(row[matrixCol1] || "")
      .toLowerCase()
      .trim();
    const val2 = String(row[matrixCol2] || "")
      .toLowerCase()
      .trim();

    if (val1 !== category1.toLowerCase() || val2 !== category2.toLowerCase())
      return;

    const isInvalid = invalidIndices.includes(index);

    const matchesRule = flatRules.some((rule) => {
      return allColumns.every((colName, colIdx) => {
        const ruleValue = String(rule.columnValues[colIdx] || "")
          .toLowerCase()
          .trim();
        const rowValue = String(row[colName] || "")
          .toLowerCase()
          .trim();
        return ruleValue === rowValue;
      });
    });

    const targetSet = matchesRule && !isInvalid ? validData : invalidData;
    allColumns.forEach((colName) => {
      const value = String(row[colName] || "")
        .toLowerCase()
        .trim();
      if (value) targetSet[colName].add(value);
    });
  });

  return { validData, invalidData };
}

/**
 * Generate tooltip template content
 */
function generateTooltipTemplate(
  cellData: {
    validData: { [key: string]: Set<string> };
    invalidData: { [key: string]: Set<string> };
  },
  columns: [string, string, string],
  cellType: string,
  ruleType: string // Default to MultipleCondition
): string {
  const { validData, invalidData } = cellData;

  const formatDataSet = (data: { [key: string]: Set<string> }): string => {
    const parts: string[] = [];
    columns.forEach((colName) => {
      const values = Array.from(data[colName] || new Set());
      if (values.length > 0) {
        const valueList =
          values.length > 1 ? `[${values.join(", ")}]` : values[0];
        parts.push(`<strong>${colName}</strong>: ${valueList}`);
      }
    });
    return `{${parts.join(", ")}}`;
  };

  let template = "";

  if (cellType === "valid") {
    const hasValidData = Object.values(validData).some((set) => set.size > 0);
    if (hasValidData) {
      const validDataStr = formatDataSet(validData);
      template = CONFIG.TOOLTIPS.getValidTemplate(validDataStr, ruleType);
    } else {
      template = CONFIG.TOOLTIPS.getNoValidData(ruleType);
    }
  } else if (cellType === "invalid") {
    const hasInvalidData = Object.values(invalidData).some(
      (set) => set.size > 0
    );
    if (hasInvalidData) {
      const invalidDataStr = formatDataSet(invalidData);
      template = CONFIG.TOOLTIPS.getInvalidTemplate(invalidDataStr, ruleType);
    } else {
      template = CONFIG.TOOLTIPS.getNoInvalidData(ruleType);
    }
  } else if (cellType === "conflict") {
    const parts: string[] = [];
    const hasValidData = Object.values(validData).some((set) => set.size > 0);
    const hasInvalidData = Object.values(invalidData).some(
      (set) => set.size > 0
    );

    if (hasValidData) {
      const validDataStr = formatDataSet(validData);
      parts.push(
        `${validDataStr} <strong style="color: ${CONFIG.COLORS.valid};">is valid</strong>`
      );
    }

    if (hasInvalidData) {
      const invalidDataStr = formatDataSet(invalidData);
      parts.push(
        `${invalidDataStr} <strong style="color: ${CONFIG.COLORS.invalid};">is invalid</strong>`
      );
    }

    template = CONFIG.TOOLTIPS.getConflictTemplate(parts, ruleType);
  } else {
    template = CONFIG.TOOLTIPS.getNoData(ruleType);
  }

  return template;
}

/**
 * Generate tooltip content for dynamic multi-column matrix
 */
function generateDynamicTooltipTemplate(
  cellData: {
    validData: { [key: string]: Set<string> };
    invalidData: { [key: string]: Set<string> };
  },
  columns: string[],
  cellType: string,
  ruleType: string
): string {
  const { validData, invalidData } = cellData;

  const formatDataSet = (data: { [key: string]: Set<string> }): string => {
    const parts: string[] = [];
    columns.forEach((colName) => {
      const values = Array.from(data[colName] || new Set());
      if (values.length > 0) {
        const valueList =
          values.length > 1 ? `[${values.join(", ")}]` : values[0];
        parts.push(`<strong>${colName}</strong>: ${valueList}`);
      }
    });
    return `{${parts.join(", ")}}`;
  };

  let template = "";

  if (cellType === "valid") {
    const hasValidData = Object.values(validData).some((set) => set.size > 0);
    if (hasValidData) {
      const validDataStr = formatDataSet(validData);
      template = CONFIG.TOOLTIPS.getValidTemplate(validDataStr, ruleType);
    } else {
      template = CONFIG.TOOLTIPS.getNoValidData(ruleType);
    }
  } else if (cellType === "invalid") {
    const hasInvalidData = Object.values(invalidData).some(
      (set) => set.size > 0
    );
    if (hasInvalidData) {
      const invalidDataStr = formatDataSet(invalidData);
      template = CONFIG.TOOLTIPS.getInvalidTemplate(invalidDataStr, ruleType);
    } else {
      template = CONFIG.TOOLTIPS.getNoInvalidData(ruleType);
    }
  } else if (cellType === "conflict") {
    const parts: string[] = [];
    const hasValidData = Object.values(validData).some((set) => set.size > 0);
    const hasInvalidData = Object.values(invalidData).some(
      (set) => set.size > 0
    );

    if (hasValidData) {
      const validDataStr = formatDataSet(validData);
      parts.push(
        `${validDataStr} <strong style="color: ${CONFIG.COLORS.valid};">is valid</strong>`
      );
    }

    if (hasInvalidData) {
      const invalidDataStr = formatDataSet(invalidData);
      parts.push(
        `${invalidDataStr} <strong style="color: ${CONFIG.COLORS.invalid};">is invalid</strong>`
      );
    }

    template = CONFIG.TOOLTIPS.getConflictTemplate(parts, ruleType);
  } else {
    template = CONFIG.TOOLTIPS.getNoData(ruleType);
  }

  return template;
}

/**
 * Hide all multi-matrix tooltips
 */
function hideAllMultipleMatrixTooltips(): void {
  d3.selectAll("foreignObject[id^='tooltip-']").style("visibility", "hidden");
  d3.selectAll("line")
    .filter(function () {
      const line = d3.select(this);
      return (
        line.attr("stroke") === CONFIG.TOOLTIP.stroke &&
        (line.attr("stroke-width") === CONFIG.TOOLTIP.strokeWidth ||
          line.attr("stroke-width") === "2" ||
          parseFloat(line.attr("stroke-width")) > 0) // Fix: Include all possible stroke-width values
      );
    })
    .style("visibility", "hidden");

  // Reset global variables
  currentTooltip = null;
  currentTooltipCell = null;
}

/**
 * Handle tooltip interaction
 */
function handleTooltipInteraction(
  tooltip: any,
  category1: string,
  category2: string,
  isValid = false,
  isConflict = false
): void {
  // Check if the same cell is clicked
  if (
    currentTooltip &&
    currentTooltipCell &&
    currentTooltipCell.category1 === category1 &&
    currentTooltipCell.category2 === category2
  ) {
    // Clicked the same location, hide tooltip
    hideAllMultipleMatrixTooltips();
    return;
  }

  // Hide all other tooltips
  hideAllMultipleMatrixTooltips();

  // Show current tooltip
  if (tooltip.tooltip_line_1) {
    tooltip.tooltip_line_1.style("visibility", "visible").raise();
  }
  if (tooltip.tooltip_line_2) {
    tooltip.tooltip_line_2.style("visibility", "visible").raise();
  }
  if (tooltip.inputBox) {
    tooltip.inputBox.style("visibility", "visible");
  }

  // Update global variables
  currentTooltip = tooltip;
  currentTooltipCell = { category1, category2 };
}

/**
 * Set up backward compatible event handlers
 */
function setupLegacyEventHandlers(
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  columns: string[]
) {
  const handleSafeHighlightEvent = (event: Event) => {
    const customEvent = event as CustomEvent;
    if (customEvent.detail) {
      const { rowIds, highlightColumns, sortedIndices } = customEvent.detail;
      updateHighlightedIndices(rowIds, highlightColumns);
    }
  };

  window.addEventListener(
    "safe-highlight-invalid-data",
    handleSafeHighlightEvent
  );
  return () => {
    window.removeEventListener(
      "safe-highlight-invalid-data",
      handleSafeHighlightEvent
    );
  };
}

/**
 * Analyze categories to highlight
 */
function analyzeHighlightCategories(
  csvData: Row[],
  rowIds: number[],
  columns: string[]
): Map<string, string[]> {
  const highlightCategories = new Map<string, string[]>();

  columns.forEach((column) => {
    highlightCategories.set(column, []);
  });

  rowIds.forEach((rowId) => {
    if (rowId >= 0 && rowId < csvData.length) {
      const row = csvData[rowId];
      if (row) {
        columns.forEach((column) => {
          const value = String(row[column] || "")
            .toLowerCase()
            .trim();
          if (value) {
            const categories = highlightCategories.get(column) || [];
            if (!categories.includes(value)) {
              categories.push(value);
            }
            highlightCategories.set(column, categories);
          }
        });
      }
    }
  });

  return highlightCategories;
}

/**
 * Get default edge configuration for matrix
 */
function getMatrixConfigById(
  matrixConfigs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }>,
  matrixId: string
) {
  return matrixConfigs.find((cfg) => cfg.id === matrixId);
}

// Return visible edges based on matrix configuration: category1 uses horizontal edges, category2 uses vertical edges
function getEdgesForCategory(
  config: { edges: string[] },
  categoryType: "category1" | "category2"
): string[] {
  const preferred =
    categoryType === "category1" ? ["bottom", "top"] : ["left", "right"];
  const filtered = config.edges.filter((e) => preferred.includes(e));
  return filtered.length > 0 ? filtered : config.edges;
}

/**
 * Create highlight state for specified matrix (dynamic multi-matrix version)
 */
function createHighlightStateForMatrixDynamic(
  matrixId: string,
  matrixConfigs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }>,
  highlightCategories: Map<string, string[]>
): HighlightState {
  const highlightState: HighlightState = {
    matrixId,
    category1Highlights: [],
    category2Highlights: [],
    cellHighlights: [],
  };

  const config = getMatrixConfigById(matrixConfigs, matrixId);
  if (!config) return highlightState;

  const [col1, col2] = config.columns;

  const col1Categories = highlightCategories.get(col1) || [];
  col1Categories.forEach((category) => {
    highlightState.category1Highlights.push({
      category,
      color: CONFIG.COLORS.highlight,
      edges: getEdgesForCategory(config, "category1"),
    });
  });

  const col2Categories = highlightCategories.get(col2) || [];
  col2Categories.forEach((category) => {
    highlightState.category2Highlights.push({
      category,
      color: CONFIG.COLORS.highlight,
      edges: getEdgesForCategory(config, "category2"),
    });
  });

  return highlightState;
}

/**
 * Set up multi-matrix interactions
 */
function setupMultipleMatrixInteractions(
  containerGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  columns: string[],
  manager: MultipleMatrixManager,
  csvData: Row[],
  direction: "right" | "top" = "right",
  matrixConfigs: Array<{
    id: string;
    columns: [string, string];
    edges: string[];
  }>
) {
  const safeColumns = toPlainArray<string>(columns);
  const safeCsvData = toPlainArray<Row>(csvData);

  const handleHighlightInvalidData = (event: Event) => {
    const customEvent = event as CustomEvent;

    try {
      if (customEvent.detail) {
        const {
          rowIds,
          highlightColumns,
          sortedIndices,
          isRightClick,
          isFromMatrixClick,
          isFromBarClick,
          isClearEvent,
          cellType, // New: get cellType info
        } = customEvent.detail;

        if (isClearEvent) {
          const safeEvent = new CustomEvent("safe-highlight-invalid-data", {
            detail: {
              rowIds: [],
              highlightColumns: [],
              sortedIndices: [],
              isRightClick: false,
              isFromMultipleMatrix: true,
              isFromBarClick: true,
              isClearEvent: true,
            },
          });
          window.dispatchEvent(safeEvent);
          return;
        }

        const safeRowIds = toPlainArray<number>(rowIds);
        const safeHighlightColumns = toPlainArray<string>(highlightColumns);
        const safeSortedIndices = toPlainArray<number>(sortedIndices);
        const finalSortedIndices =
          safeSortedIndices.length > 0 ? safeSortedIndices : safeRowIds;

        if (isFromMatrixClick || isFromBarClick) {
          const eventDetail = {
            rowIds: safeRowIds,
            highlightColumns: safeHighlightColumns,
            sortedIndices: finalSortedIndices,
            isRightClick: !!isRightClick,
            isFromMultipleMatrix: true,
            isFromMatrixClick: !!isFromMatrixClick,
            isFromBarClick: !!isFromBarClick,
            isClearEvent: !!isClearEvent,
            cellType: cellType,
          };

          const safeEvent = new CustomEvent("safe-highlight-invalid-data", {
            detail: eventDetail,
          });
          window.dispatchEvent(safeEvent);
          return;
        }

        if (manager && safeRowIds.length > 0) {
          const highlightCategories = analyzeHighlightCategories(
            safeCsvData,
            safeRowIds,
            safeColumns
          );

          manager.getRegisteredMatrices().forEach((matrixId) => {
            const highlightState = createHighlightStateForMatrixDynamic(
              matrixId,
              matrixConfigs,
              highlightCategories
            );
            manager.updateMatrixHighlights(matrixId, highlightState);
          });
        } else {
          if (manager) manager.hideAllLabels();
        }

        const eventDetail = {
          rowIds: safeRowIds,
          highlightColumns: safeHighlightColumns,
          sortedIndices: finalSortedIndices,
          isRightClick: !!isRightClick,
          isFromMultipleMatrix: true,
          cellType: cellType,
        };

        const safeEvent = new CustomEvent("safe-highlight-invalid-data", {
          detail: eventDetail,
        });
        window.dispatchEvent(safeEvent);
      } else {
        if (manager) manager.hideAllLabels();

        const emptyEvent = new CustomEvent("safe-highlight-invalid-data", {
          detail: {
            rowIds: [],
            highlightColumns: [],
            sortedIndices: [],
            isRightClick: false,
            isFromMultipleMatrix: true,
          },
        });
        window.dispatchEvent(emptyEvent);
      }
    } catch (error) {
      // Error handling intentionally silent or minimal
    }
  };
}

/**
 * Set up tooltips for a single matrix
 */
function setupMatrixTooltips(
  matrixGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  matrixColumns: [string, string],
  allColumns: [string, string, string],
  invalidIndices: number[],
  flatRules: SimpleThreeColumnRule[],
  matrixId: string,
  ruleType: string,
  scaleRatio = 1
): void {
  const [col1, col2, col3] = allColumns;
  const [matrixCol1, matrixCol2] = matrixColumns;

  const matrixCells = matrixGroup.selectAll("rect[id='matrix']");

  matrixCells.each(function () {
    const cell = d3.select(this);
    const category1 = cell.attr("data-category1");
    const category2 = cell.attr("data-category2");
    const cellType = cell.attr("data-cell-type") || "invalid";

    if (!category1 || !category2) return;

    const rectX = parseFloat(cell.attr("x"));
    const rectY = parseFloat(cell.attr("y"));
    const rectWidth = parseFloat(cell.attr("width"));
    const rectHeight = parseFloat(cell.attr("height"));

    const cellData = analyzeCellThreeColumnData(
      csvData,
      allColumns,
      matrixColumns,
      category1,
      category2,
      invalidIndices,
      flatRules
    );

    const tooltipTemplate = generateTooltipTemplate(
      cellData,
      allColumns,
      cellType,
      ruleType
    );

    const tooltip = createTooltip(
      matrixGroup,
      rectX,
      rectY,
      0,
      0,
      rectWidth,
      tooltipTemplate,
      allColumns,
      ruleType,
      `${category1}-${category2}`,
      scaleRatio
    );

    const originalClickHandler = cell.on("click");
    const originalContextMenuHandler = cell.on("contextmenu");

    cell.on("click", function (event, d) {
      if (originalClickHandler) {
        originalClickHandler.call(this, event, d);
      }

      setTimeout(() => {
        handleTooltipInteraction(
          tooltip,
          category1,
          category2,
          cellType === "valid",
          cellType === "conflict"
        );
      }, 50);
    });

    cell.on("contextmenu", function (event, d) {
      event.preventDefault();

      if (originalContextMenuHandler) {
        originalContextMenuHandler.call(this, event, d);
      }

      setTimeout(() => {
        handleTooltipInteraction(
          tooltip,
          category1,
          category2,
          cellType === "valid",
          cellType === "conflict"
        );
      }, 50);
    });
  });
}

/**
 * Set up global click listener to handle tooltip hiding
 */
function setupGlobalClickHandler(
  containerGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>
): () => void {
  // Listen for click events on document
  const globalClickHandler = (event: MouseEvent) => {
    // Check if click is inside matrix container
    const containerNode = containerGroup.node();
    if (!containerNode) return;

    // Check if click target is a matrix cell or tooltip element
    const target = event.target as Element;
    const isMatrixCell =
      target && target.closest && target.closest("rect[id='matrix']");
    const isTooltipElement =
      target &&
      target.closest &&
      (target.closest("foreignObject[id^='tooltip-']") ||
        target.closest("line[stroke='black']"));

    // If click is not on a matrix cell or tooltip element, hide all tooltips
    if (!isMatrixCell && !isTooltipElement) {
      hideAllMultipleMatrixTooltips();
    }
  };

  // Add global click listener
  document.addEventListener("click", globalClickHandler);

  // Return cleanup function
  return () => {
    document.removeEventListener("click", globalClickHandler);
  };
}

/**
 * Render multi-matrix visualization for multi-column dependency
 * Supports 3 or more columns, generating N-1 matrices for N columns
 */
export async function multiple_matrix(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumns: string[],
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  invalidIndices: number[],
  multiColumnRules: (ThreeColumnRule | MultiColumnRule)[],
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  ruleType: string,
  scaleRatio = 1,
  direction: "right" | "top" = "top"
): Promise<void> {
  const safeCsvData = toPlainArray<Row>(csvData);
  const safeSelectedColumns = toPlainArray<string>(selectedColumns);
  const safeInvalidIndices = toPlainArray<number>(invalidIndices);
  const safeMultiColumnRules = toPlainArray<ThreeColumnRule | MultiColumnRule>(
    multiColumnRules
  );

  // Validate input
  if (safeCsvData.length === 0) {
    throw new Error("csvData must be a valid non-empty array");
  }

  if (safeSelectedColumns.length < 3) {
    throw new Error(
      `Multiple matrix requires at least 3 columns, got ${safeSelectedColumns.length}`
    );
  }

  const numColumns = safeSelectedColumns.length;

  try {
    // Show loading animation
    const loadingGroup = svg.append("g").attr("class", "loading-animation");
    createLoadingAnimation(loadingGroup, width, height);

    // 1. Normalize rules
    const flatRules = normalizeRules(safeMultiColumnRules, safeSelectedColumns);

    // 2. Generate matrix configurations (N-1 matrices for N columns)
    const matrixConfigs = generateMatrixConfigsForMultipleMatrix(
      safeSelectedColumns,
      direction
    );

    // 3. Generate valid rules for each matrix
    const matrixValidRulesMap = generateValidRulesForMultipleMatrices(
      flatRules,
      safeSelectedColumns,
      matrixConfigs
    );

    // 4. Analyze conflict areas for each matrix
    const matrixConflictsMap = analyzeConflictAreasForMultipleMatrices(
      safeCsvData,
      safeSelectedColumns,
      flatRules,
      safeInvalidIndices,
      matrixConfigs
    );

    // 5. Create event bus and manager
    const eventBus = new MatrixEventBus();
    const manager = new MultipleMatrixManager(
      eventBus,
      safeSelectedColumns,
      safeCsvData
    );
    manager.setInvalidIndices(safeInvalidIndices);

    // 6. Create container group
    const containerGroup = svg
      .append("g")
      .attr("class", "multiple-matrix-container")
      .style("opacity", 0);

    // 7. Create all matrix instances
    const matrixInstances = new Map<string, any>();
    const matrixGroups = new Map<string, any>();

    for (const config of matrixConfigs) {
      const matrixGroup = containerGroup
        .append("g")
        .attr("class", `matrix-group ${config.id}`);

      matrixGroups.set(config.id, matrixGroup);

      const matrixConfig: MatrixRenderConfig = {
        data: safeCsvData,
        columns: config.columns,
        position: config.id,
        validRules: matrixValidRulesMap.get(config.id) || [],
        conflictAreas: matrixConflictsMap.get(config.id) || [],
        invalidIndices: safeInvalidIndices,
        ruleType: "multiple logical and condition",
        edges: config.edges,
        rotationAngle: 0,
      };

      const instance = await renderMatrixCore(
        matrixGroup,
        matrixConfig,
        eventBus
      );

      if (instance) {
        matrixInstances.set(config.id, instance);
        manager.registerMatrix(config.id, instance);
      }
    }

    // 8. Calculate and apply layout
    const layout = calculateMultipleMatricesLayout(
      matrixInstances,
      matrixConfigs,
      direction,
      CONFIG.MULTIPLE_MATRIX.spacing,
      CONFIG.MULTIPLE_MATRIX.edgeChartHeight
    );

    if (layout) {
      // Apply positions
      layout.positions.forEach((pos, matrixId) => {
        const group = matrixGroups.get(matrixId);
        if (group) {
          group.attr("transform", `translate(${pos.x}, ${pos.y})`);
        }
      });

      // 9. Calculate overall scale and centering
      const availableWidth = width + margin.left + margin.right;
      const availableHeight = height + margin.top + margin.bottom;
      const rotationAngle = CONFIG.MULTIPLE_MATRIX.rotationAngle;
      const radians = (rotationAngle * Math.PI) / 180;
      const cos = Math.abs(Math.cos(radians));
      const sin = Math.abs(Math.sin(radians));

      const rotatedWidth =
        layout.totalBounds.width * cos + layout.totalBounds.height * sin;
      const rotatedHeight =
        layout.totalBounds.width * sin + layout.totalBounds.height * cos;

      const scaleX = availableWidth / rotatedWidth;
      const scaleY = availableHeight / rotatedHeight;
      const rawScale = Math.min(scaleX, scaleY);

      // Prefer filling ~90% of the viewport so tiny systems stay legible
      const targetFillScale = Math.min(
        (availableWidth * 0.9) / rotatedWidth,
        (availableHeight * 0.9) / rotatedHeight
      );

      const scale = Math.min(
        CONFIG.MULTIPLE_MATRIX.maxScale || 2,
        Math.max(
          CONFIG.MULTIPLE_MATRIX.minScale || 0.6,
          Math.max(rawScale, targetFillScale)
        )
      );

      const centerX = layout.totalBounds.minX + layout.totalBounds.width / 2;
      const centerY = layout.totalBounds.minY + layout.totalBounds.height / 2;

      const targetX = availableWidth / 2;
      const targetY = availableHeight / 2;
      const translateX = targetX - centerX * scale;
      const translateY = targetY - centerY * scale;

      const transformString = `translate(${translateX}, ${translateY}) scale(${scale}) rotate(${rotationAngle}, ${centerX}, ${centerY})`;
      containerGroup.attr("transform", transformString);

      // 10. Remove loading animation and show matrix
      loadingGroup.remove();
      containerGroup
        .transition()
        .duration(CONFIG.ANIMATION.duration)
        .style("opacity", 1);

      // 11. Delayed setup for interaction (wait for animation)
      setTimeout(() => {
        // Set up tooltips (if needed)
        setupMultipleMatrixTooltipsForDynamic(
          containerGroup,
          safeCsvData,
          safeSelectedColumns,
          safeInvalidIndices,
          flatRules,
          matrixInstances,
          matrixConfigs,
          ruleType,
          scale
        );

        // Set up global click handler
        setupGlobalClickHandler(containerGroup);
      }, 600);
    }

    // 12. Set up event handlers
    setupLegacyEventHandlers(updateHighlightedIndices, safeSelectedColumns);
    setupMultipleMatrixInteractions(
      containerGroup,
      safeSelectedColumns,
      manager,
      safeCsvData,
      direction,
      matrixConfigs
    );
  } catch (error) {
    console.error("Error in multiple_matrix:", error);
    throw error;
  }
}
