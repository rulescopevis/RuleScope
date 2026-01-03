import * as d3 from "d3";
import { api_submit_text } from "@/utils/callapi";

/**
 * Create an adaptive tooltip with a send button using inline measurement for sizing.
 */
export function createTooltip(
  mainGroup: d3.Selection<SVGGElement, unknown, HTMLElement, any>,
  rectX: number,
  rectY: number,
  x_start: number,
  y_start: number,
  subSquareLength: number,
  template: string,
  columnNames: string[],
  ruleType: string,
  ruleValue = "",
  scaleRatio = 1 // Scale ratio, default is 1
) {
  const MIN_SCALE_FACTOR = 0.75;
  const MAX_SCALE_FACTOR = 2.5;
  const BASE_CELL_SIZE = 22;
  const VISUAL_SHRINK_FACTOR = 0.9;

  const MAX_LINES = 5;
  const MIN_WIDTH_REM = 15;
  const MAX_WIDTH_REM = 45;
  const CHAR_WIDTH_FACTOR = 0.6;

  const cellScaleFactor = Math.min(
    1.2,
    Math.max(0.6, subSquareLength / BASE_CELL_SIZE)
  );

  const tooltipScaleFactor = scaleRatio * cellScaleFactor;
  const actualScaleFactor = Math.max(
    MIN_SCALE_FACTOR,
    Math.min(MAX_SCALE_FACTOR, tooltipScaleFactor)
  );
  const visualScaleFactor = actualScaleFactor * VISUAL_SHRINK_FACTOR;

  const tooltipId = `tooltip-${Math.random().toString(36).substr(2, 9)}`;
  const inputId = `input-${Math.random().toString(36).substr(2, 9)}`;

  const cellCenterX = rectX + subSquareLength / 2;
  const cellCenterY = rectY + subSquareLength / 2;

  const baseVerticalLineLength = 100;
  const verticalLineLength = baseVerticalLineLength * visualScaleFactor;
  const x2 = cellCenterX;
  const y2 = cellCenterY - verticalLineLength;

  const baseHorizontalLineLength = 40;
  const horizontalLineLength = baseHorizontalLineLength * visualScaleFactor;
  const x3 = x2 + horizontalLineLength / Math.sqrt(2);
  const y3 = y2 - horizontalLineLength / Math.sqrt(2);

  const baseStrokeWidth = 2;
  const adjustedStrokeWidth = baseStrokeWidth * visualScaleFactor;

  const tooltip_line_1 = mainGroup
    .append("line")
    .style("visibility", "hidden")
    .attr("x1", cellCenterX)
    .attr("y1", cellCenterY)
    .attr("x2", x2)
    .attr("y2", y2)
    .attr("stroke", "black")
    .attr("stroke-width", adjustedStrokeWidth);

  const tooltip_line_2 = mainGroup
    .append("line")
    .style("visibility", "hidden")
    .attr("x1", x2)
    .attr("y1", y2)
    .attr("x2", x3)
    .attr("y2", y3)
    .attr("stroke", "black")
    .attr("stroke-width", adjustedStrokeWidth);

  const baseYOffset = 20;
  const adjustedYOffset = baseYOffset * visualScaleFactor;

  const inputBox = mainGroup
    .append("foreignObject")
    .attr("id", tooltipId)
    .attr("x", x3)
    .attr("y", y3 - adjustedYOffset)
    .attr("width", 9999)
    .attr("height", 1)
    .style("visibility", "hidden")
    .style("overflow", "visible")
    .attr("transform", `rotate(-45, ${x3}, ${y3})`);

  const baseFontSize = 0.95;
  const adjustedFontSize = baseFontSize * visualScaleFactor;

  const inputDiv = inputBox
    .append("xhtml:div")
    .attr("id", inputId)
    .attr("contenteditable", "true")
    .html(template)
    .style("position", "relative")
    .style("display", "inline-block")
    .style("width", "auto")
    .style("min-width", `${MIN_WIDTH_REM * visualScaleFactor}rem`)
    .style("max-width", "none")
    .style("background-color", "white")
    .style("border", `${1 * visualScaleFactor}px solid #E0E0E0`)
    .style("border-radius", `${0.75 * visualScaleFactor}rem`)
    .style(
      "box-shadow",
      `0 ${4 * visualScaleFactor}px ${
        12 * visualScaleFactor
      }px rgba(0, 0, 0, 0.1)`
    )
    .style("padding", `${1 * visualScaleFactor}rem`)
    .style("padding-right", `${3 * visualScaleFactor}rem`)
    .style("font-family", "inherit")
    .style("font-size", `${adjustedFontSize}rem`)
    .style("line-height", "1.6")
    .style("color", "black")
    .style("text-align", "left")
    .style("word-wrap", "break-word")
    .style("white-space", "nowrap")
    .style("outline", "none")
    .style("cursor", "text")
    .style("box-sizing", "border-box")
    .on("mousedown", (event) => {
      event.stopPropagation();
    });

  const baseButtonSize = 1.75;
  const buttonSize = baseButtonSize * visualScaleFactor;
  const baseBottomOffset = 0.75;
  const baseRightOffset = 0.75;
  const buttonBottomOffset = baseBottomOffset * visualScaleFactor;
  const buttonRightOffset = baseRightOffset * visualScaleFactor;

  const sendIconHtml = `<img src="/send.svg" alt="Send" style="width: 100%; height: 100%;" />`;
  const loadingSpinnerHtml = `
    <svg viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
      <circle
        cx="25"
        cy="25"
        r="20"
        fill="none"
        stroke="#4570b6"
        stroke-width="5"
        stroke-linecap="round"
        stroke-dasharray="31.4 31.4"
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 25 25"
          to="360 25 25"
          dur="1s"
          repeatCount="indefinite"
        />
      </circle>
    </svg>
  `;

  const statusText = inputDiv
    .append("div")
    .style("margin-top", `${0.4 * visualScaleFactor}rem`)
    .style("font-size", `${0.85 * adjustedFontSize}rem`)
    .style("color", "#4570b6")
    .style("font-weight", "600")
    .style("display", "none")
    .style("transition", "opacity 0.2s ease")
    .style("opacity", "0");

  let isSubmitting = false;

  const sendButton = inputDiv
    .append("div")
    .style("position", "absolute")
    .style("bottom", `${buttonBottomOffset}rem`)
    .style("right", `${buttonRightOffset}rem`)
    .style("width", `${buttonSize}rem`)
    .style("height", `${buttonSize}rem`)
    .style("cursor", "pointer")
    .style("display", "flex")
    .style("align-items", "center")
    .style("justify-content", "center")
    .html(sendIconHtml)
    .on("click", async (event) => {
      event.stopPropagation();
      if (isSubmitting) return;
      const textContent = (d3.select(`#${inputId}`).node() as HTMLDivElement)
        .textContent;
      if (!textContent) return;

      const showStatus = (message: string) => {
        statusText
          .text(message)
          .style("display", "block")
          .style("opacity", "1");
        setTimeout(updateLayout, 0);
      };

      const hideStatus = () => {
        statusText.style("opacity", "0").style("display", "none").text("");
        setTimeout(updateLayout, 0);
      };

      try {
        isSubmitting = true;
        sendButton
          .style("opacity", "0.7")
          .style("pointer-events", "none")
          .html(loadingSpinnerHtml);
        showStatus("Updating rule...");

        const result_message = await api_submit_text(
          textContent,
          columnNames,
          ruleType,
          ruleValue
        );

        const selectedExamples = {
          selectedExamples: result_message,
        };
        const customEvent = new CustomEvent("rules-update", {
          detail: { selectedExamples },
        });
        document.dispatchEvent(customEvent);

        showStatus("Rule updated");
        setTimeout(() => {
          hideStatus();
        }, 1500);
      } catch (error) {
        console.error("Failed to submit tooltip text", error);
        showStatus("Update failed, please retry");
      } finally {
        isSubmitting = false;
        sendButton
          .style("opacity", "1")
          .style("pointer-events", "auto")
          .html(sendIconHtml);
      }
    });

  const calculateOptimalWidth = (
    element: HTMLDivElement
  ): { width: number | null; shouldWrap: boolean } => {
    const textContent = element.textContent || "";
    const textLength = textContent.length;

    const estimatedTextWidth =
      textLength * CHAR_WIDTH_FACTOR * visualScaleFactor;

    const maxAllowedWidth = MAX_WIDTH_REM * visualScaleFactor;

    if (estimatedTextWidth <= maxAllowedWidth) {
      return { width: null, shouldWrap: false };
    }

    let optimalLines = Math.ceil(estimatedTextWidth / maxAllowedWidth);
    optimalLines = Math.min(optimalLines, MAX_LINES);

    const charsPerLine = Math.ceil(textLength / optimalLines);
    const optimalWidth = charsPerLine * CHAR_WIDTH_FACTOR * visualScaleFactor;

    const minWidth = MIN_WIDTH_REM * visualScaleFactor;
    const finalWidth = Math.max(
      minWidth,
      Math.min(optimalWidth, maxAllowedWidth)
    );

    return { width: finalWidth, shouldWrap: true };
  };

  const updateLayout = () => {
    const inputNode = inputDiv.node() as HTMLDivElement;
    if (!inputNode) return;

    const { width: optimalWidth } = calculateOptimalWidth(inputNode);

    if (optimalWidth === null) {
      inputDiv
        .style("width", "auto")
        .style("max-width", `${MAX_WIDTH_REM * visualScaleFactor}rem`)
        .style("white-space", "nowrap");
    } else {
      inputDiv
        .style("width", `${optimalWidth}rem`)
        .style("max-width", `${optimalWidth}rem`)
        .style("white-space", "pre-wrap");
    }

    requestAnimationFrame(() => {
      const { width, height } = inputNode.getBoundingClientRect();

      inputBox.attr("width", width).attr("height", height);

      inputBox.attr("y", y3 - height / 2);
    });
  };

  inputDiv.on("input", () => {
    setTimeout(updateLayout, 0);
  });

  setTimeout(updateLayout, 0);

  return { inputBox, tooltip_line_1, tooltip_line_2 };
}
