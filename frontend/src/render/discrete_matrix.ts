import * as d3 from "d3";
import { renderCharacterChart } from "./character";
import {
  GridInvalidInfo,
  validRange_Equality_Equality,
  Row,
  MatrixDimensions,
  ConflictArea,
  CategoryData,
  HighlightState,
  CrossMatrixHighlightEvent,
  EdgePosition,
  EdgeGroups,
  ChartGroups,
  EdgeLabelInfo,
} from "@/types/types";
import { createLoadingAnimation } from "@/utils/utils";
import { createTooltip } from "@/utils/tootips";

const MATRIX_CONFIG = {
  colors: {
    gridStroke: "#cad2d7",
    borderStroke: "#9a9a9a",
    gridFill: "white",
    labelText: "black",
    barDefault: "#B5D2F8",
    highlightPrimary: "#4570b6",
    highlightSecondary: "#fd8d3c",
    conflictArea: "#FBDE71",
    invalidDataColor: "#fd8d3c",
  },
  layout: {
    edgeChartHeight: 120,
    labelOffset: 10,
    finalPadding: 0.1,
    defaultCellSize: 30,
    labelRotation: 45,
    gridStrokeWidth: 1,
    borderStrokeWidth: 1.5,
  },
  animation: {
    duration: 500,
  },
  dimensions: {
    containerTransform: "translate(0, 0)",
    width: 750,
    height: 250,
    margin: { top: 20, right: 20, bottom: 20, left: 20 },
  },
  tooltips: {
    /**
     * Tooltip template for valid rule areas.
     * @param cols Feature column names.
     * @param status1 Condition value.
     * @param status2 Constraint value.
     * @param ruleType Rule type.
     * @returns HTML string.
     */
    getValidRuleTemplate: (
      cols: string[],
      status1: string,
      status2: string,
      ruleType: string
    ): string => {
      switch (ruleType.toLowerCase()) {
        case "sequence":
          return `<strong style="color: black;">${status2}</strong> <strong style="color: red;">can</strong> follow <strong style="color: black;">${status1}</strong> in <strong style="color: black;">${cols[0]}</strong>.`;
        case "logical and condition":
        case "multiple logical and condition":
          return `if <strong style="color: black;">${
            cols[0]
          }</strong> is <strong style="color: red;">${status1}</strong>, then <strong style="color: black;">${
            cols[1]
          }</strong> needs to be <strong style="color: red;">${status2}</strong>${
            ruleType.toLowerCase() === "multiple logical and condition"
              ? " (part of multi-column rule)"
              : ""
          }.`;
        case "multipleduplicate":
          return `The combination of <strong style="color: black;">${cols[0]}</strong> = <strong style="color: red;">${status1}</strong> and <strong style="color: black;">${cols[1]}</strong> = <strong style="color: red;">${status2}</strong> is <strong style="color: red;">duplicated</strong>.`;
        default:
          return `if <strong style="color: black;">${cols[0]}</strong> is <strong style="color: red;">${status1}</strong>, then <strong style="color: black;">${cols[1]}</strong> needs to be <strong style="color: red;">${status2}</strong>.`;
      }
    },
    /**
     * Tooltip template for invalid data areas.
     * @param cols Feature column names.
     * @param category1 Category on the primary axis.
     * @param category2 Category on the secondary axis.
     * @param ruleType Rule type.
     * @returns HTML string.
     */
    getInvalidDataTemplate: (
      cols: string[],
      category1: string,
      category2: string,
      ruleType: string
    ): string => {
      switch (ruleType.toLowerCase()) {
        case "sequence":
          return `<strong style="color: black;">${category2}</strong> <strong style="color: red;">cannot</strong> follow <strong style="color: black;">${category1}</strong> in <strong style="color: black;">${cols[0]}</strong>.`;
        case "logical and condition":
        case "multiple logical and condition":
          return `if <strong style="color: black;">${
            cols[0]
          }</strong> is <strong style="color: red;">${category1}</strong>, then <strong style="color: black;">${
            cols[1]
          }</strong> <strong style="color: red;">cannot</strong> be <strong style="color: red;">${category2}</strong>${
            ruleType.toLowerCase() === "multiple logical and condition"
              ? " (part of multi-column rule)"
              : ""
          }.`;
        case "multipleduplicate":
          return `The combination of <strong style="color: black;">${cols[0]}</strong> = <strong style="color: red;">${category1}</strong> and <strong style="color: black;">${cols[1]}</strong> = <strong style="color: red;">${category2}</strong> is <strong style="color: red;">duplicated</strong>.`;
        default:
          return `if <strong style="color: black;">${cols[0]}</strong> is <strong style="color: red;">${category1}</strong>, then <strong style="color: black;">${cols[1]}</strong> <strong style="color: red;">cannot</strong> be <strong style="color: red;">${category2}</strong>.`;
      }
    },
    /**
     * Tooltip template for conflict areas.
     * @param cols Feature column names.
     * @param category1 Category on the primary axis.
     * @param category2 Category on the secondary axis.
     * @param ruleType Rule type.
     * @returns HTML string.
     */
    getConflictAreaTemplate: (
      cols: string[],
      category1: string,
      category2: string,
      ruleType: string
    ): string => {
      return `<strong style="color: black;">${cols[0]}</strong> = <strong style="color: red;">${category1}</strong> and <strong style="color: black;">${cols[1]}</strong> = <strong style="color: red;">${category2}</strong> has <strong style="color: orange;">conflicting rules</strong> (both valid and invalid cases exist).`;
    },
  },
};

/**
 * Ensures single-edge configurations are mirrored so layout math stays consistent.
 */
function processEdges(edges: string[]): {
  renderEdges: string[];
  visibleEdges: string[];
} {
  const renderEdges = [...edges];
  const visibleEdges = [...edges];

  if (renderEdges.length === 1) {
    const singleEdge = renderEdges[0];
    const edgePairs: Record<string, string> = {
      bottom: "right",
      right: "bottom",
      top: "left",
      left: "top",
    };

    if (edgePairs[singleEdge]) {
      renderEdges.push(edgePairs[singleEdge]);
    }
  }

  return { renderEdges, visibleEdges };
}

/**
 * Calculate matrix dimensions based on category counts and rule type.
 */
function calculateMatrixDimensions(
  categoryCount1: number,
  categoryCount2: number,
  ruleType: string
): MatrixDimensions {
  if (ruleType.toLowerCase() === "sequence") {
    const divisions = categoryCount1;
    const subSquareLength =
      (MATRIX_CONFIG.layout.defaultCellSize * divisions) / categoryCount1;
    return {
      divisions_left: divisions,
      divisions_right: divisions,
      subSquareLength_left: subSquareLength,
      subSquareLength_right: subSquareLength,
      matrixWidth: divisions * subSquareLength,
      matrixHeight: divisions * subSquareLength,
    };
  } else {
    const subSquareLength = MATRIX_CONFIG.layout.defaultCellSize;
    return {
      divisions_left: categoryCount1,
      divisions_right: categoryCount2,
      subSquareLength_left: subSquareLength,
      subSquareLength_right: subSquareLength,
      matrixWidth: categoryCount1 * subSquareLength,
      matrixHeight: categoryCount2 * subSquareLength,
    };
  }
}

