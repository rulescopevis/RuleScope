<template>
  <div class="chart-container">
    <div class="header-container">
      <img src="/rulescope.svg" alt="RuleScope" class="rulescope-title" />
      <div class="dataset-selector">
        <div class="selector-group">
          <span class="dataset-label">Mode:</span>
          <select v-model="workflowMode" @change="handleWorkflowModeChange">
            <option
              v-for="mode in workflowOptions"
              :key="mode.value"
              :value="mode.value"
            >
              {{ mode.label }}
            </option>
          </select>
        </div>
        <div class="selector-group">
          <span class="dataset-label">Case:</span>
          <select v-model="selectedDataset" @change="changeDataset">
            <option value="" disabled>Select Case</option>
            <option
              v-for="option in datasetOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="upload-btn-wrapper">
          <button
            class="upload-btn"
            :class="{ loading: isUploading }"
            :disabled="isUploading"
            @click="triggerFileDialog"
          >
            <span v-if="!isUploading">Upload File</span>
            <span v-else class="loading-content">
              <span class="spinner" aria-hidden="true"></span>
              Generating...
            </span>
          </button>
          <input
            ref="uploadInput"
            type="file"
            accept=".csv"
            @change="handleFileUpload"
          />
        </div>
        <div class="upload-btn-wrapper">
          <button class="upload-btn" @click="showExportDialog">Export</button>
        </div>
      </div>
    </div>

    <div v-if="isEmpty">
      <el-empty
        :image="require('../../public/nodata.svg')"
        :image-size="200"
        description="Please Choose Validation Card"
      />
    </div>
    <div id="view"></div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, PropType } from "vue";
import * as d3 from "d3";
import {
  invalidRange_Compare_Numeric,
  invalidRange_Difference,
  validRange_Equality_Equality,
  invalidRange_Equality_Range,
  Row,
  ColumnBasedRule,
} from "@/types/types";
import { renderCharacterChart } from "@/render/character";
import { discrete_matrix } from "@/render/discrete_matrix";
import { renderNumericChart } from "@/render/numeric";
import { renderDateChart } from "@/render/date";
import { discrete_continuous_matrix } from "@/render/discrete_continuous_matrix";
import { continuous_matrix } from "@/render/continuous_matrix";
import { api_upload_dataset } from "@/utils/callapi";
import { multiple_matrix } from "@/render/multiple_matrix";

