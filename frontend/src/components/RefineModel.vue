<template>
  <div class="modal-overlay">
    <div class="modal-container">
      <button class="close-btn" @click="closeModal">
        <span class="close-icon">×</span>
      </button>
      <div class="modal-left">
        <div class="refine-example">
          <div class="example-section-header">
            <span class="title-text">Refine Example</span>
          </div>
          <div
            class="data-table-container"
            :class="{ 'scrollable-table': tableNeedsScroll }"
          >
            <table
              class="data-table"
              :class="{ 'table-flex-width': tableNeedsScroll }"
              v-if="selectedData && selectedData.length > 0"
            >
              <thead>
                <tr>
                  <th v-for="(item, index) in getUniqueColumns()" :key="index">
                    {{ item }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, rowIndex) in getFormattedData()"
                  :key="rowIndex"
                >
                  <td
                    v-for="(cell, colIndex) in row"
                    :key="colIndex"
                    :class="{ 'highlighted-cell': cell.isHighlighted }"
                  >
                    {{ cell.value }}
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="no-data">There are no relevant rules.</div>
          </div>
        </div>

        <div class="related-rules">
          <div class="rules-section-header">
            <span class="title-text-2">Related Rules</span>
          </div>
          <div class="related-rules-content">
            <div v-if="hasRules" class="rules-list">
              <div class="rules-container">
                <div
                  v-for="(ruleType, index) in uniqueRuleTypes"
                  :key="`rule-${index}`"
                  class="rule-item"
                >
                  <img
                    :src="getRuleIcon(ruleType)"
                    class="related-rule-icon"
                    :alt="ruleType"
                  />
                  <span class="rule-type">{{ ruleType }}</span>
                </div>
              </div>
            </div>
            <div v-else class="no-rules">There are no relevant rules.</div>
          </div>
        </div>
      </div>
      <div class="modal-right">
        <div class="right-section-header">
          <span class="title-text">Refine Rules</span>
        </div>
        <div class="rules-content">
          <div v-if="hasRules">
            <div v-if="updateRules.length > 0" class="rule-category">
              <div class="refine-title">
                <img src="/refinemodel_icon/arrow.svg" class="arrow_icon" />
                <span>Modify</span>
              </div>
              <div
                v-for="(rule, index) in updateRules"
                :key="`update-${index}`"
                class="rule-item"
              >
                <span class="rule-number">{{ index + 1 }}.</span>
                <img
                  :src="getRuleIcon(rule.type)"
                  class="rule-icon"
                  :alt="rule.type"
                />
                <span class="refine-rule-type">
                  {{ getDisplayRuleType(rule.type) }}
                </span>
                <span class="original-example">
                  ({{ getOriginalExample(rule) }})
                </span>
                <div class="rule-example-container">
                  <template v-if="hasMultipleExamples(rule)">
                    <div
                      v-for="(example, exampleIndex) in splitRefineExamples(
                        getRefineExample(rule)
                      )"
                      :key="`example-${exampleIndex}`"
                      class="example-item"
                    >
                      <label class="checkbox-container">
                        <input
                          type="checkbox"
                          :checked="isExampleSelected(rule, example)"
                          @change="toggleExampleSelection(rule, example)"
                          class="example-checkbox"
                        />
                        <span class="checkmark"></span>
                        <span class="refine-rule-example">{{ example }}</span>
                      </label>
                    </div>
                  </template>
                  <template v-else>
                    <label class="checkbox-container">
                      <input
                        type="checkbox"
                        v-model="rule.exampleSelected"
                        class="example-checkbox"
                      />
                      <span class="checkmark"></span>
                      <span class="refine-rule-example">
                        {{ getRefineExample(rule) }}
                      </span>
                    </label>
                  </template>
                </div>
              </div>
            </div>
            <div v-if="addRules.length > 0" class="rule-category">
              <div class="refine-title">
                <img src="/refinemodel_icon/arrow.svg" class="arrow_icon" />
                <span>Add</span>
              </div>
              <div
                v-for="(rule, index) in addRules"
                :key="`add-${index}`"
                class="rule-item"
              >
                <span class="rule-number">{{ index + 1 }}.</span>
                <img
                  :src="getRuleIcon(rule.type)"
                  class="rule-icon"
                  :alt="rule.type"
                />
                <span class="refine-rule-type">
                  {{ getDisplayRuleType(rule.type) }}
                </span>
                <span class="original-example">
                  ({{ getOriginalExample(rule) }})
                </span>
                <div class="rule-example-container">
                  <label class="checkbox-container">
                    <input
                      type="checkbox"
                      v-model="rule.exampleSelected"
                      class="example-checkbox"
                    />
                    <span class="checkmark"></span>
                    <span class="refine-rule-example">
                      {{ getRefineExample(rule) }}
                    </span>
                  </label>
                </div>
              </div>
            </div>
            <div v-if="deleteRules.length > 0" class="rule-category">
              <div class="refine-title">
                <img src="/refinemodel_icon/arrow.svg" class="arrow_icon" />
                <span>Delete</span>
              </div>
              <div
                v-for="(rule, index) in deleteRules"
                :key="`delete-${index}`"
                class="rule-item"
              >
                <span class="rule-number">{{ index + 1 }}.</span>
                <img
                  :src="getRuleIcon(rule.type)"
                  class="rule-icon"
                  :alt="rule.type"
                />
                <span class="refine-rule-type">
                  {{ getDisplayRuleType(rule.type) }}
                </span>
                <div class="rule-example-container">
                  <label class="checkbox-container">
                    <input
                      type="checkbox"
                      v-model="rule.exampleSelected"
                      class="example-checkbox"
                    />
                    <span class="checkmark"></span>
                    <span class="refine-rule-example">
                      {{ getDeleteSummary(rule) }}
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="no-rules">There are no relevant rules.</div>
        </div>

        <button class="submit-btn" @click="submitModal">
          <img src="/refinemodel_icon/mark.svg" class="mark_icon" />
          Submit
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { RefineResult } from "@/types/types";
import { defineComponent, PropType } from "vue";

