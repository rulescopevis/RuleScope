import * as d3 from "d3";
import { renderCharacterChart, x, top10 } from "./character";
import { renderNumericChart } from "./numeric";
import { invalidRange_Equality_Range, Row } from "@/types/types";
import { createLoadingAnimation } from "@/utils/utils";
import { createTooltip } from "@/utils/tootips";
import { api_load_column_data } from "@/utils/callapi";

// Matrix rendering configuration
const MATRIX_CONFIG = {
  colors: {
    gridStroke: "#cad2d7",
    borderStroke: "#9a9a9a",
    gridFill: "white",
    labelText: "black",
    barDefault: "#4570b6",
    barBackground: "#B5D2F8",
    highlightPrimary: "#4570b6",
    highlightSecondary: "#fd8d3c",
    rangeOpacity: 0.3,
    invalidDataOpacity: 0.6,
  },
  tooltips: {
    /**
     * Tooltip template for valid rule ranges.
     * @param characterColumn Categorical column name
     * @param numericColumn Numeric column name
     * @param conditionContent Condition value for the category
     * @param start Range start value
     * @param end Range end value
     * @param startInclusive Whether the start value is inclusive
     * @param endInclusive Whether the end value is inclusive
     * @param ruleType Rule type string
     * @returns HTML string for tooltip content
     */
    getValidRuleTemplate: (
      characterColumn: string,
      numericColumn: string,
      conditionContent: string,
      start: number,
      end: number,
      startInclusive: boolean,
      endInclusive: boolean,
      ruleType: string
    ): string => {
      if (ruleType.toLocaleLowerCase() === "logical and condition") {
        return `If <strong style="color: black">${characterColumn}</strong> = <strong style="color: red">${conditionContent}</strong>, then <strong style="color: black">${numericColumn}</strong> needs to be <strong style="color: red">${
          startInclusive ? "[" : "("
        }${start},${end}${endInclusive ? "]" : ")"}</strong>.`;
      } else {
        return `If <strong style="color: black">${characterColumn}</strong> = <strong style="color: red">${conditionContent}</strong>, then <strong style="color: black">${numericColumn}</strong> needs to be <strong style="color: red">${
          startInclusive ? "[" : "("
        }${start},${end}${endInclusive ? "]" : ")"}</strong>.`;
      }
    },
    /**
     * Tooltip template for invalid data points.
     * @param characterColumn Categorical column name
     * @param numericColumn Numeric column name
     * @param category Category value
     * @param numericValue Numeric value of the point
     * @param ruleType Rule type string
     * @returns HTML string for tooltip content
     */
    getInvalidDataTemplate: (
      characterColumn: string,
      numericColumn: string,
      category: string,
      numericValue: number,
      ruleType: string
    ): string => {
      if (ruleType.toLocaleLowerCase() === "multipleduplicate") {
        return `The combination of <strong style="color: black;">${characterColumn}</strong> and <strong style="color: black;">${numericColumn}</strong> <strong style="color: red"> does not allow </strong> duplicate values.`;
      } else if (ruleType.toLocaleLowerCase() === "logical and condition") {
        return `If <strong style="color: black;">${characterColumn}</strong> = <strong style="color: red;">${category}</strong>, then <strong style="color: black;">${numericColumn}</strong> cannot be <strong style="color: red;">${numericValue.toFixed(
          2
        )}</strong>.`;
      } else {
        return `If <strong style="color: black;">${characterColumn}</strong> = <strong style="color: red;">${category}</strong>, then <strong style="color: black;">${numericColumn}</strong> cannot be <strong style="color: red;">${numericValue.toFixed(
          2
        )}</strong>.`;
      }
    },
  },
  layout: {
    labelOffset: 10,
    finalPadding: 0.1,
    matrix: {
      baseSubSquareLength: 40,
      defaultHeight: 360,
      divisionsY: 20,
      minNumericEdgeLength: 400,
    },
    validAreaWidthRatio: 0.75,
    invalidDataWidthRatio: 0.75,
    invalidDataHeightRatio: 0.25,
    characterEdgeHeight: 180,
    numericEdgeHeight: 180,
    edgeOffset: 10,
    gridStrokeWidth: 1,
    borderStrokeWidth: 1.5,
  },
  animation: {
    loadingDelay: 0,
    duration: 500,
  },
};

type EdgePosition = "bottom" | "right" | "top" | "left";
type ChartType = "character" | "numeric";
type EdgeGroups = {
  [K in EdgePosition]: d3.Selection<SVGGElement, unknown, HTMLElement, any>;
};
type ChartGroups = {
  [K in EdgePosition]?: d3.Selection<SVGGElement, unknown, HTMLElement, any>;
};

interface MatrixDimensions {
  subSquareLength: number;
  matrixWidth: number;
  matrixHeight: number;
  divisionsX: number;
}

interface ChartData {
  characterCategories: any[];
  characterX: any;
  x_min: number;
  x_max: number;
}