export default defineComponent({
  name: "ChartView",
  props: {
    selectedColumns: {
      type: Array as () => string[],
      required: true,
      default: () => [],
    },
    csvData: {
      type: Array as () => Row[],
      required: true,
      default: () => [],
    },
    columnTypes: {
      type: Array as () => string[],
      required: true,
    },
    columnNames: {
      type: Array as () => string[],
      required: true,
    },
    relationType: {
      type: String,
      default: "",
    },
    invalidIndices: {
      type: Array as () => number[],
      required: true,
    },
    invalid_pairs: {
      type: Array as () => {
        currentIndex: number;
        nextIndex: number;
        sortCurrentIndex: number;
        sortNextIndex: number;
      }[],
      required: true,
    },
    invalid_range: {
      type: [Array, Object] as PropType<
        | invalidRange_Equality_Range[]
        | validRange_Equality_Equality[]
        | invalidRange_Compare_Numeric
        | invalidRange_Difference
      >,
      required: true,
    },
    threeColumnRules: {
      type: Array as PropType<ColumnBasedRule[]>,
      required: false,
      default: () => [],
    },
  },
  emits: [
    "update-highlighted-indices",
    "dataset-changed",
    "show-export-dialog",
    "workflow-mode-changed",
  ],
  watch: {
    selectedColumns: {
      handler(newVal) {
        this.$nextTick(() => {
          d3.select("#view").selectAll("*").remove();
        });
      },
    },
    columnNames: {
      handler(newVal) {
        this.resetZoomState();
        this.handleUpdateChart();
        if (this.columnNames.length > 0) {
          this.isEmpty = false;
        }
      },
    },
    relationType: {
      handler(newVal) {
        this.resetZoomState();
        this.handleUpdateChart();
      },
    },
  },
  data(): {
    margin: { top: number; right: number; bottom: number; left: number };
    basicChartMargin: {
      top: number;
      right: number;
      bottom: number;
      left: number;
    };
    width: number;
    height: number;
    tempHeight: number;
    updateTriggered: boolean;
    currentRenderToken: number;
    selectedDataset: string;
    datasetLoadingId: number;
    isEmpty: boolean;
    rotationAngle: number;
    edge: [string, string];
    currentTransform: d3.ZoomTransform;
    workflowMode: string;
    workflowOptions: { label: string; value: string }[];
    datasetOptions: { label: string; value: string }[];
    isUploading: boolean;
  } {
    return {
      margin: { top: 50, right: 50, bottom: 50, left: 50 },
      basicChartMargin: { top: 100, right: 150, bottom: 100, left: 150 },
      width: 0,
      height: 0,
      tempHeight: 100,
      updateTriggered: false,
      currentRenderToken: 0,
      selectedDataset: "",
      datasetLoadingId: 0,
      isEmpty: true,
      rotationAngle: 45,
      edge: ["bottom", "right"],
      currentTransform: d3.zoomIdentity, // Initialize transform state
      workflowMode: "ollama",
      workflowOptions: [
        { label: "ollama", value: "ollama" },
        { label: "api", value: "api" },
      ],
      datasetOptions: [
        { label: "electrocar", value: "electrocar1" },
        { label: "basketball", value: "basketball" },
        { label: "animal", value: "animal" },
      ],
      isUploading: false,
    };
  },
  methods: {
    handleResize() {
      this.calculateDimensions();
      this.updateChart();
    },
    resetZoomState() {
      // Reset zoom so new visualizations start at the default scale
      this.currentTransform = d3.zoomIdentity;
    },
    calculateDimensions() {
      const container = this.$el.querySelector(".chart-container") || this.$el;
      if (!container) return;

      const computedStyle = window.getComputedStyle(container);
      const width = parseInt(computedStyle.width, 10);
      const height = parseInt(computedStyle.height, 10);

      this.width = width - this.margin.left - this.margin.right;
      this.height = height - this.margin.top - this.margin.bottom;

      if (this.width < 0) this.width = 0;
      if (this.height < 0) this.height = 0;
    },
    handleUpdateChart() {
      if (!this.updateTriggered) {
        this.updateChart();
        this.updateTriggered = true;

        setTimeout(() => {
          this.updateTriggered = false;
        }, 50);
      }
    },
    updateHighlightedIndices(rowIds: number[], columns: string[]) {
      this.$emit("update-highlighted-indices", rowIds, columns);
    },
    async updateChart() {
      this.currentRenderToken += 1;
      const renderToken = this.currentRenderToken;
      // Always reset zoom before rendering a fresh visualization
      this.resetZoomState();
      // Check only necessary render conditions, ignoring isEmpty
      if (!this.columnNames || this.columnNames.length === 0) return;

      d3.select("#view").selectAll("*").remove();

      const svg = d3
        .select("#view")
        .append("svg")
        .attr("width", this.width + this.margin.left + this.margin.right)
        .attr("height", this.height + this.margin.top + this.margin.bottom);

      const g = svg
        .append("g")
        .attr("transform", `translate(${this.margin.left},${this.margin.top})`)
        .attr("class", "zoomable-group");

      // Track if content was actually rendered
      let contentRendered = false;

      if (this.columnNames.length === 1) {
        if (this.columnTypes[0] === "character") {
          if (
            this.relationType === "Missing" ||
            this.relationType === "Duplicate" ||
            this.relationType === "Type"
          ) {
            renderCharacterChart(
              g,
              this.csvData,
              this.columnNames[0],
              this.width,
              this.height,
              this.basicChartMargin,
              this.updateHighlightedIndices
            );
            contentRendered = true;
          } else if (this.relationType === "Sequence") {
            discrete_matrix(
              g,
              this.csvData,
              [this.columnNames[0], this.columnNames[0]],
              this.width,
              this.height,
              this.margin,
              this.invalid_pairs,
              this.invalid_range as validRange_Equality_Equality[],
              this.updateHighlightedIndices,
              this.relationType,
              this.rotationAngle,
              this.edge
            );
            contentRendered = true;
          }
        } else if (this.columnTypes[0] === "numeric") {
          if (
            this.relationType === "Missing" ||
            this.relationType === "Duplicate" ||
            this.relationType === "Type" ||
            this.relationType === "Outlier" ||
            this.relationType === "Range" ||
            this.relationType === "Distribution"
          ) {
            renderNumericChart(
              g,
              this.csvData,
              this.columnNames[0],
              this.width,
              this.height,
              this.basicChartMargin,
              this.updateHighlightedIndices,
              false,
              this.relationType || ""
            );
            contentRendered = true;
          } else if (this.relationType === "Difference") {
            continuous_matrix(
              g,
              this.csvData,
              [this.columnNames[0], this.columnNames[0]],
              this.width,
              this.height,
              this.margin,
              this.invalid_pairs,
              this.invalid_range as invalidRange_Difference,
              this.updateHighlightedIndices,
              this.relationType,
              this.edge,
              this.rotationAngle,
              (this.columnTypes.length === 1
                ? [this.columnTypes[0], this.columnTypes[0]]
                : this.columnTypes) as ("character" | "numeric" | "datetime")[]
            );
            contentRendered = true;
          }
        } else if (this.columnTypes[0] === "datetime") {
          renderDateChart(
            g,
            this.csvData,
            this.columnNames[0],
            this.width,
            this.height,
            this.margin
          );
          contentRendered = true;
        }
      } else if (this.columnNames.length === 2) {
        if (
          this.relationType === "Logical and condition" ||
          this.relationType === "Lookup"
        ) {
          if (
            this.columnTypes[0] === "character" &&
            this.columnTypes[1] === "numeric"
          ) {
            discrete_continuous_matrix(
              g,
              this.csvData,
              this.columnNames,
              this.width,
              this.height,
              this.margin,
              this.invalidIndices,
              this.invalid_range as invalidRange_Equality_Range[],
              this.updateHighlightedIndices,
              this.relationType,
              this.edge,
              this.rotationAngle
            );
            contentRendered = true;
          } else if (
            this.columnTypes[0] === "character" &&
            this.columnTypes[1] === "character"
          ) {
            discrete_matrix(
              g,
              this.csvData,
              this.columnNames,
              this.width,
              this.height,
              this.margin,
              this.invalidIndices,
              this.invalid_range as validRange_Equality_Equality[],
              this.updateHighlightedIndices,
              this.relationType,
              this.rotationAngle,
              this.edge
            );
            contentRendered = true;
          }
        } else if (this.relationType === "Compare") {
          continuous_matrix(
            g,
            this.csvData,
            this.columnNames,
            this.width,
            this.height,
            this.margin,
            this.invalidIndices,
            this.invalid_range as invalidRange_Compare_Numeric,
            this.updateHighlightedIndices,
            this.relationType,
            this.edge,
            this.rotationAngle,
            this.columnTypes as ("character" | "numeric" | "datetime")[]
          );
          contentRendered = true;
        } else if (this.relationType === "MultipleDuplicate") {
          const isChar0 = this.columnTypes[0] === "character";
          const isNum0 = this.columnTypes[0] === "numeric";
          const isChar1 = this.columnTypes[1] === "character";
          const isNum1 = this.columnTypes[1] === "numeric";

          if ((isChar0 && isNum1) || (isNum0 && isChar1)) {
            discrete_continuous_matrix(
              g,
              this.csvData,
              this.columnNames,
              this.width,
              this.height,
              this.margin,
              this.invalidIndices,
              this.invalid_range as invalidRange_Equality_Range[],
              this.updateHighlightedIndices,
              this.relationType,
              this.edge,
              this.rotationAngle
            );
            contentRendered = true;
          } else if (isChar0 && isChar1) {
            discrete_matrix(
              g,
              this.csvData,
              this.columnNames,
              this.width,
              this.height,
              this.margin,
              this.invalidIndices,
              this.invalid_range as validRange_Equality_Equality[],
              this.updateHighlightedIndices,
              this.relationType,
              this.rotationAngle,
              this.edge
            );
            contentRendered = true;
          }
        }
      } else if (this.columnNames.length >= 3) {
        // Support multi-matrix visualization for three or more columns
        if (this.relationType === "MultipleCondition") {
          try {
            await multiple_matrix(
              g,
              this.csvData,
              this.columnNames,
              this.width,
              this.height,
              this.margin,
              this.invalidIndices,
              this.threeColumnRules as ColumnBasedRule[],
              this.updateHighlightedIndices,
              this.relationType,
              1,
              "top"
            );
            if (renderToken !== this.currentRenderToken) {
              return;
            }
            contentRendered = true;
          } catch (error) {
            console.error("Failed to render MultipleCondition matrix", error);
          }
        }
      }

      // Apply zoom only if content was actually rendered
      if (contentRendered && renderToken === this.currentRenderToken) {
        svg.call(this.setupZoomPan);
      }
    },
    setupZoomPan(svg: d3.Selection<SVGSVGElement, unknown, HTMLElement, any>) {
      const zoom = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.5, 8])
        .wheelDelta((event: WheelEvent) => {
          return -event.deltaY * 0.0007;
        })
        .on("zoom", (event) => this.handleZoom(event));

      svg.call(zoom).on("dblclick.zoom", () => {
        const resetTransform = d3.zoomIdentity.translate(
          this.margin.left,
          this.margin.top
        );
        this.currentTransform = resetTransform;

        svg.transition().duration(750).call(zoom.transform, resetTransform);
      });

      // Fix: Apply initial transform only on first load, otherwise maintain state
      if (
        this.currentTransform.x === d3.zoomIdentity.x &&
        this.currentTransform.y === d3.zoomIdentity.y &&
        this.currentTransform.k === d3.zoomIdentity.k
      ) {
        // First load, apply initial transform (no upward offset)
        const initialTransform = d3.zoomIdentity.translate(
          this.margin.left,
          this.margin.top
        );
        this.currentTransform = initialTransform;
        svg.call(zoom.transform, initialTransform);
      } else {
        // Restore previous transform state
        svg.call(zoom.transform, this.currentTransform);
      }
    },

    handleZoom(event: d3.D3ZoomEvent<SVGSVGElement, unknown>) {
      // Save current transform state
      this.currentTransform = event.transform;

      d3.select(".zoomable-group").attr(
        "transform",
        event.transform.toString()
      );
    },
    removeTooltip() {
      d3.select(".inputBox").remove();
    },

    // === Export Modal Methods ===
    showExportDialog() {
      // Trigger event to MainComponent passing current component data
      this.$emit("show-export-dialog", {
        selectedDataset: this.selectedDataset,
        columnNames: this.columnNames,
        columnTypes: this.columnTypes,
        relationType: this.relationType,
        invalidIndices: this.invalidIndices,
        invalid_range: this.invalid_range,
        threeColumnRules: this.threeColumnRules,
      });
    },

    addDatasetOption(value: string, label: string) {
      if (!value) return;
      const exists = this.datasetOptions.some(
        (option) => option.value === value
      );
      if (!exists) {
        this.datasetOptions.push({ value, label });
      }
    },
    handleWorkflowModeChange() {
      this.$emit("workflow-mode-changed", this.workflowMode);
    },
    triggerFileDialog() {
      const input = this.$refs.uploadInput as HTMLInputElement | undefined;
      if (input && !this.isUploading) {
        input.click();
      }
    },
    async handleFileUpload(event: Event) {
      const target = event.target as HTMLInputElement;
      const file = target?.files?.[0];
      if (!file) {
        return;
      }
      try {
        this.isUploading = true;
        const response = await api_upload_dataset(file, this.workflowMode);
        const optionLabel = response.displayName || file.name;
        this.addDatasetOption(response.dataset, optionLabel);
        this.selectedDataset = response.dataset;
        this.changeDataset();
        alert(response.message || "Dataset uploaded successfully");
      } catch (error) {
        console.error("File upload failed", error);
        alert("Upload failed. Please try again.");
      } finally {
        this.isUploading = false;
        if (target) {
          target.value = "";
        }
      }
    },
    async changeDataset() {
      try {
        this.datasetLoadingId++;
        const currentLoadingId = this.datasetLoadingId;
        this.$emit(
          "dataset-changed",
          this.selectedDataset,
          this.workflowMode,
          currentLoadingId
        );
      } catch (error) {
        alert("Failed to switch dataset. Please try again later.");
      }
    },
    exportChart() {
      try {
        const svgElement = document.querySelector("#view svg");

        if (!svgElement) {
          alert("No chart found to export.");
          return;
        }

        const svgClone = svgElement.cloneNode(true) as SVGElement;

        if (!svgClone.getAttribute("xmlns")) {
          svgClone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        }

        const svgData = new XMLSerializer().serializeToString(svgClone);

        const svgBlob = new Blob([svgData], {
          type: "image/svg+xml;charset=utf-8",
        });
        const downloadLink = document.createElement("a");
        downloadLink.href = URL.createObjectURL(svgBlob);
        downloadLink.download = `chart_${new Date()
          .toISOString()
          .slice(0, 10)}.svg`;

        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);

        URL.revokeObjectURL(downloadLink.href);
      } catch (error) {
        alert("Failed to export chart. Please try again later.");
      }
    },
  },
  mounted() {
    this.selectedDataset = "";
    this.isEmpty = true;

    localStorage.removeItem("selectedDataset");
    this.calculateDimensions();
    window.addEventListener("resize", this.handleResize);
  },

  beforeUnmount() {
    window.removeEventListener("resize", this.handleResize);
  },
});
</script>

