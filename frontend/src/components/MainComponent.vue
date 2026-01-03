<template>
  <div class="main-container">
    <div class="left-container">
      <ChartView
        ref="chartView"
        :selectedColumns="selectedColumns"
        :csvData="csvData"
        :columnTypes="cardColumnTypes"
        :columnNames="cardcolumnNames"
        :relationType="cardrelationType"
        :invalidIndices="invalidIndices"
        :invalid_range="cardinvalid_range"
        :invalid_pairs="cardinvalid_pairs"
        :threeColumnRules="cardThreeColumnRules"
        @dataset-changed="handleDatasetChanged"
        @workflow-mode-changed="handleWorkflowModeChanged"
        @show-export-dialog="handleShowExportDialog"
      />
      <TableComponent
        ref="tableComponent"
        @columnsChanged="handleSelectedColumnsUpdate"
        @csvDataChanged="handleCsvDataUpdate"
        @rules-update="handleRulesRefined"
        :highlightedIndices="invalidIndices"
        :activeHighlightColumns="cardcolumnNames"
        :sort_conditions="cardsort_conditions"
        :sortedIndices="cardsortedIndices"
        :currentCardType="currentCardType"
        :validationCards="validationCards"
      />
    </div>
    <div class="right-container">
      <CardPanel
        :selectedColumns="selectedColumns"
        :csvData="csvData"
        :rulesUpdate="refinedRules"
        :currentDatasetLoadingId="currentDatasetLoadingId"
        @card-clicked="handleCardClicked"
        @clear-visualization="handleClearVisualization"
        @validation-cards-updated="handleValidationCardsUpdated"
        @rules-refresh-requested="handleRulesRefresh"
      />
    </div>

    <div
      v-if="showExportModal"
      class="modal-overlay"
      @click="closeExportDialog"
    >
      <div class="export-modal" @click.stop>
        <div class="export-modal-header">
          <h3>Export Options</h3>
          <button class="close-btn" @click="closeExportDialog">&times;</button>
        </div>
        <div class="export-modal-content">
          <div class="export-option">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="exportOptions.validationRules"
                class="export-checkbox"
              />
              <span class="checkmark"></span>
              Export Validation Rules (JSON File)
            </label>
          </div>
          <div class="export-option">
            <label class="checkbox-label">
              <input
                type="checkbox"
                v-model="exportOptions.detectFunctions"
                class="export-checkbox"
              />
              <span class="checkmark"></span>
              Export Detect Functions (Python File)
            </label>
          </div>
        </div>
        <div class="export-modal-footer">
          <button
            class="confirm-btn"
            @click="confirmExport"
            :disabled="
              !exportOptions.validationRules && !exportOptions.detectFunctions
            "
          >
            Confirm Export
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import TableComponent from "./TableComponent.vue";
import ChartView from "./ChartView.vue";
import CardPanel from "./DetailView.vue";
import { defineComponent, ref, onMounted, onUnmounted } from "vue";
import { Row, SortCondition, ColumnBasedRule } from "@/types/types";
import type { EventListener } from "@/types/types";
import {
  api_change_dataset,
  api_download_detect_functions,
  api_download_validation_rules,
  api_get_current_csv_content,
  api_set_workflow_mode,
} from "@/utils/callapi";

interface FileSystemFileHandle {
  createWritable(): Promise<FileSystemWritableFileStream>;
}

interface FileSystemWritableFileStream {
  write(data: string | ArrayBuffer | ArrayBufferView | Blob): Promise<void>;
  close(): Promise<void>;
}

interface FileSystemSaveFilePickerOptions {
  suggestedName?: string;
  types?: Array<{
    description?: string;
    accept: Record<string, string[]>;
  }>;
}

declare global {
  interface Window {
    showSaveFilePicker?: (
      options?: FileSystemSaveFilePickerOptions
    ) => Promise<FileSystemFileHandle>;
  }
}

