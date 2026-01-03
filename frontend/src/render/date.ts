import * as d3 from "d3";
import {
  api_load_missing_duplicate_detect_flag,
  api_load_missing_duplicate_flag,
} from "@/utils/callapi";
import { icon_x, Row } from "@/types/types";

const chartConfig = {
  font: {
    family: "Roboto, sans-serif",
    color: "black",
    size: "12px",
  },
  colors: {
    area: {
      default: "#B5D2F8",
      outOfRange: "#fdd0a2",
    },
    axis: {
      stroke: "#cad2d7",
    },
    iconFill: "#4570b6",
  },
  layout: {
    yAxisTopSpaceFactor: 1.2,
    icon: {
      x_offset: -20,
      y_spacing: 50,
      width: 25,
      height: 25,
    },
  },
  axis: {
    x: {
      tickDensity: 80,
      labelRotation: {
        angle: -45,
        dx: "-0.8em",
        dy: "0.15em",
        anchor: "end",
        lengthThreshold: 5,
      },
    },
    y: {
      tickDensity: 40,
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
    updateHighlight: "update-highlighted-indices", // Custom event name for highlighted row updates
  },
};

type AggregatedDateValue = { value: Date; count: number };

function parseDateValue(value: string | number | undefined): Date | null {
  if (value === undefined || value === null || value === "") {
    return null;
  }

  if (typeof value === "number") {
    const dateFromNumber = new Date(value);
    return Number.isNaN(dateFromNumber.getTime()) ? null : dateFromNumber;
  }

  const normalized = String(value).trim();
  if (!normalized) {
    return null;
  }

  const dateFromString = new Date(normalized);
  if (!Number.isNaN(dateFromString.getTime())) {
    return dateFromString;
  }

  const numericTimestamp = Number(normalized);
  if (Number.isFinite(numericTimestamp)) {
    const timestampDate = new Date(numericTimestamp);
    return Number.isNaN(timestampDate.getTime()) ? null : timestampDate;
  }

  return null;
}

function buildDateValueList(
  csvData: Row[],
  selectedColumn: string
): AggregatedDateValue[] {
  const counts = new Map<number, AggregatedDateValue>();

  csvData.forEach((row) => {
    const parsedDate = parseDateValue(row[selectedColumn]);
    if (!parsedDate) {
      return;
    }

    const timestamp = parsedDate.getTime();
    const current = counts.get(timestamp);
    if (current) {
      current.count += 1;
    } else {
      counts.set(timestamp, { value: parsedDate, count: 1 });
    }
  });

  return Array.from(counts.values()).sort(
    (a, b) => a.value.getTime() - b.value.getTime()
  );
}

export async function renderDateChart(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumn: string,
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  updateHighlightedIndices?: (indices: number[], columns: string[]) => void,
  matrixFlag = false
): Promise<{ x_min: number; x_max: number } | null> {
  const adjustedWidth = matrixFlag ? width : width - margin.left - margin.right;
  const adjustedHeight = matrixFlag
    ? height
    : height - margin.top - margin.bottom;

  const xOffset = matrixFlag ? 0 : (width - adjustedWidth) / 2;
  const yOffset = matrixFlag ? 0 : (height - adjustedHeight) / 2;

  svg
    .style("font-family", chartConfig.font.family)
    .style("color", chartConfig.font.color);

  const sortedValueList = buildDateValueList(csvData, selectedColumn);

  if (sortedValueList.length === 0) {
    return null;
  }

  const firstValue = sortedValueList[0].value.getTime();
  const lastValue = sortedValueList[sortedValueList.length - 1].value.getTime();

  const x = d3
    .scaleTime()
    .domain(d3.extent(sortedValueList, (d) => d.value) as [Date, Date])
    .range([0, adjustedWidth]);

  const yMax = d3.max(sortedValueList, (d) => d.count) as number;
  const y = d3
    .scaleLinear()
    .domain([0, yMax * chartConfig.layout.yAxisTopSpaceFactor])
    .range([adjustedHeight, 0]);

  const chartGroup = svg
    .append("g")
    .attr("transform", `translate(${xOffset},${yOffset})`);

  const area = d3
    .area<{ value: Date; count: number }>()
    .x((d) => x(d.value))
    .y0(y(0))
    .y1((d) => y(d.count));

  chartGroup
    .append("path")
    .attr("fill", chartConfig.colors.area.default)
    .attr("d", area(sortedValueList));

  if (matrixFlag) {
    const axisGroup = chartGroup.append("g");

    axisGroup
      .append("g")
      .attr("transform", `translate(0,${adjustedHeight})`)
      .call(
        d3
          .axisBottom(x)
          .tickSize(0)
          .tickFormat(() => "")
      )
      .select(".domain")
      .attr("stroke", chartConfig.colors.axis.stroke);

    axisGroup
      .append("g")
      .call(
        d3
          .axisLeft(y)
          .tickSize(0)
          .tickFormat(() => "")
      )
      .select(".domain")
      .attr("stroke", chartConfig.colors.axis.stroke);
  } else {
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

    const formatTime = d3.timeFormat("%Y-%m-%d");

    const xAxis = d3
      .axisBottom(x)
      .ticks(10) // Date type default display 10 bottom labels
      .tickFormat(formatTime as any)
      .tickSizeOuter(0);

    xAxisGroup.call(xAxis);

    xAxisGroup.select(".domain").remove();
    xAxisGroup
      .selectAll(".tick line")
      .attr("stroke", chartConfig.colors.axis.stroke);
    xAxisGroup
      .selectAll(".tick text")
      .style("font-size", chartConfig.font.size);

    const tickLabels = x.ticks(10).map((d) => formatTime(d));
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
  return { x_min: firstValue, x_max: lastValue };
}