<style>
.chart-container {
  width: 100%;
  height: 59.69vh;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  z-index: 5;
}

.header-container {
  position: absolute;
  top: 1vh;
  left: 1vw;
  display: flex;
  align-items: center;
  z-index: 100;
  width: 71vw;
}

.rulescope-title {
  width: 10.8vw;
  height: 5.37vh;
  margin: 0;
}

.dataset-selector {
  min-width: 30vw;
  height: 3.6vh;
  margin-left: auto;
  margin-right: 1.85vh;
  display: flex;
  align-items: center;
  column-gap: 0.4vw;
  flex-wrap: nowrap;
  justify-content: flex-end;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 0.35vw;
}

.dataset-selector select {
  padding: 0 1.11vh;
  height: 3.4vh;
  line-height: 3.4vh;
  width: 5.8vw;
  border-radius: 0.46vh;
  border: 2px solid #4570b6;
  background-color: white;
  font-size: 1.2vh;
  font-style: normal;
  font-family: Roboto;
  line-height: normal;
  cursor: pointer;
  margin-top: 0;
  margin-right: 0.92vh;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url("../../public/dropdown_arrow.svg");
  background-repeat: no-repeat;
  background-position: right 0.92vh center;
  background-size: 1.6vh;
  transition: border-color 0.3s, box-shadow 0.3s;
}

