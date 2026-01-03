import {
  invalidRange_Difference,
  invalidRange_Compare_Numeric,
  Row,
  EdgePosition,
  ColumnType,
} from "@/types/types";
import * as d3 from "d3";
import { renderNumericChart } from "./numeric";
import { renderDateChart } from "./date";
import { createLoadingAnimation } from "@/utils/utils";
import { createTooltip } from "@/utils/tootips";

type GeneralInvalidRange =
  | invalidRange_Difference
  | invalidRange_Compare_Numeric;

type EdgeGroups = {
  [K in EdgePosition]: d3.Selection<SVGGElement, unknown, HTMLElement, any>;
};

type ChartGroups = {
  [K in EdgePosition]?: d3.Selection<SVGGElement, unknown, HTMLElement, any>;
};

interface TooltipState {
  box: d3.Selection<HTMLElement, unknown, null, undefined>;
  lines: {
    line1: d3.Selection<SVGLineElement, unknown, HTMLElement, any>;
    line2: d3.Selection<SVGLineElement, unknown, HTMLElement, any>;
  };
}

interface DataRange {
  x_min: number;
  x_max: number;
}

interface InvalidPairData {
  currentIndex: number;
  nextIndex: number;
  sortCurrentIndex: number;
  sortNextIndex: number;
}

const NUMERIC_MATRIX_CONFIG = {
  colors: {
    matrixStroke: "#9a9a9a",
    matrixFill: "white",
    areaFill: "#4570b6",
    highlightRectFill: "#fd8d3c",
    highlightRectOpacity: 0.3,
    highlightLabelFill: "black",
    invalidPointFill: "#fd8d3c",
    invalidPointOpacity: 0.6,
  },
  dimensions: {
    matrixSize: 540,
    edgeChartHeight: 180,
    edgeOffset: 10,
    highlightLabelOffset: 20,
    subSquareDivisor: 20,
    pointRadiusDivisor: 6,
    borderStrokeWidth: 1.5,
  },
  transforms: {
    initialContainer: "translate(0, 0)",
    highlightLabelRotate: -45,
  },
  animation: {
    fadeInDuration: 500,
    finalPadding: 0.9,
  },
  ruleTypes: {
    difference: "difference",
    compare: "compare",
  },
  tooltips: {
    getDifferenceAreaTemplate: (
      columnName: string,
      range: invalidRange_Difference
    ): string =>
      `Difference between adjacent values in <strong style="color: black;">${columnName}</strong> should be within <strong style="color: red;">${
        range.startInclusive ? "[" : "("
      }${range.start},${range.end}${range.endInclusive ? "]" : ")"}</strong>.`,
    getCompareAreaTemplate: (columns: string[], compareType: string): string =>
      `The value in <strong style="color: black">${columns[0]}</strong> should be <strong style="color: red">${compareType}</strong> the value in <strong style="color: black">${columns[1]}</strong>.`,
    getDifferencePointTemplate: (
      columnName: string,
      val1: number,
      val2: number
    ): string =>
      `The difference between consecutive values in <strong style="color: black;">${columnName}</strong> cannot be <strong style="color: red;">${(
        val2 - val1
      ).toFixed(2)}</strong>.`,
    getComparePointTemplate: (
      columns: string[],
      compareType: string,
      formattedVal1: string,
      formattedVal2: string
    ): string =>
      `Rule: the value in <strong style="color: black;">${columns[0]}</strong> must be <strong style="color: red;">${compareType}</strong> the value in <strong style="color: black;">${columns[1]}</strong>.<br/>Current values — <strong style="color: black;">${columns[0]}:</strong> <strong style="color: red;">${formattedVal1}</strong>, <strong style="color: black;">${columns[1]}:</strong> <strong style="color: red;">${formattedVal2}</strong>.`,
  },
};

const DATE_LABEL_FORMAT = d3.timeFormat("%Y-%m-%d");

function isDateType(type?: ColumnType): boolean {
  return type === "datetime";
}

function toComparableValue(
  value: string | number | undefined,
  type?: ColumnType
): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  if (isDateType(type)) {
    const dateValue =
      typeof value === "number" ? new Date(value) : new Date(String(value));
    const timestamp = dateValue.getTime();
    return Number.isNaN(timestamp) ? null : timestamp;
  }

  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function formatValueLabel(value: number, type?: ColumnType): string {
  if (isDateType(type)) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "--" : DATE_LABEL_FORMAT(date);
  }

  return Number.isFinite(value) ? value.toFixed(2) : "--";
}

interface DataPoint {
  x: number;
  y: number;
}

const DIAGONAL_EPSILON = 1e-6;

function isGreaterComparison(compareType: string): boolean {
  return compareType === "larger" || compareType === "larger_equal";
}

function isPointInsideHalfPlane(
  point: DataPoint,
  compareType: string
): boolean {
  return isGreaterComparison(compareType)
    ? point.x >= point.y - DIAGONAL_EPSILON
    : point.x <= point.y + DIAGONAL_EPSILON;
}

function computeDiagonalIntersection(
  p1: DataPoint,
  p2: DataPoint
): DataPoint | null {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const denominator = dx - dy;

  if (Math.abs(denominator) < DIAGONAL_EPSILON) {
    return null;
  }

  const t = (p1.y - p1.x) / denominator;
  if (t < 0 || t > 1) {
    return null;
  }

  return {
    x: p1.x + t * dx,
    y: p1.y + t * dy,
  };
}