interface SelectedCellData {
  rowId: number;
  rowIndex: number;
  columnIndex: number;
  columnName: string;
  value: any;
  isHighlighted: boolean;
}

interface RowData {
  [key: string]: {
    value: any;
    isHighlighted: boolean;
  };
}

export default defineComponent({
  props: {
    isInvalid: {
      type: Boolean,
      default: false,
    },
    selectedData: {
      type: Array as PropType<SelectedCellData[]>,
      default: () => [],
    },
    refineResult: {
      type: [Object, String] as PropType<RefineResult | string>,
      default: () => ({
        refineStatus: false,
        refineDict: {
          addRules: [],
          deleteRules: [],
          updateRules: [],
        },
      }),
    },
  },
  emits: ["close", "submit"],
  data() {
    return {
      refineExample: "",
      refineRules: "",
    };
  },
  mounted() {
    // Automatically fill selected data into example text box
    if (this.selectedData && this.selectedData.length > 0) {
      // Initialize rule selection state
      this.initializeRuleSelections();
    }
  },
  methods: {
    // Initialize rule selection state
    initializeRuleSelections() {
      // Add selection state tracking for each rule
      [...this.updateRules, ...this.addRules, ...this.deleteRules].forEach(
        (rule) => {
          if (this.hasMultipleExamples(rule)) {
            // For multiple examples, initialize an array to track selected examples
            rule.selectedExamples = [];
          } else {
            // For single example, initialize a boolean value
            rule.exampleSelected = false;
          }
        }
      );
    },

    // Check if example is selected
    isExampleSelected(rule, example) {
      return rule.selectedExamples && rule.selectedExamples.includes(example);
    },

    // Toggle example selection state
    toggleExampleSelection(rule, example) {
      if (!rule.selectedExamples) {
        rule.selectedExamples = [];
      }

      const index = rule.selectedExamples.indexOf(example);
      if (index === -1) {
        rule.selectedExamples.push(example);
      } else {
        rule.selectedExamples.splice(index, 1);
      }
    },

    // Split multiple refine_examples
    splitRefineExamples(exampleString) {
      return exampleString
        .split(";")
        .map((example) => example.trim())
        .filter((example) => example);
    },

    getDisplayRuleType(ruleType: string): string {
      const normalized = (ruleType || "").toLowerCase();
      const ruleTypeMap: Record<string, string> = {
        lookup: "Mapping and cardinality",
        differentdomain: "Consistency (domain)",
        sequence: "Sequence (sequence)",
      };
      return ruleTypeMap[normalized] || ruleType || "Unknown";
    },

    isLookupType(ruleType: string): boolean {
      return (ruleType || "").toLowerCase() === "lookup";
    },

    getDeleteSummary(rule: any): string {
      const cols = Array.isArray(rule?.column)
        ? rule.column
        : typeof rule?.column === "string"
        ? rule.column
            .split(/[+,]/)
            .map((c: string) => c.trim())
            .filter((c: string) => c)
        : [];
      const columnsText =
        cols.length >= 2
          ? `${cols[0]} and ${cols[1]}`
          : cols.join(" and ") || "the selected columns";
      const ruleLabel = this.getDisplayRuleType(rule?.type);
      if (
        this.isLookupType(rule?.type) ||
        ruleLabel === "Mapping and cardinality"
      ) {
        return `Delete mapping and cardinality rule between ${columnsText}`;
      }
      return `Delete ${ruleLabel} rule for ${columnsText}`;
    },

    getOriginalExample(rule: any): string {
      return this.pickFirstExample([
        rule?.original_example,
        rule?.refine_example,
        rule?.originalRule,
        rule?.refineRule,
      ]);
    },

    getRefineExample(rule: any): string {
      return this.pickFirstExample([
        rule?.refine_example,
        rule?.original_example,
        rule?.refineRule,
        rule?.originalRule,
      ]);
    },

    hasMultipleExamples(rule: any): boolean {
      const exampleString = this.getRefineExample(rule);
      return exampleString.includes(";");
    },

    pickFirstExample(candidates: any[]): string {
      for (const candidate of candidates) {
        const formatted = this.formatRuleValue(candidate);
        if (formatted.trim().length > 0) {
          return formatted;
        }
      }
      return "N/A";
    },

    formatRuleValue(value: any): string {
      if (value === undefined || value === null) return "";
      if (typeof value === "string") return this.sanitizeExampleText(value);
      if (Array.isArray(value)) {
        return value
          .map((item) => this.formatRuleValue(item))
          .filter((item) => item.trim().length > 0)
          .join("; ");
      }
      if (typeof value === "object") {
        const entries = Object.entries(value);
        if (entries.length === 0) return "";
        return this.sanitizeExampleText(
          entries.map(([key, val]) => `${key}: ${val}`).join(", ")
        );
      }
      return this.sanitizeExampleText(String(value));
    },

    sanitizeExampleText(text: string): string {
      return text.replace(/lookup/gi, "Mapping and cardinality");
    },

    closeModal() {
      this.$emit("close");
    },

    submitModal() {
      // Record selected examples
      const selectedExamples = this.getSelectedExamples();

      // First send selected rules to backend
      fetch("/api/get_refine_rules", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(selectedExamples),
      })
        .then((response) => response.json())
        .then(() => {
          // Continue with original submit logic and pass rule update flag
          const emitData = {
            example: this.refineExample,
            rules: this.refineRules,
            isInvalid: this.isInvalid,
            selectedData: this.selectedData,
            selectedExamples: selectedExamples,
          };
          this.$emit("submit", emitData);
          this.closeModal();
        })
        .catch((error) => console.error("Error:", error));
    },

    getSelectedExamples() {
      const processRules = (rulesList, isDelete: boolean) => {
        return rulesList
          .filter((rule) => {
            if (this.hasMultipleExamples(rule)) {
              // Case of multiple examples
              return rule.selectedExamples && rule.selectedExamples.length > 0;
            } else {
              // Case of single example
              return rule.exampleSelected;
            }
          })
          .map((rule) => {
            const isLookupDelete = isDelete && this.isLookupType(rule?.type);
            const exampleString = isLookupDelete
              ? this.getDeleteSummary(rule)
              : this.getRefineExample(rule);
            const hasMultiple = this.hasMultipleExamples(rule);
            // Create a new object, keeping all original fields
            const newRule = {
              type: rule.type,
              column: rule.column,
              originalRule: rule.originalRule,
              refineRule: rule.refineRule,
              original_example: isLookupDelete
                ? this.getDeleteSummary(rule)
                : this.getOriginalExample(rule),
              refine_example: exampleString,
            };

            if (hasMultiple) {
              // Case of multiple examples, keep only selected examples
              const selectedExamplesList = rule.selectedExamples || [];
              newRule.refine_example = selectedExamplesList.join("; ");
              const allExamples = this.splitRefineExamples(exampleString);

              // Handle Missing type rules
              if (rule.type === "Missing" && Array.isArray(rule.refineRule)) {
                const selectedRules: any[] = [];

                selectedExamplesList.forEach((selectedExample) => {
                  const exampleIndex = allExamples.indexOf(selectedExample);
                  if (
                    exampleIndex !== -1 &&
                    exampleIndex < rule.refineRule.length
                  ) {
                    selectedRules.push(rule.refineRule[exampleIndex]);
                  }
                });

                if (selectedRules.length > 0) {
                  newRule.refineRule = selectedRules;
                }
              }
              // Handle Range type rules
              else if (
                rule.type === "Range" &&
                Array.isArray(rule.refineRule)
              ) {
                // Handle nested array case
                const refineRules = Array.isArray(rule.refineRule[0])
                  ? rule.refineRule[0]
                  : rule.refineRule;

                // Get all possible refine_examples
                // Keep only user-selected refineRules
                const selectedRules: any[] = [];
                selectedExamplesList.forEach((selectedExample) => {
                  const exampleIndex = allExamples.indexOf(selectedExample);
                  if (
                    exampleIndex !== -1 &&
                    exampleIndex < refineRules.length
                  ) {
                    selectedRules.push(refineRules[exampleIndex]);
                  }
                });

                // Update refineRule to user-selected rules
                if (selectedRules.length > 0) {
                  newRule.refineRule = [selectedRules];
                }
              }
              // Handle multiple rules for other types
              else if (
                rule.type === "Difference" &&
                Array.isArray(rule.refineRule)
              ) {
                const selectedRules: any[] = [];

                selectedExamplesList.forEach((selectedExample) => {
                  const exampleIndex = allExamples.indexOf(selectedExample);
                  if (
                    exampleIndex !== -1 &&
                    exampleIndex < rule.refineRule.length
                  ) {
                    selectedRules.push(rule.refineRule[exampleIndex]);
                  }
                });
                if (selectedRules.length > 0) {
                  newRule.refineRule = selectedRules;
                }
              }
            } else {
              // Case of single example, keep original refine_example
              newRule.refine_example = exampleString;
            }

            return newRule;
          });
      };

      return {
        updateRules: processRules(this.updateRules, false),
        addRules: processRules(this.addRules, false),
        deleteRules: processRules(this.deleteRules, true),
      };
    },
    // Get all unique column names
    getUniqueColumns() {
      if (!this.selectedData || this.selectedData.length === 0) return [];
      const columnMap = new Map<string, number>();
      this.selectedData.forEach((item) => {
        const currentIndex = columnMap.get(item.columnName);
        if (
          currentIndex === undefined ||
          (typeof item.columnIndex === "number" &&
            item.columnIndex < currentIndex)
        ) {
          columnMap.set(
            item.columnName,
            typeof item.columnIndex === "number"
              ? item.columnIndex
              : Number.MAX_SAFE_INTEGER
          );
        }
      });
      return Array.from(columnMap.entries())
        .sort((a, b) => a[1] - b[1])
        .map(([columnName]) => columnName);
    },

    // Format data into table rows and columns
    getFormattedData() {
      if (!this.selectedData || this.selectedData.length === 0) return [];

      // Group by row ID
      const rowGroups: Record<number, RowData> = {};
      const rowOrder: number[] = [];
      this.selectedData.forEach((item) => {
        const rowKey = item.rowIndex;
        if (!rowGroups[rowKey]) {
          rowGroups[rowKey] = {};
          rowOrder.push(rowKey);
        }
        rowGroups[rowKey][item.columnName] = {
          value: item.value,
          isHighlighted: item.isHighlighted,
        };
      });

      rowOrder.sort((a, b) => a - b);

      // Convert to table data
      const columns = this.getUniqueColumns();
      return rowOrder.map((rowIndex) => {
        const row = rowGroups[rowIndex];
        return columns.map((col) => {
          return (
            row[col as keyof RowData] || { value: "", isHighlighted: false }
          );
        });
      });
    },
    getRuleIcon(ruleType: string): string {
      // Handle icon paths for special rule types
      const normalized = (ruleType || "").toLowerCase();
      if (
        ruleType === "Consistency (domain)" ||
        normalized === "differentdomain"
      ) {
        return "/refinemodel_icon/differentdomain.svg";
      } else if (
        ruleType === "Sequence (sequence)" ||
        normalized === "sequence"
      ) {
        return "/refinemodel_icon/sequence.svg";
      } else if (
        ruleType === "Mapping and cardinality" ||
        normalized === "mapping and cardinality" ||
        normalized === "lookup"
      ) {
        return "/refinemodel_icon/lookup.svg";
      }
      // Return corresponding icon path based on rule type
      return `/refinemodel_icon/${normalized}.svg`;
    },
  },
  computed: {
    parsedRefineResult(): any {
      try {
        if (typeof this.refineResult === "string") {
          return JSON.parse(this.refineResult);
        }
        return this.refineResult || {};
      } catch (e) {
        // Error parsing refineResult
        return {};
      }
    },
    addRules(): any[] {
      return this.parsedRefineResult?.refineDict?.addRules || [];
    },
    deleteRules(): any[] {
      return this.parsedRefineResult?.refineDict?.deleteRules || [];
    },
    updateRules(): any[] {
      return this.parsedRefineResult?.refineDict?.updateRules || [];
    },
    hasRules(): boolean {
      return (
        this.addRules.length > 0 ||
        this.deleteRules.length > 0 ||
        this.updateRules.length > 0
      );
    },
    allRules(): any[] {
      return [...this.addRules, ...this.deleteRules, ...this.updateRules];
    },
    uniqueRuleTypes(): string[] {
      return Array.from(
        new Set(this.allRules.map((rule) => this.getDisplayRuleType(rule.type)))
      );
    },
    tableNeedsScroll(): boolean {
      const columns = this.getUniqueColumns();
      const rows = this.getFormattedData();
      return rows.length > 4 || columns.length > 3;
    },
  },
});
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-container {
  width: 44vw;
  height: 38.33vh;
  border-radius: 0.92vh;
  border: 0.23vh solid #cce2f0;
  background: #f7f9fe;
  box-shadow: 0px 0px 10px 0px rgba(149, 149, 149, 0.25);
  display: flex;
  position: relative;
  /* Remove any styles that might affect positioning */
}