export default defineComponent({
  name: "MainComponent",
  components: {
    TableComponent,
    ChartView,
    CardPanel,
  },
  setup(props, { emit }) {
    const selectedColumns = ref<string[]>([]);
    const csvData = ref<Row[]>([]);
    const tableComponent = ref<InstanceType<typeof TableComponent> | null>(
      null
    );
    const chartView = ref<InstanceType<typeof ChartView> | null>(null);

    const showExportModal = ref(false);
    const exportOptions = ref({
      validationRules: false,
      detectFunctions: false,
    });

    const handleSelectedColumnsUpdate = (columns: string[]) => {
      selectedColumns.value = columns;
    };

    const handleCsvDataUpdate = (data: Row[]) => {
      csvData.value = data;
    };

    const cardColumnTypes = ref<string[]>([]);
    const cardcolumnNames = ref<string[]>([]);
    const invalidIndices = ref<number[]>([]);
    const cardrelationType = ref<string>("");
    const cardsort_conditions = ref<SortCondition[]>([]);
    const cardsortedIndices = ref<number[]>([]);
    const cardinvalid_pairs = ref<
      {
        currentIndex: number;
        nextIndex: number;
        sortCurrentIndex: number;
        sortNextIndex: number;
      }[]
    >([]);
    const cardinvalid_range = ref<
      {
        conditionContent: string;
        start: number;
        startInclusive: boolean;
        end: number;
        endInclusive: boolean;
      }[]
    >([]);
    const currentCardType = ref<string>("");
    const validationCards = ref([]);
    const currentDatasetLoadingId = ref(0);
    const cardThreeColumnRules = ref<ColumnBasedRule[]>([]);
    const refinedRules = ref<Record<string, any>>({});

    const handleShowExportDialog = () => {
      showExportModal.value = true;
      exportOptions.value.validationRules = false;
      exportOptions.value.detectFunctions = false;
    };

    const closeExportDialog = () => {
      showExportModal.value = false;
    };

    const isFsPermissionError = (error: unknown) => {
      return (
        error instanceof DOMException &&
        (error.name === "NotAllowedError" || error.name === "SecurityError")
      );
    };

    const runDownloadFallback = async () => {
      if (exportOptions.value.validationRules) {
        await downloadValidationRules();
      }

      if (exportOptions.value.detectFunctions) {
        await downloadDetectFunctions();
      }

      alert("Files downloaded successfully!");
    };

    const confirmExport = async () => {
      try {
        if (
          !exportOptions.value.validationRules &&
          !exportOptions.value.detectFunctions
        ) {
          alert("Please select at least one export option.");
          return;
        }

        const canUseSavePicker = "showSaveFilePicker" in window;

        if (canUseSavePicker) {
          try {
            if (exportOptions.value.validationRules) {
              await exportValidationRulesWithPicker();
            }

            if (exportOptions.value.detectFunctions) {
              await exportDetectFunctionsWithPicker();
            }

            alert("Files saved successfully!");
            closeExportDialog();
            return;
          } catch (error) {
            if (error instanceof DOMException && error.name === "AbortError") {
              return;
            }

            if (isFsPermissionError(error)) {
              console.warn(
                "Save picker denied access. Falling back to browser download.",
                error
              );
              await runDownloadFallback();
              closeExportDialog();
              return;
            }

            throw error;
          }
        }

        await runDownloadFallback();
        closeExportDialog();
      } catch (error) {
        if (error instanceof Error && error.name !== "AbortError") {
          console.error("Export failed:", error);
          alert("Export failed. Please try again.");
        }
      }
    };

    const normalizeFileName = (name: string, extension: string) => {
      return name.toLowerCase().endsWith(extension)
        ? name
        : `${name}${extension}`;
    };

    const promptForFileName = (defaultName: string, extension: string) => {
      const input = window.prompt(
        `Enter file name (${extension})`,
        defaultName.replace(new RegExp(`${extension}$`, "i"), "")
      );

      const baseName = input?.trim() ? input.trim() : defaultName;
      return normalizeFileName(baseName, extension);
    };

    const saveFileWithPicker = async (
      suggestedName: string,
      extension: string,
      mimeType: string,
      content: string
    ) => {
      if (!("showSaveFilePicker" in window)) {
        throw new Error("Save picker is not supported in this browser");
      }

      const pickerHandle = await window.showSaveFilePicker!({
        suggestedName: normalizeFileName(suggestedName, extension),
        types: [
          {
            description: `${extension} file`,
            accept: {
              [mimeType]: [extension],
            },
          },
        ],
      });

      const writable = await pickerHandle.createWritable();
      await writable.write(new Blob([content], { type: mimeType }));
      await writable.close();
    };

    const fetchCurrentValidationRules = async () => {
      const { fileName, content } = await api_download_validation_rules();
      return { fileName, content };
    };

    const fetchDetectFunctionScript = async () => {
      const { fileName, content } = await api_download_detect_functions();
      return { fileName, content };
    };

    const exportValidationRulesWithPicker = async () => {
      const { fileName, content } = await fetchCurrentValidationRules();
      await saveFileWithPicker(fileName, ".json", "application/json", content);
    };

    const exportDetectFunctionsWithPicker = async () => {
      const { fileName, content } = await fetchDetectFunctionScript();
      const suggestedName =
        fileName ||
        `detect_functions_${new Date().toISOString().slice(0, 10)}.py`;
      await saveFileWithPicker(suggestedName, ".py", "text/x-python", content);
    };

    const downloadValidationRules = async () => {
      const { fileName, content } = await fetchCurrentValidationRules();
      const targetName = promptForFileName(fileName, ".json");
      const blob = new Blob([content], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = targetName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    const downloadDetectFunctions = async () => {
      const { fileName, content } = await fetchDetectFunctionScript();
      const fallbackName = `detect_functions_${new Date()
        .toISOString()
        .slice(0, 10)}.py`;
      const targetName = promptForFileName(fileName || fallbackName, ".py");
      const blob = new Blob([content], { type: "text/x-python" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = targetName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    onMounted(() => {
      document.addEventListener("rules-update", ((event: CustomEvent) => {
        refinedRules.value = event.detail.selectedExamples;
      }) as EventListener);
    });

    onUnmounted(() => {
      document.removeEventListener("rules-update", ((event: CustomEvent) => {
        refinedRules.value = event.detail.selectedExamples;
      }) as EventListener);
    });

    const handleCardClicked = (
      columnTypes: string[],
      indices: number[],
      columnNames: string[],
      relationType: string,
      invalid_range: {
        conditionContent: string;
        start: number;
        startInclusive: boolean;
        end: number;
        endInclusive: boolean;
      }[],
      sort_conditions: SortCondition[],
      invalid_pairs: {
        currentIndex: number;
        nextIndex: number;
        sortCurrentIndex: number;
        sortNextIndex: number;
      }[],
      sortedIndices: number[],
      threeColumnRules: ColumnBasedRule[]
    ) => {
      cardColumnTypes.value = columnTypes;
      invalidIndices.value = indices;
      cardcolumnNames.value = columnNames;
      cardrelationType.value = relationType;
      currentCardType.value = relationType;
      cardinvalid_range.value = invalid_range;
      cardsort_conditions.value = sort_conditions;
      cardinvalid_pairs.value = invalid_pairs;
      cardsortedIndices.value = sortedIndices;
      cardThreeColumnRules.value = threeColumnRules;
    };

    const handleRulesRefined = (data) => {
      refinedRules.value = data;
    };

    const handleClearVisualization = () => {
      cardColumnTypes.value = [];
      cardcolumnNames.value = [];
      invalidIndices.value = [];
      cardrelationType.value = "";
      currentCardType.value = "";
      cardinvalid_range.value = [];
      cardsort_conditions.value = [];
      cardinvalid_pairs.value = [];
      cardsortedIndices.value = [];
      cardThreeColumnRules.value = [];
      if (chartView.value) {
        chartView.value.$el.querySelector("#view").innerHTML = "";
      }
    };

    const handleRulesRefresh = () => {
      const tableRef = tableComponent.value as any;
      tableRef?.getConstraintMap?.();
    };
    const handleValidationCardsUpdated = (cards) => {
      validationCards.value = cards;
    };

    const handleDatasetChanged = async (
      dataset: string,
      workflowMode: string,
      loadingId: number
    ) => {
      try {
        currentDatasetLoadingId.value = loadingId;

        cardColumnTypes.value = [];
        cardcolumnNames.value = [];
        invalidIndices.value = [];
        cardrelationType.value = "";
        currentCardType.value = "";
        cardinvalid_range.value = [];
        cardsort_conditions.value = [];
        cardinvalid_pairs.value = [];
        cardsortedIndices.value = [];
        validationCards.value = [];
        selectedColumns.value = [];

        await api_change_dataset(dataset, workflowMode);
        const csvContent = await api_get_current_csv_content();

        if (tableComponent.value) {
          tableComponent.value.loadCsvFromContent(csvContent, loadingId);
        }
      } catch (error) {
        console.error("Failed to load dataset:", error);
      }
    };

    const handleWorkflowModeChanged = async (mode: string) => {
      try {
        await api_set_workflow_mode(mode);
      } catch (error) {
        console.error("Failure to update workflow mode:", error);
      }
    };

    return {
      selectedColumns,
      csvData,
      handleSelectedColumnsUpdate,
      handleCsvDataUpdate,
      cardColumnTypes,
      invalidIndices,
      handleCardClicked,
      cardcolumnNames,
      cardrelationType,
      cardinvalid_range,
      cardsort_conditions,
      cardinvalid_pairs,
      cardsortedIndices,
      refinedRules,
      handleRulesRefined,
      handleClearVisualization,
      currentCardType,
      validationCards,
      handleValidationCardsUpdated,
      handleRulesRefresh,
      handleDatasetChanged,
      handleWorkflowModeChanged,
      tableComponent,
      chartView,
      cardThreeColumnRules,
      currentDatasetLoadingId,
      showExportModal,
      exportOptions,
      handleShowExportDialog,
      closeExportDialog,
      confirmExport,
    };
  },
  props: {
    msg: String,
  },
});
</script>

<style>
html,
body {
  height: 100%;
  margin: 0;
  padding: 0;
}

.main-container {
  display: flex;
  height: 100vh;
  position: relative; /* 为模态框提供定位上下文 */
}

.left-container {
  display: flex;
  flex-direction: column;
  width: 70.68vw;
  height: 100vh;
}

.right-container {
  display: flex;
  flex-direction: column;
  width: 27.8vw;
  margin-left: 1vw;
  height: 100vh;
}

/* === Export Modal Styles === */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    transform: translateY(-50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.export-modal {
  background: white;
  border-radius: 12px;
  width: 450px;
  max-width: 90vw;
  max-height: 80vh;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  animation: slideIn 0.3s ease-out;
  position: relative;
}

.export-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.export-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  font-family: Roboto;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background-color: #f3f4f6;
  color: #374151;
  transform: scale(1.1);
}

.export-modal-content {
  padding: 24px;
  background-color: #ffffff;
}

.export-option {
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s ease;
}

.export-option:hover {
  border-color: #4570b6;
  background-color: #f8fafc;
}

.checkbox-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 15px;
  font-family: Roboto;
  color: #374151;
  position: relative;
  padding-left: 35px;
  user-select: none;
  font-weight: 500;
  line-height: 1.5;
}

.export-checkbox {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

.checkmark {
  position: absolute;
  left: 0;
  height: 22px;
  width: 22px;
  background-color: #fff;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.checkbox-label:hover .checkmark {
  border-color: #4570b6;
  background-color: #f8fafc;
  transform: scale(1.05);
}

.export-checkbox:checked ~ .checkmark {
  background-color: #4570b6;
  border-color: #4570b6;
  transform: scale(1.1);
}

.checkmark:after {
  content: "";
  position: absolute;
  display: none;
  left: 7px;
  top: 3px;
  width: 6px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.export-checkbox:checked ~ .checkmark:after {
  display: block;
}

.export-modal-footer {
  padding: 24px;
  border-top: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.confirm-btn {
  background: linear-gradient(135deg, #4570b6 0%, #3a7ca3 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 15px;
  font-family: Roboto;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(69, 112, 182, 0.3);
  position: relative;
  overflow: hidden;
}

.confirm-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(69, 112, 182, 0.4);
}

.confirm-btn:active:not(:disabled) {
  transform: translateY(0);
}

.confirm-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
</style>