function clipRectangleWithDiagonal(
  rectangle: DataPoint[],
  compareType: string
): DataPoint[] {
  const clipped: DataPoint[] = [];
  const length = rectangle.length;

  for (let i = 0; i < length; i++) {
    const current = rectangle[i];
    const previous = rectangle[(i - 1 + length) % length];
    const currentInside = isPointInsideHalfPlane(current, compareType);
    const previousInside = isPointInsideHalfPlane(previous, compareType);

    if (currentInside) {
      if (!previousInside) {
        const intersection = computeDiagonalIntersection(previous, current);
        if (intersection) {
          clipped.push(intersection);
        }
      }
      clipped.push(current);
    } else if (previousInside) {
      const intersection = computeDiagonalIntersection(previous, current);
      if (intersection) {
        clipped.push(intersection);
      }
    }
  }

  return clipped;
}

function createRectangleCorners(ranges: {
  x1_min: number;
  x1_max: number;
  x2_min: number;
  x2_max: number;
}): DataPoint[] {
  return [
    { x: ranges.x1_min, y: ranges.x2_min },
    { x: ranges.x1_min, y: ranges.x2_max },
    { x: ranges.x1_max, y: ranges.x2_max },
    { x: ranges.x1_max, y: ranges.x2_min },
  ];
}

/**
 * Create chart groups on the four edges and apply positioning transforms.
 * @param edgeGroups Parent edge groups container.
 * @param edges Edge positions to render (e.g., top, right).
 * @param matrixParams Matrix origin and size.
 * @param chartHeight Height of the edge charts.
 * @returns A map of created chart groups keyed by edge.
 */
function createChartGroups(
  edgeGroups: EdgeGroups,
  edges: string[],
  matrixParams: { x_start: number; y_start: number; s_length: number },
  chartHeight: number
): ChartGroups {
  const { x_start, y_start, s_length } = matrixParams;
  const { edgeOffset } = NUMERIC_MATRIX_CONFIG.dimensions;

  const chartGroups: ChartGroups = {};
  const transforms = {
    bottom: `translate(${x_start}, ${y_start + s_length + edgeOffset})`,
    right: `translate(${x_start + s_length + edgeOffset}, ${
      y_start + s_length
    }) rotate(-90)`,
    top: `translate(${x_start}, ${y_start - chartHeight - edgeOffset})`,
    left: `translate(${x_start - chartHeight - edgeOffset}, ${
      y_start + s_length
    }) rotate(-90)`,
  };

  edges.forEach((edge) => {
    if (transforms[edge as EdgePosition]) {
      chartGroups[edge as EdgePosition] = edgeGroups[edge as EdgePosition]
        .append("g")
        .attr("transform", transforms[edge as EdgePosition]);
    }
  });

  return chartGroups;
}

/**
 * Render edge charts and return their data ranges.
 * @param chartGroups Edge chart groups.
 * @param edges Edge positions to render.
 * @param ruleType Rule type: difference or compare.
 * @param csvData Input rows.
 * @param selectedColumns Columns used for charting.
 * @param chartWidth Chart width in pixels.
 * @param chartHeight Chart height in pixels.
 * @param margin Chart margin config.
 * @param updateHighlightedIndices Callback to highlight indices.
 * @param columnTypes Optional column types for formatting.
 */
async function renderEdgeCharts(
  chartGroups: ChartGroups,
  edges: string[],
  ruleType: string,
  csvData: Row[],
  selectedColumns: string[],
  chartWidth: number,
  chartHeight: number,
  margin: { top: number; right: number; bottom: number; left: number },
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  columnTypes: ColumnType[] = []
): Promise<{
  x_min: number;
  x_max: number;
  x1_min: number;
  x1_max: number;
  x2_min: number;
  x2_max: number;
}> {
  let x_min = 0,
    x_max = 0;
  let x1_min = 0,
    x1_max = 0,
    x2_min = 0,
    x2_max = 0;
  let rangeIsSet = false;

  const setRange = (range: DataRange) => {
    if (!rangeIsSet) {
      x_min = range.x_min;
      x_max = range.x_max;
      rangeIsSet = true;
    }
  };

  if (ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.difference) {
    const columnName = selectedColumns[0];
    const columnType = columnTypes[0] || "numeric";
    for (const edge of edges) {
      const chartGroup = chartGroups[edge as EdgePosition];
      if (chartGroup) {
        const range = isDateType(columnType)
          ? await renderDateChart(
              chartGroup,
              csvData,
              columnName,
              chartWidth,
              chartHeight,
              margin,
              updateHighlightedIndices,
              true
            )
          : await renderNumericChart(
              chartGroup,
              csvData,
              columnName,
              chartWidth,
              chartHeight,
              margin,
              updateHighlightedIndices,
              true
            );
        if (range) {
          setRange(range);
        }
      }
    }
  } else if (
    ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.compare
  ) {
    for (const edge of ["bottom", "top"]) {
      if (edges.includes(edge) && chartGroups[edge as EdgePosition]) {
        const columnType = columnTypes[0] || "numeric";
        const range = isDateType(columnType)
          ? await renderDateChart(
              chartGroups[edge as EdgePosition]!,
              csvData,
              selectedColumns[0],
              chartWidth,
              chartHeight,
              margin,
              updateHighlightedIndices,
              true
            )
          : await renderNumericChart(
              chartGroups[edge as EdgePosition]!,
              csvData,
              selectedColumns[0],
              chartWidth,
              chartHeight,
              margin,
              updateHighlightedIndices,
              true
            );
        if (edge === "bottom") {
          x1_min = range?.x_min ?? 0;
          x1_max = range?.x_max ?? 0;
        }
      }
    }
    for (const edge of ["right", "left"]) {
      if (edges.includes(edge) && chartGroups[edge as EdgePosition]) {
        const columnType = columnTypes[1] || "numeric";
        const range = isDateType(columnType)
          ? await renderDateChart(
              chartGroups[edge as EdgePosition]!,
              csvData,
              selectedColumns[1],
              chartWidth,
              chartHeight,
              margin,
              updateHighlightedIndices,
              true
            )
          : await renderNumericChart(
              chartGroups[edge as EdgePosition]!,
              csvData,
              selectedColumns[1],
              chartWidth,
              chartHeight,
              margin,
              updateHighlightedIndices,
              true
            );
        if (edge === "right") {
          x2_min = range?.x_min ?? 0;
          x2_max = range?.x_max ?? 0;
        }
      }
    }
  }

  return { x_min, x_max, x1_min, x1_max, x2_min, x2_max };
}

