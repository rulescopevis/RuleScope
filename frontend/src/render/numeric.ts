import * as d3 from "d3";
import {
  api_detect_numeric_range,
  api_detect_outliers,
  api_json_numeric_range,
  api_load_column_data,
  api_load_missing_duplicate_detect_flag,
  api_load_missing_duplicate_flag,
} from "@/utils/callapi";

import { icon_x, Row } from "@/types/types";

/**
 * @description Chart Configuration
 * Centralizes all configurable constants (colors, fonts, layout parameters, etc.)
 * for unified management and modification.
 */
const chartConfig = {
  font: {
    family: "Roboto, sans-serif",
    color: "black",
    size: "12px",
  },
  colors: {
    area: {
      default: "#B5D2F8", // Fill color for data within range
      outOfRange: "#fdd0a2", // Fill color for data out of range
    },
    axis: {
      stroke: "#cad2d7", // Color for axis lines and grid lines
    },
    iconFill: "#4570b6", // Fill color for icons (Note: might not apply to <image> elements)
  },
  layout: {
    yAxisTopSpaceFactor: 1.2, // Factor for whitespace above Y-axis max value (1.2 = 20% extra space)
    icon: {
      x_offset: -32, // X-axis offset for icons relative to imported icon_x (further left for non-matrix mode)
      y_spacing: 50, // Vertical spacing between icons
      width: 25, // Icon width
      height: 25, // Icon height
    },
  },
  axis: {
    x: {
      tickDensity: 80, // X-axis tick density, one tick every 80 pixels
      labelRotation: {
        angle: -45, // Label rotation angle
        dx: "-0.8em", // X offset after rotation
        dy: "0.15em", // Y offset after rotation
        anchor: "end", // Text anchor
        lengthThreshold: 5, // Character length threshold to trigger rotation
      },
      maxDiscreteTicks: 15, // Use data values directly as ticks when unique values are few
    },
    y: {
      tickDensity: 40, // Y-axis tick density, one tick every 40 pixels
    },
  },
  icons: {
    missing: {
      true: "/table_icon/missing_true.svg",
      false: "/table_icon/missing_false.svg",
    },
    duplicate: {
      true: "/table_icon/duplicate_true.svg",
      false: "/table_icon/duplicate_false.svg",
    },
  },
  events: {
    updateHighlight: "update-highlighted-indices", // Custom event name for updating highlighted row indices
  },
};

/**
 * Renders an area chart for numeric data and optimizes styles and functionality based on requirements.
 *
 * @param svg The D3 selection of the SVG g element used for drawing the chart.
 * @param csvData The raw data.
 * @param selectedColumn The name of the currently selected column.
 * @param width The width of the chart area.
 * @param height The height of the chart area.
 * @param margin The margins of the chart.
 * @param updateHighlightedIndices Callback function to update highlighted row indices.
 * @param matrixFlag Flag indicating whether it is in matrix view mode.
 * @param relationType The type of relationship/validation to visualize (e.g., "Range", "Outlier").
 * @returns Returns an object containing the minimum and maximum x-axis values.
 */
