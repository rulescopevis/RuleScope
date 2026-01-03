import * as d3 from "d3";
import {
  api_load_column_data,
  api_load_missing_duplicate_detect_flag,
  api_load_missing_duplicate_flag,
} from "@/utils/callapi";
import { Row, icon_x } from "@/types/types";

// Centralized chart configuration
const chartConfig = {
  colors: {
    barFill: "#B5D2F8",
    axisDomainStroke: "#CAD2D7",
    axisTickStroke: "#CAD2D7",
    axisTextFill: "black",
    matrixAxisStroke: "#ffffff",
  },
  scales: {
    xScalePadding: 0.3,
    xScalePaddingOuter: 0.1,
    yLogConstant: 50,
  },
  layout: {
    minBarHeight: 5,
  },
  fontStyles: {
    fontFamily: "Roboto",
    yAxisFontSize: "12px",
    xAxisSmallFontSize: "12px",
    xAxisLargeFontSize: "14px",
  },
  xAxisTicks: {
    rotation: "rotate(-45)",
    dx: "-.8em",
    dy: ".15em",
  },
  tooltip: {
    format: (category: string, total: number) => `${category}: ${total}`,
  },
  interaction: {
    cursor: "pointer",
  },
  icons: {
    matrixSize: 30,
    normalSize: 25,
    normalXOffset: -26,
    ySpacing: 50,
    paths: {
      missingTrue: "/table_icon/missing_true.svg",
      missingFalse: "/table_icon/missing_false.svg",
      duplicateTrue: "/table_icon/duplicate_true.svg",
      duplicateFalse: "/table_icon/duplicate_false.svg",
    },
  },
};

export let x: d3.ScaleBand<string>;
export let top10: {
  category: string;
  total: number;
  subCategories: Record<string, number>;
}[];

// 添加导出的接口，用于在其他文件中引用
export interface CharacterChartData {
  x: d3.ScaleBand<string>;
  top10: Array<{
    category: string;
    total: number;
    subCategories: Record<string, number>;
  }>;
  // 新增：每个bar的高度信息
  barHeights?: Record<string, number>;
}

