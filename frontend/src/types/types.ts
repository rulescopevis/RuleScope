import * as d3 from "d3";

// 数据行定义
export type Row = Record<string, string | number | undefined>;
export const icon_x = -40;
// 解析后的csv文件定义
export interface ParsedCSV {
  csvData: Row[];
  headers: string[];
}

export interface ConstraintMap {
  [key: string]: string[];
}

export type SortOrder = "asc" | "desc";

export interface SortCondition {
  columnName: string;
  order: SortOrder;
}

export interface CellPosition {
  rowIndex: number;
  colIndex: number;
}

export interface RelationItem {
  object1: CellPosition;
  relationContent: string;
  object2: CellPosition;
  columns: string;
  allRelations: string[];
}

export interface invalidRange_Equality_Range {
  conditionContent: string;
  start: number;
  startInclusive: boolean;
  end: number;
  endInclusive: boolean;
}

export interface validRange_Equality_Equality {
  conditionValue: string;
  constraintValue: string[] | null;
}

export interface invalidRange_Compare_Numeric {
  compareRelation: string;
}

export interface invalidRange_Difference {
  start: number;
  startInclusive: boolean;
  end: number;
  endInclusive: boolean;
}

export interface ValidationCard {
  columnName: string[];
  columnType: string[];
  displayColumnOrder?: string[];
  relationClass: string;
  relationType: string;
  ruleValue: any;
  constraintType?: string[];
  ifConflict: number;
  example?: string;
  invalid_index?: number[];
  invalid_range?:
    | invalidRange_Equality_Range[]
    | validRange_Equality_Equality[]
    | invalidRange_Compare_Numeric
    | invalidRange_Difference;
  invalid_pairs?: {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[];
  valid_pairs?: {
    currentIndex: number;
    nextIndex: number;
    sortCurrentIndex: number;
    sortNextIndex: number;
  }[];
  sort_conditions?: SortCondition[];
  sortedIndices?: number[];
  threeColumnRules?: any[];
  multiColumnRules?: any[];
}

export interface SequenceRule {
  columnName: string;
  value: string;
  allowed_next: string[];
}

export interface ConstraintValue {
  start: number;
  end: number;
  startInclusive: boolean;
  endInclusive: boolean;
}

export interface ConditionRule {
  columnName: string;
  conditionValue: string;
  constraintValue: ConstraintValue;
}

export type ColumnType =
  | "datetime"
  | "numeric"
  | "character"
  | "mixed"
  | "bool"
  | "unknown";

export type FetchedColumnTypes = {
  [columnName: string]: { type: ColumnType };
};

export interface GridInvalidInfo {
  count: number;
  category1: string;
  category2: string;
  indices: number[];
}

export interface SelectInfo {
  columnList: string[];
  indexList: number[];
  conditionIndexList?: number[];
}

export interface RefineResult {
  refineStatus: boolean;
  refineDict: {
    addRules: any[];
    deleteRules: any[];
    updateRules: any[];
  };
}

export type EventListener = (event: Event) => void;

export interface MatrixRenderConfig {
  data: Row[];
  columns: [string, string];
  position: string;
  validRules: validRange_Equality_Equality[];
  conflictAreas: ConflictArea[];
  invalidIndices: number[];
  ruleType: string;
  edges: string[];
  rotationAngle?: number;
}

type EventCallback<T = any> = (data: T) => void;

export interface HighlightState {
  matrixId: string;
  category1Highlights: {
    category: string;
    color: string;
    edges: string[];
  }[];
  category2Highlights: {
    category: string;
    color: string;
    edges: string[];
  }[];
  cellHighlights: {
    category1: string;
    category2: string;
    color: string;
  }[];
}

export interface MatrixEvent {
  type: "cell-click" | "cell-hover" | "highlight-update";
  matrixId: string;
  data: any;
}

export interface CellClickEvent {
  matrixId: string;
  category1: string;
  category2: string;
  cellType: "valid" | "invalid" | "conflict";
  isRightClick: boolean;
  rowIds: number[];
  sortedIndices: number[];
}

export interface CrossMatrixHighlightEvent {
  sourceMatrixId: string;
  category1: string;
  category2: string;
  highlightType: "primary" | "secondary" | "conflict";
  isRightClick: boolean;
  relatedData?: {
    rowIds: number[];
    sortedIndices: number[];
  };
}

export interface MatrixInstance {
  id: string;
  config: MatrixRenderConfig;
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>;
  updateHighlights(highlights: HighlightState): void;
  getRelatedCategories(
    category1: string,
    category2: string
  ): {
    relatedInMatrix1: string[];
    relatedInMatrix2: string[];
  };
  handleCrossMatrixHighlight(event: CrossMatrixHighlightEvent): void;
  clearHighlights(): void;
  getDimensions(): {
    matrixWidth: number;
    matrixHeight: number;
    barHeight: number;
    barWidth: number;
    totalWidth: number;
    totalHeight: number;
  };
}

export class MatrixEventBus {
  private listeners: Map<string, EventCallback[]> = new Map();

  on<T = any>(eventType: string, callback: EventCallback<T>) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(callback);
  }

  emit<T = any>(eventType: string, data: T) {
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      callbacks.forEach((callback) => callback(data));
    }
  }

  off<T = any>(eventType: string, callback: EventCallback<T>) {
    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }
}

export interface MatrixDimensions {
  divisions_left: number;
  divisions_right: number;
  subSquareLength_left: number;
  subSquareLength_right: number;
  matrixWidth: number;
  matrixHeight: number;
}

export interface CategoryData {
  column1_categories: any[];
  column1_x: any;
  column2_categories: any[];
  column2_x: any;
  column1_barHeights?: Record<string, number>;
  column2_barHeights?: Record<string, number>;
}

export interface ConflictArea {
  category1: string;
  category2: string;
  conflictType: "both" | "partial";
}

export type EdgePosition = "bottom" | "right" | "top" | "left";

export type EdgeGroups = {
  [K in EdgePosition]: d3.Selection<SVGGElement, unknown, HTMLElement, any>;
};
export type ChartGroups = {
  [K in EdgePosition]?: d3.Selection<SVGGElement, unknown, HTMLElement, any>;
};

export interface EdgeLabelInfo {
  edge: EdgePosition;
  category: string;
  value: string;
  x: number;
  y: number;
  anchor: string;
  baseline: string;
}

export interface ColumnBasedRule {
  [columnName: string]: string[];
}

export interface SimpleThreeColumnRule {
  col1Value: string;
  col2Value: string;
  col3Value: string;
}

export type ThreeColumnRule = ColumnBasedRule | SimpleThreeColumnRule;

export interface SimpleMultiColumnRule {
  columnValues: string[];
}

export type MultiColumnRule = ColumnBasedRule | SimpleMultiColumnRule;

export interface MatrixConfig {
  id: string;
  columns: [string, string];
  edges: string[];
  position: { x: number; y: number };
}