export async function renderNumericChart(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumn: string,
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  matrixFlag = false,
  relationType = "edge"
): Promise<{ x_min: number; x_max: number }> {
  const normalizedRelationType = relationType || "";
  const shouldShowInvalidRange =
    !matrixFlag &&
    (normalizedRelationType === "Range" ||
      normalizedRelationType === "Outlier");

  // Adjust visible area dimensions based on matrixFlag
  const adjustedWidth = matrixFlag ? width : width - margin.left - margin.right;
  const adjustedHeight = matrixFlag
    ? height
    : height - margin.top - margin.bottom;

  // Calculate centering offsets
  const xOffset = matrixFlag ? 0 : (width - adjustedWidth) / 2;
  const yOffset = matrixFlag ? 0 : (height - adjustedHeight) / 2;

  // Unify font styles
  svg
    .style("font-family", chartConfig.font.family)
    .style("color", chartConfig.font.color);

  const valueList = await api_load_column_data(selectedColumn);

  // Sort by value
  const sortedValueList = [...valueList]
    .map(({ value, count }) => ({ value: Number(value), count: Number(count) }))
    .sort((a, b) => Number(a.value) - Number(b.value));

  // X-axis scale
  const x = d3
    .scaleLinear()
    .domain([
      d3.min(sortedValueList, (d) => Number(d.value)) as number,
      d3.max(sortedValueList, (d) => Number(d.value)) as number,
    ])
    .range([0, adjustedWidth]);

  // Adjust Y-axis range
  const yMax = d3.max(sortedValueList, (d) => d.count) as number;
  const y = d3
    .scaleLinear()
    .domain([0, yMax * chartConfig.layout.yAxisTopSpaceFactor]) // Add top spacing
    .range([adjustedHeight, 0]);

  // Create a wrapper group for centering
  const chartGroup = svg
    .append("g")
    .attr("transform", `translate(${xOffset},${yOffset})`);

  // Declare area generator
  const area = d3
    .area<{ value: number; count: number }>()
    .x((d) => x(d.value))
    .y0(y(0))
    .y1((d) => y(d.count));

  chartGroup
    .append("path")
    .attr("fill", chartConfig.colors.area.default)
    .attr("d", area(sortedValueList));

  // Determine axis styles based on matrixFlag
  if (matrixFlag) {
    // Matrix Mode: Keep XY axis lines but remove grid lines, ticks, and labels.
    const axisGroup = chartGroup.append("g");

    // Draw X-axis line (domain path)
    axisGroup
      .append("g")
      .attr("transform", `translate(0,${adjustedHeight})`)
      .call(
        d3
          .axisBottom(x)
          .tickSize(0) // Remove ticks
          .tickFormat(() => "") // Remove tick labels
      )
      .select(".domain")
      .attr("stroke", chartConfig.colors.axis.stroke); // Use visible axis color

    // Draw Y-axis line (domain path)
    axisGroup
      .append("g")
      .call(
        d3
          .axisLeft(y)
          .tickSize(0) // Remove ticks
          .tickFormat(() => "") // Remove tick labels
      )
      .select(".domain")
      .attr("stroke", chartConfig.colors.axis.stroke); // Use visible axis color
  } else {
    // Main View Mode: Draw complete axes and grid lines.
    const yAxisGroup = chartGroup
      .append("g")
      .call(
        d3.axisLeft(y).ticks(adjustedHeight / chartConfig.axis.y.tickDensity)
      );

    yAxisGroup.select(".domain").remove();
    yAxisGroup
      .selectAll(".tick line")
      .attr("stroke", chartConfig.colors.axis.stroke);
    yAxisGroup
      .selectAll(".tick text")
      .style("font-size", chartConfig.font.size);

    yAxisGroup
      .selectAll(".tick line")
      .clone()
      .attr("x2", adjustedWidth)
      .attr("stroke", chartConfig.colors.axis.stroke)
      .attr("stroke-opacity", 0.5);

    const xAxisGroup = chartGroup
      .append("g")
      .attr("transform", `translate(0,${adjustedHeight})`);

    const uniqueXValues = Array.from(
      new Set(sortedValueList.map((d) => d.value))
    ).sort((a, b) => a - b);
    const tickDensityCount = adjustedWidth / chartConfig.axis.x.tickDensity;
    const useDiscreteTicks =
      uniqueXValues.length > 0 &&
      uniqueXValues.length <= chartConfig.axis.x.maxDiscreteTicks;

    const formatDiscreteTick = (value: number): string => {
      if (Number.isInteger(value)) {
        return value.toString();
      }
      const trimmed = Number(value.toFixed(6));
      return trimmed.toString();
    };

    const xAxis = d3.axisBottom(x).tickSizeOuter(0);
    let tickValuesForRotation: number[] = [];

    if (useDiscreteTicks) {
      xAxis
        .tickValues(uniqueXValues)
        .tickFormat((d) => formatDiscreteTick(Number(d)));
      tickValuesForRotation = uniqueXValues;
    } else {
      xAxis.ticks(tickDensityCount);
      tickValuesForRotation = x.ticks(tickDensityCount);
    }

    xAxisGroup.call(xAxis);

    xAxisGroup.select(".domain").remove();
    xAxisGroup
      .selectAll(".tick line")
      .attr("stroke", chartConfig.colors.axis.stroke);
    xAxisGroup
      .selectAll(".tick text")
      .style("font-size", chartConfig.font.size);

    const formatter = xAxis.tickFormat() ?? ((value: number) => `${value}`);
    const tickLabels = tickValuesForRotation.map((tick, index) =>
      String(formatter(tick, index))
    );
    const { lengthThreshold } = chartConfig.axis.x.labelRotation;
    const shouldRotate = tickLabels.some(
      (label) => String(label).length > lengthThreshold
    );

    if (shouldRotate) {
      const { angle, dx, dy, anchor } = chartConfig.axis.x.labelRotation;
      xAxisGroup
        .selectAll(".tick text")
        .style("text-anchor", anchor)
        .attr("dx", dx)
        .attr("dy", dy)
        .attr("transform", `rotate(${angle})`);
    }

    const normalizeBound = (value: number | string | null | undefined) => {
      if (value === null || value === undefined) {
        return null;
      }
      const numericValue = Number(value);
      return Number.isFinite(numericValue) ? numericValue : null;
    };

    if (shouldShowInvalidRange) {
      const activeRuleType =
        normalizedRelationType === "Outlier" ? "Outlier" : "Range";
      const { start, end } = await api_json_numeric_range(
        selectedColumn,
        activeRuleType
      );
      const normalizedStart = normalizeBound(start);
      const normalizedEnd = normalizeBound(end);

      if (normalizedStart !== null || normalizedEnd !== null) {
        updateAreas(normalizedStart, normalizedEnd, activeRuleType);
      }
    }
  }

  function updateAreas(
    newStart: number | null,
    newEnd: number | null,
    activeRuleType: "Range" | "Outlier"
  ) {
    if (newStart === null && newEnd === null) {
      return;
    }

    chartGroup.selectAll("path.area").remove();

    const detectInvalid =
      activeRuleType === "Outlier"
        ? api_detect_outliers
        : api_detect_numeric_range;

    let beforeStartData: { value: number; count: number }[] = [];
    if (newStart !== null) {
      beforeStartData = sortedValueList.filter((d) => d.value < newStart);
    }

    const betweenData = sortedValueList.filter((d) => {
      const meetsLowerBound = newStart === null || d.value >= newStart;
      const meetsUpperBound = newEnd === null || d.value <= newEnd;
      return meetsLowerBound && meetsUpperBound;
    });

    let afterEndData: { value: number; count: number }[] = [];
    if (newEnd !== null) {
      afterEndData = sortedValueList.filter((d) => d.value > newEnd);
    }

    chartGroup
      .append("path")
      .attr("class", "area")
      .attr("fill", chartConfig.colors.area.outOfRange)
      .attr("d", area(beforeStartData))
      .on("click", async () => {
        const invalidIndices = await detectInvalid(selectedColumn);
        const event = new CustomEvent(chartConfig.events.updateHighlight, {
          detail: { invalidIndices, columns: [selectedColumn] },
          bubbles: true,
          cancelable: true,
        });
        svg.node()?.dispatchEvent(event);
      });

    chartGroup
      .append("path")
      .attr("class", "area")
      .attr("fill", chartConfig.colors.area.outOfRange)
      .attr("d", area(afterEndData))
      .on("click", async () => {
        const invalidIndices = await detectInvalid(selectedColumn);
        updateHighlightedIndices(invalidIndices, [selectedColumn]);
      });

    chartGroup
      .append("path")
      .attr("class", "area")
      .attr("fill", chartConfig.colors.area.default)
      .attr("d", area(betweenData));
  }

  let iconSize: number;
  let final_icon_x: number;

  if (matrixFlag) {
    iconSize = adjustedHeight * 0.15;
    final_icon_x = icon_x + 10;
  } else {
    iconSize = chartConfig.layout.icon.width;
    final_icon_x = icon_x + chartConfig.layout.icon.x_offset;
  }

  let icon_count = -1;

  const { missing_detect_flag, duplicate_detect_flag } =
    await api_load_missing_duplicate_detect_flag(selectedColumn);
  const { missing_flag, duplicate_flag } =
    await api_load_missing_duplicate_flag(selectedColumn);
  if (normalizedRelationType === "Outlier") {
    await api_detect_outliers(selectedColumn);
  }

  // Create icon group and apply centering offset
  const iconGroup = svg
    .append("g")
    .attr("transform", matrixFlag ? "" : `translate(${xOffset},${yOffset})`);

  if (missing_detect_flag) {
    icon_count++;
    const iconPath = missing_flag
      ? chartConfig.icons.missing.true
      : chartConfig.icons.missing.false;
    iconGroup
      .append("image")
      .attr("xlink:href", iconPath)
      .attr("x", final_icon_x)
      .attr("y", icon_count * chartConfig.layout.icon.y_spacing)
      .attr("width", iconSize)
      .attr("height", iconSize);
  }
  if (duplicate_detect_flag) {
    icon_count++;
    const iconPath = duplicate_flag
      ? chartConfig.icons.duplicate.true
      : chartConfig.icons.duplicate.false;
    iconGroup
      .append("image")
      .attr("xlink:href", iconPath)
      .attr("x", final_icon_x)
      .attr("y", icon_count * chartConfig.layout.icon.y_spacing)
      .attr("width", iconSize)
      .attr("height", iconSize);
  }

  const x_min = d3.min(sortedValueList, (d) => Number(d.value)) as number;
  const x_max = d3.max(sortedValueList, (d) => Number(d.value)) as number;
  return { x_min, x_max };
}