export async function renderCharacterChart(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumn: string,
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  updateHighlightedIndices: (indices: number[], columns: string[]) => void,
  matrixFlag = false,
  iconGroup?: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  onCategoryClick?: (category: string) => void
): Promise<CharacterChartData> {
  const valueList = await api_load_column_data(selectedColumn);

  valueList.sort((a, b) => b.count - a.count);

  // Adjusted dimensions for the chart area
  const adjustedWidth = matrixFlag ? width : width - margin.left - margin.right;
  const adjustedHeight = matrixFlag
    ? height
    : height - margin.top - margin.bottom;

  // Centering offsets
  const xOffset = matrixFlag ? 0 : (width - adjustedWidth) / 2;
  const yOffset = matrixFlag ? 0 : (height - adjustedHeight) / 2;

  const useLogScale =
    valueList.length > 1 && valueList[0].count >= valueList[1].count * 5;

  const displayCategories: {
    category: string;
    total: number;
    subCategories: Record<string, number>;
  }[] = valueList.map((item) => ({
    category: String(item.value).toLowerCase(),
    total: item.count,
    subCategories: { [String(item.value).toLowerCase()]: item.count },
  }));

  top10 = displayCategories;

  const minBarHeight = chartConfig.layout.minBarHeight;

  x = d3
    .scaleBand<string>()
    .domain(displayCategories.map((d) => d.category))
    .range([0, adjustedWidth])
    .padding(chartConfig.scales.xScalePadding)
    .paddingOuter(chartConfig.scales.xScalePaddingOuter);

  const yRange: [number, number] = [adjustedHeight - minBarHeight, 0];
  const y = useLogScale
    ? d3
        .scaleSymlog()
        .domain([0, d3.max(displayCategories, (d) => d.total) as number])
        .nice()
        .range(yRange)
        .constant(chartConfig.scales.yLogConstant)
    : d3
        .scaleLinear()
        .domain([0, d3.max(displayCategories, (d) => d.total) as number])
        .nice()
        .range(yRange);

  // record each bar height
  const barHeights: Record<string, number> = {};

  // 创建一个包装组用于居中对齐
  const chartGroup = svg
    .append("g")
    .attr("transform", `translate(${xOffset},${yOffset})`);

  if (matrixFlag) {
    // 矩阵模式下不渲染坐标轴
    chartGroup
      .append("g")
      .attr("transform", `translate(0,${adjustedHeight})`)
      .call(
        d3
          .axisBottom(x)
          .tickSize(0)
          .tickFormat(() => "")
      )
      .select(".domain")
      .attr("stroke", chartConfig.colors.matrixAxisStroke);
    chartGroup
      .append("g")
      .call(
        d3
          .axisLeft(y)
          .tickFormat(() => "")
          .tickSize(0)
          .ticks(5)
      )
      .select(".domain")
      .attr("stroke", chartConfig.colors.matrixAxisStroke);
  } else {
    // --- X轴渲染 ---
    const axisBottomG = chartGroup
      .append("g")
      .attr("transform", `translate(0,${adjustedHeight})`)
      .call(d3.axisBottom(x));

    axisBottomG.select(".domain").remove();
    axisBottomG.selectAll(".tick line").remove();

    const textLabels = axisBottomG
      .selectAll("text")
      .style("font-family", chartConfig.fontStyles.fontFamily)
      .style("fill", chartConfig.colors.axisTextFill)
      .style(
        "font-size",
        displayCategories.length > 20
          ? chartConfig.fontStyles.xAxisSmallFontSize
          : chartConfig.fontStyles.xAxisLargeFontSize
      );

    let needsRotation = false;
    textLabels.each(function (this: SVGTextElement) {
      if (this.getBBox().width > x.bandwidth()) {
        needsRotation = true;
      }
    });

    if (needsRotation) {
      textLabels
        .style("text-anchor", "end")
        .attr("dx", chartConfig.xAxisTicks.dx)
        .attr("dy", chartConfig.xAxisTicks.dy)
        .attr("transform", chartConfig.xAxisTicks.rotation);
    } else {
      textLabels.style("text-anchor", "middle");
    }

    // --- Y轴渲染 ---
    const axisLeftG = chartGroup.append("g").call(
      d3
        .axisLeft(y)
        .tickFormat((d) => d3.format(".0f")(d))
        .ticks(5)
    );

    axisLeftG
      .select(".domain")
      .attr("stroke", chartConfig.colors.axisDomainStroke);
    axisLeftG
      .selectAll(".tick line")
      .attr("stroke", chartConfig.colors.axisTickStroke);
    axisLeftG
      .selectAll("text")
      .style("font-family", chartConfig.fontStyles.fontFamily)
      .style("fill", chartConfig.colors.axisTextFill)
      .style("font-size", chartConfig.fontStyles.yAxisFontSize);
  }

  // --- 移除堆叠逻辑，只绘制简单条形图 ---
  displayCategories.forEach((d) => {
    const yPos = y(d.total);
    const barHeight = adjustedHeight - yPos;

    // 新增：记录每个类别的bar高度
    barHeights[d.category] = barHeight;

    const rect = chartGroup
      .append("rect")
      .attr("x", x(d.category as string) ?? 0)
      .attr("y", yPos)
      .attr("height", barHeight)
      .attr("width", x.bandwidth())
      .attr("data-category", d.category)
      .attr("fill", chartConfig.colors.barFill)
      .style("cursor", chartConfig.interaction.cursor)
      .on("mouseover", (event) => {
        d3.select(event.currentTarget)
          .append("title")
          .text(chartConfig.tooltip.format(d.category, d.total));
      });

    rect.on("click", function () {
      const event1 = new CustomEvent("category-click", {
        detail: { category: d.category },
      });
      window.dispatchEvent(event1);
      if (onCategoryClick) {
        onCategoryClick(d.category);
      }
    });
  });

  // --- 根据matrixFlag动态调整图标大小和位置 ---
  let iconSize: number;
  let final_icon_x: number;

  if (matrixFlag) {
    iconSize = adjustedHeight * 0.15;
    final_icon_x = icon_x + 10;
  } else {
    iconSize = chartConfig.icons.normalSize;
    final_icon_x = icon_x + chartConfig.icons.normalXOffset;
  }

  let icon_count = -1;
  const { missing_detect_flag, duplicate_detect_flag } =
    await api_load_missing_duplicate_detect_flag(selectedColumn);
  const { missing_flag, duplicate_flag } =
    await api_load_missing_duplicate_flag(selectedColumn);

  // 创建图标组并应用居中偏移
  const iconsGroup =
    iconGroup ||
    svg
      .append("g")
      .attr("transform", matrixFlag ? "" : `translate(${xOffset},${yOffset})`);

  if (missing_detect_flag) {
    icon_count++;
    const iconPath = missing_flag
      ? chartConfig.icons.paths.missingTrue
      : chartConfig.icons.paths.missingFalse;
    iconsGroup
      .append("image")
      .attr("xlink:href", iconPath)
      .attr("x", final_icon_x)
      .attr("y", icon_count * chartConfig.icons.ySpacing)
      .attr("width", iconSize)
      .attr("height", iconSize);
  }

  if (duplicate_detect_flag) {
    icon_count++;
    const iconPath = duplicate_flag
      ? chartConfig.icons.paths.duplicateTrue
      : chartConfig.icons.paths.duplicateFalse;
    iconsGroup
      .append("image")
      .attr("xlink:href", iconPath)
      .attr("x", final_icon_x)
      .attr("y", icon_count * chartConfig.icons.ySpacing)
      .attr("width", iconSize)
      .attr("height", iconSize);
  }

  // return chart data with bar heights
  const chartData: CharacterChartData = { x, top10, barHeights };
  svg.datum<CharacterChartData>(chartData);

  return chartData;
}