/**
 * Add a rotated highlight label to a group.
 * @param group Target SVG group.
 * @param x X position.
 * @param y Y position.
 * @param text Label text.
 * @param anchor Text anchor alignment.
 */
function createHighlightLabel(
  group: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  x: number,
  y: number,
  text: string,
  anchor = "end"
): d3.Selection<SVGTextElement, unknown, HTMLElement, any> {
  return group
    .append("text")
    .attr("class", "highlight-label")
    .attr("x", x)
    .attr("y", y)
    .attr("text-anchor", anchor)
    .attr("fill", NUMERIC_MATRIX_CONFIG.colors.highlightLabelFill)
    .attr(
      "transform",
      `rotate(${NUMERIC_MATRIX_CONFIG.transforms.highlightLabelRotate}, ${x}, ${y})`
    )
    .text(text);
}

/**
 * Add a highlight bar and label on an edge chart.
 * @param chartGroup Edge chart group.
 * @param labelGroup Group to host the label.
 * @param value Value to highlight.
 * @param range Data range for scaling.
 * @param width Chart width.
 * @param height Chart height.
 * @param labelPosition Label coordinates and anchor.
 * @param columnType Column type for formatting.
 */
function addHighlightElements(
  chartGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any> | undefined,
  labelGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  value: number,
  range: DataRange,
  width: number,
  height: number,
  labelPosition: {
    x: number;
    y: number;
    anchor: string;
  },
  columnType: ColumnType = "numeric"
): void {
  if (!chartGroup) return;

  const rangeWidth = Math.max(2, width * 0.02);
  const denominator = range.x_max - range.x_min || 1;
  const rangeX = ((value - range.x_min) / denominator) * width;

  chartGroup
    .append("rect")
    .attr("class", "highlight-range")
    .attr("x", rangeX - rangeWidth / 2)
    .attr("y", 0)
    .attr("width", rangeWidth)
    .attr("height", height)
    .attr("fill", NUMERIC_MATRIX_CONFIG.colors.highlightRectFill)
    .attr("opacity", NUMERIC_MATRIX_CONFIG.colors.highlightRectOpacity);

  createHighlightLabel(
    labelGroup,
    labelPosition.x,
    labelPosition.y,
    formatValueLabel(value, columnType),
    labelPosition.anchor
  );
}

/**
 * Remove all highlight bars and labels.
 * @param chartGroups Edge chart groups.
 * @param edgeGroups Edge container groups.
 * @param containerGroup Main container group.
 * @param edges Edge positions to clear.
 * @param ruleType Current rule type.
 */
function removeAllHighlights(
  chartGroups: ChartGroups,
  edgeGroups: EdgeGroups,
  containerGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  edges: string[],
  ruleType: string
): void {
  edges.forEach((edge) => {
    const chartGroup = chartGroups[edge as EdgePosition];
    const edgeGroup = edgeGroups[edge as EdgePosition];

    if (chartGroup) {
      chartGroup.selectAll(".highlight-range").remove();
    }
    if (edgeGroup) {
      edgeGroup.selectAll(".highlight-label").remove();
    }
  });

  if (ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.compare) {
    containerGroup.selectAll(".highlight-label").remove();
  }
}

/**
 * Centralize tooltip toggling logic to ensure single tooltip visibility.
 * @param tooltip Tooltip instance to show.
 * @param currentTooltip Currently visible tooltip state.
 * @param svg Root SVG selection for layout calculations.
 * @param onShow Callback after showing the tooltip.
 * @param onHide Callback after hiding the tooltip.
 */
function handleTooltipInteraction(
  tooltip: ReturnType<typeof createTooltip>,
  currentTooltip: TooltipState | null,
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  onShow?: () => void,
  onHide?: () => void
): TooltipState | null {
  const isCurrentTooltipVisible =
    currentTooltip &&
    currentTooltip.box.style("visibility") === "visible" &&
    tooltip.inputBox.node() === currentTooltip.box.node();

  if (currentTooltip) {
    currentTooltip.box.style("visibility", "hidden");
    currentTooltip.lines.line1.style("visibility", "hidden");
    currentTooltip.lines.line2.style("visibility", "hidden");
    if (onHide) onHide();
  }

  if (!isCurrentTooltipVisible) {
    fixTooltipLayout(tooltip, svg);
    tooltip.tooltip_line_1.style("visibility", "visible").raise();
    tooltip.tooltip_line_2.style("visibility", "visible").raise();
    tooltip.inputBox.style("visibility", "visible").raise();

    if (onShow) onShow();

    return {
      box: tooltip.inputBox as unknown as d3.Selection<
        HTMLElement,
        unknown,
        null,
        undefined
      >,
      lines: {
        line1: tooltip.tooltip_line_1,
        line2: tooltip.tooltip_line_2,
      },
    };
  }

  return null;
}

/**
 * Adjust tooltip size and position to account for current SVG scaling.
 * @param tooltip Tooltip instance.
 * @param svgElement Root SVG selection.
 */
function fixTooltipLayout(
  tooltip: ReturnType<typeof createTooltip>,
  svgElement: d3.Selection<SVGGElement, unknown, HTMLElement, any>
): void {
  const inputBox = tooltip.inputBox;
  const line2 = tooltip.tooltip_line_2;
  const y3 = parseFloat(line2.attr("y2"));
  const svgNode = svgElement.node();
  if (!svgNode) return;

  const scale = svgNode.getScreenCTM()?.a || 1;
  const divNode = inputBox.select<HTMLDivElement>("div").node();
  if (!divNode) return;

  const { width, height } = divNode.getBoundingClientRect();
  const unscaledWidth = width / scale;
  const unscaledHeight = height / scale;

  inputBox.attr("width", unscaledWidth);
  inputBox.attr("height", unscaledHeight);
  inputBox.attr("y", y3 - unscaledHeight / 2);
}