.close-btn {
  position: absolute;
  top: 1vh;
  right: 0.5vw;
  width: 2.5vh;
  height: 2.5vh;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  z-index: 1100; /* Ensure button is on top */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: all 0.2s ease;
  background-color: #ffffff;
}

.close-btn:active {
  transform: scale(0.95);
}

.close-icon {
  color: #5e5e5e;
  font-size: 2vh;
  font-weight: bold;
  line-height: 1;
  display: block;
  margin-top: 0.2vh; /* Fine-tune to ensure X is centered */
}

.modal-left {
  flex: 0 0 40%;
  max-width: 40%;
  height: 100%;
  padding: 0 1vw;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.example-section-header {
  width: 100%;
  height: 2.96vh;
  display: flex;
  align-items: center;
  padding-right: 0.52vw;
  position: relative;
}

.rules-section-header {
  width: 9vw;
  height: 2.96vh;
  display: flex;
  align-items: center;
  padding-right: 0.52vw;
  position: relative;
}

.right-section-header {
  width: 7.39vw;
  height: 2.96vh;
  display: flex;
  align-items: center;
  padding-right: 0.52vw;
}

.title-text {
  color: #4570b6;
  font-family: Roboto;
  font-size: 1.5vh;
  font-style: normal;
  font-weight: 900;
  line-height: normal;
  text-decoration-line: underline;
  text-decoration-style: solid;
  text-decoration-skip-ink: auto;
  text-decoration-thickness: auto;
  text-underline-offset: auto;
  text-underline-position: from-font;
  position: absolute;
  z-index: 2;
  padding-top: 0.92vh;
  padding-bottom: 0.46vh;
  padding-left: 0.78vw;
  padding-right: 0.26vw;
  left: 0; /* Ensure left aligns with section-header */
  top: 0; /* Ensure top aligns with section-header */
}

.title-text-2 {
  color: #304166;
  font-family: Roboto;
  font-size: 1.5vh;
  font-style: normal;
  font-weight: 900;
  line-height: normal;
  text-decoration-line: underline;
  text-decoration-style: solid;
  text-decoration-skip-ink: auto;
  text-decoration-thickness: auto;
  text-underline-offset: auto;
  text-underline-position: from-font;
  position: absolute;
  z-index: 2;
  padding-top: 0.92vh;
  padding-bottom: 0.46vh;
  padding-left: 0.78vw;
  padding-right: 0.26vw;
  left: 0; /* Ensure left aligns with section-header */
  top: 0; /* Ensure top aligns with section-header */
}

.invalid-tag {
  background-color: #f38383;
  color: black;
  padding: 0.46vh 0.92vh;
  border-radius: 0.23vh;
  font-weight: bold;
  position: absolute;
  top: 1vh;
  right: 2vw;
}

.valid-tag {
  background-color: #52c41a;
  color: black;
  padding: 0.46vh 0.92vh;
  border-radius: 0.23vh;
  font-weight: bold;
  position: absolute;
  top: 1vh;
  right: 2vw;
}

.refine-example {
  margin-top: 1.11vh;
  width: 100%;
  background-color: #ffffff;
  border: 1px solid #ffffff;
  border-radius: 0.92vh;
  height: 21.11vh;
  display: flex;
  flex-direction: column;
}

.related-rules {
  height: 14.53vh;
  width: 100%;
  margin-top: 0.75vh;
  background-color: #e5f1ff;
  border: 1px solid #e5f1ff;
  border-radius: 0.92vh;
}

.modal-right {
  flex: 1;
  height: 36.39vh;
  padding-left: 0.3125vw;
  margin-top: 1.11vh;
  margin-right: 0.625vw; /* Add right margin */
  background-color: #ffffff;
  border: 1px solid #ffffff;
  border-radius: 0.92vh;
  position: relative; /* Ensure child absolute positioning is relative to this */
}

.selected-data {
  margin-top: 1.39vh;
  border: 1px solid #eee;
  padding: 0.92vh;
  border-radius: 0.46vh;
  max-height: 13.9vh;
  overflow-y: auto;
}

.data-item {
  margin-bottom: 0.46vh;
  padding: 0.46vh;
  background-color: #f0f0f0;
  border-radius: 0.27vh;
}

.submit-btn {
  background-color: #4570b6;
  padding: 0.5vh 1vh;
  border-radius: 0.46vh;
  color: #fff;
  font-family: Roboto;
  font-size: 1.5vh;
  font-style: normal;
  font-weight: 600;
  line-height: normal;
  cursor: pointer;
  border: none;
  position: absolute;
  right: 1vh;
  bottom: 1vh;
}

.mark_icon {
  width: 1vw;
  height: 1.2vh;
}

.highlighted-cell {
  background-color: #b5d2f8;
}

.data-table-container {
  margin-top: 0.92vh;
  padding-left: 0.27vh;
  overflow: hidden;
  max-height: calc(100% - 4vh);
  width: 100%;
  padding-left: 0.78vw;
  padding-right: 0.78vw;
  box-sizing: border-box;
}

.scrollable-table {
  overflow: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85vw; /* Increase font size */
  table-layout: fixed;
}

.table-flex-width {
  min-width: 100%;
  width: max-content;
  table-layout: auto;
}

.data-table th,
.data-table td {
  border: 1px solid #ddd;
  padding: 0.75vh; /* Increase padding */
  text-align: left;
  white-space: nowrap; /* Prevent text wrapping */
  overflow: hidden;
  font-size: 1.3vh;
  text-overflow: ellipsis; /* Text overflow shows ellipsis */
  min-width: 4vw; /* Set min width to avoid being too narrow */
  text-align: center;
}

.data-table th {
  background-color: #f2f2f2;
  position: sticky;
  top: 0;
  font-size: 1.3vh; /* Increase header font size */
  padding: 0.75vh 0.74vh; /* Increase header padding */
}

.data-table tr {
  height: 2.22vh; /* Increase row height */
}

.data-table tr:nth-child(even) {
  background-color: #f9f9f9;
}

.data-table tr:hover {
  background-color: #f1f1f1;
}

.no-data {
  text-align: center;
  color: #999;
  padding: 1.85vh;
}

.related-rules-content {
  overflow-y: auto;
  max-height: calc(90% - 3vh);
  display: flex;
  justify-content: center;
  height: 90%;
  padding-top: 0.5vh;

  /* Hide scrollbar but keep scrolling functionality */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

/* Hide Webkit browser scrollbar */
.related-rules-content::-webkit-scrollbar {
  display: none;
}

.rules-list {
  font-size: 1.6vh;
  width: 13.81vw;
  padding-left: 0.78vw;
  padding-right: 0.78vw;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start; /* Change to top-down distribution */
  align-items: left;
  padding-top: 1vh; /* Add top padding */
}

.rule-category {
  display: flex;
  flex-direction: column;
  margin-top: 1vh;
  gap: 1.2vh; /* Use gap property to control min spacing between rules */
  margin-right: 0.5vw;
  padding-bottom: 1vh;
  border-bottom: 1px dashed#000;
}

.category-title {
  font-weight: bold;
  margin-bottom: 0.46vh;
  color: #4570b6;
}

.refine-title {
  margin-left: 0.5vw;
  text-align: left;
  width: 6vw;
  color: #000;
  font-family: Roboto;
  font-size: 1.4vh;
  font-style: normal;
  font-weight: 700;
  line-height: normal;
}

.refine-title span {
  margin-bottom: 0.5vh;
  transform: translateY(-0.1vh); /* Move span element up */
  display: inline-block; /* Ensure transform takes effect */
}

.rule-item {
  margin-left: 0.5vw;
  border-radius: 0.27vh;
  display: flex;
  flex-wrap: wrap;
  justify-content: left;
  align-items: left;
}

.rule-type {
  font-weight: normal;
  text-align: center;
}

.refine-rule-type {
  color: #000;
  font-family: Roboto;
  font-size: 1.4vh;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  margin-bottom: 0.3vh;
}

.rule-column {
  color: #666;
}

.no-rules {
  text-align: center;
  color: #999;
  padding: 1.85vh;
}

.rules-container {
  display: flex;
  flex-direction: column;
  gap: 1vh;
  width: 100%;
}

.related-rule-icon {
  width: 2.3vh;
  height: 2.3vh;
  margin-top: -0.2vh;
  margin-right: 0.5vw;
}

.rule-icon {
  width: 1.85vh;
  height: 1.85vh;
  margin-right: 0.5vw;
}

.rule-number {
  margin-right: 0.3vw;
  color: #000;
  font-family: Roboto;
  font-size: 1.3vh;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}

.rule-example-container {
  width: 100%;
  margin-left: 0.4vw; /* Indentation aligned with number and icon */
  margin-top: 0.6vh;
  text-align: left; /* Ensure text is left-aligned */
}

.refine-rule-example {
  color: #000;
  font-size: 1.4vh;
  font-style: italic;
  font-weight: 400;
  line-height: normal;
  margin-left: 0.4vw;
}

/* Checkbox container */
.checkbox-container {
  display: flex;
  align-items: center;
  position: relative;
  cursor: pointer;
  user-select: none;
  margin-left: 0.5vw;
  margin-top: 0.5vh;
}

/* Hide default checkbox */
.example-checkbox {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

/* Custom checkbox style */
.checkmark {
  position: relative;
  display: inline-block;
  height: 1.7vh;
  width: 1.7vh;
  background-color: #ffffff;
  border: 1px solid #575757;
  border-radius: 0.18vh;
}

/* Selected state style */
.example-checkbox:checked ~ .checkmark {
  background-color: #12b600;
  border-color: #575757;
}

/* Create checkmark */
.checkmark:after {
  content: "";
  position: absolute;
  display: none;
}

/* Show checkmark */
.example-checkbox:checked ~ .checkmark:after {
  display: block;
  left: 0.46vh;
  top: 0.2vh;
  width: 0.4vh;
  height: 0.7vh;
  border: solid white;
  border-width: 0 0.18vh 0.18vh 0;
  transform: rotate(45deg);
}

.original-example {
  color: #4d4d4d;
  font-size: 1.4vh;
  font-family: Arial;
  font-style: italic;
  font-weight: 400;
  line-height: normal;
  margin-left: 0.6vw;
}

.example-item {
  margin-bottom: 0.5vh;
}

.arrow_icon {
  width: 1.3vh;
  height: 1.3vh;
  margin-right: 0.52vw;
}
</style>