/**
 * Create transform strings for edge charts.
 */
function createChartTransforms(
  x_start: number,
  y_start: number,
  matrixDimensions: MatrixDimensions
): Record<string, string> {
  const edgeChartHeight = MATRIX_CONFIG.layout.edgeChartHeight;

  return {
    bottom: `translate(${x_start}, ${
      y_start + matrixDimensions.matrixHeight + 10
    })`,
    right: `translate(${x_start + matrixDimensions.matrixWidth + 10}, ${
      y_start + matrixDimensions.matrixHeight
    }) rotate(-90)`,
    top: `translate(${x_start}, ${y_start - edgeChartHeight - 10})`,
    left: `translate(${x_start - edgeChartHeight - 10}, ${
      y_start + matrixDimensions.matrixHeight
    }) rotate(-90)`,
  };
}

/**
 * Draw a generic feature-feature or sequence matrix.
 * @param svg D3 group selection.
 * @param csvData Table rows.
 * @param selectedColumns Two feature names.
 * @param width Outer width.
 * @param height Outer height.
 * @param margin Margin configuration.
 * @param invalidIndicesOrPairs Invalid indices or invalid pairs for sequences.
 * @param validRuleRange Valid rule ranges to render.
 * @param updateHighlightedIndices Highlight callback.
 * @param ruleType Rule type label.
 * @param rotationAngle Final rotation angle.
 * @param edges Edges to render ["bottom", "right", "top", "left"].
 * @param conflictAreas Conflict areas to render.
 */