/**
 * Compute final scale factor considering edges, rotation, and available space.
 * @param edges Visible edge charts.
 * @param s_length Matrix side length.
 * @param width Available viewport width.
 * @param height Available viewport height.
 * @param margin Outer margins.
 * @param rotationAngle Rotation in degrees.
 */
function calculateFinalScale(
  edges: string[],
  s_length: number,
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  rotationAngle: number
): number {
  const { edgeChartHeight, edgeOffset } = NUMERIC_MATRIX_CONFIG.dimensions;

  let totalCalculatedWidth = s_length;
  let totalCalculatedHeight = s_length;

  if (edges.includes("left")) {
    const thickness = edgeChartHeight;
    totalCalculatedWidth += thickness + edgeOffset;
  }
  if (edges.includes("right")) {
    const thickness = edgeChartHeight;
    totalCalculatedWidth += thickness + edgeOffset;
  }
  if (edges.includes("top")) {
    const thickness = edgeChartHeight;
    totalCalculatedHeight += thickness + edgeOffset;
  }
  if (edges.includes("bottom")) {
    const thickness = edgeChartHeight;
    totalCalculatedHeight += thickness + edgeOffset;
  }

  if (totalCalculatedWidth > 0 && totalCalculatedHeight > 0) {
    const availableWidth = width + margin.left + margin.right;
    const availableHeight = height + margin.top + margin.bottom;

    const radians = (rotationAngle * Math.PI) / 180;
    const cos = Math.abs(Math.cos(radians));
    const sin = Math.abs(Math.sin(radians));

    const rotatedWidth =
      totalCalculatedWidth * cos + totalCalculatedHeight * sin;
    const rotatedHeight =
      totalCalculatedWidth * sin + totalCalculatedHeight * cos;

    const scaleX = availableWidth / rotatedWidth;
    const scaleY = availableHeight / rotatedHeight;
    return Math.min(scaleX, scaleY) * 0.85;
  }

  return 1;
}

/**
 * Render the continuous matrix visualization for difference/compare rules.
 * @param svg Root SVG selection to render into.
 * @param csvData Table rows.
 * @param selectedColumns Columns involved in the rule.
 * @param width Available width.
 * @param height Available height.
 * @param margin Outer margins.
 * @param invalidIndicesOrPairs Invalid rows or index pairs.
 * @param invalid_range Invalid range configuration.
 * @param updateHighlightedIndices Callback to highlight rows.
 * @param ruleType Rule type: difference or compare.
 * @param edges Edge charts to display.
 * @param rotationAngle Rotation angle for the matrix.
 * @param columnTypes Optional column types.
 */