#view:active {
  cursor: grabbing;
}

#user-input {
  pointer-events: auto;
  cursor: text;
}

#matrix {
  pointer-events: auto;
  cursor: pointer;
}

#invalid-area {
  pointer-events: auto;
  cursor: pointer;
}

#invalid-data {
  pointer-events: auto;
  cursor: pointer;
}

.upload-btn-wrapper {
  position: relative;
  overflow: hidden;
  display: inline-block;
  margin-top: 0;
  margin-left: 0.35vw;
}

.upload-btn {
  padding: 0 1.6vh;
  border-radius: 0.46vh;
  border: 1px solid #4570b6;
  background-color: #4570b6;
  color: white;
  font-size: 1.35vh;
  font-weight: 600;
  font-family: Roboto;
  cursor: pointer;
  transition: background-color 0.3s;
  height: 3.4vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-btn:disabled {
  cursor: not-allowed;
  opacity: 0.8;
}

.upload-btn:hover {
  background-color: #3a7ca3;
}

.upload-btn-wrapper input[type="file"] {
  display: none;
}

.upload-btn .loading-content {
  display: flex;
  align-items: center;
  gap: 0.6vh;
  font-size: 1.2vh;
}

.upload-btn .spinner {
  width: 1.8vh;
  height: 1.8vh;
  aspect-ratio: 1 / 1;
  border: 0.3vh solid rgba(255, 255, 255, 0.35);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
  box-sizing: border-box;
  flex-shrink: 0;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.dataset-label {
  margin-top: 0;
  margin-right: 0.5vh;
  font-size: 1.4vh;
  font-weight: 900;
  font-family: Roboto;
  font-style: normal;
  line-height: normal;
  text-decoration-style: solid;
  text-decoration-skip-ink: auto;
  text-decoration-thickness: auto;
  text-underline-offset: auto;
  text-underline-position: from-font;
  color: #0c4672;
}

.el-empty__description p {
  color: #7a94a8;
  font-size: 1.6vh;
  font-family: Roboto;
  font-style: normal;
  line-height: normal;
}
</style>
