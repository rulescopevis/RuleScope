<template>
  <div>
    <div class="table-container">
      <div class="table-top-controls">
        <button class="sort-settings-btn" @click="toggleSortSettings">
          <img
            src="/table_icon/conditions.svg"
            alt="Multi-level Sort Settings"
            class="sort-icon"
          />
        </button>
        <div
          class="sort-conditions-display"
          v-if="
            sortConditions &&
            sortConditions.length > 0 &&
            sortConditions[0].columnName
          "
        >
          <span class="sort-title">Condition</span>
          <div class="sort-conditions-container">
            <div
              class="sort-condition-item"
              v-for="(condition, index) in sortConditions"
              :key="index"
            >
              <img
                :src="`/table_icon/sort_${index + 1}.svg`"
                :alt="`Condition ${index + 1}`"
                class="condition-number-icon"
              />
              {{ condition.columnName }}
              <img
                :src="`/table_icon/${
                  condition.order === 'asc' ? 'asc' : 'desc'
                }.svg`"
                :alt="condition.order === 'asc' ? 'asc' : 'desc'"
                class="sort-direction-icon"
              />
            </div>
          </div>
        </div>
        <div class="sort-conditions-display" v-else>
          <span class="sort-title">Conditions: None</span>
        </div>

        <div class="top-buttons">
          <span class="invalid-data-info">
            <input
              type="number"
              v-model.number="invalidInputIndex"
              :min="1"
              :max="jumpHighlightIndex.length"
              class="inline-invalid-input"
              :disabled="!hasHighlightedData"
              @keyup.enter="jumpToSpecificInvalid"
            />
            / {{ jumpHighlightIndex.length }} Invalid Data
          </span>
          <button
            class="invalid-data-button-last"
            @click="jumpToPrevInvalidData"
            :disabled="!hasHighlightedData"
          >
            <img
              src="/table_icon/lastpage.svg"
              alt="Previous"
              class="button-icon"
            />
            <span class="button-text-last">Last</span>
          </button>
          <div
            class="button-divider"
            :class="{ 'disabled-divider': !hasHighlightedData }"
          ></div>
          <button
            class="invalid-data-button-next"
            @click="jumpToNextInvalidData"
            :disabled="!hasHighlightedData"
          >
            <span class="button-text-next">Next</span>
            <img
              src="/table_icon/nextpage.svg"
              alt="Next"
              class="button-icon"
            />
          </button>
        </div>
      </div>

      <div
        class="scrollable-container"
        ref="scrollableContainerRef"
        @mousedown="handleMouseDown"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp"
        @mouseleave="handleMouseLeave"
        @scroll="updateSelectionIconPosition"
      >
        <div
          v-if="isDragging"
          class="selection-box"
          :style="{
            left: selectionBox.left + 'px',
            top: selectionBox.top + 'px',
            width: selectionBox.width + 'px',
            height: selectionBox.height + 'px',
          }"
        ></div>
        <table ref="tableRef" class="csv-table">
          <thead>
            <tr>
              <th
                v-for="(header, cellIndex) in headers"
                :key="header"
                draggable="true"
                :class="{
                  'selected-column': selectedColumns.includes(header),
                  'disabled-column': !isColumnEnabled(header),
                }"
                :style="columnWidthStyle"
                @click="toggleColumnSelection(header)"
              >
                <span
                  v-if="columnConflictCounts[header] > 0"
                  class="conflict-badge"
                  >{{ columnConflictCounts[header] }}</span
                >
                <span class="header-text" :title="header">{{ header }}</span>
                <div
                  :ref="'histogram-' + cellIndex"
                  class="histogram-container"
                ></div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, rowIndex) in displayedRows"
              :key="rowIndex"
              :data-id="row.id"
            >
              <td
                v-for="(cell, cellIndex) in Object.values(row)"
                :key="cellIndex"
                :class="[
                  highlightCell(row.id as number, cellIndex),
                  isSelectedCell(rowIndex, cellIndex) ? 'selected-cell' : ''
                ]"
                :data-row="rowIndex"
                :data-col="cellIndex"
                :style="columnWidthStyle"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
        <div
          v-if="selectedCells.length > 0"
          class="selection-icon"
          @click="showSelectionMenu"
        ></div>

        <Teleport to="body">
          <div
            v-if="showSelectionOptions"
            class="selection-menu"
            :style="selectionMenuStyle"
          >
            <div class="menu-option" @click="handleOptionValid">
              <img src="/valid_example.png" alt="Icon 1" class="menu-icon" />
              Valid Example
            </div>
            <div class="menu-option dashed" @click="handleOptionInvalid">
              <img src="/invalid_example.png" alt="Icon 2" class="menu-icon" />
              Invalid Example
            </div>
          </div>
        </Teleport>
      </div>

      <div class="table-controls">
        <div class="column-selector">
          <div class="selected-columns-display">
            <span class="sort-title">Selected Columns</span>
            <template v-if="selectedColumns && selectedColumns.length > 0">
              <div
                class="column-tag"
                v-for="column in selectedColumns"
                :key="column"
              >
                <span class="column-name">{{ column }}</span>
                <span class="delete-icon" @click.stop="removeColumn(column)"
                  >×</span
                >
              </div>
            </template>
            <span v-else class="sort-title">:None</span>
          </div>
        </div>

        <div class="pagination-controls">
          <div v-if="isFiltered">
            <span
              >filtered: {{ currentFilterInfo?.column }} =
              {{ currentFilterInfo?.value }}</span
            >
            <button class="reset-filter-btn" @click="resetFilter">
              reset filter
            </button>
          </div>

          <button @click="prevPage" :disabled="currentPage === 0">
            <img
              src="/table_icon/lastpage_black.svg"
              alt="Previous"
              class="button-icon"
            />
          </button>

          <span class="page-info">
            <template v-if="totalPages > 0">
              <template
                v-for="(pageNum, index) in displayedPageNumbers"
                :key="index"
              >
                <span
                  class="page-number"
                  :class="{ 'current-page': pageNum === currentPage + 1 }"
                  @click="goToPageNumber(pageNum)"
                >
                  {{ pageNum }}
                </span>
                <span
                  v-if="index < displayedPageNumbers.length - 1"
                  class="page-separator"
                  >,</span
                >
              </template>
            </template>
            <template v-else> 0 total page </template>
          </span>

          <input
            type="number"
            v-model.number="inputPage"
            min="1"
            :max="totalPages"
            @keyup.enter="goToPage"
            placeholder="input page number"
          />
          <button @click="nextPage" :disabled="currentPage >= totalPages - 1">
            <img
              src="/table_icon/nextpage_black.svg"
              alt="Next"
              class="button-icon"
            />
          </button>
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="showSortSettings" class="sort-settings">
        <div class="sort-header">
          <span>Multi-level Sort Settings</span>
          <button @click="toggleSortSettings">Close</button>
        </div>
        <div class="sort-options">
          <div
            v-for="(sortCondition, index) in sortConditions"
            :key="index"
            class="sort-condition"
          >
            <select v-model="sortCondition.columnName">
              <option v-for="header in headers" :key="header" :value="header">
                {{ header }}
              </option>
            </select>
            <select v-model="sortCondition.order">
              <option value="asc">Ascending</option>
              <option value="desc">Descending</option>
            </select>
            <button @click="removeSortCondition(index)">Delete</button>
          </div>
          <button @click="addSortCondition">Add Condition</button>
        </div>
        <button @click="applySortSettings">Apply Sort</button>
      </div>
    </transition>

    <RefineModel
      v-if="showRefineModal"
      :isInvalid="!validFlag"
      :selectedData="selectedCellsData"
      :refineResult="refineResult"
      @close="closeRefineModal"
      @submit="handleRefineSubmit"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted } from "vue";
import {
  Row,
  ParsedCSV,
  ConstraintMap,
  SortCondition,
  CellPosition,
  RelationItem,
  SelectInfo,
  RefineResult,
} from "@/types/types";
import { parseCSV } from "@/methods/tablemethods";
import {
  api_refine_validation_rules,
  api_get_refine_rules,
  api_load_table_vis_valueList,
  api_get_constraint_map,
} from "@/utils/callapi";
import RefineModel from "./RefineModel.vue";
import { ElMessage, ElMessageBox } from "element-plus";
import * as d3 from "d3";

interface HistogramData {
  value: string;
  count: number;
}

export default defineComponent({
  name: "TableComponent",
  components: {
    RefineModel,
  },
  props: {
    sort_conditions: {
      type: Array as () => SortCondition[],
      required: true,
    },
    highlightedIndices: {
      type: Array as () => number[],
      required: true,
    },
    activeHighlightColumns: {
      type: Array as () => string[],
      required: true,
    },
    sortedIndices: {
      type: Array as () => number[],
      required: true,
    },
    currentCardType: {
      type: String,
      default: "",
    },
    validationCards: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["columnsChanged", "csvDataChanged", "rulesRefined", "rules-update"],
  setup() {
    const tableRef = ref<HTMLElement | null>(null);
    const scrollableContainerRef = ref<HTMLElement | null>(null);
    return {
      tableRef,
      scrollableContainerRef,
    };
  },
  data(): {
    sortIndex: number[];
    csvData: Row[];
    headers: string[];
    rows: Row[];
    displayedRows: Row[];
    currentPage: number;
    rowsPerPage: number;
    inputPage: number;
    showSortSettings: boolean;
    selectedColumns: string[];
    selectedOptions: string[];
    currenthighlightedIndices: number[];
    currentHighlightColumns: string[];
    constraintMap: ConstraintMap;
    sortConditions: SortCondition[];
    selectedCells: CellPosition[];
    ctrlClickCells: CellPosition[];
    genCell: CellPosition | null;
    currentFilterColumn: number;
    ctrlSelectedCells: CellPosition[];
    startX: number;
    startY: number;
    selectionRectangle: HTMLElement | null;
    startCell: CellPosition | null;
    isDragging: boolean;
    ifStartFromCtrl: boolean;
    headerShadowElement: HTMLElement | null;
    isRightClick: boolean;
    isColor: boolean;
    colorIndex: number;
    showContextMenu: boolean;
    contextMenuTop: number;
    contextMenuLeft: number;
    purpleRange: string[];
    blueRange: string[];
    startPosition: { x: number; y: number };
    selectionBox: { left: number; top: number; width: number; height: number };
    showSelectionOptions: boolean;
    selectionMenuStyle: { top: string; left: string };
    showRefineModal: boolean;
    isInvalidExample: boolean;
    refineResult: RefineResult;
    selectedCellsData: any[];
    validFlag: boolean;
    refineData: {
      selectInfo: SelectInfo;
      selectedData: any[];
      isInvalid: boolean;
      isFromSequenceMatrix: boolean;
    };
    tableVisInfo: { [key: string]: { value: number; count: number }[] } | null;
    filteredRows: Row[];
    isFiltered: boolean;
    currentFilterInfo: { column: string; value: string } | null;
    currentHighlightIndex: number;
    jumpHighlightIndex: number[];
    invalidInputIndex: number;
    columnConflictCounts: { [key: string]: number };
  } {
    return {
      sortIndex: [],
      csvData: [],
      headers: [],
      rows: [],
      displayedRows: [],
      currentPage: 0,
      rowsPerPage: 50,
      inputPage: 1,
      showSortSettings: false,
      selectedColumns: [],
      selectedOptions: [],
      currenthighlightedIndices: [],
      currentHighlightColumns: [],
      constraintMap: {},
      sortConditions: [{ columnName: "", order: "asc" }],
      selectedCells: [],
      ctrlClickCells: [],
      genCell: null,
      currentFilterColumn: 0,
      ctrlSelectedCells: [],
      startX: 0,
      startY: 0,
      selectionRectangle: null,
      startCell: null,
      ifStartFromCtrl: false,
      headerShadowElement: null,
      isRightClick: false,
      isColor: false,
      colorIndex: 0,
      showContextMenu: false,
      contextMenuTop: 0,
      contextMenuLeft: 0,
      blueRange: ["#DEEBF7", "#C2E1FF", "#8BB8E6"],
      purpleRange: ["#E0E0F0", "#C2BFE0", "#A59BCF"],
      isDragging: false,
      startPosition: { x: 0, y: 0 },
      selectionBox: { left: 0, top: 0, width: 0, height: 0 },
      showSelectionOptions: false,
      selectionMenuStyle: { top: "0px", left: "0px" },
      showRefineModal: false,
      isInvalidExample: false,
      refineResult: {
        refineStatus: false,
        refineDict: {
          addRules: [],
          deleteRules: [],
          updateRules: [],
        },
      },
      selectedCellsData: [],
      validFlag: true,
      refineData: {
        selectInfo: {
          columnList: [],
          indexList: [],
          conditionIndexList: [],
        },
        selectedData: [],
        isInvalid: false,
        isFromSequenceMatrix: false,
      },
      tableVisInfo: null,
      filteredRows: [],
      isFiltered: false,
      currentFilterInfo: null,
      currentHighlightIndex: -1,
      jumpHighlightIndex: [],
      invalidInputIndex: 1,
      columnConflictCounts: {},
    };
  },
  watch: {
    sort_conditions: {
      handler(newVal: SortCondition[]) {
        this.sortConditions = newVal; // Assuming sortConditions data structure exists
        this.orderSort(); // Execute sort
      },
    },
    activeHighlightColumns: {
      handler(newVal: string[]) {
        this.currentHighlightColumns = [...newVal];
      },
    },
    highlightedIndices: {
      handler(newVal: number[]) {
        this.currenthighlightedIndices = [...newVal];
        this.resetFilter();
        this.highlightAndScrollToTable(
          this.currenthighlightedIndices,
          this.currentHighlightColumns,
          this.sortedIndices
        );
      },
    },
    sortedIndices: {
      handler(newVal: number[]) {
        this.jumpHighlightIndex = [...newVal];
        // Reset current index
        this.currentHighlightIndex = -1;
      },
    },
    jumpHighlightIndex: {
      handler(newVal: number[]) {
        this.currentHighlightIndex = -1;
        // Ensure input shows 1 when highlighted data exists
        this.invalidInputIndex = newVal.length > 0 ? 1 : 0;
      },
      immediate: true, // Ensure execution on initialization
    },
    validationCards: {
      handler(newCards) {
        this.updateColumnConflictCounts(newCards);
      },
      immediate: true,
      deep: true,
    },
    currentHighlightIndex: {
      handler(newVal) {
        if (newVal !== -1) {
          this.invalidInputIndex = newVal + 1;
        } else if (this.jumpHighlightIndex.length > 0) {
          this.invalidInputIndex = 1;
        } else {
          this.invalidInputIndex = 0;
        }
      },
      immediate: true,
    },
  },
  computed: {
    totalPages(): number {
      const sourceData = this.isFiltered ? this.filteredRows : this.rows;
      return Math.ceil(sourceData.length / this.rowsPerPage);
    },
    hasHighlightedData(): boolean {
      return this.currenthighlightedIndices.length > 0;
    },
    // Page number display logic
    displayedPageNumbers(): (number | string)[] {
      const result: (number | string)[] = [];
      const maxPages = this.totalPages;
      const currentPage = this.currentPage + 1;

      // Always show three consecutive page numbers
      // If current is page 1, show 1, 2, 3
      if (currentPage === 1) {
        for (let i = 1; i <= Math.min(3, maxPages); i++) {
          result.push(i);
        }
      } else {
        // Otherwise show currentPage-1, currentPage, currentPage+1
        const startPage = Math.max(1, currentPage - 1);
        for (let i = startPage; i <= Math.min(startPage + 2, maxPages); i++) {
          result.push(i);
        }
      }

      // If more pages, add ellipsis and last page
      const lastItem = result[result.length - 1];
      if (typeof lastItem === "number" && lastItem < maxPages - 1) {
        result.push("...");
        result.push(maxPages);
      } else if (lastItem === maxPages - 1) {
        // If the last displayed is the second to last page, just show last page
        result.push(maxPages);
      }

      return result;
    },
    columnWidthStyle(): Record<string, string> {
      const columnCount =
        this.headers && this.headers.length > 0 ? this.headers.length : 1;
      if (columnCount >= 10) {
        return {
          width: "13.29vh",
          minWidth: "13.29vh",
        };
      }
      const widthPercent = `${(100 / columnCount).toFixed(4)}%`;
      return {
        width: widthPercent,
        minWidth: widthPercent,
      };
    },
  },
  methods: {
    onFileChange(e: Event): void {
      const target = e.target as HTMLInputElement;
      const file = target.files ? target.files[0] : null;
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e: ProgressEvent<FileReader>): void => {
        const datasetText = e.target?.result as string;
        this.parseCsv(datasetText);
      };
      reader.readAsText(file);
    },
    async parseCsv(datasetText: string): Promise<void> {
      try {
        const { csvData, headers }: ParsedCSV = parseCSV(datasetText);

        this.csvData = csvData.map((row, index) => ({
          ...row,
          id: index,
        }));
        this.headers = headers;
        this.$emit("csvDataChanged", this.csvData); // Ensure this event triggers

        this.sortIndex = headers.map(() => 0);
        this.rows = this.csvData;

        // Load table visualization info after successful CSV parse
        await this.drawHistograms();
        // Update constraintMap
        await this.getConstraintMap();
        this.loadPageData();
      } catch (error) {
        // Handle CSV parse error
      }
    },
    prevPage() {
      if (this.currentPage > 0) {
        this.currentPage--;
        this.loadPageData();
      }
    },
    nextPage() {
      if (this.currentPage < this.totalPages - 1) {
        this.currentPage++;
        this.loadPageData();
      }
    },
    goToPage() {
      const page = Math.max(1, Math.min(this.inputPage, this.totalPages)) - 1;
      this.currentPage = page;
      this.loadPageData();
    },
    // Modified data loading method
    loadPageData() {
      const start = this.currentPage * this.rowsPerPage;
      const end = start + this.rowsPerPage;
      // Use filtered data or original data
      const sourceData = this.isFiltered ? this.filteredRows : this.rows;
      this.displayedRows = sourceData.slice(start, end);
      this.inputPage = this.currentPage + 1; // Sync input box
    },
    toggleSortSettings(): void {
      this.showSortSettings = !this.showSortSettings;
    },
    handleColumnSelection() {
      this.$emit("columnsChanged", this.selectedColumns);
      // Update chart logic, temporarily commented out
      // this.updateChart();
    },
    // Check if column is enabled in current selection state
    isColumnEnabled(column: string) {
      // If selected, keep enabled (prevent self-disabling)
      if (this.selectedColumns.includes(column)) {
        return true;
      }
      // If none selected, all are enabled
      if (this.selectedColumns.length === 0) {
        return true;
      }
      // Intersect all constraints from constraintMap for selected columns
      let commonConstraints: string[] | null = null;
      for (const col of this.selectedColumns) {
        const constraints = this.constraintMap[col] || [];
        if (commonConstraints === null) {
          // First assignment
          commonConstraints = constraints.slice();
        } else {
          // Intersect
          commonConstraints = commonConstraints.filter((c) =>
            constraints.includes(c)
          );
        }
      }
      // If final intersection contains column, it's enabled
      return commonConstraints && commonConstraints.includes(column);
    },
    // Toggle column selection on header click
    toggleColumnSelection(column: string) {
      // If disabled in current state, do nothing
      if (!this.isColumnEnabled(column)) {
        return;
      }
      const index = this.selectedColumns.indexOf(column);
      if (index > -1) {
        // If selected, deselect
        this.selectedColumns.splice(index, 1);
      } else {
        // If not selected, add
        this.selectedColumns.push(column);
      }
      this.handleColumnSelection();
    },
    isSort(cellIndex: number, index: number): boolean {
      return index === this.sortIndex[cellIndex];
    },
    handleSortClick(event: MouseEvent, cellIndex: number, index: number): void {
      event.stopPropagation(); // Stop event propagation
      this.sortConditions = [{ columnName: "", order: "asc" }];
      this.sortIndex = this.headers.map(() => 0); // Initialize or reset sortIndex
      this.sortIndex[cellIndex] = index;

      if (index === 0) {
        this.rows = [...this.csvData];
      } else {
        const columnName = this.headers[cellIndex];
        this.rows = [...this.csvData].sort((a, b) => {
          const valueA = a[columnName] as string;
          const valueB = b[columnName] as string;
          return (index === 1 ? 1 : -1) * (valueA < valueB ? -1 : 1);
        });
      }
      this.loadPageData();
    },
    highlightCell(rowId: number, cellIndex: number) {
      if (!this.headers || cellIndex >= this.headers.length) {
        return "";
      }
      const currentColumnName = this.headers[cellIndex];
      // Modify logic: check if current column is in the column name array of the clicked card
      const isTargetColumn = this.currentHighlightColumns.some(
        (name: string) => currentColumnName === name
      );

      const isHighlighted = this.currenthighlightedIndices.includes(rowId);
      return isHighlighted && isTargetColumn ? "highlight-cell" : "";
    },
    updateHighlightedIndices(rowIds: number[], columns: string[]) {
      this.currenthighlightedIndices = [...rowIds];
      this.currentHighlightColumns = [...columns]; // Update highlighted column array
    },

    async handleHighlightInvalidData(event: Event) {
      const customEvent = event as CustomEvent;
      const { rowIds, highlightColumns, sortedIndices } = customEvent.detail;

      this.resetFilter();
      this.jumpHighlightIndex = [...sortedIndices];
      this.updateHighlightedIndices(rowIds, highlightColumns);

      if (sortedIndices.length > 0) {
        const firstRowId = sortedIndices[0];
        await this.scrollToRow(firstRowId);
      }

      // Trigger refine popup only when allowed, avoiding duplicate hints for Sequence right-click
      if (
        customEvent.detail.isRightClick &&
        !customEvent.detail.disableRefine &&
        this.currentCardType !== "Sequence"
      ) {
        this.handleRightClick(rowIds, highlightColumns, sortedIndices);
      }
    },
    async highlightAndScrollToTable(
      rowIds: number[],
      selectedColumns: string[],
      sortedIndices: number[]
    ) {
      // Click card propagation
      this.updateHighlightedIndices(rowIds, selectedColumns);
      if (sortedIndices.length > 0) {
        const firstRowId = sortedIndices[0];
        await this.scrollToRow(firstRowId);
      }
    },

    async scrollToRow(targetRowId: number) {
      const tableRef = this.$refs.tableRef as HTMLElement;

      // Add safety check
      if (!tableRef) {
        return;
      }

      // Calculate target page (0-based index)
      const targetPage = Math.floor(targetRowId / this.rowsPerPage);
      // If not current page, load target page
      if (targetPage !== this.currentPage) {
        this.currentPage = targetPage;
        this.loadPageData();
      }

      const rowIndexInCurrentPage = targetRowId % this.rowsPerPage;

      // Scroll after DOM update
      this.$nextTick(() => {
        // Check refs availability again
        if (!this.$refs.tableRef || !this.$refs.scrollableContainerRef) {
          return;
        }

        const container = this.$refs.scrollableContainerRef as HTMLElement;
        const tableRef = this.$refs.tableRef as HTMLElement;

        const rowElement = tableRef.querySelector(
          `tbody tr:nth-child(${rowIndexInCurrentPage + 1})`
        ) as HTMLElement;

        if (rowElement) {
          container.scrollTop =
            rowElement.offsetTop - container.offsetHeight / 2;
          rowElement.classList.add("scroll-highlight");
          setTimeout(
            () => rowElement.classList.remove("scroll-highlight"),
            1000
          );
        }
      });
    },
    removeSortCondition(index: number): void {
      this.sortConditions.splice(index, 1);
    },
    addSortCondition() {
      this.sortConditions.push({ columnName: "", order: "asc" });
    },
    orderSort(): void {
      this.sortIndex.fill(0); // Reset all sort indices
      let rows = [...this.csvData];

      // Modify sort logic
      rows.sort((a, b) => {
        // Iterate all sort conditions
        for (const condition of this.sortConditions) {
          if (!condition.columnName) continue; // Skip empty conditions

          const valA = a[condition.columnName] as string;
          const valB = b[condition.columnName] as string;

          // If values under current condition are not equal, return comparison result
          if (valA !== valB) {
            // Try numeric comparison
            const numA = Number(valA);
            const numB = Number(valB);

            if (!isNaN(numA) && !isNaN(numB)) {
              // Numeric comparison
              return condition.order === "asc" ? numA - numB : numB - numA;
            } else {
              // String comparison
              return condition.order === "asc"
                ? valA.localeCompare(valB)
                : valB.localeCompare(valA);
            }
          }
        }
        return 0; // Maintain original order if all conditions are equal
      });

      this.rows = rows;
      this.loadPageData(); // Reload current page data
    },
    applySortSettings(): void {
      this.sortIndex.fill(0); // Reset all sort indices
      let rows = [...this.csvData];

      // Modify sort logic
      rows.sort((a, b) => {
        // Iterate all sort conditions
        for (const condition of this.sortConditions) {
          if (!condition.columnName) continue; // Skip empty conditions

          const valA = a[condition.columnName] as string;
          const valB = b[condition.columnName] as string;

          // If values under current condition are not equal, return comparison result
          if (valA !== valB) {
            // Try numeric comparison
            const numA = Number(valA);
            const numB = Number(valB);

            if (!isNaN(numA) && !isNaN(numB)) {
              // Numeric comparison
              return condition.order === "asc" ? numA - numB : numB - numA;
            } else {
              // String comparison
              return condition.order === "asc"
                ? valA.localeCompare(valB)
                : valB.localeCompare(valA);
            }
          }
        }
        return 0; // Maintain original order if all conditions are equal
      });

      this.rows = rows;

      // Update highlighted indices
      const highlightedRowIds = this.highlightedIndices.map(
        (rowIndex) => this.csvData[rowIndex].id
      );
      const newHighlightedIndices = highlightedRowIds
        .map((rowId) => this.rows.findIndex((row) => row.id === rowId))
        .filter((index) => index !== -1);
      this.updateHighlightedIndices(
        newHighlightedIndices,
        this.currentHighlightColumns
      );

      this.loadPageData(); // Reload current page data
      this.toggleSortSettings(); // Close sort settings panel
    },
    // Get constraintMap for column selection constraints
    async getConstraintMap() {
      try {
        const data = await api_get_constraint_map();
        this.constraintMap = data;
      } catch (error) {
        // Handle error
      }
    },
    // Handle mouse down event
    handleMouseDown(event: MouseEvent): void {
      // If clicking selection icon or menu, do not trigger selection
      if (
        (event.target as HTMLElement).closest(".selection-icon") ||
        (event.target as HTMLElement).closest(".selection-menu")
      ) {
        return;
      }

      // If clicking outside menu area, close menu
      if (!(event.target as HTMLElement).closest(".selection-menu")) {
        this.showSelectionOptions = false;
      }

      // Only handle left click
      if (event.button !== 0) return;

      // Check if clicking on a table cell
      const target = event.target as HTMLElement;
      const cell = target.closest("td");
      if (!cell) return;

      // Get click position
      this.isDragging = true;
      this.startPosition = {
        x: event.clientX,
        y: event.clientY,
      };

      // Initialize selection box
      this.selectionBox = {
        left: event.clientX,
        top: event.clientY,
        width: 0,
        height: 0,
      };

      // Clear previous selection if Ctrl is not pressed
      if (!(event as MouseEvent).ctrlKey) {
        this.selectedCells = [];
      }

      // Prevent default behavior and bubbling
      event.preventDefault();
    },

    // Handle mouse move event
    handleMouseMove(event: MouseEvent): void {
      if (!this.isDragging) return;

      // Calculate selection box size and position
      const currentX = event.clientX;
      const currentY = event.clientY;

      // Calculate top-left coordinate and dimensions
      const left = Math.min(this.startPosition.x, currentX);
      const top = Math.min(this.startPosition.y, currentY);
      const width = Math.abs(currentX - this.startPosition.x);
      const height = Math.abs(currentY - this.startPosition.y);

      this.selectionBox = { left, top, width, height };

      // Update selected cells
      this.updateSelectedCells();
    },

    // Handle mouse up event
    handleMouseUp(event: MouseEvent): void {
      if (!this.isDragging) return;

      this.isDragging = false;

      // Final update of selected cells
      this.updateSelectedCells();

      // Ensure icon position updates after mouse up
      if (this.selectedCells.length > 0) {
        this.$nextTick(() => {
          this.updateSelectionIconPosition();
        });
      }
    },

    // Handle mouse leave event
    handleMouseLeave(event: MouseEvent): void {
      if (this.isDragging) {
        this.handleMouseUp(event);
      }
    },

    // Update selected cells
    updateSelectedCells(): void {
      if (!this.isDragging) return;

      const container = this.$refs.scrollableContainerRef as HTMLElement;
      const table = this.$refs.tableRef as HTMLElement;

      // Get table position relative to container
      const tableRect = table.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();

      // Get selection box position relative to table
      const selectionRect = {
        left: this.selectionBox.left - tableRect.left + container.scrollLeft,
        top: this.selectionBox.top - tableRect.top + container.scrollTop,
        right:
          this.selectionBox.left +
          this.selectionBox.width -
          tableRect.left +
          container.scrollLeft,
        bottom:
          this.selectionBox.top +
          this.selectionBox.height -
          tableRect.top +
          container.scrollTop,
      };

      // Find all cells inside selection box
      const cells = table.querySelectorAll("tbody td");
      const newSelectedCells: { rowIndex: number; colIndex: number }[] = [];

      cells.forEach((cell) => {
        const cellRect = cell.getBoundingClientRect();
        const cellRelativeRect = {
          left: cellRect.left - tableRect.left + container.scrollLeft,
          top: cellRect.top - tableRect.top + container.scrollTop,
          right: cellRect.right - tableRect.left + container.scrollLeft,
          bottom: cellRect.bottom - tableRect.top + container.scrollTop,
        };

        // Check intersection
        if (
          cellRelativeRect.right > selectionRect.left &&
          cellRelativeRect.left < selectionRect.right &&
          cellRelativeRect.bottom > selectionRect.top &&
          cellRelativeRect.top < selectionRect.bottom
        ) {
          const rowIndex = parseInt(cell.getAttribute("data-row") || "-1");
          const colIndex = parseInt(cell.getAttribute("data-col") || "-1");

          if (rowIndex >= 0 && colIndex >= 0) {
            newSelectedCells.push({ rowIndex: rowIndex, colIndex: colIndex });
          }
        }
      });

      // Update selected cells
      if (!(event as MouseEvent).ctrlKey) {
        this.selectedCells = newSelectedCells;
      } else {
        // Merge new cells, avoid duplicates
        newSelectedCells.forEach((newCell) => {
          const exists = this.selectedCells.some(
            (cell) =>
              cell.rowIndex === newCell.rowIndex &&
              cell.colIndex === newCell.colIndex
          );
          if (!exists) {
            this.selectedCells.push(newCell);
          }
        });
      }

      // If cells are selected, calculate icon position
      if (this.selectedCells.length > 0) {
        this.$nextTick(() => {
          this.updateSelectionIconPosition();
        });
      }
    },

    // Check if cell is selected
    isSelectedCell(rowIndex: number, colIndex: number): boolean {
      return this.selectedCells.some(
        (cell) => cell.rowIndex === rowIndex && cell.colIndex === colIndex
      );
    },

    // Show selection menu
    showSelectionMenu(event: MouseEvent): void {
      event.stopPropagation();
      this.selectedCells.forEach((cell, index) => {
        // Get row in current page
        const currentPageRow = this.displayedRows[cell.rowIndex];
        // Get original data ID
        const originalDataId = currentPageRow.id;
      });
      // Toggle menu display
      this.showSelectionOptions = !this.showSelectionOptions;

      if (this.showSelectionOptions) {
        // Calculate menu position, display to right of icon; flip to left if space insufficient
        const iconRect = (
          event.currentTarget as HTMLElement
        ).getBoundingClientRect();

        const GAP = 8;
        const MENU_WIDTH = 180;
        const MENU_HEIGHT = 120;

        let left = iconRect.right + GAP;
        let top = iconRect.top;

        // If right side insufficient, flip to left
        if (left + MENU_WIDTH > window.innerWidth) {
          left = Math.max(GAP, iconRect.left - MENU_WIDTH - GAP);
        }

        // Ensure menu doesn't go below viewport
        if (top + MENU_HEIGHT > window.innerHeight) {
          top = Math.max(GAP, window.innerHeight - MENU_HEIGHT - GAP);
        }

        this.selectionMenuStyle = {
          top: `${top}px`,
          left: `${left}px`,
        };
      }
    },

    // Handle Option 1 - Valid Example
    async handleOptionValid(): Promise<void> {
      await this.handleRefineValidation(true);
    },

    // Handle Option 2 - Invalid Example
    async handleOptionInvalid(): Promise<void> {
      await this.handleRefineValidation(false);
    },

    async handleRefineValidation(validFlag: boolean) {
      // Close selection menu
      this.showSelectionOptions = false;

      // Get selected cell data info
      const selectInfo: SelectInfo = {
        columnList: [],
        indexList: [],
        conditionIndexList: [],
      };

      // Get all unique column indices
      const uniqueColumnIndices = Array.from(
        new Set(this.selectedCells.map((cell) => cell.colIndex))
      );

      // Get column names
      selectInfo.columnList = uniqueColumnIndices.map(
        (colIndex) => this.headers[Number(colIndex)]
      );

      // Get row indices
      selectInfo.indexList = Array.from(
        new Set(
          this.selectedCells.map((cell) => {
            const currentPageRow = this.displayedRows[cell.rowIndex];
            // Get original data ID
            const originalDataId = currentPageRow.id;
            return originalDataId as number;
          })
        )
      );

      // conditionIndexList - Get total row index after sorting
      selectInfo.conditionIndexList = Array.from(
        new Set(
          this.selectedCells.map((cell) => {
            const currentPageRow = this.displayedRows[cell.rowIndex];
            // Get index in sorted data
            const sortedIndex = this.rows.findIndex(
              (row) => row.id === currentPageRow.id
            );
            return sortedIndex;
          })
        )
      );
      // Get data of selected cells
      const selectedData = this.getSelectedCellsData();

      // Open RefineModel and pass data
      this.showRefineModal = true;
      this.refineData = {
        selectInfo: selectInfo,
        selectedData: selectedData,
        isInvalid: !validFlag, // Set based on validFlag
        isFromSequenceMatrix: false, // Default not from sequence_matrix
      };

      this.selectedCellsData = this.getSelectedCellsData();

      try {
        // Call refine rule API
        const result = await api_refine_validation_rules(validFlag, selectInfo);

        // Handle result
        if (result) {
          // Set refineResult data
          this.refineResult = result;
          // Open RefineModel modal
          this.showRefineModal = true;
        } else {
          // No rules refined
        }
      } catch (error) {
        // Error handling
      }
    },
    // Add handler for sequence_matrix right click
    async handleRightClick(
      rowIds: number[],
      columnNames: string[],
      conditionIndexList: number[]
    ) {
      // Close selection menu
      this.showSelectionOptions = false;

      // Create selection info
      const selectInfo: SelectInfo = {
        columnList: columnNames,
        indexList: rowIds,
        conditionIndexList: conditionIndexList,
      };

      const refine_rules = await api_refine_validation_rules(true, selectInfo);

      // Check if rules need update
      if (refine_rules && refine_rules.refineDict) {
        // Get current selected card type
        const currentCardType = this.currentCardType || "";

        // Filter updateRules matching current card type
        let filteredUpdateRules =
          refine_rules.refineDict.updateRules?.filter(
            (rule) => rule.type === currentCardType
          ) || [];

        // If Compare type and multiple rules, keep only first
        if (currentCardType === "Compare" && filteredUpdateRules.length > 0) {
          filteredUpdateRules = [filteredUpdateRules[0]];
          if (filteredUpdateRules[0].refineRule?.length > 1) {
            filteredUpdateRules[0].refineRule = [
              filteredUpdateRules[0].refineRule[0],
            ];
          }
        }

        // Create formatted rules object
        const formattedRules = {
          updateRules: filteredUpdateRules,
          addRules: [],
          deleteRules: [],
        };

        // Check if there are rules to update
        if (formattedRules.updateRules.length > 0) {
          // Use Element UI confirm dialog
          ElMessageBox.confirm(
            `There are ${formattedRules.updateRules[0].type} rules that can be updated, do you want to apply these updates?`,
            "Confirm Update Rules",
            {
              confirmButtonText: "Confirm",
              cancelButtonText: "Cancel",
              type: "warning",
            }
          )
            .then(async () => {
              // User clicked confirm, call API to update rules
              try {
                const response = await api_get_refine_rules(formattedRules);
                ElMessage({
                  type: "success",
                  message: "Rules updated successfully",
                });
                // Send event to parent notifying rules updated
                this.$emit("rules-update", {
                  selectedExamples: formattedRules,
                });
              } catch (error) {
                ElMessage.error("Rules update failed: " + error);
              }
            })
            .catch(() => {
              // User clicked cancel
              ElMessage({
                type: "info",
                message: "Rules update canceled",
              });
            });
        } else {
          ElMessage({
            type: "info",
            message: "No rules to update",
          });
        }
      }
    },

    // Close RefineModel and clear selected cells
    closeRefineModal(): void {
      this.showRefineModal = false;
      this.selectedCells = []; // Clear selection after closing modal
    },

    // Get selected cells data, modifiable
    getSelectedCellsData(): any {
      if (!this.selectedCells || this.selectedCells.length === 0) {
        return [];
      }

      const MIN_ROWS = 4;
      const MIN_COLS = 3;

      const rowIndices = this.selectedCells
        .map((cell) => cell.rowIndex)
        .sort((a, b) => a - b);
      const colIndices = this.selectedCells
        .map((cell) => cell.colIndex)
        .sort((a, b) => a - b);

      const expandRange = (
        minIndex: number,
        maxIndex: number,
        targetSize: number,
        upperBound: number
      ) => {
        let start = minIndex;
        let end = maxIndex;
        const currentSize = end - start + 1;

        if (currentSize >= targetSize) {
          return { start, end };
        }

        let extraNeeded = targetSize - currentSize;
        let addBefore = Math.floor(extraNeeded / 2);
        let addAfter = Math.ceil(extraNeeded / 2);

        start = Math.max(0, start - addBefore);
        end = Math.min(upperBound - 1, end + addAfter);

        // If one side hits boundary, try to fill from other side
        while (end - start + 1 < targetSize && start > 0) {
          start--;
        }
        while (end - start + 1 < targetSize && end < upperBound - 1) {
          end++;
        }

        return { start, end };
      };

      const rowRange = expandRange(
        rowIndices[0],
        rowIndices[rowIndices.length - 1],
        Math.max(
          MIN_ROWS,
          rowIndices[rowIndices.length - 1] - rowIndices[0] + 1
        ),
        this.displayedRows.length
      );

      const colRange = expandRange(
        colIndices[0],
        colIndices[colIndices.length - 1],
        Math.max(
          MIN_COLS,
          colIndices[colIndices.length - 1] - colIndices[0] + 1
        ),
        this.headers.length
      );

      const highlightedSet = new Set(
        this.selectedCells.map((cell) => `${cell.rowIndex}-${cell.colIndex}`)
      );

      const selectedData: {
        rowId: string | number | undefined;
        rowIndex: number;
        columnIndex: number;
        columnName: string;
        value: string | number | undefined;
        isHighlighted: boolean;
      }[] = [];

      for (let r = rowRange.start; r <= rowRange.end; r++) {
        const row = this.displayedRows[r];
        if (!row) continue;

        for (let c = colRange.start; c <= colRange.end; c++) {
          const columnName = this.headers[c];
          if (!columnName) continue;

          selectedData.push({
            rowId: row.id,
            rowIndex: r,
            columnIndex: c,
            columnName,
            value: row[columnName],
            isHighlighted: highlightedSet.has(`${r}-${c}`),
          });
        }
      }

      return selectedData;
    },

    // Update selection icon position
    updateSelectionIconPosition(): void {
      // Add safety check
      if (!this.$refs.tableRef || !this.$refs.scrollableContainerRef) {
        return;
      }

      let maxRow = -1;
      let maxCol = -1;

      this.selectedCells.forEach((cell) => {
        if (
          cell.rowIndex > maxRow ||
          (cell.rowIndex === maxRow && cell.colIndex > maxCol)
        ) {
          maxRow = cell.rowIndex;
          maxCol = cell.colIndex;
        }
      });

      const table = this.$refs.tableRef as HTMLElement;
      const container = this.$refs.scrollableContainerRef as HTMLElement;

      // Get selection icon element
      const selectionIcon = container.querySelector(
        ".selection-icon"
      ) as HTMLElement | null;

      if (maxRow >= 0 && maxCol >= 0 && selectionIcon) {
        const cell = table.querySelector(
          `td[data-row="${maxRow}"][data-col="${maxCol}"]`
        ) as HTMLElement | null;

        if (cell) {
          // Use offsetTop and offsetLeft to get cell position relative to table
          let cellOffsetTop = cell.offsetTop;
          let cellOffsetLeft = cell.offsetLeft;
          let cellHeight = cell.offsetHeight;
          let cellWidth = cell.offsetWidth;

          // Get current scroll position
          const scrollTop = container.scrollTop;
          const scrollLeft = container.scrollLeft;

          // Set icon position at bottom right of cell, considering scroll offset
          const iconTop = cellOffsetTop + cellHeight - 15 - scrollTop;
          const iconLeft = cellOffsetLeft + cellWidth - 15 - scrollLeft;

          // Update icon position
          selectionIcon.style.top = `${iconTop}px`;
          selectionIcon.style.left = `${iconLeft}px`;

          // Check if icon is within visible area
          const containerRect = container.getBoundingClientRect();
          const cellRect = cell.getBoundingClientRect();

          // Check if cell is in visible area
          const isCellVisible =
            cellRect.top < containerRect.bottom &&
            cellRect.bottom > containerRect.top &&
            cellRect.left < containerRect.right &&
            cellRect.right > containerRect.left;

          // If cell is visible, show icon, otherwise hide
          selectionIcon.style.display = isCellVisible ? "block" : "none";

          // Ensure icon visible
          selectionIcon.style.position = "absolute";
          selectionIcon.style.zIndex = "100";
        }
      } else {
        // If no cells selected, hide icon
        if (selectionIcon) {
          selectionIcon.style.display = "none";
        }
      }
    },
    // Check if cell is highlighted
    isHighlighted(rowId: number, cellIndex: number): boolean {
      const currentColumnName = this.headers[cellIndex];
      const isTargetColumn = this.currentHighlightColumns.some(
        (name: string) => currentColumnName === name
      );
      const isHighlighted = this.currenthighlightedIndices.includes(rowId);
      return isHighlighted && isTargetColumn;
    },
    // Handle RefineModel submit event
    handleRefineSubmit(data) {
      this.closeRefineModal();
      // Send event to parent MainComponent
      this.$emit("rules-update", {
        selectedExamples: data.selectedExamples,
      });
    },

    // Add in handle RefineModel submit method
    handleRefineModelSubmit(data) {
      // emit to MainComponent
      this.$emit("rules-update", data.selectedExamples);
    },

    async drawHistograms() {
      // Wait for next DOM update cycle
      await this.$nextTick();

      // Create a batch processing function, process part of columns each time
      const batchSize = 5; // Number of columns per batch
      const headers = [...this.headers]; // Copy headers array

      // Define function to process a single batch
      const processBatch = async (startIndex) => {
        const endIndex = Math.min(startIndex + batchSize, headers.length);
        const promises: Promise<any>[] = [];

        // Fetch data for this batch in parallel
        for (let i = startIndex; i < endIndex; i++) {
          const header = headers[i];
          promises.push(api_load_table_vis_valueList(header));
        }

        // Wait for all data to load
        const results = await Promise.all(promises);

        // Draw histograms for this batch
        for (let i = 0; i < results.length; i++) {
          const index = startIndex + i;
          const header = headers[index];
          const valueList = results[i];

          // Get container ref
          const containerRef = this.$refs[
            `histogram-${index}`
          ] as HTMLElement[];
          if (!containerRef || containerRef.length === 0) continue;
          const container = containerRef[0];

          // Clear existing charts
          d3.select(container).selectAll("*").remove();

          // Set margins and dimensions
          const margin = { top: 2, right: 2, bottom: 2, left: 2 };
          const width = container.clientWidth - margin.left - margin.right;
          const height = 60 - margin.top - margin.bottom;

          // Create SVG container
          const svg = d3
            .select(container)
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g");

          // Create scale
          const x = d3
            .scaleBand<string>()
            .domain(valueList.map((d) => String(d.value)))
            .range([margin.left, width - margin.right])
            .padding(0.1);

          const maxCount = d3.max(valueList, (d: any) => Number(d.count)) || 0;

          const y = d3
            .scaleLinear()
            .domain([0, maxCount])
            .range([height - margin.bottom, margin.top])
            .nice();

          // Create a group to contain each bar and its click area
          const bars = svg
            .append("g")
            .selectAll("g")
            .data(valueList)
            .enter()
            .append("g");

          // Add actual bar, modify height calculation
          bars
            .append("rect")
            .attr("x", (d: any) => x(String(d.value))!)
            .attr("y", (d: any) => y(Number(d.count)))
            .attr("height", (d: any) => Math.max(0, y(0) - y(Number(d.count))))
            .attr("width", x.bandwidth())
            .attr("fill", (d: any) =>
              this.isBarHighlighted(header, d.value) ? "#fdd0a2" : "#4570b6"
            );

          // Add transparent rectangle covering entire bar area for click
          bars
            .append("rect")
            .attr("x", (d: any) => x(String(d.value))!)
            .attr("y", margin.top)
            .attr("height", height - margin.top - margin.bottom)
            .attr("width", x.bandwidth())
            .attr("fill", "transparent")
            .attr("cursor", "pointer")
            .on("contextmenu", (event, d: any) => {
              event.preventDefault();
              this.filterDataByHistogram(header, d.value, d.index);
            })
            .on("click", (event, d: any) => {
              if (
                this.isFiltered &&
                this.currentFilterInfo &&
                this.currentFilterInfo.column === header &&
                this.currentFilterInfo.value === d.value
              ) {
                this.resetFilter();
              }
            })
            .append("title")
            .text(
              (d: any) =>
                `${d.duration}: ${d.count} counts(right click to filter)`
            );
        }

        // If remaining columns, continue processing next batch
        if (endIndex < headers.length) {
          // Use setTimeout to allow browser to render current batch
          setTimeout(() => processBatch(endIndex), 0);
        }
      };

      // Start processing first batch
      processBatch(0);
    },

    // Check if bar should be highlighted
    isBarHighlighted(column: string, value: any): boolean {
      return (
        !!this.isFiltered && // Ensure isFiltered is boolean
        !!this.currentFilterInfo && // Ensure currentFilterInfo exists
        this.currentFilterInfo.column === column &&
        this.currentFilterInfo.value === value
      );
    },

    // Filter data method
    filterDataByHistogram(column: string, value: any, indices: number[]) {
      // Save filter info
      this.currentFilterInfo = { column, value };

      // Filter data by index
      if (indices && indices.length > 0) {
        // Filter original data using index array
        this.filteredRows = this.csvData.filter((row, index) =>
          indices.includes(index)
        );
        this.isFiltered = true;

        // Reset to first page
        this.currentPage = 0;

        // Reload data
        this.loadPageData();

        // Show filter info tip
        ElMessage({
          message: `filtered: ${column} = ${value} (total ${indices.length} records)`,
          type: "info",
        });

        // Redraw histograms to update highlights
        this.drawHistograms();
      }
    },

    // Reset filter
    resetFilter() {
      if (this.isFiltered) {
        this.isFiltered = false;
        this.currentFilterInfo = null;
        this.filteredRows = [];

        // Reset to first page
        this.currentPage = 0;

        // Reload data
        this.loadPageData();

        // Show tip
        ElMessage({
          message: "reset filter, show all data",
          type: "success",
        });

        // Redraw histograms
        this.drawHistograms();
      }
    },

    removeColumn(column: string): void {
      const index = this.selectedColumns.indexOf(column);
      if (index > -1) {
        this.selectedColumns.splice(index, 1);
        this.handleColumnSelection();
      }
    },

    // Modify jump method to use jumpHighlightIndex
    async jumpToNextInvalidData() {
      if (!this.hasHighlightedData) return;

      // If initial state (-1), set to first index
      if (this.currentHighlightIndex === -1) {
        this.currentHighlightIndex = 0;
      } else {
        // Increment current index
        this.currentHighlightIndex++;

        // If reached end, restart from beginning
        if (this.currentHighlightIndex >= this.jumpHighlightIndex.length) {
          this.currentHighlightIndex = 0;
        }
      }

      // Get next row ID to jump to
      const nextRowId = this.jumpHighlightIndex[this.currentHighlightIndex];

      // Scroll to target row
      await this.scrollToRow(nextRowId);
    },

    async jumpToPrevInvalidData() {
      if (!this.hasHighlightedData || this.jumpHighlightIndex.length === 0)
        return;

      this.currentHighlightIndex =
        this.currentHighlightIndex <= 0
          ? this.jumpHighlightIndex.length - 1
          : this.currentHighlightIndex - 1;
      const prevRowId = this.jumpHighlightIndex[this.currentHighlightIndex];
      await this.scrollToRow(prevRowId);
    },

    async jumpToSpecificInvalid() {
      if (!this.hasHighlightedData || !this.jumpHighlightIndex.length) return;

      // Validate input
      const targetIndex =
        Math.min(
          Math.max(1, this.invalidInputIndex),
          this.jumpHighlightIndex.length
        ) - 1;

      // Update current index
      this.currentHighlightIndex = targetIndex;

      // Get row ID and scroll
      const rowId = this.jumpHighlightIndex[targetIndex];
      await this.scrollToRow(rowId);
    },

    updateColumnConflictCounts(validationCards) {
      const counts = {};

      // Initialize all column counts to 0
      if (this.headers) {
        this.headers.forEach((header) => {
          counts[header] = 0;
        });
      }

      // Calculate conflict count in relevant cards for each column
      if (validationCards && validationCards.length > 0) {
        validationCards.forEach((card) => {
          if (card.ifConflict) {
            // Increment count for each column name in the card
            card.columnName.forEach((colName) => {
              if (counts[colName] !== undefined) {
                counts[colName]++;
              }
            });
          }
        });
      }

      this.columnConflictCounts = counts;
    },

    // Add new method to load CSV directly from content
    loadCsvFromContent(csvContent: string, _loadingId: number): void {
      void _loadingId; // explicitly mark unused parameter to satisfy lint rules

      // Clear selected columns
      this.selectedColumns = [];
      this.$emit("columnsChanged", this.selectedColumns);

      // Clear previous constraintMap
      this.constraintMap = {};

      this.parseCsv(csvContent);
    },

    // Handle page number click
    goToPageNumber(pageNum) {
      // If ellipsis is clicked, do nothing
      if (pageNum === "...") return;

      // Page number starts from 1, but currentPage starts from 0
      this.currentPage = pageNum - 1;
      this.loadPageData();
    },
  },
  mounted(): void {
    // Get ConstraintMap immediately
    // this.getConstraintMap();
    // Listen for invalid data scatter point or grid cell click events
    window.addEventListener(
      "highlight-invalid-data",
      this.handleHighlightInvalidData
    );
    // Add listener for window resize to redraw charts
    window.addEventListener("resize", this.drawHistograms);
  },
  beforeUnmount(): void {
    window.removeEventListener(
      "highlight-invalid-data",
      this.handleHighlightInvalidData
    );
    window.removeEventListener("resize", this.drawHistograms);
  },
});
</script>

<style scoped>
.table-container {
  width: 100%;
  height: 40vh;
  background-color: #eff2fc;
  border-radius: 15px;
  margin-left: 0.5vw;
  border: 1px solid #cce2f0;
  z-index: 10;
  position: relative; /* Add relative positioning */
}

/* Table styles */
.scrollable-container {
  overflow-x: hidden; /* Default hidden horizontal scrollbar */
  overflow-y: hidden; /* Default hidden vertical scrollbar */
  width: 97.14%;
  height: 30vh;
  margin: 0 auto; /* Add horizontal centering */
  border-radius: 15px;
  border: none;
  transition: overflow 0.3s ease; /* Add transition effect */
}

/* Show scrollbars on hover */
.scrollable-container:hover {
  overflow-x: auto; /* Show horizontal scrollbar on hover */
  overflow-y: auto; /* Show vertical scrollbar on hover */
}

/* Custom scrollbar styles */
.scrollable-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.scrollable-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.scrollable-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.scrollable-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.csv-table {
  border-collapse: separate; /* Separate borders */
  border-spacing: 0;
  width: 100%;
  table-layout: fixed; /* Fixed layout */
  border: none;
}

/* Selected column header style */
.selected-column {
  background-color: #c6dbef;
  font-weight: bold;
  vertical-align: middle;
  text-align: center;
}

.disabled-column {
  background-color: #f5f5f5; /* Grey background */
  color: #ccc;
  cursor: not-allowed;
}

.sort-icon-1 {
  position: absolute;
  vertical-align: middle;
  right: 0.5vh;
  width: 1.3vh;
  height: 1.3vh;
}

.sort-icon-2 {
  position: absolute;
  vertical-align: middle;
  right: 0.5vh;
  width: 1.5vh;
  height: 1.5vh;
}

.cell-icon {
  position: absolute;
  top: 0.2vh;
  left: 0.2vh;
  width: 1vh;
  height: 1vh;
}

th,
td {
  border: 0.1px solid #e9e9e9;
  padding-top: 1.1vh;
  padding-bottom: 1.1vh;
  position: relative;
  width: auto;
  white-space: nowrap; /* Prevent text wrapping */
  overflow: hidden; /* Hide overflow content */
  text-overflow: ellipsis; /* Show ellipsis */
  font-size: 1.4vh; /* Increase font size */
}

th {
  background-color: #eaeaec;
  font-weight: bold;
  text-align: center;
  vertical-align: middle;
  position: sticky;
  top: 0;
  z-index: 10;
  border-left: 1px solid #b2b2b2;
}

/* Header column name style */
th .header-text {
  display: inline-block;
  max-width: 75%;
  transform: translateX(
    0.15vw
  ); /* nudge text right to clear conflict badge without affecting column width */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  margin: 0 auto;
}

/* First column left border */
th:first-child {
  border-left: 0.1px solid #e9e9e9;
}

/* Last column right border */
th:last-child {
  border-right: 0.1px solid #e9e9e9;
}

/* Set background color for odd rows */
.csv-table tbody tr:nth-child(odd) {
  background-color: white;
}

/* Set background color for even rows */
.csv-table tbody tr:nth-child(even) {
  background-color: #fafafa; /* Light grey */
}

* {
  user-select: none;
  font-size: 1.5vh; /* Increase default font size */
}

.highlight-cell {
  background-color: #fdae6b;
}

.sort-settings {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: white;
  padding: 2vh;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  min-width: 10vw;
  z-index: 1000;
}

.sort-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2vh;
  padding-bottom: 1vh;
  border-bottom: 1px solid #eee;
}

.sort-header h3 {
  margin: 0;
  font-size: 1.6vh;
  color: #333;
}

/* Close button style */
.close-button {
  cursor: pointer;
  padding: 0.5vh;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.close-button:hover {
  background-color: #f5f5f5;
}

/* Sort condition container */
.sort-condition {
  display: flex;
  gap: 1vh;
  margin-bottom: 1.5vh;
  align-items: center;
  padding: 1vh;
  background-color: #f9f9f9;
  border-radius: 6px;
}

/* Dropdown select style */
.sort-condition select {
  padding: 0.8vh 1.2vh;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1.3vh;
  background-color: white;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.sort-condition select:hover {
  border-color: #bbb;
}

.sort-condition select:focus {
  border-color: #4570b6;
  box-shadow: 0 0 0 2px rgba(75, 156, 226, 0.1);
}

.sort-buttons {
  display: flex;
  gap: 1vh;
  margin-top: 2vh;
  justify-content: flex-end;
}

.sort-buttons button {
  padding: 0.8vh 1.5vh;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.3vh;
  transition: background-color 0.2s;
}

.add-condition {
  background-color: #4570b6;
  color: white;
}

.add-condition:hover {
  background-color: #3d8cd3;
}

.delete-condition {
  background-color: #ff4d4f;
  color: white;
}

.delete-condition:hover {
  background-color: #ff3333;
}

/* Confirm and cancel button container */
.sort-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1vh;
  margin-top: 2vh;
  padding-top: 1.5vh;
  border-top: 1px solid #eee;
}

/* Confirm and cancel button style */
.sort-actions button {
  padding: 0.8vh 2vh;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.3vh;
  transition: all 0.2s;
}

.confirm-sort {
  background-color: #4570b6;
  color: white;
}

.confirm-sort:hover {
  background-color: #3d8cd3;
}

.cancel-sort {
  background-color: #f5f5f5;
  color: #666;
}

.cancel-sort:hover {
  background-color: #e8e8e8;
}

/* Disabled state style */
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* New bottom control area style */
.table-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 97.14%;
  margin: 10px auto;
}

/* Column selector style */
.column-selector {
  flex: 0.5;
  width: 30%;
  text-align: left;
  display: flex;
}

/* Pagination controls style */
.pagination-controls {
  flex: 1;
  max-width: 70%;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 5px;
}

.pagination-controls button {
  background-color: #f8f8f8;
  cursor: pointer;
  border: none;
  padding: 0;
  width: 1.2vh;
  height: 1.2vh;
}

.pagination-controls button:disabled {
  cursor: not-allowed;
}

.pagination-controls input {
  width: 1.6vw;
  padding: 0.4vh;
  background-color: #eaeaec;
  border: 1px solid #c9c9c9;
  /* Remove up/down arrows on right of number input */
  appearance: textfield; /* Standard property */
  -moz-appearance: textfield; /* Firefox */
}

/* Styles for Chrome, Safari, Edge, Opera */
.pagination-controls input::-webkit-outer-spin-button,
.pagination-controls input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.page-info {
  margin: 0.2vh 0.92vh 0vh 0.92vh;
  height: 100%;
  width: 8vw;
  font-size: 1.6vh;
  font-family: Arial;
  color: #000000;
}

.page-number {
  cursor: pointer;
  padding: 0 3px;
}

.page-number:hover {
  text-decoration: underline;
}

.current-page {
  font-weight: bold;
  font-size: 1.5vh;
  font-family: Arial;
  padding: 0 3px;
  color: #4570b6;
}

.page-separator {
  margin: 0 2px;
}

/* Selected cell style */
.selected-cell {
  background-color: #b5d2f8 !important;
  background-blend-mode: overlay;
}

/* Selection box style */
.selection-box {
  position: absolute;
  pointer-events: none;
  z-index: 100;
}

/* Selection icon style */
.selection-icon {
  position: absolute;
  width: 0.8vw;
  height: 0.8vw;
  cursor: pointer;
  z-index: 12001;
  background-image: url("../assets/images/selectmenu.svg"); /* Use local image */
  background-size: cover; /* Ensure icon fills container */
  background-position: center; /* Center align image */
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translate(-50%, -50%);
}

.selection-icon:hover {
  opacity: 0.8;
}

/* Selection menu style */
.selection-menu {
  position: fixed;
  background-color: #ffffff;
  border: 1px solid #4570b6;
  border-radius: 0.18vh;
  box-shadow: 0px 0px 10px 0px rgba(0, 0, 0, 0.25);
  padding: 0.2vw 0;
  z-index: 12002;
  min-width: 7vw; /* Adjust popup width to fit icon */
}

.menu-option {
  display: flex;
  align-items: center; /* Align text and icon */
  padding: 0.3vw 0.5vw;
  cursor: pointer;
  font-weight: bold; /* Bold text */
  font-size: 1.3vh; /* Font size */
  color: #000000; /* Font color black */
}

/* Hover effect */
.menu-option:hover {
  background-color: #f5f7fa;
}

/* Dashed border effect */
.menu-option.dashed {
  border-top: 2px dashed #4570b6;
}

/* Icon style */
.menu-icon {
  width: 0.8vw; /* Icon width */
  height: 0.8vw; /* Icon height */
  margin-right: 0.3vw; /* Gap between icon and text */
}

/* Top control area style */
.table-top-controls {
  display: flex;
  align-items: center;
  width: 73vw;
  height: 3.7vh;
  margin: 0 auto 5px auto;
  padding-top: 1vh;
  padding-left: 1vw;
  font-size: 1.8vh;
}

/* Sort condition display area style */
.sort-conditions-display {
  flex: 0.6;
  text-align: left;
  padding: 0.18vh 0.31vw;
  background-color: #eff2fc;
  border-radius: 0.37vh;
  border: none;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  min-height: 3.7vh;
  width: 30%;
}

/* Selected columns display style */
.selected-columns-display {
  flex: 1;
  text-align: left;
  padding: 0.18vh 0.31vw;
  background-color: #eff2fc;
  border-radius: 0.37vh;
  border: none;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  min-height: 2.03vh;
  font-size: 0.85em;
  width: 100%;
}

.sort-title {
  color: #0c4672;
  font-family: Roboto;
  font-size: 1.6vh;
  font-style: normal;
  font-weight: 900;
  line-height: normal;
  text-decoration-line: underline;
  text-decoration-style: solid;
  text-decoration-skip-ink: auto;
  text-decoration-thickness: auto;
  text-underline-offset: auto;
  text-underline-position: from-font;
}

.sort-conditions-container {
  border: 1px solid #4570b6;
  width: 80%;
  height: 3.5vh;
  border-radius: 4.6vh;
  padding: 0vh 0.31vw;
  margin-left: 0.5vw;
  background-color: #fff;
  display: flex; /* Add flex layout */
  align-items: center; /* Vertical center */
}

.sort-condition-item {
  display: inline-flex;
  align-items: center;
  margin-right: 0.46vh;
  font-weight: 600;
  color: #000000;
  font-family: Roboto;
  font-style: normal;
  line-height: normal;
  font-size: 1.5vh;
  background-color: #d5dfff;
  padding: 0.5vh 0.7vh 0.5vh 0.7vh;
  margin-right: 0.5vh;
  border-radius: 1.85vh;
}

.condition-number-icon {
  width: 1.3vh;
  height: 1.3vh;
  margin-right: 0.5vh;
  vertical-align: middle;
}

.sort-direction-icon {
  width: 2vh;
  height: 2vh;
  margin-left: 0.5vh;
  vertical-align: middle;
}

/* Right button group style */
.top-buttons {
  display: flex;
  align-items: center;
  flex: 0.35;
  justify-content: end;
  margin-right: 1vw;
}

.invalid-data-info {
  margin: 0vh 0.92vh 0vh 0.92vh;
  height: 100%;
  width: 12vw;
  font-size: 1.5vh;
  color: #3e3e3f;
  font-family: Roboto;
  font-style: normal;
  font-weight: 600;
  line-height: normal;
  text-align: end;
  display: flex; /* Add flex layout */
  align-items: center; /* Vertical center */
  justify-content: flex-end; /* Right align */
}

.invalid-data-button-last {
  padding: 0.2vh 0.92vh;
  background-color: #4570b6;
  border: none;
  cursor: pointer;
  border-top-left-radius: 0.46vh;
  border-bottom-left-radius: 0.46vh;
  height: 2.5vh;
  font-size: 1.6vh;
}

.invalid-data-button-next {
  padding: 0.2vh 0.92vh;
  background-color: #4570b6;
  border: none;
  cursor: pointer;
  border-top-right-radius: 0.46vh;
  border-bottom-right-radius: 0.46vh;
  height: 2.5vh;
  font-size: 1.6vh;
}

.invalid-input {
  width: 2vw;
  padding: 0.2vh 0.4vh;
  background-color: #eaeaec;
  border: 1px solid #c9c9c9;
  font-size: 1.8vh;
  color: #000;
}

.inline-invalid-input {
  width: 1vw; /* Adjust width */
  height: 1.6vh;
  border: none;
  text-align: center;
  font-size: 1.5vh;
  color: #3e3e3f;
  background-color: #eff2fc;
  font-family: Roboto;
  font-style: normal;
  font-weight: 600;
  line-height: normal;
  padding: 0.2vh 0;
  /* Chrome, Safari, Edge, Opera */
  appearance: textfield;
  -webkit-appearance: none;
  -moz-appearance: textfield;
  margin: 0;
}

/* Hide spin buttons, keep input functional */
.inline-invalid-input::-webkit-outer-spin-button,
.inline-invalid-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.button-icon {
  width: 1.2vh;
  height: 1.2vh;
}

.button-text-last {
  color: #fff;
  font-size: 1.6vh;
  font-family: Roboto;
  font-style: normal;
  font-weight: 600;
  line-height: normal;
  margin-left: 0.46vh;
}

.button-divider {
  height: 60%; /* Divider height, adjustable */
  width: 1px; /* Divider width */
  background-color: #ddd; /* Divider color */
  align-self: center; /* Vertical center in parent */
}

.button-text-next {
  color: #fff;
  font-size: 1.6vh;
  font-family: Roboto;
  font-style: normal;
  font-weight: 600;
  line-height: normal;
  margin-right: 0.46vh;
}

/* Hide original file input */
.file-input {
  width: 0.1px;
  height: 0.1px;
  opacity: 0;
  overflow: hidden;
  position: absolute;
  z-index: -1;
}

/* Custom file input button style */
.file-input-label {
  padding: 5px 12px;
  background-color: #4570b6;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  font-weight: 550;
  font-size: 0.9em;
}

.file-input-label:hover {
  background-color: #357ab7;
}

/* Multi-level sort button style */
.sort-settings-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #eff2fc;
  border: none;
}

.sort-icon {
  width: 1.5vh;
  height: 1.5vh;
}

/* Modify histogram container style */
.histogram-container {
  width: 100%;
  height: 4.63vh; /* Increase container height */
  margin-top: 0.5vh;
  overflow: visible; /* Modified to visible to allow overflow */
}

/* Adjust header height */
th {
  padding-bottom: 1vh; /* Increase bottom padding to fit histogram */
}

/* Column tag style */
.column-tag {
  display: inline-flex;
  align-items: center;
  background-color: #d5dfff;
  border-radius: 0.46vh;
  padding: 0.23vh 0.74vh;
  margin: 0vh 0.46vh;
}

.column-name {
  margin-right: 0.46vh;
  color: #494949;
  font-family: Arial;
  font-size: 1.6vh;
  font-style: normal;
  font-weight: 700;
  line-height: normal;
}

.delete-icon {
  cursor: pointer;
  color: #666;
  font-weight: bold;
  font-size: 1.4vh;
  padding: 0 2px;
}

.delete-icon:hover {
  color: #ff4d4f;
}

/* Filter info style */
.filter-info {
  display: flex;
  align-items: center;
  background-color: #f0f8ff;
  padding: 5px 5px;
  border-radius: 4px;
  margin-right: 5px; /* Adjust right margin */
  border: 1px solid #d0e3ff;
  white-space: nowrap; /* Prevent text wrapping */
}

.reset-filter-btn {
  margin-left: 10px;
  padding: 2px 5px;
  background-color: #ff7f0e;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.8em;
  white-space: nowrap; /* Prevent button text wrapping */
}

.reset-filter-btn:hover {
  background-color: #ff6600;
}

/* Highlighted histogram style */
.histogram-highlight {
  fill: #ff7f0e !important;
}

/* Selected column text tip */
text.reset-filter {
  cursor: pointer;
  font-weight: bold;
}

text.reset-filter:hover {
  text-decoration: underline;
}

.conflict-badge {
  position: absolute;
  top: 1vh;
  left: 0.25vh;
  background-color: #fdae6b;
  color: white;
  padding: 0.185vh 0.26vw;
  font-size: 1.11vh;
  border-radius: 0.37vh;
}
</style>