export async function discrete_matrix(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumns: string[],
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  invalidIndicesOrPairs:
    | number[]
    | {
        currentIndex: number;
        nextIndex: number;
        sortCurrentIndex: number;
        sortNextIndex: number;
      }[],
  validRuleRange: validRange_Equality_Equality[],
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  ruleType = "",
  rotationAngle = 45,
  edges: string[] = ["top", "left"],
  conflictAreas: ConflictArea[] = []
): Promise<void> {
  const cols: string[] = [selectedColumns[0], selectedColumns[1]];

  if (!Array.isArray(invalidIndicesOrPairs)) {
    throw new Error("invalidIndicesOrPairs must be an array");
  }

  const { renderEdges, visibleEdges } = processEdges(edges);
  const loadingGroup = svg.append("g").attr("class", "loading-animation");
  createLoadingAnimation(loadingGroup, width, height);

  const containerGroup = svg
    .append("g")
    .attr("transform", MATRIX_CONFIG.dimensions.containerTransform)
    .style("opacity", 0);

  const edgeGroups: EdgeGroups = {
    bottom: containerGroup.append("g").attr("class", "bottom-edge-group"),
    right: containerGroup.append("g").attr("class", "right-edge-group"),
    top: containerGroup.append("g").attr("class", "top-edge-group"),
    left: containerGroup.append("g").attr("class", "left-edge-group"),
  };

  const matrixGroup = containerGroup.append("g").attr("class", "matrix-group");
  const labelGroup = containerGroup.append("g").attr("class", "label-group");
  const column_1_Values = csvData.map((row) => row[cols[0]]);
  const column_2_Values = csvData.map((row) => row[cols[1]]);
  const Categories_1 = new Set(column_1_Values);
  const Categories_2 = new Set(column_2_Values);
  const CategoryCount_1 = Categories_1.size;
  const CategoryCount_2 = Categories_2.size;
  const x_start = 0;
  const y_start = 0;
  const matrixDimensions = calculateMatrixDimensions(
    CategoryCount_1,
    CategoryCount_2,
    ruleType
  );
  const edgeLabelsInfo: EdgeLabelInfo[] = [];
  const getCategoryPosition = (
    category: string,
    categoryArray: any[],
    xScale: d3.ScaleBand<string>
  ) => {
    const foundCategory = categoryArray.find(
      (d) => String(d.category).toLowerCase() === String(category).toLowerCase()
    );
    if (foundCategory) {
      return xScale(foundCategory.category);
    }
    return undefined;
  };
  const createLabelInfo = (
    edge: EdgePosition,
    x: number,
    y: number,
    text: string,
    anchor: string,
    baseline: string,
    value: string
  ): EdgeLabelInfo => {
    return {
      edge,
      category: text,
      value,
      x,
      y,
      anchor,
      baseline,
    };
  };

  const highlightBar = (
    chartGroup:
      | d3.Selection<SVGGElement, unknown, HTMLElement, any>
      | undefined,
    category: string,
    color: string
  ) => {
    if (chartGroup) {
      chartGroup
        .selectAll(`rect[data-category="${String(category).toLowerCase()}"]`)
        .attr("fill", color)
        .raise();
    }
  };

  const resetBars = (
    chartGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any> | undefined
  ) => {
    if (chartGroup) {
      chartGroup
        .selectAll("rect")
        .attr("fill", MATRIX_CONFIG.colors.barDefault);
    }
  };
  const addEdgeLabelInfo = (
    edge: EdgePosition,
    category: string,
    categoryData: CategoryData,
    value = ""
  ) => {
    const labelOffset = MATRIX_CONFIG.layout.labelOffset;
    const edgeChartHeight = MATRIX_CONFIG.layout.edgeChartHeight;

    if (edge === "bottom" || edge === "top") {
      const categoryPos = getCategoryPosition(
        category,
        categoryData.column1_categories,
        categoryData.column1_x
      );
      if (categoryPos !== undefined) {
        const barCenterX = categoryPos + categoryData.column1_x.bandwidth() / 2;
        const labelX = x_start + barCenterX;

        let labelY: number;
        let anchor: string;
        let baseline: string;

        if (edge === "bottom") {
          labelY =
            y_start +
            matrixDimensions.matrixHeight +
            edgeChartHeight +
            labelOffset;
          anchor = "end";
          baseline = "text-before-edge";
        } else {
          let actualBarHeight = edgeChartHeight;
          if (
            categoryData.column1_barHeights &&
            categoryData.column1_barHeights[category]
          ) {
            actualBarHeight = categoryData.column1_barHeights[category];
          }
          labelY =
            y_start -
            edgeChartHeight +
            (edgeChartHeight - actualBarHeight) -
            labelOffset;
          anchor = "start";
          baseline = "text-after-edge";
        }

        const labelInfo = createLabelInfo(
          edge,
          labelX,
          labelY,
          category,
          anchor,
          baseline,
          value
        );
        edgeLabelsInfo.push(labelInfo);
      }
    } else if (edge === "right" || edge === "left") {
      const categoryPos = getCategoryPosition(
        category,
        categoryData.column2_categories,
        categoryData.column2_x
      );
      if (categoryPos !== undefined) {
        const barCenterY = categoryPos + categoryData.column2_x.bandwidth() / 2;

        let yPos: number;
        let xPos: number;
        let anchor: string;
        const baseline = "text-before-edge";

        if (edge === "right") {
          xPos =
            x_start +
            matrixDimensions.matrixWidth +
            edgeChartHeight +
            labelOffset;
          yPos = y_start + matrixDimensions.matrixHeight - barCenterY;
          anchor = "start";
        } else {
          let actualBarWidth = edgeChartHeight;
          if (
            categoryData.column2_barHeights &&
            categoryData.column2_barHeights[category]
          ) {
            actualBarWidth = categoryData.column2_barHeights[category];
          }
          xPos =
            x_start -
            15 -
            edgeChartHeight +
            (edgeChartHeight - actualBarWidth) -
            labelOffset;
          yPos = y_start + matrixDimensions.matrixHeight - barCenterY - 10;
          anchor = "end";
        }

        const labelInfo = createLabelInfo(
          edge,
          xPos,
          yPos,
          category,
          anchor,
          baseline,
          value
        );
        edgeLabelsInfo.push(labelInfo);
      }
    }
  };
  const createAllLabels = () => {
    edgeLabelsInfo.forEach((labelInfo, index) => {
      labelGroup
        .append("text")
        .attr("class", "edge-label")
        .attr("data-edge", labelInfo.edge)
        .attr("data-category", labelInfo.category.toLowerCase())
        .attr("data-value", labelInfo.value)
        .attr("data-label-id", `label-${index}`)
        .attr("x", labelInfo.x)
        .attr("y", labelInfo.y)
        .attr("text-anchor", labelInfo.anchor)
        .attr("dominant-baseline", labelInfo.baseline)
        .attr("fill", MATRIX_CONFIG.colors.labelText)
        .attr(
          "transform",
          `rotate(-${MATRIX_CONFIG.layout.labelRotation}, ${labelInfo.x}, ${labelInfo.y})`
        )
        .style("visibility", "hidden")
        .text(labelInfo.value || labelInfo.category);
    });
  };
  const showEdgeLabels = (edges: EdgePosition[], categories: string[]) => {
    edges.forEach((edge) => {
      categories.forEach((category) => {
        labelGroup
          .selectAll(
            `.edge-label[data-edge="${edge}"][data-category="${String(
              category
            ).toLowerCase()}"]`
          )
          .style("visibility", "visible");
      });
    });
  };
  const hideAllLabels = () => {
    labelGroup.selectAll(".edge-label").style("visibility", "hidden");
  };
  const renderMatrix = async () => {
    matrixGroup.selectAll("*").remove();
    Object.values(edgeGroups).forEach((group) => group.selectAll("*").remove());

    matrixGroup
      .append("rect")
      .attr("x", x_start)
      .attr("y", y_start)
      .attr("width", matrixDimensions.matrixWidth)
      .attr("height", matrixDimensions.matrixHeight)
      .attr("stroke", MATRIX_CONFIG.colors.borderStroke)
      .attr("stroke-width", MATRIX_CONFIG.layout.borderStrokeWidth)
      .attr("fill", MATRIX_CONFIG.colors.gridFill);

    const chartGroups: ChartGroups = {};
    const chartTransforms = createChartTransforms(
      x_start,
      y_start,
      matrixDimensions
    );
    renderEdges.forEach((edge) => {
      if (chartTransforms[edge as EdgePosition]) {
        chartGroups[edge as EdgePosition] = edgeGroups[edge as EdgePosition]
          .append("g")
          .attr("transform", chartTransforms[edge as EdgePosition]);
      }
    });

    const highlightRelatedElements = (
      category1: string,
      category2: string,
      useBlueHighlight = false
    ) => {
      removeHighlights();

      const highlightColor = useBlueHighlight
        ? MATRIX_CONFIG.colors.highlightPrimary
        : MATRIX_CONFIG.colors.highlightSecondary;

      ["bottom", "top"].forEach((edge) => {
        if (renderEdges.includes(edge)) {
          highlightBar(
            chartGroups[edge as EdgePosition],
            category1,
            highlightColor
          );
        }
      });

      ["right", "left"].forEach((edge) => {
        if (renderEdges.includes(edge)) {
          highlightBar(
            chartGroups[edge as EdgePosition],
            category2,
            highlightColor
          );
        }
      });

      const horizontalEdges = renderEdges.filter((edge) =>
        ["bottom", "top"].includes(edge)
      ) as EdgePosition[];
      const verticalEdges = renderEdges.filter((edge) =>
        ["right", "left"].includes(edge)
      ) as EdgePosition[];

      showEdgeLabels(horizontalEdges, [category1]);
      showEdgeLabels(verticalEdges, [category2]);
    };
    const removeHighlights = () => {
      renderEdges.forEach((edge) => {
        resetBars(chartGroups[edge as EdgePosition]);
      });
      hideAllLabels();
    };
    const handleMatrixCellHighlight = (
      targetCategory: string,
      targetEdges: EdgePosition[],
      sourceCategory: string,
      isHorizontal: boolean
    ) => {
      const relatedCells = matrixGroup
        .selectAll("rect[id='matrix']")
        .filter(function () {
          const cell = d3.select(this);
          const checkCategory = isHorizontal
            ? "data-category1"
            : "data-category2";
          return (
            cell.attr(checkCategory) === String(sourceCategory).toLowerCase()
          );
        });

      if (relatedCells.size() > 0) {
        relatedCells.each(function () {
          const cell = d3.select(this);
          const categoryAttr = isHorizontal
            ? "data-category2"
            : "data-category1";
          const relatedCategory = cell.attr(categoryAttr);
          const fillColor = cell.attr("fill");

          targetEdges.forEach((edge) => {
            if (renderEdges.includes(edge)) {
              let color = MATRIX_CONFIG.colors.highlightSecondary;

              if (fillColor === MATRIX_CONFIG.colors.highlightPrimary) {
                color = MATRIX_CONFIG.colors.highlightPrimary;
              } else if (fillColor === MATRIX_CONFIG.colors.conflictArea) {
                color = MATRIX_CONFIG.colors.conflictArea;
              }

              if (fillColor !== MATRIX_CONFIG.colors.gridFill) {
                highlightBar(chartGroups[edge], relatedCategory, color);
                showEdgeLabels([edge], [relatedCategory]);
              }
            }
          });
        });
      }
    };
    const handleChartClick = (category: string, chartPosition: string) => {
      const chartGroup = chartGroups[chartPosition as EdgePosition];
      if (!chartGroup) return;

      if (currentTooltip) {
        currentTooltip.box.style("visibility", "hidden");
        currentTooltip.lines.line1.style("visibility", "hidden");
        currentTooltip.lines.line2.style("visibility", "hidden");
        currentTooltip = null;
      }

      const isAlreadyHighlighted =
        chartGroup
          .selectAll(`rect[data-category="${String(category).toLowerCase()}"]`)
          .filter(function (this: SVGRectElement) {
            return (
              d3.select(this).attr("fill") !== MATRIX_CONFIG.colors.barDefault
            );
          })
          .size() > 0;

      if (isAlreadyHighlighted) {
        if (ruleType === "multiple logical and condition") {
          const clearHighlightEvent = new CustomEvent(
            "clear-all-matrix-highlights",
            {
              detail: {
                source: "bar-click",
                category: category,
                chartPosition: chartPosition,
              },
            }
          );
          window.dispatchEvent(clearHighlightEvent);
        } else {
          removeHighlights();
        }
        return;
      }

      removeHighlights();

      if (ruleType === "multiple logical and condition") {
        const isHorizontal =
          chartPosition === "bottom" || chartPosition === "top";
        const columnIndex = isHorizontal ? 0 : 1;
        const clickedColumn = cols[columnIndex];

        const barClickEvent = new CustomEvent("matrix-bar-clicked", {
          detail: {
            category: category,
            column: clickedColumn,
            columnIndex: columnIndex,
            chartPosition: chartPosition,
            isHorizontal: isHorizontal,
            matrixColumns: cols,
          },
        });
        window.dispatchEvent(barClickEvent);
      }

      const isHorizontal =
        chartPosition === "bottom" || chartPosition === "top";
      const oppositeEdge = isHorizontal
        ? chartPosition === "bottom"
          ? "top"
          : "bottom"
        : chartPosition === "right"
        ? "left"
        : "right";

      const primaryEdge = chartPosition as EdgePosition;

      highlightBar(
        chartGroups[primaryEdge],
        category,
        MATRIX_CONFIG.colors.highlightPrimary
      );

      if (renderEdges.includes(oppositeEdge)) {
        highlightBar(
          chartGroups[oppositeEdge as EdgePosition],
          category,
          MATRIX_CONFIG.colors.highlightPrimary
        );
      }

      const edgesToShow = [primaryEdge];
      if (renderEdges.includes(oppositeEdge)) {
        edgesToShow.push(oppositeEdge as EdgePosition);
      }
      showEdgeLabels(edgesToShow, [category]);

      const otherEdges = isHorizontal ? ["right", "left"] : ["bottom", "top"];
      otherEdges.forEach((edge) => {
        if (renderEdges.includes(edge)) {
          resetBars(chartGroups[edge as EdgePosition]);
        }
      });

      handleMatrixCellHighlight(
        category,
        otherEdges as EdgePosition[],
        category,
        isHorizontal
      );
    };
    const categoryData: CategoryData = {
      column1_categories: [],
      column1_x: null,
      column2_categories: [],
      column2_x: null,
    };
    for (const edge of ["bottom", "top"]) {
      if (renderEdges.includes(edge) && chartGroups[edge as EdgePosition]) {
        const chartData = await renderCharacterChart(
          chartGroups[edge as EdgePosition]!,
          csvData,
          cols[0],
          matrixDimensions.matrixWidth,
          MATRIX_CONFIG.layout.edgeChartHeight,
          margin,
          updateHighlightedIndices,
          true,
          undefined,
          (category: string) => handleChartClick(category, edge)
        );
        if (!categoryData.column1_categories.length) {
          categoryData.column1_categories = chartData.top10;
          categoryData.column1_x = chartData.x;
          categoryData.column1_barHeights = chartData.barHeights;
        }
      }
    }
    for (const edge of ["right", "left"]) {
      if (renderEdges.includes(edge) && chartGroups[edge as EdgePosition]) {
        const chartData = await renderCharacterChart(
          chartGroups[edge as EdgePosition]!,
          csvData,
          cols[1],
          matrixDimensions.matrixHeight,
          MATRIX_CONFIG.layout.edgeChartHeight,
          margin,
          updateHighlightedIndices,
          true,
          undefined,
          (category: string) => handleChartClick(category, edge)
        );
        if (!categoryData.column2_categories.length) {
          categoryData.column2_categories = chartData.top10;
          categoryData.column2_x = chartData.x;
          categoryData.column2_barHeights = chartData.barHeights;
        }
      }
    }
    visibleEdges.forEach((edge) => {
      if (edge === "bottom" || edge === "top") {
        categoryData.column1_categories.forEach((categoryInfo) => {
          addEdgeLabelInfo(
            edge as EdgePosition,
            categoryInfo.category,
            categoryData,
            categoryInfo.category
          );
        });
      } else if (edge === "right" || edge === "left") {
        categoryData.column2_categories.forEach((categoryInfo) => {
          addEdgeLabelInfo(
            edge as EdgePosition,
            categoryInfo.category,
            categoryData,
            categoryInfo.category
          );
        });
      }
    });
    createAllLabels();
    let currentTooltip: {
      box: d3.Selection<HTMLElement, unknown, null, undefined>;
      lines: {
        line1: d3.Selection<SVGLineElement, unknown, HTMLElement, any>;
        line2: d3.Selection<SVGLineElement, unknown, HTMLElement, any>;
      };
    } | null = null;

    const createMatrixCell = (
      rectX: number,
      rectY: number,
      width: number,
      height: number,
      fillColor: string,
      category1: string,
      category2: string,
      areaId: string,
      tooltipTemplate: string,
      clickHandler: () => void,
      contextMenuHandler: (event: MouseEvent) => void,
      cellType: "valid" | "invalid" | "conflict" = "invalid",
      rowIds: number[] = [],
      sortedIndices: number[] = []
    ) => {
      let tooltip: any = null;
      if (ruleType !== "multiple logical and condition") {
        tooltip = createTooltip(
          containerGroup,
          rectX,
          rectY,
          x_start,
          y_start,
          ruleType.toLowerCase() === "sequence"
            ? matrixDimensions.subSquareLength_left
            : matrixDimensions.subSquareLength_right,
          tooltipTemplate,
          ruleType.toLowerCase() === "sequence" ? [cols[0]] : cols,
          ruleType,
          category1
        );
      }

      matrixGroup
        .append("rect")
        .attr("id", "matrix")
        .attr("x", rectX)
        .attr("y", rectY)
        .attr("width", width)
        .attr("height", height)
        .attr("stroke", "none")
        .attr("fill", fillColor)
        .attr("data-category1", String(category1).toLowerCase())
        .attr("data-category2", String(category2).toLowerCase())
        .attr("data-area-id", areaId)
        .attr("data-cell-type", cellType)
        .attr("data-row-ids", JSON.stringify(rowIds))
        .attr("data-sorted-indices", JSON.stringify(sortedIndices))
        .on("click", function () {
          clickHandler();
          if (ruleType !== "multiple logical and condition" && tooltip) {
            handleTooltipInteraction(
              tooltip,
              category1,
              category2,
              fillColor === MATRIX_CONFIG.colors.highlightPrimary,
              cellType === "conflict"
            );
          }
        })
        .on("contextmenu", function (event) {
          event.preventDefault();
          contextMenuHandler(event);
        });
    };
    const handleTooltipInteraction = (
      tooltip: any,
      category1: string,
      category2: string,
      isValid = false,
      isConflict = false
    ) => {
      if (ruleType === "multiple logical and condition") {
        return;
      }

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
        tooltip.tooltip_line_1.style("visibility", "visible").raise();
        tooltip.tooltip_line_2.style("visibility", "visible").raise();
        tooltip.inputBox.style("visibility", "visible");
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

        if (isConflict) {
          highlightRelatedElements(category1, category2, false);
          ["bottom", "top"].forEach((edge) => {
            if (renderEdges.includes(edge)) {
              highlightBar(
                chartGroups[edge as EdgePosition],
                category1,
                MATRIX_CONFIG.colors.conflictArea
              );
            }
          });
          ["right", "left"].forEach((edge) => {
            if (renderEdges.includes(edge)) {
              highlightBar(
                chartGroups[edge as EdgePosition],
                category2,
                MATRIX_CONFIG.colors.conflictArea
              );
            }
          });
          const horizontalEdges = renderEdges.filter((edge) =>
            ["bottom", "top"].includes(edge)
          ) as EdgePosition[];
          const verticalEdges = renderEdges.filter((edge) =>
            ["right", "left"].includes(edge)
          ) as EdgePosition[];
          showEdgeLabels(horizontalEdges, [category1]);
          showEdgeLabels(verticalEdges, [category2]);
        } else {
          highlightRelatedElements(category1, category2, isValid);
        }
      } else {
        removeHighlights();
      }
    };

    if (conflictAreas && conflictAreas.length > 0) {
      conflictAreas.forEach((conflictArea) => {
        const category_1 = String(conflictArea.category1).toLowerCase();
        const category_2 = String(conflictArea.category2).toLowerCase();

        const foundCategoryIndex_1 = categoryData.column1_categories.findIndex(
          (d) => String(d.category).toLowerCase() === category_1
        );
        const foundCategoryIndex_2 = categoryData.column2_categories.findIndex(
          (d) => String(d.category).toLowerCase() === category_2
        );

        if (foundCategoryIndex_1 === -1 || foundCategoryIndex_2 === -1) {
          return;
        }

        const categoryPosition_1 = categoryData.column1_x(
          categoryData.column1_categories[foundCategoryIndex_1].category
        );
        const categoryPosition_2 = categoryData.column2_x(
          categoryData.column2_categories[foundCategoryIndex_2].category
        );

        if (
          categoryPosition_1 === undefined ||
          categoryPosition_2 === undefined
        )
          return;

        const barCenter_1 =
          categoryPosition_1 + categoryData.column1_x.bandwidth() / 2;
        const barCenter_2 =
          categoryPosition_2 + categoryData.column2_x.bandwidth() / 2;
        const status_ratio_1 = barCenter_1 / matrixDimensions.matrixWidth;
        const status_ratio_2 = barCenter_2 / matrixDimensions.matrixHeight;
        const grid_x_index = Math.floor(
          status_ratio_1 * matrixDimensions.divisions_left
        );
        const grid_y_index =
          ruleType.toLowerCase() === "sequence"
            ? matrixDimensions.divisions_right -
              1 -
              Math.floor(status_ratio_2 * matrixDimensions.divisions_right)
            : Math.floor(
                (1 - status_ratio_2) * matrixDimensions.divisions_right
              );
        const rectX =
          x_start + grid_x_index * matrixDimensions.subSquareLength_left;
        const rectY =
          y_start + grid_y_index * matrixDimensions.subSquareLength_right;

        const tooltipTemplate = MATRIX_CONFIG.tooltips.getConflictAreaTemplate(
          cols,
          conflictArea.category1,
          conflictArea.category2,
          ruleType
        );

        const areaId = `conflict-area-${conflictArea.category1}-${conflictArea.category2}`;

        const associatedInvalidData = {
          rowIds: [] as number[],
          sortedIndices: [] as number[],
        };

        if (ruleType.toLowerCase() === "sequence") {
          const invalidPairs = invalidIndicesOrPairs as {
            currentIndex: number;
            nextIndex: number;
            sortCurrentIndex: number;
            sortNextIndex: number;
          }[];
          invalidPairs.forEach((pair) => {
            const status1 = String(
              csvData[pair.currentIndex][cols[0]]
            ).toLowerCase();
            const status2 = String(
              csvData[pair.nextIndex][cols[0]]
            ).toLowerCase();
            if (status1 === category_1 && status2 === category_2) {
              associatedInvalidData.rowIds.push(
                pair.currentIndex,
                pair.nextIndex
              );
              associatedInvalidData.sortedIndices.push(
                pair.sortCurrentIndex,
                pair.sortNextIndex
              );
            }
          });
        } else {
          const invalidIndices = invalidIndicesOrPairs as number[];
          invalidIndices.forEach((index) => {
            const status1 = String(csvData[index][cols[0]]).toLowerCase();
            const status2 = String(csvData[index][cols[1]]).toLowerCase();
            if (status1 === category_1 && status2 === category_2) {
              associatedInvalidData.rowIds.push(index);
              associatedInvalidData.sortedIndices.push(index);
            }
          });
        }

        const uniqueRowIds = [...new Set(associatedInvalidData.rowIds)];
        const uniqueSortedIndices = [
          ...new Set(associatedInvalidData.sortedIndices),
        ];

        createMatrixCell(
          rectX,
          rectY,
          matrixDimensions.subSquareLength_left,
          matrixDimensions.subSquareLength_right,
          MATRIX_CONFIG.colors.conflictArea,
          conflictArea.category1,
          conflictArea.category2,
          areaId,
          tooltipTemplate,
          () => {
            const eventType = "conflict-area-clicked";
            const eventDetail = {
              category1: conflictArea.category1,
              category2: conflictArea.category2,
              conflictType: conflictArea.conflictType,
              relationType: ruleType,
              isRightClick: false,
            };

            const clickEvent = new CustomEvent(eventType, {
              detail: eventDetail,
            });
            window.dispatchEvent(clickEvent);
          },
          () => {
            const eventType = "conflict-area-clicked";
            const eventDetail = {
              category1: conflictArea.category1,
              category2: conflictArea.category2,
              conflictType: conflictArea.conflictType,
              relationType: ruleType,
              isRightClick: true,
            };

            const clickEvent = new CustomEvent(eventType, {
              detail: eventDetail,
            });
            window.dispatchEvent(clickEvent);
          },
          "conflict",
          uniqueRowIds,
          uniqueSortedIndices
        );
      });
    }
    if (
      ruleType !== "condition" &&
      validRuleRange &&
      validRuleRange.length > 0
    ) {
      validRuleRange.forEach((item) => {
        const conditionContent = item.conditionValue;
        const constraintContentArray = item.constraintValue;

        constraintContentArray?.forEach((constraintContent) => {
          const invalid_status_1 = conditionContent;
          const invalid_status_2 = constraintContent;
          const category_1 = String(invalid_status_1).toLowerCase();
          const category_2 = String(invalid_status_2).toLowerCase();
          const isConflict = conflictAreas.some(
            (conflict) =>
              String(conflict.category1).toLowerCase() === category_1 &&
              String(conflict.category2).toLowerCase() === category_2
          );
          if (isConflict) {
            return;
          }

          const foundCategoryIndex_1 =
            categoryData.column1_categories.findIndex(
              (d) => String(d.category).toLowerCase() === category_1
            );
          const foundCategoryIndex_2 =
            categoryData.column2_categories.findIndex(
              (d) => String(d.category).toLowerCase() === category_2
            );

          if (foundCategoryIndex_1 === -1 || foundCategoryIndex_2 === -1) {
            return;
          }

          const categoryPosition_1 = categoryData.column1_x(
            categoryData.column1_categories[foundCategoryIndex_1].category
          );
          const categoryPosition_2 = categoryData.column2_x(
            categoryData.column2_categories[foundCategoryIndex_2].category
          );

          if (
            categoryPosition_1 === undefined ||
            categoryPosition_2 === undefined
          )
            return;

          const barCenter_1 =
            categoryPosition_1 + categoryData.column1_x.bandwidth() / 2;
          const barCenter_2 =
            categoryPosition_2 + categoryData.column2_x.bandwidth() / 2;
          const status_ratio_1 = barCenter_1 / matrixDimensions.matrixWidth;
          const status_ratio_2 = barCenter_2 / matrixDimensions.matrixHeight;
          const grid_x_index = Math.floor(
            status_ratio_1 * matrixDimensions.divisions_left
          );
          const grid_y_index =
            ruleType.toLowerCase() === "sequence"
              ? matrixDimensions.divisions_right -
                1 -
                Math.floor(status_ratio_2 * matrixDimensions.divisions_right)
              : Math.floor(
                  (1 - status_ratio_2) * matrixDimensions.divisions_right
                );
          const rectX =
            x_start + grid_x_index * matrixDimensions.subSquareLength_left;
          const rectY =
            y_start + grid_y_index * matrixDimensions.subSquareLength_right;

          const tooltipTemplate = MATRIX_CONFIG.tooltips.getValidRuleTemplate(
            ruleType.toLowerCase() === "sequence" ? [cols[0]] : cols,
            invalid_status_1,
            invalid_status_2,
            ruleType
          );

          const areaId = `area-${invalid_status_1}-${invalid_status_2}`;

          createMatrixCell(
            rectX,
            rectY,
            matrixDimensions.subSquareLength_left,
            matrixDimensions.subSquareLength_right,
            MATRIX_CONFIG.colors.highlightPrimary,
            invalid_status_1,
            invalid_status_2,
            areaId,
            tooltipTemplate,
            () => {
              const eventType =
                ruleType.toLowerCase() === "sequence"
                  ? "matrix-cell-clicked"
                  : "condition-area-clicked";
              const eventDetail =
                ruleType.toLowerCase() === "sequence"
                  ? {
                      category1: invalid_status_1,
                      category2: invalid_status_2,
                      relationType: "Sequence",
                    }
                  : {
                      conditionValue: invalid_status_1,
                      constraintValue: invalid_status_2,
                      relationType: ruleType,
                      isRightClick: false,
                    };

              const clickEvent = new CustomEvent(eventType, {
                detail: eventDetail,
              });
              window.dispatchEvent(clickEvent);
            },
            () => {
              const eventType =
                ruleType.toLowerCase() === "sequence"
                  ? "matrix-cell-clicked"
                  : "condition-area-clicked";
              const eventDetail =
                ruleType.toLowerCase() === "sequence"
                  ? {
                      category1: invalid_status_1,
                      category2: invalid_status_2,
                      relationType: "Sequence",
                      isRightClick: true,
                    }
                  : {
                      conditionValue: invalid_status_1,
                      constraintValue: invalid_status_2,
                      relationType: ruleType,
                      isRightClick: true,
                    };

              const clickEvent = new CustomEvent(eventType, {
                detail: eventDetail,
              });
              window.dispatchEvent(clickEvent);
            },
            "valid"
          );
        });
      });
    }
    const gridinvalidCount: Record<string, GridInvalidInfo> = {};
    const sortedIndices: Record<string, number[]> = {};

    if (ruleType.toLowerCase() === "sequence") {
      const invalid_pairs = invalidIndicesOrPairs as {
        currentIndex: number;
        nextIndex: number;
        sortCurrentIndex: number;
        sortNextIndex: number;
      }[];

      invalid_pairs.forEach((invalid_pair) => {
        const currentIndex = invalid_pair.currentIndex;
        const nextIndex = invalid_pair.nextIndex;
        const sortCurrentIndex = invalid_pair.sortCurrentIndex;
        const sortNextIndex = invalid_pair.sortNextIndex;

        const invalid_status_1 = csvData[currentIndex][cols[0]];
        const invalid_status_2 = csvData[nextIndex][cols[0]];

        const category_1 = String(invalid_status_1).toLowerCase();
        const category_2 = String(invalid_status_2).toLowerCase();

        const foundCategoryIndex_1 = categoryData.column1_categories.findIndex(
          (d) => String(d.category).toLowerCase() === category_1
        );
        const foundCategoryIndex_2 = categoryData.column1_categories.findIndex(
          (d) => String(d.category).toLowerCase() === category_2
        );

        if (foundCategoryIndex_1 === -1 || foundCategoryIndex_2 === -1) {
          return;
        }

        const categoryPosition_1 = categoryData.column1_x(
          categoryData.column1_categories[foundCategoryIndex_1].category
        );
        const categoryPosition_2 = categoryData.column1_x(
          categoryData.column1_categories[foundCategoryIndex_2].category
        );

        if (
          categoryPosition_1 === undefined ||
          categoryPosition_2 === undefined
        )
          return;

        const barCenter_1 =
          categoryPosition_1 + categoryData.column1_x.bandwidth() / 2;
        const barCenter_2 =
          categoryPosition_2 + categoryData.column1_x.bandwidth() / 2;

        const status_ratio_1 = barCenter_1 / matrixDimensions.matrixWidth;
        const status_ratio_2 = barCenter_2 / matrixDimensions.matrixHeight;

        const grid_x_index = Math.floor(
          status_ratio_1 * matrixDimensions.divisions_left
        );
        const grid_y_index =
          matrixDimensions.divisions_right -
          1 -
          Math.floor(status_ratio_2 * matrixDimensions.divisions_right);

        const gridKey = `${grid_x_index},${grid_y_index}`;

        if (!gridinvalidCount[gridKey]) {
          gridinvalidCount[gridKey] = {
            count: 0,
            category1: "",
            category2: "",
            indices: [],
          };
          sortedIndices[gridKey] = [];
        }

        gridinvalidCount[gridKey].category1 = invalid_status_1 as string;
        gridinvalidCount[gridKey].category2 = invalid_status_2 as string;
        gridinvalidCount[gridKey].count += 1;
        gridinvalidCount[gridKey].indices.push(currentIndex, nextIndex);
        sortedIndices[gridKey].push(sortCurrentIndex, sortNextIndex);
      });
    } else {
      const invalid_indices = invalidIndicesOrPairs as number[];

      invalid_indices.forEach((index) => {
        const invalid_status_1 = csvData[index][cols[0]];
        const invalid_status_2 = csvData[index][cols[1]];

        const category_1 = String(invalid_status_1).toLowerCase();
        const category_2 = String(invalid_status_2).toLowerCase();

        const foundCategoryIndex_1 = categoryData.column1_categories.findIndex(
          (d) => String(d.category).toLowerCase() === category_1
        );
        const foundCategoryIndex_2 = categoryData.column2_categories.findIndex(
          (d) => String(d.category).toLowerCase() === category_2
        );

        if (foundCategoryIndex_1 === -1 || foundCategoryIndex_2 === -1) {
          return;
        }

        const categoryPosition_1 = categoryData.column1_x(
          categoryData.column1_categories[foundCategoryIndex_1].category
        );
        const categoryPosition_2 = categoryData.column2_x(
          categoryData.column2_categories[foundCategoryIndex_2].category
        );

        if (
          categoryPosition_1 === undefined ||
          categoryPosition_2 === undefined
        )
          return;

        const barCenter_1 =
          categoryPosition_1 + categoryData.column1_x.bandwidth() / 2;
        const barCenter_2 =
          categoryPosition_2 + categoryData.column2_x.bandwidth() / 2;

        const status_ratio_1 = barCenter_1 / matrixDimensions.matrixWidth;
        const status_ratio_2 = barCenter_2 / matrixDimensions.matrixHeight;

        const grid_x_index = Math.floor(
          status_ratio_1 * matrixDimensions.divisions_left
        );
        const grid_y_index = Math.floor(
          (1 - status_ratio_2) * matrixDimensions.divisions_right
        );

        const gridKey = `${grid_x_index},${grid_y_index}`;

        if (!gridinvalidCount[gridKey]) {
          gridinvalidCount[gridKey] = {
            count: 0,
            category1: "",
            category2: "",
            indices: [],
          };
          sortedIndices[gridKey] = [];
        }

        gridinvalidCount[gridKey].category1 = invalid_status_1 as string;
        gridinvalidCount[gridKey].category2 = invalid_status_2 as string;
        gridinvalidCount[gridKey].count += 1;
        gridinvalidCount[gridKey].indices.push(index);
        sortedIndices[gridKey].push(index);
      });
    }

    if (Object.keys(gridinvalidCount).length > 0) {
      Object.entries(gridinvalidCount).forEach(([gridKey, info]) => {
        const isConflict = conflictAreas.some(
          (conflict) =>
            String(conflict.category1).toLowerCase() ===
              String(info.category1).toLowerCase() &&
            String(conflict.category2).toLowerCase() ===
              String(info.category2).toLowerCase()
        );
        if (isConflict) {
          return;
        }

        const [grid_x_index, grid_y_index] = gridKey.split(",").map(Number);

        const rectX =
          x_start + grid_x_index * matrixDimensions.subSquareLength_left;
        const rectY =
          y_start + grid_y_index * matrixDimensions.subSquareLength_right;
        const fillColor_invalid = MATRIX_CONFIG.colors.invalidDataColor;
        const tooltipTemplate = MATRIX_CONFIG.tooltips.getInvalidDataTemplate(
          ruleType.toLowerCase() === "sequence" ? [cols[0]] : cols,
          info.category1,
          info.category2,
          ruleType
        );

        const areaId = `invalid-area-${info.category1}-${info.category2}`;

        createMatrixCell(
          rectX,
          rectY,
          matrixDimensions.subSquareLength_left,
          matrixDimensions.subSquareLength_right,
          fillColor_invalid,
          info.category1,
          info.category2,
          areaId,
          tooltipTemplate,
          () => {
            const eventType =
              ruleType.toLowerCase() === "sequence"
                ? "matrix-cell-clicked"
                : "condition-area-clicked";
            const eventDetail =
              ruleType.toLowerCase() === "sequence"
                ? {
                    category1: info.category1,
                    category2: info.category2,
                    relationType: "Sequence",
                    isRightClick: false,
                  }
                : {
                    conditionValue: info.category1,
                    constraintValue: info.category2,
                    relationType: ruleType,
                    isRightClick: false,
                  };

            const clickEvent = new CustomEvent(eventType, {
              detail: eventDetail,
            });
            window.dispatchEvent(clickEvent);

            const rowIds = gridinvalidCount[gridKey].indices || [];
            const scrollIndices = sortedIndices[gridKey] || [];
            const highlightEvent = new CustomEvent("highlight-invalid-data", {
              detail: {
                rowIds: rowIds,
                highlightColumns: cols,
                sortedIndices: scrollIndices,
                isRightClick: false,
                disableRefine: ["sequence", "lookup"].includes(
                  ruleType.toLowerCase()
                ),
              },
            });
            window.dispatchEvent(highlightEvent);
          },
          (event) => {
            const eventType =
              ruleType.toLowerCase() === "sequence"
                ? "matrix-cell-clicked"
                : "condition-area-clicked";
            const eventDetail =
              ruleType.toLowerCase() === "sequence"
                ? {
                    category1: info.category1,
                    category2: info.category2,
                    relationType: "Sequence",
                    isRightClick: true,
                  }
                : {
                    conditionValue: info.category1,
                    constraintValue: info.category2,
                    relationType: ruleType,
                    isRightClick: true,
                  };

            const clickEvent = new CustomEvent(eventType, {
              detail: eventDetail,
            });
            window.dispatchEvent(clickEvent);

            const rowIds = gridinvalidCount[gridKey].indices || [];
            const scrollIndices = sortedIndices[gridKey] || [];
            const highlightEvent = new CustomEvent("highlight-invalid-data", {
              detail: {
                rowIds: rowIds,
                highlightColumns: cols,
                sortedIndices: scrollIndices,
                isRightClick: true,
                disableRefine: ["sequence", "lookup"].includes(
                  ruleType.toLowerCase()
                ),
              },
            });
            window.dispatchEvent(highlightEvent);
          },
          "invalid",
          gridinvalidCount[gridKey].indices,
          sortedIndices[gridKey]
        );
      });
    }
    for (let i = 0; i <= matrixDimensions.divisions_right; i++) {
      const offset = i * matrixDimensions.subSquareLength_right;
      matrixGroup
        .append("line")
        .attr("x1", x_start)
        .attr("y1", y_start + offset)
        .attr("x2", x_start + matrixDimensions.matrixWidth)
        .attr("y2", y_start + offset)
        .attr("stroke", MATRIX_CONFIG.colors.gridStroke)
        .attr("stroke-width", MATRIX_CONFIG.layout.gridStrokeWidth);
    }

    for (let i = 0; i <= matrixDimensions.divisions_left; i++) {
      const offset = i * matrixDimensions.subSquareLength_left;
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

    renderEdges.forEach((edge) => {
      if (!visibleEdges.includes(edge)) {
        edgeGroups[edge as EdgePosition].style("display", "none");
      }
    });
  };
  await renderMatrix();
  loadingGroup.remove();
  const gap = 10;
  const edgeChartHeight = MATRIX_CONFIG.layout.edgeChartHeight;

  let totalCalculatedWidth = matrixDimensions.matrixWidth;
  let totalCalculatedHeight = matrixDimensions.matrixHeight;
  let minX = 0;
  let minY = 0;

  // MODIFICATION: Use renderEdges for layout calculation
  if (renderEdges.includes("left")) {
    totalCalculatedWidth += edgeChartHeight + gap;
    minX = -(edgeChartHeight + gap);
  }
  if (renderEdges.includes("right")) {
    totalCalculatedWidth += edgeChartHeight + gap;
  }
  if (renderEdges.includes("top")) {
    totalCalculatedHeight += edgeChartHeight + gap;
    minY = -(edgeChartHeight + gap);
  }
  if (renderEdges.includes("bottom")) {
    totalCalculatedHeight += edgeChartHeight + gap;
  }
  // console.log("Rendered Edges for Calculation:", renderEdges);

  if (
    totalCalculatedWidth > 0 &&
    totalCalculatedHeight > 0 &&
    ruleType !== "multiple logical and condition"
  ) {
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
    const scale = Math.min(scaleX, scaleY, 1);

    const calculatedCenterX = minX + totalCalculatedWidth / 2;
    const calculatedCenterY = minY + totalCalculatedHeight / 2;

    const targetX = width / 2;
    const targetY = height / 2;

    const translateX = targetX - calculatedCenterX * scale;
    const translateY = targetY - calculatedCenterY * scale;

    const matrixCenterX = x_start + matrixDimensions.matrixWidth / 2;
    const matrixCenterY = y_start + matrixDimensions.matrixHeight / 2;

    containerGroup
      .attr(
        "transform",
        `translate(${translateX}, ${translateY}) scale(${scale}) rotate(${rotationAngle}, ${matrixCenterX}, ${matrixCenterY})`
      )
      .transition()
      .duration(MATRIX_CONFIG.animation.duration)
      .style("opacity", 1);
  } else {
    containerGroup
      .attr(
        "transform",
        `${MATRIX_CONFIG.dimensions.containerTransform} rotate(${rotationAngle})`
      )
      .transition()
      .duration(MATRIX_CONFIG.animation.duration)
      .style("opacity", 1);
  }
}

