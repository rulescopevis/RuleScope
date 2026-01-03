import * as d3 from "d3";
import { Row, icon_x } from "@/types/types";

export function getDecimalPlaces(num: number): number {
  const str = num.toString();
  if (str.includes(".")) {
    return str.split(".")[1].length;
  }
  return 0;
}

export function hasEmpty(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumn: string,
  margin: { top: number; right: number; bottom: number; left: number }
): void {
  let hasEmptyValue = false;
  csvData.forEach((row) => {
    const value = row[selectedColumn];
    if (
      value === null ||
      value === undefined ||
      (typeof value === "string" && value.trim() === "") ||
      (typeof value === "number" && isNaN(value))
    ) {
      hasEmptyValue = true;
    }
  });

  if (hasEmptyValue) {
    svg
      .append("image")
      .attr("xlink:href", "/null.png")
      .attr("x", -margin.left + 230)
      .attr("y", 0)
      .attr("width", 30)
      .attr("height", 30);
  }
}

export function hasDuplicate(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  csvData: Row[],
  selectedColumn: string,
  margin: { top: number; right: number; bottom: number; left: number }
): void {
  let hasDuplicateValue = false;
  const valuesSet = new Set();
  csvData.forEach((row) => {
    const value = row[selectedColumn];
    if (
      value !== null &&
      value !== undefined &&
      ((typeof value === "string" && value.trim() !== "") ||
        (typeof value === "number" && !isNaN(value)))
    ) {
      if (valuesSet.has(value)) {
        hasDuplicateValue = true;
      } else {
        valuesSet.add(value);
      }
    }
  });

  if (hasDuplicateValue) {
    svg
      .append("image")
      .attr("xlink:href", "/duplicate.png")
      .attr("x", -margin.left + 230)
      .attr("y", 50)
      .attr("width", 25)
      .attr("height", 25);
  }
}

export function getXCoordinateForRowIndex(
  csvData: Row[],
  selectedColumn: string,
  index: number,
  xScale: d3.ScaleLinear<number, number, never>
) {
  const rawValue = csvData[index][selectedColumn];

  if (rawValue === undefined) {
    console.warn(`Value at row ${index} is undefined.`);
    return null;
  }
  const value = typeof rawValue === "number" ? rawValue : parseFloat(rawValue);

  if (isNaN(value)) {
    console.warn(`Invalid value at row ${index}: ${rawValue}`);
    return null;
  }

  const xCoordinate = xScale(value);
  return xCoordinate;
}

export function drawDuplicate(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  margin: { top: number; right: number; bottom: number; left: number }
): void {
  svg
    .append("image")
    .attr("xlink:href", "/duplicate.png")
    .attr("x", icon_x)
    .attr("y", 50)
    .attr("width", 25)
    .attr("height", 25)
    .attr("id", "duplicateIcon")
    .append("title")
    .text("Click to highlight duplicate values");
}
export function drawMissing(
  svg: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  margin: { top: number; right: number; bottom: number; left: number }
): void {
  svg
    .append("image")
    .attr("xlink:href", "/null.png")
    .attr("x", icon_x)
    .attr("y", 0)
    .attr("width", 25)
    .attr("height", 25)
    .attr("id", "missingIcon")
    .append("title")
    .text("Click to highlight missing values");
}
export function loadFontAwesomeCDN(): void {
  const linkEl = document.createElement("link");
  linkEl.rel = "stylesheet";
  linkEl.href =
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css";
  document.head.appendChild(linkEl);
}

export function createLoadingAnimation(
  loadingGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  width: number,
  height: number
): void {
  const circleRadius = 15;
  const dotsCount = 8;
  const dotRadius = 3;

  const spinnerGroup = loadingGroup
    .append("g")
    .attr("transform", `translate(${width / 2}, ${height / 2})`);

  spinnerGroup
    .append("circle")
    .attr("r", circleRadius)
    .attr("fill", "none")
    .attr("stroke", "#f0f0f0")
    .attr("stroke-width", 3);

  for (let i = 0; i < dotsCount; i++) {
    const angle = (i * 2 * Math.PI) / dotsCount;
    const x = circleRadius * Math.cos(angle);
    const y = circleRadius * Math.sin(angle);
    const opacity = 0.2 + (0.8 * i) / dotsCount;

    spinnerGroup
      .append("circle")
      .attr("class", "loading-dot")
      .attr("cx", x)
      .attr("cy", y)
      .attr("r", dotRadius)
      .attr("fill", "#4285F4")
      .style("opacity", opacity);
  }

  loadingGroup
    .append("text")
    .attr("x", width / 2)
    .attr("y", height / 2 + circleRadius + 25)
    .attr("text-anchor", "middle")
    .attr("font-size", "16px")
    .attr("fill", "#333")
    .text("Loading...");

  function rotateSpinner() {
    spinnerGroup
      .transition()
      .duration(1500)
      .ease(d3.easeLinear)
      .attrTween("transform", function () {
        return function (t) {
          return `translate(${width / 2}, ${height / 2}) rotate(${360 * t})`;
        };
      })
      .on("end", rotateSpinner);
  }

  rotateSpinner();
}