export async function continuous_matrix(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumns: string[],
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  invalidIndicesOrPairs: number[] | InvalidPairData[],
  invalid_range: GeneralInvalidRange,
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  ruleType: string,
  edges: string[] = ["top", "left"],
  rotationAngle = 45,
  columnTypes: ColumnType[] = []
): Promise<void> {
  const resolvedColumnTypes: ColumnType[] = selectedColumns.map(
    (_, index) => columnTypes[index] || "numeric"
  );
  const primaryColumnType = resolvedColumnTypes[0] || "numeric";
  const secondaryColumnType =
    resolvedColumnTypes[1] || resolvedColumnTypes[0] || "numeric";
  const loadingGroup = svg.append("g").attr("class", "loading-animation");
  createLoadingAnimation(loadingGroup, width, height);

  const containerGroup = svg
    .append("g")
    .attr("transform", NUMERIC_MATRIX_CONFIG.transforms.initialContainer)
    .style("opacity", 0);

  const edgeGroups: EdgeGroups = {
    bottom: containerGroup.append("g").attr("class", "bottom-edge-group"),
    right: containerGroup.append("g").attr("class", "right-edge-group"),
    top: containerGroup.append("g").attr("class", "top-edge-group"),
    left: containerGroup.append("g").attr("class", "left-edge-group"),
  };

  const matrixGroup = containerGroup.append("g").attr("class", "matrix-group");

  const x_start = 0;
  const y_start = 0;
  const s_length = NUMERIC_MATRIX_CONFIG.dimensions.matrixSize;
  const tooltipCellSize =
    s_length / NUMERIC_MATRIX_CONFIG.dimensions.subSquareDivisor;
  const estimatedContainerScale = calculateFinalScale(
    edges,
    s_length,
    width,
    height,
    margin,
    rotationAngle
  );
  const tooltipScaleRatio =
    estimatedContainerScale < 1 ? Math.min(1 / estimatedContainerScale, 3) : 1;

  matrixGroup
    .append("rect")
    .attr("x", x_start)
    .attr("y", y_start)
    .attr("width", s_length)
    .attr("height", s_length)
    .attr("stroke", NUMERIC_MATRIX_CONFIG.colors.matrixStroke)
    .attr("stroke-width", NUMERIC_MATRIX_CONFIG.dimensions.borderStrokeWidth)
    .attr("fill", NUMERIC_MATRIX_CONFIG.colors.matrixFill);

  const { edgeChartHeight } = NUMERIC_MATRIX_CONFIG.dimensions;
  const chartGroups = createChartGroups(
    edgeGroups,
    edges,
    { x_start, y_start, s_length },
    edgeChartHeight
  );

  const ranges = await renderEdgeCharts(
    chartGroups,
    edges,
    ruleType,
    csvData,
    selectedColumns,
    s_length,
    edgeChartHeight,
    margin,
    updateHighlightedIndices,
    resolvedColumnTypes
  );

  let currentTooltip: TooltipState | null = null;
  const circleTooltips: Record<string, ReturnType<typeof createTooltip>> = {};

  const finalScale = calculateFinalScale(
    edges,
    s_length,
    width,
    height,
    margin,
    rotationAngle
  );

  const highlightRelatedElements = (x1Value: number, x2Value: number) => {
    removeAllHighlights(
      chartGroups,
      edgeGroups,
      containerGroup,
      edges,
      ruleType
    );

    const labelOffset = NUMERIC_MATRIX_CONFIG.dimensions.highlightLabelOffset;
    const chartThickness = edgeChartHeight;

    if (ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.difference) {
      const dataRange = { x_min: ranges.x_min, x_max: ranges.x_max };

      edges.forEach((edge) => {
        const chartGroup = chartGroups[edge as EdgePosition];
        const edgeGroup = edgeGroups[edge as EdgePosition];

        if (edge === "bottom" && chartGroup) {
          addHighlightElements(
            chartGroup,
            edgeGroup,
            x1Value,
            dataRange,
            s_length,
            chartThickness,
            {
              x:
                x_start +
                ((x1Value - ranges.x_min) / (ranges.x_max - ranges.x_min)) *
                  s_length,
              y: y_start + s_length + chartThickness + labelOffset,
              anchor: "end",
            },
            primaryColumnType
          );
        } else if (edge === "right" && chartGroup) {
          addHighlightElements(
            chartGroup,
            edgeGroup,
            x2Value,
            dataRange,
            s_length,
            chartThickness,
            {
              x: x_start + s_length + chartThickness + labelOffset,
              y:
                y_start +
                s_length -
                ((x2Value - ranges.x_min) / (ranges.x_max - ranges.x_min)) *
                  s_length,
              anchor: "start",
            },
            primaryColumnType
          );
        } else if (edge === "top" && chartGroup) {
          addHighlightElements(
            chartGroup,
            edgeGroup,
            x1Value,
            dataRange,
            s_length,
            chartThickness,
            {
              x:
                x_start +
                ((x1Value - ranges.x_min) / (ranges.x_max - ranges.x_min)) *
                  s_length,
              y: y_start - chartThickness - labelOffset,
              anchor: "start",
            },
            primaryColumnType
          );
        } else if (edge === "left" && chartGroup) {
          addHighlightElements(
            chartGroup,
            edgeGroup,
            x2Value,
            dataRange,
            s_length,
            chartThickness,
            {
              x: x_start - chartThickness - labelOffset,
              y:
                y_start +
                s_length -
                ((x2Value - ranges.x_min) / (ranges.x_max - ranges.x_min)) *
                  s_length,
              anchor: "end",
            },
            primaryColumnType
          );
        }
      });
    } else if (
      ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.compare
    ) {
      edges.forEach((edge) => {
        const chartGroup = chartGroups[edge as EdgePosition];

        if ((edge === "bottom" || edge === "top") && chartGroup) {
          const dataRange = { x_min: ranges.x1_min, x_max: ranges.x1_max };
          const labelX =
            x_start +
            ((x1Value - ranges.x1_min) / (ranges.x1_max - ranges.x1_min)) *
              s_length;
          const labelY =
            edge === "bottom"
              ? y_start + s_length + chartThickness + labelOffset
              : y_start - chartThickness - labelOffset;

          addHighlightElements(
            chartGroup,
            containerGroup,
            x1Value,
            dataRange,
            s_length,
            edgeChartHeight,
            {
              x: labelX,
              y: labelY,
              anchor: edge === "bottom" ? "end" : "start",
            },
            primaryColumnType
          );
        } else if ((edge === "right" || edge === "left") && chartGroup) {
          const dataRange = { x_min: ranges.x2_min, x_max: ranges.x2_max };
          const labelX =
            edge === "right"
              ? x_start + s_length + chartThickness + labelOffset
              : x_start - chartThickness - labelOffset;
          const labelY =
            y_start +
            s_length -
            ((x2Value - ranges.x2_min) / (ranges.x2_max - ranges.x2_min)) *
              s_length;

          addHighlightElements(
            chartGroup,
            containerGroup,
            x2Value,
            dataRange,
            s_length,
            edgeChartHeight,
            {
              x: labelX,
              y: labelY,
              anchor: edge === "right" ? "start" : "end",
            },
            secondaryColumnType
          );
        }
      });
    }
  };

  function handlePolygonClick(tooltip: ReturnType<typeof createTooltip>) {
    currentTooltip = handleTooltipInteraction(
      tooltip,
      currentTooltip,
      svg,
      undefined,
      () =>
        removeAllHighlights(
          chartGroups,
          edgeGroups,
          containerGroup,
          edges,
          ruleType
        )
    );
  }

  function handleMainAreaClick(tooltip: ReturnType<typeof createTooltip>) {
    currentTooltip = handleTooltipInteraction(
      tooltip,
      currentTooltip,
      svg,
      () => {
        if (
          ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.compare
        ) {
          const invalid_index = invalidIndicesOrPairs as number[];
          const rowIds = invalid_index || [];
          const highlightColumns: string[] = selectedColumns;
          const highlightEvent = new CustomEvent("highlight-invalid-data", {
            detail: { rowIds, highlightColumns, sortedIndices: rowIds },
          });
          window.dispatchEvent(highlightEvent);
        }
      },
      () =>
        removeAllHighlights(
          chartGroups,
          edgeGroups,
          containerGroup,
          edges,
          ruleType
        )
    );
  }

  if (ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.difference) {
    const diffRange = invalid_range as invalidRange_Difference;
    const { start: difference_start, end: difference_end } = diffRange;
    const tooltipTemplate =
      NUMERIC_MATRIX_CONFIG.tooltips.getDifferenceAreaTemplate(
        selectedColumns[0],
        diffRange
      );

    const difference_start_ratio =
      difference_start / (ranges.x_max - ranges.x_min);
    const difference_end_ratio = difference_end / (ranges.x_max - ranges.x_min);

    const valid_left = [
      { x: x_start, y: y_start + (1 - difference_start_ratio) * s_length },
      { x: x_start, y: y_start + s_length * (1 - difference_end_ratio) },
      { x: x_start + s_length * (1 - difference_end_ratio), y: y_start },
      { x: x_start + s_length * (1 - difference_start_ratio), y: y_start },
    ];

    const left_centerX =
      valid_left.reduce((sum, point) => sum + point.x, 0) / valid_left.length;
    const left_centerY =
      valid_left.reduce((sum, point) => sum + point.y, 0) / valid_left.length;

    const leftTooltip = createTooltip(
      matrixGroup,
      left_centerX - tooltipCellSize / 2,
      left_centerY - tooltipCellSize / 2,
      x_start,
      y_start,
      tooltipCellSize,
      tooltipTemplate,
      selectedColumns,
      "Difference",
      "",
      tooltipScaleRatio
    );

    matrixGroup
      .append("polygon")
      .attr("id", "invalid-area")
      .attr("points", valid_left.map((d) => `${d.x},${d.y}`).join(" "))
      .attr("fill", NUMERIC_MATRIX_CONFIG.colors.areaFill)
      .on("click", () => handlePolygonClick(leftTooltip));

    const valid_right = [
      { x: x_start + s_length * difference_start_ratio, y: y_start + s_length },
      { x: x_start + s_length * difference_end_ratio, y: y_start + s_length },
      { x: x_start + s_length, y: y_start + s_length * difference_end_ratio },
      { x: x_start + s_length, y: y_start + s_length * difference_start_ratio },
    ];

    const right_centerX =
      valid_right.reduce((sum, point) => sum + point.x, 0) / valid_right.length;
    const right_centerY =
      valid_right.reduce((sum, point) => sum + point.y, 0) / valid_right.length;

    const rightTooltip = createTooltip(
      matrixGroup,
      right_centerX - tooltipCellSize / 2,
      right_centerY - tooltipCellSize / 2,
      x_start,
      y_start,
      tooltipCellSize,
      tooltipTemplate,
      selectedColumns,
      "Difference",
      "",
      tooltipScaleRatio
    );

    matrixGroup
      .append("polygon")
      .attr("id", "invalid-area")
      .attr("points", valid_right.map((d) => `${d.x},${d.y}`).join(" "))
      .attr("fill", NUMERIC_MATRIX_CONFIG.colors.areaFill)
      .on("click", () => handlePolygonClick(rightTooltip));
  } else if (
    ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.compare
  ) {
    const compareRange = invalid_range as invalidRange_Compare_Numeric;
    const compareType = String(compareRange);
    const tooltipTemplate =
      NUMERIC_MATRIX_CONFIG.tooltips.getCompareAreaTemplate(
        selectedColumns,
        compareType
      );

    const mainTooltip = createTooltip(
      matrixGroup,
      x_start + s_length / 2 - tooltipCellSize / 2,
      y_start + s_length / 2 - tooltipCellSize / 2,
      x_start,
      y_start,
      tooltipCellSize,
      tooltipTemplate,
      selectedColumns,
      "Compare",
      "",
      tooltipScaleRatio
    );

    const normalize = (value: number, min: number, max: number): number => {
      if (max - min === 0) {
        return 0.5;
      }
      const clamped = Math.max(min, Math.min(max, value));
      return (clamped - min) / (max - min);
    };

    const dataToMatrix = (data_x: number, data_y: number) => ({
      x: x_start + normalize(data_x, ranges.x1_min, ranges.x1_max) * s_length,
      y:
        y_start +
        s_length -
        normalize(data_y, ranges.x2_min, ranges.x2_max) * s_length,
    });

    const rectangleCornersData = createRectangleCorners(ranges);
    const validRegionData = clipRectangleWithDiagonal(
      rectangleCornersData,
      compareType
    );
    const validPolygonPoints = validRegionData.map((point) =>
      dataToMatrix(point.x, point.y)
    );

    if (validPolygonPoints.length >= 3) {
      const valid_centerX =
        validPolygonPoints.reduce((sum, point) => sum + point.x, 0) /
        validPolygonPoints.length;
      const valid_centerY =
        validPolygonPoints.reduce((sum, point) => sum + point.y, 0) /
        validPolygonPoints.length;

      const validAreaTooltip = createTooltip(
        matrixGroup,
        valid_centerX - tooltipCellSize / 2,
        valid_centerY - tooltipCellSize / 2,
        x_start,
        y_start,
        tooltipCellSize,
        tooltipTemplate,
        selectedColumns,
        "Compare",
        "",
        tooltipScaleRatio
      );

      matrixGroup
        .append("polygon")
        .attr("id", "valid-area")
        .attr(
          "points",
          validPolygonPoints.map((d) => `${d.x},${d.y}`).join(" ")
        )
        .attr("fill", NUMERIC_MATRIX_CONFIG.colors.areaFill)
        .attr("stroke", "none")
        .attr("opacity", 0.85)
        .on("click", () => handlePolygonClick(validAreaTooltip));
    }

    matrixGroup
      .select("rect")
      .on("click", () => handleMainAreaClick(mainTooltip));
  }

  const drawInvalidPrecise = () => {
    const subSquareLength =
      s_length / NUMERIC_MATRIX_CONFIG.dimensions.subSquareDivisor;
    const pointRadius =
      subSquareLength / NUMERIC_MATRIX_CONFIG.dimensions.pointRadiusDivisor;

    if (ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.difference) {
      const invalid_pairs = invalidIndicesOrPairs as InvalidPairData[];
      const precise_invalid: Record<string, number[]> = {};
      const sortedIndices: Record<string, number[]> = {};
      const differenceSpan = ranges.x_max - ranges.x_min;

      invalid_pairs.forEach((invalid_pair) => {
        const { currentIndex, nextIndex, sortCurrentIndex, sortNextIndex } =
          invalid_pair;

        if (differenceSpan === 0) {
          return;
        }

        const val1 = toComparableValue(
          csvData[currentIndex][selectedColumns[0]] as string | number,
          primaryColumnType
        );
        if (val1 === null) {
          return;
        }
        const ratio1 = (val1 - ranges.x_min) / differenceSpan;

        const val2 = toComparableValue(
          csvData[nextIndex][selectedColumns[0]] as string | number,
          primaryColumnType
        );
        if (val2 === null) {
          return;
        }
        const ratio2 = (val2 - ranges.x_min) / differenceSpan;

        if (ratio1 !== undefined && ratio2 !== undefined) {
          const precise_x = x_start + ratio1 * s_length;
          const precise_y = y_start + (1 - ratio2) * s_length;
          const key = `${precise_x},${precise_y}`;

          if (!precise_invalid[key]) precise_invalid[key] = [];
          if (!sortedIndices[key]) sortedIndices[key] = [];

          precise_invalid[key].push(currentIndex, nextIndex);
          sortedIndices[key].push(sortCurrentIndex, sortNextIndex);
        }
      });

      Object.entries(precise_invalid).forEach(([key, indices]) => {
        const [px, py] = key.split(",").map(Number);
        const x1Value =
          ranges.x_min +
          ((px - x_start) / s_length) * (ranges.x_max - ranges.x_min);
        const x2Value =
          ranges.x_max -
          ((py - y_start) / s_length) * (ranges.x_max - ranges.x_min);

        const circleX = Math.max(
          x_start + pointRadius,
          Math.min(px, x_start + s_length - pointRadius)
        );
        const circleY = Math.max(
          y_start + pointRadius,
          Math.min(py, y_start + s_length - pointRadius)
        );

        matrixGroup
          .append("circle")
          .attr("id", "invalid-data")
          .attr("class", "invalid-data-precise")
          .attr("cx", circleX)
          .attr("cy", circleY)
          .attr("r", pointRadius)
          .attr("fill", NUMERIC_MATRIX_CONFIG.colors.invalidPointFill)
          .attr("stroke", "none")
          .attr("opacity", NUMERIC_MATRIX_CONFIG.colors.invalidPointOpacity)
          .attr("data-x1-value", x1Value)
          .attr("data-x2-value", x2Value)
          .on("click", () => {
            if (!circleTooltips[key]) {
              const tooltipTemplate =
                NUMERIC_MATRIX_CONFIG.tooltips.getDifferencePointTemplate(
                  selectedColumns[0],
                  x1Value,
                  x2Value
                );

              circleTooltips[key] = createTooltip(
                matrixGroup,
                circleX - tooltipCellSize / 2,
                circleY - tooltipCellSize / 2,
                x_start,
                y_start,
                tooltipCellSize,
                tooltipTemplate,
                selectedColumns,
                "Difference",
                "",
                tooltipScaleRatio
              );
            }

            currentTooltip = handleTooltipInteraction(
              circleTooltips[key],
              currentTooltip,
              svg,
              () => {
                highlightRelatedElements(x1Value, x2Value);
                const event = new CustomEvent("highlight-invalid-data", {
                  detail: {
                    rowIds: indices,
                    highlightColumns: selectedColumns,
                    sortedIndices: sortedIndices[key],
                    isRightClick: false,
                  },
                });
                window.dispatchEvent(event);
              },
              () =>
                removeAllHighlights(
                  chartGroups,
                  edgeGroups,
                  containerGroup,
                  edges,
                  ruleType
                )
            );
          })
          .on("contextmenu", (event) => {
            event.preventDefault();
            removeAllHighlights(
              chartGroups,
              edgeGroups,
              containerGroup,
              edges,
              ruleType
            );
            highlightRelatedElements(x1Value, x2Value);
            const highlightEvent = new CustomEvent("highlight-invalid-data", {
              detail: {
                rowIds: indices,
                highlightColumns: selectedColumns,
                sortedIndices: indices,
                isRightClick: true,
              },
            });
            window.dispatchEvent(highlightEvent);
          });
      });
    } else if (
      ruleType.toLowerCase() === NUMERIC_MATRIX_CONFIG.ruleTypes.compare
    ) {
      const invalid_index = invalidIndicesOrPairs as number[];
      const precise_invalidCount: Record<string, number> = {};
      const gridInvalidData: Record<string, number[]> = {};
      const xSpan = ranges.x1_max - ranges.x1_min;
      const ySpan = ranges.x2_max - ranges.x2_min;

      invalid_index.forEach((index) => {
        if (xSpan === 0 || ySpan === 0) {
          return;
        }

        const val1 = toComparableValue(
          csvData[index][selectedColumns[0]] as string | number,
          primaryColumnType
        );
        const val2 = toComparableValue(
          csvData[index][selectedColumns[1]] as string | number,
          secondaryColumnType
        );
        if (val1 === null || val2 === null) {
          return;
        }
        const ratio1 = (val1 - ranges.x1_min) / xSpan;

        const ratio2 = (val2 - ranges.x2_min) / ySpan;

        if (ratio1 !== undefined && ratio2 !== undefined) {
          const px = x_start + ratio1 * s_length;
          const py = y_start + (1 - ratio2) * s_length;
          const key = `${px},${py}`;

          precise_invalidCount[key] = (precise_invalidCount[key] || 0) + 1;
          if (!gridInvalidData[key]) gridInvalidData[key] = [];
          gridInvalidData[key].push(index);
        }
      });

      Object.entries(precise_invalidCount).forEach(([key]) => {
        const [px, py] = key.split(",").map(Number);
        const x1Value =
          ranges.x1_min +
          ((px - x_start) / s_length) * (ranges.x1_max - ranges.x1_min);
        const x2Value =
          ranges.x2_max -
          ((py - y_start) / s_length) * (ranges.x2_max - ranges.x2_min);

        matrixGroup
          .append("circle")
          .attr("id", "invalid-data")
          .attr("class", "invalid-data-precise")
          .attr("cx", px)
          .attr("cy", py)
          .attr("r", pointRadius)
          .attr("fill", NUMERIC_MATRIX_CONFIG.colors.invalidPointFill)
          .attr("stroke", "none")
          .attr("opacity", NUMERIC_MATRIX_CONFIG.colors.invalidPointOpacity)
          .attr("data-x1-value", x1Value)
          .attr("data-x2-value", x2Value)
          .on("click", () => {
            if (!circleTooltips[key]) {
              const compareRange =
                invalid_range as invalidRange_Compare_Numeric;
              const compareType = String(compareRange);
              const formattedX1Value = formatValueLabel(
                x1Value,
                primaryColumnType
              );
              const formattedX2Value = formatValueLabel(
                x2Value,
                secondaryColumnType
              );
              const tooltipTemplate =
                NUMERIC_MATRIX_CONFIG.tooltips.getComparePointTemplate(
                  selectedColumns,
                  compareType,
                  formattedX1Value,
                  formattedX2Value
                );

              circleTooltips[key] = createTooltip(
                matrixGroup,
                px - tooltipCellSize / 2,
                py - tooltipCellSize / 2,
                x_start,
                y_start,
                tooltipCellSize,
                tooltipTemplate,
                selectedColumns,
                "Compare",
                "",
                tooltipScaleRatio
              );
            }

            currentTooltip = handleTooltipInteraction(
              circleTooltips[key],
              currentTooltip,
              svg,
              () => {
                highlightRelatedElements(x1Value, x2Value);
                const rowIds = gridInvalidData[key] || [];
                const event = new CustomEvent("highlight-invalid-data", {
                  detail: {
                    rowIds,
                    highlightColumns: selectedColumns,
                    sortedIndices: rowIds,
                    isRightClick: false,
                  },
                });
                window.dispatchEvent(event);
              },
              () =>
                removeAllHighlights(
                  chartGroups,
                  edgeGroups,
                  containerGroup,
                  edges,
                  ruleType
                )
            );
          })
          .on("contextmenu", (event) => {
            event.preventDefault();
            removeAllHighlights(
              chartGroups,
              edgeGroups,
              containerGroup,
              edges,
              ruleType
            );
            highlightRelatedElements(x1Value, x2Value);
            const rowIds = gridInvalidData[key] || [];
            const highlightEvent = new CustomEvent("highlight-invalid-data", {
              detail: {
                rowIds,
                highlightColumns: selectedColumns,
                sortedIndices: rowIds,
                isRightClick: true,
              },
            });
            window.dispatchEvent(highlightEvent);
          });
      });
    }
  };

  drawInvalidPrecise();

  const { edgeOffset } = NUMERIC_MATRIX_CONFIG.dimensions;
  const chartThickness = edgeChartHeight;

  let totalCalculatedWidth = s_length;
  let totalCalculatedHeight = s_length;
  let minX = 0;
  let minY = 0;

  if (edges.includes("left")) {
    const widthToAdd = chartThickness + edgeOffset;
    totalCalculatedWidth += widthToAdd;
    minX = -widthToAdd;
  }
  if (edges.includes("right")) {
    const widthToAdd = chartThickness + edgeOffset;
    totalCalculatedWidth += widthToAdd;
  }
  if (edges.includes("top")) {
    const heightToAdd = chartThickness + edgeOffset;
    totalCalculatedHeight += heightToAdd;
    minY = -heightToAdd;
  }
  if (edges.includes("bottom")) {
    const heightToAdd = chartThickness + edgeOffset;
    totalCalculatedHeight += heightToAdd;
  }

  if (totalCalculatedWidth > 0 && totalCalculatedHeight > 0) {
    const availableWidth = width + margin.left + margin.right;
    const availableHeight = height + margin.top + margin.bottom;

    const radians = (rotationAngle * Math.PI) / 180;
    const cos = Math.abs(Math.cos(radians));
    const sin = Math.abs(Math.sin(radians));

    const rotatedWidth =
      totalCalculatedWidth * cos + totalCalculatedHeight * sin;
    const rotatedHeight =
      totalCalculatedWidth * sin + totalCalculatedHeight * cos;

    const scaleX = availableWidth / rotatedWidth;
    const scaleY = availableHeight / rotatedHeight;
    const scale = Math.min(scaleX, scaleY, 1) * 0.85;

    const calculatedCenterX = minX + totalCalculatedWidth / 2;
    const calculatedCenterY = minY + totalCalculatedHeight / 2;

    const targetX = width / 2;
    const targetY = height / 2;

    const translateX = targetX - calculatedCenterX * scale;
    const translateY = targetY - calculatedCenterY * scale;

    const matrixCenterX = x_start + s_length / 2;
    const matrixCenterY = y_start + s_length / 2;

    containerGroup.attr(
      "transform",
      `translate(${translateX}, ${translateY}) scale(${scale}) rotate(${rotationAngle}, ${matrixCenterX}, ${matrixCenterY})`
    );
  } else {
    containerGroup.attr(
      "transform",
      `translate(300, -125) rotate(${rotationAngle}, 0, 0)`
    );
  }

  containerGroup
    .transition()
    .duration(NUMERIC_MATRIX_CONFIG.animation.fadeInDuration)
    .style("opacity", 1);

  loadingGroup.remove();
}