// Fallback label for aggregated categories
const OTHER_CATEGORY_LABEL = "\u5176\u4ed6";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Render a categorical-numeric matrix with optional edge charts.
 * @param svg D3 group container to render into
 * @param csvData Table rows for visualization
 * @param selectedColumns Two columns: categorical first, numeric second (unless chartTypes swaps)
 * @param width Available width for layout
 * @param height Available height for layout
 * @param margin External margins for layout calculations
 * @param invalid_index Row indices flagged as invalid data points
 * @param invalid_range Ranges representing valid rule areas
 * @param updateHighlightedIndices Callback to notify highlighted rows/columns
 * @param ruleType Rule type string (e.g., logical and condition, multipleDuplicate)
 * @param edges Edges to render charts on: ["bottom", "right", "top", "left"]
 * @param rotationAngle Matrix rotation angle in degrees
 * @param chartTypes Chart type per edge: [bottom, right, top, left] as character|numeric
 */
export async function discrete_continuous_matrix(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumns: string[],
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  invalid_index: number[],
  invalid_range: invalidRange_Equality_Range[],
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  ruleType = "",
  edges: string[] = ["top", "left"],
  rotationAngle = 45,
  chartTypes: [ChartType, ChartType, ChartType, ChartType] = [
    "character",
    "numeric",
    "character",
    "numeric",
  ]
): Promise<void> {
  const characterColumn =
    chartTypes[0] === "character" ? selectedColumns[0] : selectedColumns[1];
  const numericColumn =
    chartTypes[0] === "character" ? selectedColumns[1] : selectedColumns[0];

  const loadingGroup = svg.append("g").attr("class", "loading-animation");
  createLoadingAnimation(loadingGroup, width, height);

  if (MATRIX_CONFIG.animation.loadingDelay > 0) {
    await delay(MATRIX_CONFIG.animation.loadingDelay);
  }

  const containerGroup = svg
    .append("g")
    .attr("transform", `translate(0, 0)`)
    .style("opacity", 0);

  const edgeGroups: EdgeGroups = {
    bottom: containerGroup.append("g").attr("class", "bottom-edge-group"),
    right: containerGroup.append("g").attr("class", "right-edge-group"),
    top: containerGroup.append("g").attr("class", "top-edge-group"),
    left: containerGroup.append("g").attr("class", "left-edge-group"),
  };

  const matrixGroup = containerGroup.append("g").attr("class", "matrix-group");

  const valueList = await api_load_column_data(characterColumn);
  const charactersCount = valueList.length;

  const calculateMatrixDimensions = (
    charactersCount: number
  ): MatrixDimensions => {
    const config = MATRIX_CONFIG.layout.matrix;
    const subSquareLength = config.baseSubSquareLength;

    const matrixWidth = charactersCount * subSquareLength;

    const matrixHeight = Math.max(matrixWidth, config.minNumericEdgeLength);

    return {
      subSquareLength,
      matrixWidth,
      matrixHeight,
      divisionsX: charactersCount,
    };
  };

  const getEdgeChartHeight = (edge: EdgePosition): number => {
    const edgeIndex = ["bottom", "right", "top", "left"].indexOf(edge);
    const type = chartTypes[edgeIndex];
    if (type === "character") {
      return MATRIX_CONFIG.layout.characterEdgeHeight;
    } else {
      // 'numeric'
      return MATRIX_CONFIG.layout.numericEdgeHeight;
    }
  };
  const getCategoryPosition = (
    category: string,
    categoryArray: any[],
    xScale: d3.ScaleBand<string>
  ) => {
    const foundCategory = categoryArray.find(
      (d) => String(d.category).toLowerCase() === category.toLowerCase()
    );

    if (foundCategory) {
      return xScale(foundCategory.category);
    }

    const otherCategory = categoryArray.find(
      (d) => d.category === OTHER_CATEGORY_LABEL
    );
    return otherCategory ? xScale(otherCategory.category) : undefined;
  };

  const createLabel = (
    group: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
    x: number,
    y: number,
    text: string,
    anchor: string,
    baseline: string,
    rotation?: string
  ) => {
    const label = group
      .append("text")
      .attr("class", "highlight-label")
      .attr("x", x)
      .attr("y", y)
      .attr("text-anchor", anchor)
      .attr("dominant-baseline", baseline)
      .attr("fill", MATRIX_CONFIG.colors.labelText)
      .text(text);

    if (rotation) {
      label.attr("transform", rotation);
    }

    return label;
  };

  const calculateFinalScale = () => {
    const matrixDimensions = calculateMatrixDimensions(charactersCount);
    const { edgeOffset } = MATRIX_CONFIG.layout;

    let totalCalculatedWidth = matrixDimensions.matrixWidth;
    let totalCalculatedHeight = matrixDimensions.matrixHeight;
    let minX = 0;
    let minY = 0;

    if (edges.includes("left")) {
      const thickness = getEdgeChartHeight("left");
      totalCalculatedWidth += thickness + edgeOffset;
      minX = -(thickness + edgeOffset);
    }
    if (edges.includes("right")) {
      const thickness = getEdgeChartHeight("right");
      totalCalculatedWidth += thickness + edgeOffset;
    }
    if (edges.includes("top")) {
      const thickness = getEdgeChartHeight("top");
      totalCalculatedHeight += thickness + edgeOffset;
      minY = -(thickness + edgeOffset);
    }
    if (edges.includes("bottom")) {
      const thickness = getEdgeChartHeight("bottom");
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
      return Math.min(scaleX, scaleY);
    }

    return 1;
  };

  const renderMatrix = async () => {
    matrixGroup.selectAll("*").remove();
    Object.values(edgeGroups).forEach((group) => group.selectAll("*").remove());

    const matrixDimensions = calculateMatrixDimensions(charactersCount);
    const x_start = 0;
    const y_start = 0;

    const finalScale = calculateFinalScale();
    const tooltipScaleRatio = finalScale < 1 ? Math.min(1 / finalScale, 3) : 1;

    matrixGroup
      .append("rect")
      .attr("x", x_start)
      .attr("y", y_start)
      .attr("width", matrixDimensions.matrixWidth)
      .attr("height", matrixDimensions.matrixHeight)
      .attr("stroke", MATRIX_CONFIG.colors.borderStroke)
      .attr("stroke-width", MATRIX_CONFIG.layout.borderStrokeWidth)
      .attr("fill", MATRIX_CONFIG.colors.gridFill);

    const { edgeOffset } = MATRIX_CONFIG.layout;

    const chartGroups: ChartGroups = {};
    const chartTransforms = {
      bottom: `translate(${x_start}, ${
        y_start + matrixDimensions.matrixHeight + edgeOffset
      })`,
      right: `translate(${
        x_start + matrixDimensions.matrixWidth + edgeOffset
      }, ${y_start + matrixDimensions.matrixHeight}) rotate(-90)`,
      top: `translate(${x_start}, ${
        y_start - getEdgeChartHeight("top") - edgeOffset
      })`,
      left: `translate(${x_start - getEdgeChartHeight("left") - edgeOffset}, ${
        y_start + matrixDimensions.matrixHeight
      }) rotate(-90)`,
    };

    edges.forEach((edge) => {
      if (chartTransforms[edge as EdgePosition]) {
        chartGroups[edge as EdgePosition] = edgeGroups[edge as EdgePosition]
          .append("g")
          .attr("transform", chartTransforms[edge as EdgePosition]);
      }
    });

    const chartData: ChartData = {
      characterCategories: [],
      characterX: null,
      x_min: 0,
      x_max: 0,
    };

    const highlightCharacterChart = (
      chartGroup: any,
      edgeGroup: any,
      position: EdgePosition,
      category: string,
      color: string
    ) => {
      chartGroup
        .selectAll("rect")
        .attr("fill", MATRIX_CONFIG.colors.barBackground);
      chartGroup
        .selectAll(`rect[data-category="${String(category).toLowerCase()}"]`)
        .attr("fill", color)
        .raise();

      const categoryPos = getCategoryPosition(
        category,
        chartData.characterCategories,
        chartData.characterX
      );
      if (categoryPos !== undefined) {
        const barCenterX = categoryPos + chartData.characterX.bandwidth() / 2;
        const labelOffset = MATRIX_CONFIG.layout.labelOffset;
        const edgeHeight = getEdgeChartHeight(position);

        if (position === "bottom") {
          const labelX = x_start + barCenterX;
          const labelY =
            y_start + matrixDimensions.matrixHeight + edgeHeight + labelOffset;
          const rotation = `rotate(-${rotationAngle}, ${labelX}, ${labelY})`;
          createLabel(
            edgeGroup,
            labelX,
            labelY,
            category,
            "end",
            "text-before-edge",
            rotation
          );
        } else if (position === "top") {
          const labelX = x_start + barCenterX;
          const labelY = y_start - edgeHeight - labelOffset;
          const rotation = `rotate(-${rotationAngle}, ${labelX}, ${labelY})`;
          createLabel(
            edgeGroup,
            labelX,
            labelY,
            category,
            "start",
            "text-after-edge",
            rotation
          );
        }
      }
    };

    const highlightNumericChart = (
      chartGroup: any,
      edgeGroup: any,
      position: EdgePosition,
      rangeStart: number,
      rangeEnd: number,
      color: string
    ) => {
      const numericChartWidth = matrixDimensions.matrixHeight;
      const numericChartHeight = getEdgeChartHeight(position);

      const rangeWidth = Math.max(
        ((rangeEnd - rangeStart) / (chartData.x_max - chartData.x_min)) *
          numericChartWidth,
        2
      );
      const rangeX =
        ((rangeStart - chartData.x_min) / (chartData.x_max - chartData.x_min)) *
        numericChartWidth;

      chartGroup
        .append("rect")
        .attr("class", "highlight-range")
        .attr("x", rangeX)
        .attr("y", 0)
        .attr("width", rangeWidth)
        .attr("height", numericChartHeight)
        .attr("fill", color)
        .attr("opacity", MATRIX_CONFIG.colors.rangeOpacity);

      const labelOffset = MATRIX_CONFIG.layout.labelOffset;
      const rangeX_start_pos =
        ((rangeStart - chartData.x_min) / (chartData.x_max - chartData.x_min)) *
        numericChartWidth;
      const edgeHeight = getEdgeChartHeight(position);

      if (position === "right") {
        const rangeY_start =
          y_start + matrixDimensions.matrixHeight - rangeX_start_pos;
        const labelX =
          x_start + matrixDimensions.matrixWidth + edgeHeight + labelOffset;
        const rotation = `rotate(-${rotationAngle}, ${labelX}, ${rangeY_start})`;
        createLabel(
          edgeGroup,
          labelX,
          rangeY_start,
          rangeStart.toFixed(2),
          "start",
          "text-before-edge",
          rotation
        );

        if (rangeStart !== rangeEnd) {
          const rangeX_end_pos =
            ((rangeEnd - chartData.x_min) /
              (chartData.x_max - chartData.x_min)) *
            numericChartWidth;
          const rangeY_end =
            y_start + matrixDimensions.matrixHeight - rangeX_end_pos;
          const endRotation = `rotate(-${rotationAngle}, ${labelX}, ${rangeY_end})`;
          createLabel(
            edgeGroup,
            labelX,
            rangeY_end,
            rangeEnd.toFixed(2),
            "start",
            "text-before-edge",
            endRotation
          );
        }
      } else if (position === "left") {
        const rangeY_start =
          y_start + matrixDimensions.matrixHeight - rangeX_start_pos;
        const labelX = x_start - edgeHeight - labelOffset;
        const rotation = `rotate(-${rotationAngle}, ${labelX}, ${rangeY_start})`;
        createLabel(
          edgeGroup,
          labelX,
          rangeY_start,
          rangeStart.toFixed(2),
          "end",
          "text-after-edge",
          rotation
        );

        if (rangeStart !== rangeEnd) {
          const rangeX_end_pos =
            ((rangeEnd - chartData.x_min) /
              (chartData.x_max - chartData.x_min)) *
            numericChartWidth;
          const rangeY_end =
            y_start + matrixDimensions.matrixHeight - rangeX_end_pos;
          const endRotation = `rotate(-${rotationAngle}, ${labelX}, ${rangeY_end})`;
          createLabel(
            edgeGroup,
            labelX,
            rangeY_end,
            rangeEnd.toFixed(2),
            "end",
            "text-after-edge",
            endRotation
          );
        }
      }
    };

    const highlightRelatedElements = (
      category: string,
      rangeStart: number,
      rangeEnd: number,
      useBlueHighlight = false
    ) => {
      removeHighlights();
      const highlightColor = useBlueHighlight
        ? MATRIX_CONFIG.colors.highlightPrimary
        : MATRIX_CONFIG.colors.highlightSecondary;
      edges.forEach((edge) => {
        const edgePos = edge as EdgePosition;
        const chartGroup = chartGroups[edgePos];
        const edgeGroup = edgeGroups[edgePos];
        if (!chartGroup) return;
        const edgeIndex = ["bottom", "right", "top", "left"].indexOf(edge);
        const chartType = chartTypes[edgeIndex];
        if (chartType === "character") {
          highlightCharacterChart(
            chartGroup,
            edgeGroup,
            edgePos,
            category,
            highlightColor
          );
        } else if (chartType === "numeric") {
          highlightNumericChart(
            chartGroup,
            edgeGroup,
            edgePos,
            rangeStart,
            rangeEnd,
            highlightColor
          );
        }
      });
    };

    const removeHighlights = () => {
      edges.forEach((edge) => {
        const edgePos = edge as EdgePosition;
        const chartGroup = chartGroups[edgePos];
        const edgeGroup = edgeGroups[edgePos];
        if (!chartGroup) return;
        const edgeIndex = ["bottom", "right", "top", "left"].indexOf(edge);
        const chartType = chartTypes[edgeIndex];
        if (chartType === "character") {
          chartGroup
            .selectAll("rect")
            .attr("fill", MATRIX_CONFIG.colors.barDefault);
          edgeGroup.selectAll(".highlight-label").remove();
        } else if (chartType === "numeric") {
          chartGroup.selectAll(".highlight-range").remove();
          edgeGroup.selectAll(".highlight-label").remove();
        }
      });
    };

    let lastClickedCategory: string | null = null;
    const handleChartClick = (category: string, chartPosition: string) => {
      if (currentTooltip) {
        currentTooltip.box.style("visibility", "hidden");
        currentTooltip.lines.line1.style("visibility", "hidden");
        currentTooltip.lines.line2.style("visibility", "hidden");
        currentTooltip = null;
      }

      if (ruleType.toLocaleLowerCase() === "multipleduplicate") {
        if (lastClickedCategory === category) {
          removeHighlights();
          lastClickedCategory = null;
          return;
        }

        removeHighlights();
        lastClickedCategory = category;

        const invalidNumericValues = invalid_index
          .filter((index) => {
            const dataCategory = csvData[index][characterColumn];
            return (
              String(dataCategory).toLowerCase() ===
              String(category).toLowerCase()
            );
          })
          .map((index) => csvData[index][numericColumn] as number);

        edges.forEach((edge) => {
          const edgePos = edge as EdgePosition;
          const chartGroup = chartGroups[edgePos];
          const edgeGroup = edgeGroups[edgePos];
          if (!chartGroup) return;

          const edgeIndex = ["bottom", "right", "top", "left"].indexOf(edge);
          const chartType = chartTypes[edgeIndex];

          if (chartType === "character") {
            highlightCharacterChart(
              chartGroup,
              edgeGroup,
              edgePos,
              category,
              MATRIX_CONFIG.colors.highlightSecondary
            );
          }
        });

        const uniqueInvalidNumericValues = [...new Set(invalidNumericValues)];
        uniqueInvalidNumericValues.forEach((numericValue) => {
          edges.forEach((edge) => {
            const edgePos = edge as EdgePosition;
            const chartGroup = chartGroups[edgePos];
            const edgeGroup = edgeGroups[edgePos];
            if (!chartGroup) return;

            const edgeIndex = ["bottom", "right", "top", "left"].indexOf(edge);
            const chartType = chartTypes[edgeIndex];

            if (chartType === "numeric") {
              highlightNumericChart(
                chartGroup,
                edgeGroup,
                edgePos,
                numericValue,
                numericValue,
                MATRIX_CONFIG.colors.highlightSecondary
              );
            }
          });
        });
      } else {
        const rule = invalid_range.find(
          (item) =>
            String(item.conditionContent).toLowerCase() ===
            String(category).toLowerCase()
        );

        removeHighlights();

        if (rule) {
          highlightRelatedElements(category, rule.start, rule.end, true);
        }
      }
    };

    const renderEdgeCharts = async () => {
      const edgeDefinitions = [
        { edge: "bottom", index: 0 },
        { edge: "right", index: 1 },
        { edge: "top", index: 2 },
        { edge: "left", index: 3 },
      ];

      const renderTasks: Promise<void>[] = [];

      edgeDefinitions.forEach(({ edge, index }) => {
        if (!(edges.includes(edge) && chartGroups[edge as EdgePosition])) {
          return;
        }

        const chartGroup = chartGroups[edge as EdgePosition]!;
        const chartType = chartTypes[index];
        const chartHeightForEdge = getEdgeChartHeight(edge as EdgePosition);

        if (chartType === "character") {
          const task = Promise.resolve(
            renderCharacterChart(
              chartGroup,
              csvData,
              characterColumn,
              matrixDimensions.matrixWidth,
              chartHeightForEdge,
              margin,
              updateHighlightedIndices,
              true,
              undefined,
              (category: string) => handleChartClick(category, edge)
            )
          ).then(() => {
            if (!chartData.characterCategories.length) {
              chartData.characterCategories = top10;
              chartData.characterX = x;
            }
          });
          renderTasks.push(task);
        } else {
          const task = Promise.resolve(
            renderNumericChart(
              chartGroup,
              csvData,
              numericColumn,
              matrixDimensions.matrixHeight,
              chartHeightForEdge,
              margin,
              updateHighlightedIndices,
              true
            )
          ).then((numericResult) => {
            if (chartData.x_min === 0 && chartData.x_max === 0) {
              chartData.x_min = numericResult.x_min;
              chartData.x_max = numericResult.x_max;
            }
          });
          renderTasks.push(task);
        }
      });

      await Promise.all(renderTasks);
    };

    await renderEdgeCharts();

    for (let i = 0; i < matrixDimensions.divisionsX; i++) {
      const offset =
        i * matrixDimensions.subSquareLength +
        matrixDimensions.subSquareLength / 2;
      matrixGroup
        .append("line")
        .attr("x1", x_start + offset)
        .attr("y1", y_start)
        .attr("x2", x_start + offset)
        .attr("y2", y_start + matrixDimensions.matrixHeight)
        .attr("stroke", MATRIX_CONFIG.colors.gridStroke)
        .attr("stroke-width", MATRIX_CONFIG.layout.gridStrokeWidth);
    }

    matrixGroup
      .append("rect")
      .attr("x", x_start)
      .attr("y", y_start)
      .attr("width", matrixDimensions.matrixWidth)
      .attr("height", matrixDimensions.matrixHeight)
      .attr("stroke", MATRIX_CONFIG.colors.borderStroke)
      .attr("stroke-width", MATRIX_CONFIG.layout.borderStrokeWidth)
      .attr("fill", "none")
      .attr("pointer-events", "none");

    let currentTooltip: {
      box: d3.Selection<HTMLElement, unknown, null, undefined>;
      lines: {
        line1: d3.Selection<SVGLineElement, unknown, HTMLElement, any>;
        line2: d3.Selection<SVGLineElement, unknown, HTMLElement, any>;
      };
    } | null = null;

    const tooltipCache = new Map<string, ReturnType<typeof createTooltip>>();

    const fixTooltipLayout = (tooltip: ReturnType<typeof createTooltip>) => {
      const divNode = tooltip.inputBox.select<HTMLDivElement>("div").node();
      if (!divNode) return;

      const { width, height } = divNode.getBoundingClientRect();
      const y3 = parseFloat(tooltip.tooltip_line_2.attr("y2"));

      tooltip.inputBox.attr("width", width).attr("height", height);
      tooltip.inputBox.attr("y", y3 - height / 2);
    };

    const getTooltipInstance = (
      key: string,
      factory: () => ReturnType<typeof createTooltip>
    ) => {
      let tooltipInstance = tooltipCache.get(key);
      if (!tooltipInstance) {
        tooltipInstance = factory();
        tooltipCache.set(key, tooltipInstance);
      }
      return tooltipInstance;
    };

    const handleTooltipInteraction = (
      tooltip: ReturnType<typeof createTooltip>,
      category: string,
      rangeStart: number,
      rangeEnd: number,
      isValid = false
    ) => {
      const isCurrentTooltipVisible =
        currentTooltip &&
        currentTooltip.box.style("visibility") === "visible" &&
        tooltip.inputBox.node() === currentTooltip.box.node();

      if (currentTooltip) {
        currentTooltip.box.style("visibility", "hidden");
        currentTooltip.lines.line1.style("visibility", "hidden");
        currentTooltip.lines.line2.style("visibility", "hidden");
        currentTooltip = null;
      }

      if (!isCurrentTooltipVisible) {
        fixTooltipLayout(tooltip);
        tooltip.tooltip_line_1.style("visibility", "visible").raise();
        tooltip.tooltip_line_2.style("visibility", "visible").raise();
        tooltip.inputBox.style("visibility", "visible").raise();

        currentTooltip = {
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

        highlightRelatedElements(category, rangeStart, rangeEnd, isValid);
      } else {
        removeHighlights();
      }
    };

    const renderValidRanges = () => {
      if (ruleType.toLocaleLowerCase() === "multipleduplicate") {
        return;
      }

      if (!invalid_range || invalid_range.length === 0) return;

      invalid_range.forEach((item) => {
        const conditionContent = item.conditionContent;
        const start = Math.max(item.start, chartData.x_min);
        const end = Math.min(item.end, chartData.x_max);

        const condition = String(conditionContent).toLowerCase();
        const foundCategoryIndex = chartData.characterCategories.findIndex(
          (d) => String(d.category).toLowerCase() === condition
        );

        if (foundCategoryIndex === -1) return;

        const rect_height =
          ((end - start) / (chartData.x_max - chartData.x_min)) *
          matrixDimensions.matrixHeight;
        const rect_end_height =
          ((chartData.x_max - end) / (chartData.x_max - chartData.x_min)) *
          matrixDimensions.matrixHeight;
        const rect_y = y_start + rect_end_height;

        const column_center_x =
          x_start +
          foundCategoryIndex * matrixDimensions.subSquareLength +
          matrixDimensions.subSquareLength / 2;
        const rect_width =
          matrixDimensions.subSquareLength *
          MATRIX_CONFIG.layout.validAreaWidthRatio;
        const rect_x = column_center_x - rect_width / 2;

        const x_for_tooltip = rect_x;
        const y_for_tooltip = rect_y + rect_height / 2 - rect_width / 2;

        const tooltipKey = `valid-${conditionContent}-${start}-${end}`;
        const tooltipFactory = () => {
          const tooltipTemplate = MATRIX_CONFIG.tooltips.getValidRuleTemplate(
            characterColumn,
            numericColumn,
            conditionContent,
            start,
            end,
            item.startInclusive,
            item.endInclusive,
            ruleType
          );

          return createTooltip(
            containerGroup,
            x_for_tooltip,
            y_for_tooltip,
            x_start,
            y_start,
            rect_width,
            tooltipTemplate,
            [characterColumn, numericColumn],
            ruleType || "Logical and condition",
            conditionContent,
            tooltipScaleRatio
          );
        };

        const areaId = `area-${conditionContent}-${start}-${end}`;

        matrixGroup
          .append("rect")
          .attr("id", "invalid-area")
          .attr("class", "invalid_range_start")
          .attr("x", rect_x)
          .attr("y", rect_y)
          .attr("width", rect_width)
          .attr("height", rect_height)
          .attr("fill", MATRIX_CONFIG.colors.highlightPrimary)
          .attr("stroke", "none")
          .attr("data-category", condition)
          .attr("data-range-start", start)
          .attr("data-range-end", end)
          .attr("data-area-id", areaId)
          .on("click", () => {
            const conditionClickEvent = new CustomEvent(
              "condition-area-clicked",
              {
                detail: {
                  conditionValue: conditionContent,
                  relationType: ruleType || "Logical and condition",
                  isRightClick: false,
                },
              }
            );
            window.dispatchEvent(conditionClickEvent);

            const tooltip = getTooltipInstance(tooltipKey, tooltipFactory);
            handleTooltipInteraction(
              tooltip,
              conditionContent,
              start,
              end,
              true
            );
          })
          .on("contextmenu", function (event) {
            event.preventDefault();
            const conditionClickEvent = new CustomEvent(
              "condition-area-clicked",
              {
                detail: {
                  conditionValue: conditionContent,
                  relationType: ruleType || "Logical and condition",
                  isRightClick: true,
                },
              }
            );
            window.dispatchEvent(conditionClickEvent);
          });
      });
    };

    renderValidRanges();

    const renderInvalidDataPoints = () => {
      const precise_invalidCount: Record<string, number> = {};
      const gridInvalidData: Record<string, number[]> = {};

      invalid_index.forEach((index) => {
        const invalid_data_character = csvData[index][characterColumn];
        const category = String(invalid_data_character).toLowerCase();

        const foundCategoryIndex = chartData.characterCategories.findIndex(
          (d) => String(d.category).toLowerCase() === category
        );

        const categoryPosition = chartData.characterX(
          foundCategoryIndex !== -1
            ? chartData.characterCategories[foundCategoryIndex].category
            : OTHER_CATEGORY_LABEL
        );
        if (categoryPosition === undefined) return;

        const characterChartWidth = matrixDimensions.matrixWidth;
        const barCenter =
          categoryPosition + chartData.characterX.bandwidth() / 2;
        const character_ratio = barCenter / characterChartWidth;

        let invalid_data_numeric = csvData[index][numericColumn];
        if (
          typeof invalid_data_numeric !== "number" ||
          isNaN(invalid_data_numeric)
        ) {
          invalid_data_numeric = 0;
        }
        const numeric_ratio =
          (invalid_data_numeric - chartData.x_min) /
          (chartData.x_max - chartData.x_min);

        if (numeric_ratio !== undefined) {
          const grid_x_index = Math.floor(
            character_ratio * matrixDimensions.divisionsX
          );
          const precise_x = grid_x_index;
          const precise_y =
            y_start + (1 - numeric_ratio) * matrixDimensions.matrixHeight;
          const precise_key = `${precise_x},${precise_y}`;

          if (!gridInvalidData[precise_key]) {
            gridInvalidData[precise_key] = [];
          }
          precise_invalidCount[precise_key] =
            (precise_invalidCount[precise_key] || 0) + 1;
          gridInvalidData[precise_key].push(index);
        }
      });

      Object.entries(precise_invalidCount).forEach(([precise_key, count]) => {
        const [precise_x, precise_y] = precise_key.split(",").map(Number);

        const subSquareLengthX =
          matrixDimensions.matrixWidth / matrixDimensions.divisionsX;
        const circleX =
          x_start + precise_x * subSquareLengthX + subSquareLengthX / 2;

        let circleY = precise_y;
        if (circleY < y_start + 2) circleY = y_start + 2;
        if (circleY > y_start + matrixDimensions.matrixHeight - 2)
          circleY = y_start + matrixDimensions.matrixHeight - 2;

        const categoryIndex = precise_x;
        const category =
          categoryIndex < chartData.characterCategories.length
            ? chartData.characterCategories[categoryIndex].category
            : OTHER_CATEGORY_LABEL;

        const normalizedY =
          (precise_y - y_start) / matrixDimensions.matrixHeight;
        const numericValue =
          chartData.x_min +
          (1 - normalizedY) * (chartData.x_max - chartData.x_min);

        const rectWidth = subSquareLengthX / 2 + subSquareLengthX / 4;
        const rectHeight = 2;
        const rectX = circleX - subSquareLengthX / 4 - subSquareLengthX / 8;

        const invalidDataRect = matrixGroup
          .append("rect")
          .attr("x", rectX)
          .attr("y", circleY)
          .attr("width", rectWidth)
          .attr("height", rectHeight)
          .attr("fill", MATRIX_CONFIG.colors.highlightSecondary)
          .attr("fill-opacity", MATRIX_CONFIG.colors.invalidDataOpacity)
          .attr("stroke", "none")
          .attr("id", "invalid-data")
          .attr("data-category", category)
          .attr("data-numeric-value", numericValue);

        const tooltipKey = `invalid-${precise_key}`;
        const tooltipFactory = () => {
          const tooltipTemplate = MATRIX_CONFIG.tooltips.getInvalidDataTemplate(
            characterColumn,
            numericColumn,
            category,
            numericValue,
            ruleType
          );

          const x_for_tooltip = rectX;
          const y_for_tooltip = circleY + rectHeight / 2 - rectWidth / 2;

          return createTooltip(
            containerGroup,
            x_for_tooltip,
            y_for_tooltip,
            x_start,
            y_start,
            rectWidth,
            tooltipTemplate,
            [characterColumn, numericColumn],
            ruleType,
            category,
            tooltipScaleRatio
          );
        };

        invalidDataRect.on("click", () => {
          const tooltip = getTooltipInstance(tooltipKey, tooltipFactory);
          const isCurrentTooltipVisible =
            currentTooltip &&
            currentTooltip.box.style("visibility") === "visible" &&
            tooltip.inputBox.node() === currentTooltip.box.node();

          if (currentTooltip) {
            currentTooltip.box.style("visibility", "hidden");
            currentTooltip.lines.line1.style("visibility", "hidden");
            currentTooltip.lines.line2.style("visibility", "hidden");
            currentTooltip = null;
          }

          const rowIds = gridInvalidData[precise_key] || [];
          const event = new CustomEvent("highlight-invalid-data", {
            detail: {
              rowIds: rowIds,
              highlightColumns: [characterColumn, numericColumn],
              sortedIndices: rowIds,
              isRightClick: false,
            },
          });
          window.dispatchEvent(event);

          if (!isCurrentTooltipVisible) {
            fixTooltipLayout(tooltip);
            tooltip.tooltip_line_1.style("visibility", "visible").raise();
            tooltip.tooltip_line_2.style("visibility", "visible").raise();
            tooltip.inputBox.style("visibility", "visible").raise();

            currentTooltip = {
              box: tooltip.inputBox as any,
              lines: {
                line1: tooltip.tooltip_line_1,
                line2: tooltip.tooltip_line_2,
              },
            };

            removeHighlights();
            highlightRelatedElements(category, numericValue, numericValue);
          } else {
            removeHighlights();
          }
        });

        invalidDataRect.on("contextmenu", (event) => {
          event.preventDefault();

          if (currentTooltip) {
            currentTooltip.box.style("visibility", "hidden");
            currentTooltip.lines.line1.style("visibility", "hidden");
            currentTooltip.lines.line2.style("visibility", "hidden");
            currentTooltip = null;
          }

          const rowIds = gridInvalidData[precise_key] || [];
          const highlightEvent = new CustomEvent("highlight-invalid-data", {
            detail: {
              rowIds: rowIds,
              highlightColumns: [characterColumn, numericColumn],
              sortedIndices: rowIds,
              isRightClick: true,
            },
          });
          window.dispatchEvent(highlightEvent);

          removeHighlights();
          highlightRelatedElements(category, numericValue, numericValue);
        });
      });
    };

    renderInvalidDataPoints();
  };

  await renderMatrix();

  const matrixDimensions = calculateMatrixDimensions(charactersCount);
  const { edgeOffset } = MATRIX_CONFIG.layout;
  const x_start = 0;
  const y_start = 0;

  let totalCalculatedWidth = matrixDimensions.matrixWidth;
  let totalCalculatedHeight = matrixDimensions.matrixHeight;
  let minX = 0;
  let minY = 0;

  if (edges.includes("left")) {
    const thickness = getEdgeChartHeight("left");
    totalCalculatedWidth += thickness + edgeOffset;
    minX = -(thickness + edgeOffset);
  }
  if (edges.includes("right")) {
    const thickness = getEdgeChartHeight("right");
    totalCalculatedWidth += thickness + edgeOffset;
  }
  if (edges.includes("top")) {
    const thickness = getEdgeChartHeight("top");
    totalCalculatedHeight += thickness + edgeOffset;
    minY = -(thickness + edgeOffset);
  }
  if (edges.includes("bottom")) {
    const thickness = getEdgeChartHeight("bottom");
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
    const scale = Math.min(scaleX, scaleY, 1); // cap maximum scale at 1

    const calculatedCenterX = minX + totalCalculatedWidth / 2;
    const calculatedCenterY = minY + totalCalculatedHeight / 2;

    const targetX = width / 2;
    const targetY = height / 2;

    const translateX = targetX - calculatedCenterX * scale;
    const translateY = targetY - calculatedCenterY * scale;

    const matrixCenterX = x_start + matrixDimensions.matrixWidth / 2;
    const matrixCenterY = y_start + matrixDimensions.matrixHeight / 2;

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
    .duration(MATRIX_CONFIG.animation.duration)
    .style("opacity", 1);
  loadingGroup.remove();
}