export async function renderMatrixCore(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  config: any,
  eventBus: any
): Promise<any> {
  let currentHighlightState: HighlightState | null = null;

  const updateHighlightedIndices = (indices: number[], columns: string[]) => {
    eventBus.emit("indices-highlighted", {
      matrixId: config.position,
      indices,
      columns,
    });
  };
  await discrete_matrix(
    svg,
    config.data,
    config.columns,
    MATRIX_CONFIG.dimensions.width,
    MATRIX_CONFIG.dimensions.height,
    MATRIX_CONFIG.dimensions.margin,
    config.invalidIndices,
    config.validRules,
    updateHighlightedIndices,
    config.ruleType,
    config.rotationAngle || 0,
    config.edges,
    config.conflictAreas
  );
  const matrixCells = svg.selectAll("rect[id='matrix']");
  matrixCells.each(function () {
    const element = d3.select(this);
    const category1 = element.attr("data-category1");
    const category2 = element.attr("data-category2");
    const cellType = element.attr("data-cell-type") || "invalid";
    const rowIds = JSON.parse(element.attr("data-row-ids") || "[]");
    const sortedIndices = JSON.parse(
      element.attr("data-sorted-indices") || "[]"
    );

    if (!category1 || !category2) return;

    const originalClickHandler = element.on("click");
    const originalContextMenuHandler = element.on("contextmenu");
    element.on("click", function (event, d) {
      if (originalClickHandler) {
        originalClickHandler.call(this, event, d);
      }
      eventBus.emit("matrix-cell-clicked", {
        matrixId: config.position,
        category1,
        category2,
        cellType,
        isRightClick: false,
        rowIds,
        sortedIndices,
      });
    });

    element.on("contextmenu", function (event, d) {
      event.preventDefault();
      if (originalContextMenuHandler) {
        originalContextMenuHandler.call(this, event, d);
      }
      eventBus.emit("matrix-cell-clicked", {
        matrixId: config.position,
        category1,
        category2,
        cellType,
        isRightClick: true,
        rowIds,
        sortedIndices,
      });
    });
  });

  return {
    id: config.position,
    config: config,
    svg: svg,
    updateHighlights: (highlights: HighlightState) => {
      currentHighlightState = highlights;
      svg
        .selectAll(
          ".bottom-edge-group rect, .top-edge-group rect, .right-edge-group rect, .left-edge-group rect"
        )
        .attr("fill", "#B5D2F8");
      highlights.category1Highlights.forEach((highlight) => {
        highlight.edges.forEach((edge) => {
          const selector = `.${edge}-edge-group rect[data-category="${highlight.category.toLowerCase()}"]`;
          const bars = svg.selectAll(selector);
          bars.attr("fill", highlight.color).raise();
        });
      });
      highlights.category2Highlights.forEach((highlight) => {
        highlight.edges.forEach((edge) => {
          const selector = `.${edge}-edge-group rect[data-category="${highlight.category.toLowerCase()}"]`;
          const bars = svg.selectAll(selector);
          bars.attr("fill", highlight.color).raise();
        });
      });
    },

    clearHighlights: () => {
      svg
        .selectAll(
          ".bottom-edge-group rect, .top-edge-group rect, .right-edge-group rect, .left-edge-group rect"
        )
        .attr("fill", "#B5D2F8");
      svg.selectAll(".edge-label").style("visibility", "hidden");

      currentHighlightState = null;
    },
    getRelatedCategories: (category1: string, category2: string) => {
      return {
        relatedInMatrix1: [],
        relatedInMatrix2: [],
      };
    },
    getDimensions: () => {
      const column_1_Values = config.data.map(
        (row: any) => row[config.columns[0]]
      );
      const column_2_Values = config.data.map(
        (row: any) => row[config.columns[1]]
      );
      const Categories_1 = new Set(column_1_Values);
      const Categories_2 = new Set(column_2_Values);
      const CategoryCount_1 = Categories_1.size;
      const CategoryCount_2 = Categories_2.size;

      const matrixWidth =
        CategoryCount_1 * MATRIX_CONFIG.layout.defaultCellSize;
      const matrixHeight =
        CategoryCount_2 * MATRIX_CONFIG.layout.defaultCellSize;
      const barHeight = MATRIX_CONFIG.layout.edgeChartHeight;
      const barWidth = Math.max(matrixWidth, matrixHeight);

      return {
        matrixWidth,
        matrixHeight,
        barHeight,
        barWidth,
        totalWidth: matrixWidth + barHeight + 20,
        totalHeight: matrixHeight + barHeight + 20,
      };
    },
  };
}
