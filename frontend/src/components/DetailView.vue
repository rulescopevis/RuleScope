<template>
  <div class="card-container">
    <SettingPanel
      v-if="chooseCard"
      :chooseCard="chooseCard"
      :csvData="csvData"
      :sequenceRules="sequenceRules"
      :conditionRules="conditionRules"
      :multiConditionRules="multiConditionRules"
      :lookupRules="lookupRules"
      @update-rule="handleRuleUpdate"
      @multi-condition-order-updated="handleMultiConditionOrderUpdated"
    />
    <div v-else class="block-2">
      <div class="default-message">Please Choose Validation Card</div>
    </div>

    <div class="block-3">
      <CardPanel
        :filterCards="filterCards"
        :chooseCard="chooseCard"
        @card-click="handleCardClick"
        @delete-card="handleDeleteCard"
        @create-rule="showCreateRuleModal = true"
      />
      <NLPanel
        ref="nlPanel"
        :chooseCard="chooseCard"
        @rules-updated="handleRulesUpdated"
        @preview-refine="handleNlPreview"
      />
    </div>
    <CreateRuleModal
      v-if="showCreateRuleModal"
      @close="showCreateRuleModal = false"
      @submit="handleCreateRuleSubmit"
    />
    <RefineModel
      v-if="showNlRefineModal"
      :isInvalid="nlIsInvalid"
      :selectedData="nlSelectedData"
      :refineResult="nlRefineResult"
      @close="handleNlRefineClose"
      @submit="handleNlRefineSubmit"
    />
  </div>
</template>

<script lang="ts">
import {
  ConditionRule,
  ConstraintValue,
  Row,
  SequenceRule,
  ValidationCard,
} from "@/types/types";
import {
  api,
  api_charactermissing_index,
  api_detect_absolute_difference,
  api_detect_compare_numeric,
  api_detect_compare_date,
  api_detect_condition_logic_index,
  api_detect_conflict_flag,
  api_detect_multi_difference,
  api_detect_multiple_duplicate,
  api_detect_numeric_range,
  api_detect_outliers,
  api_detect_relative_difference,
  api_detect_sequence,
  api_duplicate_index,
  api_extract_invalid_range,
  api_get_finalValidation,
  api_get_multi_difference_sort_conditions,
  api_get_new_finalValidation,
  api_get_sort_conditions,
  api_invalid_pairs_to_indices,
  api_invalid_pairs_to_sorted_indices,
  api_numericmissing_index,
  api_sequence_invalid_range,
  api_detect_lookup,
  api_extract_lookup_area,
  api_generate_card_example,
  api_detect_multiple_logic_condition,
  api_create_rule,
  api_get_refine_rules,
} from "@/utils/callapi";
import { defineComponent } from "vue";
import CreateRuleModal from "./CreateRuleModal.vue";
import SettingPanel from "./SettingPanel.vue";
import CardPanel from "./CardPanel.vue";
import NLPanel from "./NLPanel.vue";
import RefineModel from "./RefineModel.vue";
import { ElMessage, ElMessageBox } from "element-plus"; // Import element-plus components

export default defineComponent({
  name: "DetailView",
  components: {
    CreateRuleModal,
    SettingPanel,
    CardPanel,
    NLPanel,
    RefineModel,
  },
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
    rulesUpdate: Object,
    currentDatasetLoadingId: {
      type: Number,
      required: true,
      default: 0,
    },
  },
  emits: [
    "rules-refresh-requested",
    "validation-cards-updated",
    "clear-visualization",
    "card-clicked",
  ],
  data(): {
    showCreateRuleModal: boolean;
    chooseCard: ValidationCard | null;
    selectedSequenceValue: string; // Currently selected sequenceRule value
    sequenceRules: { [key: string]: SequenceRule[] };
    allowedNext: string[];
    conditionRules: { [key: string]: ConditionRule[] };
    selectedConditionValue: string; // Currently selected sequenceRule value
    constraintValue_Range: ConstraintValue;
    constraintValue_Equality: string[];
    filterCards: ValidationCard[];
    validationCards: ValidationCard[];
    selectedAllowedNext: string[];
    allSequenceValues: string[];
    availableConstraintValues: string[];
    selectedParentValue: string;
    selectedChildValues: string[];
    availableParentValues: string[];
    availableChildValues: string[];
    lookupRules: { [key: string]: any[] };
    allPossibleChildValues: string[];
    localDatasetLoadingId: number; // Locally stored current dataset loading ID
    // MultipleCondition related variables (refactored to support N dynamic condition columns)
    multiConditionRules: { [key: string]: any[] };
    selectedMultiConditionValues: string[]; // Array storing selected values for all condition columns
    multiConstraintValue_Range: ConstraintValue;
    multiConstraintValue_Equality: string[];
    availableMultiConstraintValues: string[];
    columnOrderOverrides: Record<string, string[]>;
    showNlRefineModal: boolean;
    nlRefineResult: any;
    nlSelectedData: any[];
    nlIsInvalid: boolean;
  } {
    return {
      showCreateRuleModal: false,
      chooseCard: null,
      selectedSequenceValue: "",
      sequenceRules: {},
      allowedNext: [],
      conditionRules: {},
      selectedConditionValue: "",
      constraintValue_Range: {
        start: 0,
        end: 0,
        startInclusive: false,
        endInclusive: false,
      },
      constraintValue_Equality: [],
      filterCards: [],
      validationCards: [],
      selectedAllowedNext: [],
      allSequenceValues: [],
      availableConstraintValues: [],
      selectedParentValue: "",
      selectedChildValues: [],
      availableParentValues: [],
      availableChildValues: [],
      lookupRules: {},
      allPossibleChildValues: [],
      localDatasetLoadingId: 0,
      multiConditionRules: {},
      selectedMultiConditionValues: [],
      multiConstraintValue_Range: {
        start: 0,
        end: 0,
        startInclusive: false,
        endInclusive: false,
      },
      multiConstraintValue_Equality: [],
      availableMultiConstraintValues: [],
      columnOrderOverrides: {},
      showNlRefineModal: false,
      nlRefineResult: {
        refineStatus: false,
        refineDict: { addRules: [], deleteRules: [], updateRules: [] },
      },
      nlSelectedData: [],
      nlIsInvalid: false,
    };
  },
  watch: {
    selectedColumns: {
      handler() {
        this.setCardList();
      },
      immediate: true,
      deep: true,
    },
    csvData: {
      handler(newVal) {
        // Run parseToValidationCards when csvData changes and is not empty
        if (newVal && newVal.length > 0) {
          const currentId = this.localDatasetLoadingId;
          this.readJsonFile(currentId);
        }
      },
      immediate: true,
      deep: true,
    },
    rulesUpdate: {
      handler(newVal) {
        if (newVal) {
          if (newVal.selectedExamples) {
            const { addRules, updateRules, deleteRules } =
              newVal.selectedExamples;
            // Handle updating rules
            if (updateRules && updateRules.length > 0) {
              for (const rule of updateRules) {
                const { type, column } = rule;
                const resolvedType = this.resolveRuleType(column, type);
                const cardIndex = this.findCardIndexByRule(
                  column,
                  resolvedType
                );

                if (cardIndex !== -1) {
                  // Remove found card
                  this.validationCards.splice(cardIndex, 1);

                  // Reload rule card
                  this.loadSpecificRuleCard(column, resolvedType).then(() => {
                    this.handleRuleMutationSideEffects();
                  });
                }
              }
            }

            // Handle adding rules
            if (addRules && addRules.length > 0) {
              for (const rule of addRules) {
                const { type, column } = rule;
                const resolvedType = this.resolveRuleType(column, type);
                this.loadSpecificRuleCard(column, resolvedType).then(() => {
                  this.handleRuleMutationSideEffects();
                });
              }
            }

            // Handle deleting rules
            if (deleteRules && deleteRules.length > 0) {
              for (const rule of deleteRules) {
                const { type, column } = rule;

                const resolvedType = this.resolveRuleType(column, type);
                const cardIndex = this.findCardIndexByRule(
                  column,
                  resolvedType
                );

                if (cardIndex !== -1) {
                  this.validationCards.splice(cardIndex, 1);
                  this.clearVisualization();
                  this.handleRuleMutationSideEffects();
                }
              }
            }
          }
        }
      },
      immediate: true,
      deep: true,
    },
    currentDatasetLoadingId: {
      handler(newVal) {
        this.localDatasetLoadingId = newVal;
      },
      immediate: true,
    },
  },

  methods: {
    handleNlPreview(payload: any) {
      const refineResult = payload?.refineResult;
      const refineDict = refineResult?.refineDict || {};
      const hasActions = ["addRules", "updateRules", "deleteRules"].some(
        (key) => Array.isArray(refineDict[key]) && refineDict[key].length > 0
      );

      if (!refineResult) {
        ElMessage({
          type: "warning",
          message: "No displayable results returned from the model.",
        });
        return;
      }

      if (!hasActions) {
        ElMessage({
          type: "info",
          message:
            "No rules to update, but you can still view the return details.",
        });
      }

      this.nlRefineResult = refineResult;
      this.nlSelectedData = [];
      this.nlIsInvalid = false;
      this.showNlRefineModal = true;
    },

    async handleNlRefineSubmit(data: any) {
      const selectedExamples = data?.selectedExamples;
      const refineDict = selectedExamples || this.nlRefineResult?.refineDict;

      if (!refineDict) {
        ElMessage({
          type: "error",
          message: "Missing applicable rule changes.",
        });
        return;
      }

      try {
        await api_get_refine_rules(refineDict);
        ElMessage({ type: "success", message: "Rules updated." });
        await this.handleRulesUpdated();
        (
          this.$refs.nlPanel as { clearInput?: () => void } | undefined
        )?.clearInput?.();
        this.$emit("rules-refresh-requested");
      } catch (err) {
        ElMessage({ type: "error", message: "Failed to update rules." });
      } finally {
        this.showNlRefineModal = false;
      }
    },

    handleNlRefineClose() {
      this.showNlRefineModal = false;
    },

    async handleRulesUpdated() {
      await this.readJsonFile(this.localDatasetLoadingId);
    },
    async handleRuleUpdate({ columnName, ruleType }) {
      const resolvedType = this.resolveRuleType(columnName, ruleType);
      const cardIndex = this.findCardIndexByRule(columnName, resolvedType);
      if (cardIndex !== -1) {
        this.validationCards.splice(cardIndex, 1);
        await this.loadSpecificRuleCard(columnName, resolvedType).then(() => {
          this.handleRuleMutationSideEffects();
        });
      }
    },
    // Dynamically calculate the maximum number of tags to display
    getMaxCollapseTags(selectedValues: string[]): number {
      if (!selectedValues || selectedValues.length === 0) {
        return 1;
      }

      // Available width for the select box (18.5vw in pixels, minus padding etc.)
      const selectWidth = window.innerWidth * 0.185; // 18.5vw
      const availableWidth = selectWidth - 40; // Subtract space for padding, arrow, etc.

      // Estimate width for each tag (including text, padding, close button)
      let totalWidth = 0;
      let maxTags = 0;

      for (let i = 0; i < selectedValues.length; i++) {
        const value = selectedValues[i];
        // Estimate tag width based on string length
        // Approx 8px for English, 16px for Chinese, plus approx 30px for tag padding/border/close button
        const estimatedTagWidth = this.estimateTagWidth(value) + 30;

        if (totalWidth + estimatedTagWidth > availableWidth) {
          break;
        }

        totalWidth += estimatedTagWidth + 5; // 5px spacing between tags
        maxTags++;
      }

      // Ensure at least 1 tag is shown
      return Math.max(1, maxTags);
    },

    // Estimate width of tag text
    estimateTagWidth(text: string): number {
      let width = 0;
      for (let i = 0; i < text.length; i++) {
        const char = text.charAt(i);
        // Check for Chinese characters
        if (/[\u4e00-\u9fa5]/.test(char)) {
          width += 16;
        } else {
          width += 8;
        }
      }
      return width;
    },
    // Get dynamic row layout for MultipleCondition
    getMultipleConditionRows(): Array<
      Array<{
        name: string;
        displayName: string;
        needsTooltip: boolean;
        type: string;
        conditionIndex?: number; // Only condition columns have an index, constraint columns do not
      }>
    > {
      if (
        !this.chooseCard ||
        this.chooseCard.relationType !== "MultipleCondition"
      ) {
        return [];
      }

      const columnNames = this.chooseCard.columnName;
      const totalColumns = columnNames.length;

      // Validate at least 3 columns
      if (totalColumns < 3) {
        console.warn(
          `MultipleCondition requires at least 3 columns, got ${totalColumns}`
        );
        return [];
      }

      // Determine layout based on column count
      let rows: Array<
        Array<{
          name: string;
          displayName: string;
          needsTooltip: boolean;
          type: string;
          conditionIndex?: number; // Only condition columns have an index, constraint columns do not
        }>
      > = [];

      // Determine constraint type
      const isEqualityBased =
        this.chooseCard.constraintType?.[0] === "EqualityBased";

      if (isEqualityBased) {
        // EqualityBased: All columns (including constraint) laid out 2 per row
        // Conditions and constraints handled together
        for (let i = 0; i < totalColumns; i += 2) {
          const rowColumns = columnNames.slice(i, i + 2);
          const row: Array<{
            name: string;
            displayName: string;
            needsTooltip: boolean;
            type: string;
            conditionIndex?: number;
          }> = rowColumns.map((colName, colIndex) => {
            const globalIndex = i + colIndex;
            const isConstraintColumn = globalIndex === totalColumns - 1;

            return {
              name: colName,
              displayName: this.truncateColumnName(colName),
              needsTooltip: colName.length > this.getMaxLabelLength(),
              type: isConstraintColumn
                ? "constraint"
                : `condition${globalIndex + 1}`,
              conditionIndex: isConstraintColumn ? undefined : globalIndex,
            };
          });

          rows.push(row);
        }
      } else {
        // RangeBased: Show only condition columns (first N-1 columns), max 2 per row
        // Constraint column displayed in a dedicated block
        const conditionColumns = columnNames.slice(0, -1);

        for (let i = 0; i < conditionColumns.length; i += 2) {
          const rowColumns = conditionColumns.slice(i, i + 2);
          const row: Array<{
            name: string;
            displayName: string;
            needsTooltip: boolean;
            type: string;
            conditionIndex?: number;
          }> = rowColumns.map((colName, index) => ({
            name: colName,
            displayName: this.truncateColumnName(colName),
            needsTooltip: colName.length > this.getMaxLabelLength(),
            type: `condition${i + index + 1}`,
            conditionIndex: i + index,
          }));

          rows.push(row);
        }
      }

      return rows;
    },

    // Truncate column name display
    truncateColumnName(columnName: string): string {
      const maxLength = this.getMaxLabelLength();
      if (columnName.length <= maxLength) {
        return columnName;
      }
      return columnName.substring(0, maxLength - 3) + "...";
    },

    // Get max label length (calculated based on fixed width)
    getMaxLabelLength(): number {
      // Based on 8vw fixed width, estimate capacity
      // Assume average char width approx 0.8vh, 8vw approx 12 chars
      return 12;
    },

    // Dynamically get all unique values for a specific condition column
    getUniqueConditionValues(conditionIndex: number): string[] {
      if (
        !this.chooseCard ||
        this.chooseCard.relationType !== "MultipleCondition"
      ) {
        return [];
      }

      const fullname = this.chooseCard.columnName.join("+");
      const rules = this.multiConditionRules[fullname] || [];
      const conditionKey = `conditionValue${conditionIndex + 1}`;

      // Extract all unique values for this condition column
      return [
        ...new Set(
          rules.map((rule) => rule[conditionKey]).filter((val) => val != null)
        ),
      ] as string[];
    },
    setCardList() {
      const validationCards = this.validationCards;
      const sortByConflict = (cards: ValidationCard[]) =>
        [...cards].sort((a, b) => {
          const conflictA = a.ifConflict ? Number(a.ifConflict) : 0;
          const conflictB = b.ifConflict ? Number(b.ifConflict) : 0;
          return conflictB - conflictA;
        });

      if (this.selectedColumns.length === 0) {
        this.filterCards = sortByConflict(validationCards);
      } else {
        const newList = validationCards.filter((card) =>
          this.selectedColumns.every((selectedCol) =>
            card.columnName.includes(selectedCol)
          )
        );
        this.filterCards = sortByConflict(newList);
      }

      this.$emit("validation-cards-updated", this.validationCards);
    },
    handleRuleMutationSideEffects() {
      this.setCardList();
      this.$emit("rules-refresh-requested");
    },
    getCardOrderKey(columns: string[], relationType: string): string {
      const sortedColumns = [...columns].sort();
      const datasetId = this.currentDatasetLoadingId || 0;
      return `${datasetId}:${relationType || "unknown"}:${sortedColumns.join(
        "|"
      )}`;
    },
    ensureCardDisplayOrder(card: ValidationCard): void {
      if (!card) {
        return;
      }
      const needsInit =
        !Array.isArray(card.displayColumnOrder) ||
        card.displayColumnOrder.length !== card.columnName.length;
      const key = this.getCardOrderKey(card.columnName, card.relationType);
      const storedOrder = this.columnOrderOverrides[key];
      if (storedOrder && storedOrder.length === card.columnName.length) {
        card.displayColumnOrder = [...storedOrder];
        return;
      }
      if (needsInit) {
        card.displayColumnOrder = [...card.columnName];
      }
    },
    // Check if column names overflow display
    checkColumnOverflow(
      columnNames: string[],
      containerKey: string
    ): { visibleCount: number; totalCount: number } {
      // Simple strategy: Estimate based on total length of column names
      const totalChars = columnNames.reduce(
        (sum, name) => sum + name.length,
        0
      );
      const maxChars = containerKey.includes("top") ? 40 : 30; // Top panel allows more characters

      if (totalChars <= maxChars) {
        // Not too many characters, show all
        return {
          visibleCount: columnNames.length,
          totalCount: columnNames.length,
        };
      }

      // Too many characters, check how many can be shown one by one
      let currentChars = 0;
      let visibleCount = 0;

      for (let i = 0; i < columnNames.length; i++) {
        const nameLength = columnNames[i].length;
        if (currentChars + nameLength > maxChars && i > 0) {
          break;
        }
        currentChars += nameLength;
        visibleCount++;
      }

      // Ensure at least one is shown
      if (visibleCount === 0) visibleCount = 1;

      return { visibleCount, totalCount: columnNames.length };
    },
    // Get visible column names
    getVisibleColumnNames(
      columnNames: string[],
      containerKey: string
    ): string[] {
      const result = this.checkColumnOverflow(columnNames, containerKey);
      return columnNames.slice(0, result.visibleCount);
    },
    // Get count of hidden columns
    getHiddenColumnCount(columnNames: string[], containerKey: string): number {
      const result = this.checkColumnOverflow(columnNames, containerKey);
      return result.totalCount - result.visibleCount;
    },
    // Get list of hidden column names
    getHiddenColumnNames(
      columnNames: string[],
      containerKey: string
    ): string[] {
      const result = this.checkColumnOverflow(columnNames, containerKey);
      return columnNames.slice(result.visibleCount);
    },
    async syncToBackend() {
      try {
        let updatedRuleValue;
        if (this.chooseCard!.relationType === "Sequence") {
          updatedRuleValue = {
            value: this.selectedSequenceValue,
            allowed_next: this.selectedAllowedNext,
          };
        } else if (this.chooseCard!.relationType === "Logical and condition") {
          if (this.chooseCard!.constraintType?.[0] === "RangeBased") {
            updatedRuleValue = {
              conditionValue: this.selectedConditionValue,
              constraintValue: this.constraintValue_Range,
            };
          } else if (this.chooseCard!.constraintType?.[0] === "EqualityBased") {
            updatedRuleValue = {
              conditionValue: this.selectedConditionValue,
              constraintValue: this.constraintValue_Equality as string[],
            };
          }
        } else if (this.chooseCard!.relationType === "Lookup") {
          updatedRuleValue = {
            parentColumnName: this.chooseCard!.ruleValue.parentColumnName,
            childColumnName: this.chooseCard!.ruleValue.childColumnName,
            lookupList: [
              {
                parentValue: this.selectedParentValue,
                childValueList: this.selectedChildValues,
              },
            ],
          };
        } else {
          updatedRuleValue = this.chooseCard!.ruleValue;
        }

        // Update backend
        await api.post("/api/update-rule", {
          columnName: this.chooseCard!.columnName,
          ruleType: this.chooseCard!.relationType,
          ruleValue: updatedRuleValue,
        });
        // Find corresponding card and remove it
        const cardIndex = this.validationCards.findIndex(
          (card) =>
            card.columnName === this.chooseCard!.columnName &&
            card.relationType === this.chooseCard!.relationType
        );
        if (cardIndex !== -1) {
          // Remove found card
          this.validationCards.splice(cardIndex, 1);
          await this.loadSpecificRuleCard(
            this.chooseCard!.columnName,
            this.chooseCard!.relationType
          ).then(() => {
            this.handleRuleMutationSideEffects();
          });
        }
      } catch (error) {
        // console.error("Failed to update value", error);
      }
    },
    rangeFormat(obj: any) {
      return (
        (obj.startInclusive ? "[" : "(") +
        String(obj.start) +
        ", " +
        String(obj.end) +
        (obj.endInclusive ? "]" : ")")
      );
    },
    updateAllowedNext() {
      // Get rules for current column
      const currentRules =
        this.sequenceRules[this.chooseCard!.columnName[0]] || [];

      // Find rule for currently selected value
      const selectedRule = currentRules.find(
        (rule: SequenceRule) => rule.value === this.selectedSequenceValue
      );

      // Set allowed next values
      this.allowedNext = selectedRule ? selectedRule.allowed_next : [];

      // Get all possible sequence values (except current one)
      this.allSequenceValues = currentRules
        .map((rule) => rule.value)
        .filter((value) => value !== this.selectedSequenceValue);

      // Initialize selected values
      this.selectedAllowedNext = [...this.allowedNext];
    },
    // Control ConstraintValue display in panel
    updateConstraintValue() {
      if (this.chooseCard?.constraintType?.[0] === "RangeBased") {
        // Find range corresponding to conditionValue in invalid_range
        const selectedRange = (
          this.chooseCard?.invalid_range as Array<any>
        )?.find(
          (range) => range.conditionContent === this.selectedConditionValue
        );

        if (selectedRange) {
          // Update range value
          this.constraintValue_Range = {
            start: selectedRange.start,
            end: selectedRange.end,
            startInclusive: selectedRange.startInclusive,
            endInclusive: selectedRange.endInclusive,
          };
        } else {
          // If no range found, reset to default
          this.constraintValue_Range = {
            start: 0,
            end: 0,
            startInclusive: false,
            endInclusive: false,
          };
        }
      } else {
        // Reset default value
        if (this.chooseCard!.constraintType?.[0] === "EqualityBased") {
          const columnName = this.chooseCard!.columnName[1];
          const uniqueValues = [
            ...new Set(this.csvData.map((row) => String(row[columnName]))),
          ];
          this.availableConstraintValues = uniqueValues.filter(
            (value) => value && value.trim() !== ""
          );

          // Find constraint value corresponding to currently selected condition value
          const fullname = this.chooseCard!.columnName.join("+");
          const selectedCondition = this.conditionRules[fullname]?.find(
            (condition) =>
              condition.conditionValue === this.selectedConditionValue
          );

          // If constraint value found, set as currently selected constraint value
          if (selectedCondition && selectedCondition.constraintValue) {
            this.constraintValue_Equality = Array.isArray(
              selectedCondition.constraintValue
            )
              ? selectedCondition.constraintValue.map((value) => String(value)) // Ensure conversion to string
              : [String(selectedCondition.constraintValue)];
          } else {
            // If not found, clear selection
            this.constraintValue_Equality = [];
          }
        } else {
          this.constraintValue_Range = {
            start: 0,
            end: 0,
            startInclusive: false,
            endInclusive: false,
          };
        }
      }
    },
    // Control ConstraintValue display in multicondition (refactored for N dynamic condition columns)
    updateMultiConstraintValue() {
      if (!this.chooseCard) {
        return;
      }

      // Get number of condition columns (Total columns - 1)
      const numConditionColumns = this.chooseCard.columnName.length - 1;

      // For EqualityBased, always get all available constraint values first
      if (this.chooseCard!.constraintType?.[0] === "EqualityBased") {
        // Constraint column is the last one
        const constraintColumnIndex = this.chooseCard!.columnName.length - 1;
        const columnName = this.chooseCard!.columnName[constraintColumnIndex];
        const uniqueValues = [
          ...new Set(this.csvData.map((row) => String(row[columnName]))),
        ];
        this.availableMultiConstraintValues = uniqueValues.filter(
          (value) => value && (value as string).trim() !== ""
        );
      }

      // Validate if enough selected values exist
      if (this.selectedMultiConditionValues.length < numConditionColumns) {
        console.warn(
          `Expected ${numConditionColumns} condition values, got ${this.selectedMultiConditionValues.length}`
        );
        return;
      }

      // Check if all condition values are selected
      const allConditionsSelected = this.selectedMultiConditionValues
        .slice(0, numConditionColumns)
        .every((val) => val && val.trim() !== "");

      if (!allConditionsSelected) {
        return;
      }

      if (this.chooseCard?.constraintType?.[0] === "RangeBased") {
        // Find range corresponding to multi-condition values in invalid_range
        const selectedRange = (
          this.chooseCard?.invalid_range as Array<any>
        )?.find((range) => {
          // Dynamically match all condition columns
          for (let i = 0; i < numConditionColumns; i++) {
            const conditionKey = `conditionContent${i + 1}`;
            if (range[conditionKey] !== this.selectedMultiConditionValues[i]) {
              return false;
            }
          }
          return true;
        });

        if (selectedRange) {
          // Update range value
          this.multiConstraintValue_Range = {
            start: selectedRange.start,
            end: selectedRange.end,
            startInclusive: selectedRange.startInclusive,
            endInclusive: selectedRange.endInclusive,
          };
        } else {
          // If no range found, reset to default
          this.multiConstraintValue_Range = {
            start: 0,
            end: 0,
            startInclusive: false,
            endInclusive: false,
          };
        }
      } else if (this.chooseCard!.constraintType?.[0] === "EqualityBased") {
        // Find constraint value corresponding to selected multi-condition values
        const fullname = this.chooseCard!.columnName.join("+");
        const selectedCondition = this.multiConditionRules[fullname]?.find(
          (condition) => {
            // Dynamically match all condition columns
            for (let i = 0; i < numConditionColumns; i++) {
              const conditionKey = `conditionValue${i + 1}`;
              if (
                condition[conditionKey] !== this.selectedMultiConditionValues[i]
              ) {
                return false;
              }
            }
            return true;
          }
        );

        // If constraint value found, set as currently selected constraint value
        if (selectedCondition && selectedCondition.constraintValue) {
          this.multiConstraintValue_Equality = Array.isArray(
            selectedCondition.constraintValue
          )
            ? selectedCondition.constraintValue.map((value) => String(value)) // Ensure conversion to string
            : [String(selectedCondition.constraintValue)];
        } else {
          // If not found, clear selection
          this.multiConstraintValue_Equality = [];
        }
      } else {
        this.multiConstraintValue_Range = {
          start: 0,
          end: 0,
          startInclusive: false,
          endInclusive: false,
        };
      }
    },
    // Handle changes in constraint column value (user manual edit)
    handleMultiConstraintChange() {
      // No extra processing needed when constraint value changes
      // User can freely edit constraint values
      console.log(
        "Constraint value changed:",
        this.multiConstraintValue_Equality
      );
    },
    // Handle changes in condition column values
    handleMultiConditionChange(changedIndex: number) {
      if (!this.chooseCard) {
        return;
      }

      const fullname = this.chooseCard.columnName.join("+");
      const multiConditionRules = this.multiConditionRules[fullname] || [];
      const numConditionColumns = this.chooseCard.columnName.length - 1;

      // Get currently changed condition value
      const changedValue = this.selectedMultiConditionValues[changedIndex];

      if (!changedValue || changedValue.trim() === "") {
        return;
      }

      // Find first rule matching the changed condition column value
      const matchedRule = multiConditionRules.find((rule) => {
        const conditionKey = `conditionValue${changedIndex + 1}`;
        return rule[conditionKey] === changedValue;
      });

      if (matchedRule) {
        // Auto-fill other condition column values
        for (let i = 0; i < numConditionColumns; i++) {
          if (i !== changedIndex) {
            const conditionKey = `conditionValue${i + 1}`;
            this.selectedMultiConditionValues[i] =
              matchedRule[conditionKey] || "";
          }
        }

        // Update constraint value
        this.updateMultiConstraintValue();
      }
    },
    async handleCardClick(card: ValidationCard) {
      this.ensureCardDisplayOrder(card);
      this.chooseCard = card;
      console.log("Selected card:", this.chooseCard);

      // Condition rule initialization
      if (card.relationType === "Logical and condition") {
        // Set first item as default selected
        this.selectedConditionValue = card.ruleValue[0]?.conditionValue || "";
        // Immediately update constraint value display
        this.updateConstraintValue();
      }
      // Multi-condition rule initialization (refactored for N dynamic condition columns)
      if (card.relationType === "MultipleCondition") {
        // Set first item as default selected
        const fullname = card.columnName.join("+");
        const multiConditionRules = this.multiConditionRules[fullname] || [];
        if (multiConditionRules.length > 0) {
          const firstRule = multiConditionRules[0];
          const numConditionColumns = card.columnName.length - 1; // Total columns - 1

          // Dynamically extract all condition values
          this.selectedMultiConditionValues = [];
          for (let i = 0; i < numConditionColumns; i++) {
            const conditionKey = `conditionValue${i + 1}`;
            this.selectedMultiConditionValues.push(
              firstRule[conditionKey] || ""
            );
          }

          // Immediately update constraint value display
          this.updateMultiConstraintValue();
        }
      }
      if (card.columnName.length === 1) {
        if (card.relationType === "Missing") {
          if (card.columnType[0] == "character") {
            card.sortedIndices = card.invalid_index;
          } else if (card.columnType[0] == "numeric") {
            card.sortedIndices = card.invalid_index;
          }
        } else if (card.relationType === "Duplicate") {
          card.sortedIndices = card.invalid_index;
        } else if (card.relationType === "Type") {
          card.sortedIndices = [];
        } else if (card.relationType === "Sequence") {
          const sequenceRules =
            this.sequenceRules[String(card.columnName)] || [];
          if (sequenceRules.length > 0) {
            this.selectedSequenceValue = sequenceRules[0].value;
            // Update allowed next values
            this.updateAllowedNext();
          }
          card.invalid_range = await api_sequence_invalid_range(
            card.columnName[0]
          );
          card.sort_conditions = await api_get_sort_conditions(
            card.columnName[0]
          );
          card.sortedIndices = await api_invalid_pairs_to_sorted_indices(
            card.invalid_pairs || []
          );
        } else if (card.relationType === "Difference") {
          card.sortedIndices = await api_invalid_pairs_to_sorted_indices(
            card.invalid_pairs || []
          );
          card.invalid_range = card.ruleValue;
          card.sort_conditions = await api_get_sort_conditions(
            card.columnName[0]
          );
        } else if (card.relationType === "relativeDifference") {
          card.sortedIndices = await api_invalid_pairs_to_sorted_indices(
            card.invalid_pairs || []
          );
          card.invalid_range = card.ruleValue;
          card.sort_conditions = await api_get_sort_conditions(
            card.columnName[0]
          );
        } else if (card.relationType === "Outlier") {
          card.sortedIndices = card.invalid_index;
        } else if (card.relationType === "Range") {
          card.sortedIndices = card.invalid_index;
        } else if (card.relationType === "Distribution") {
          card.sortedIndices = card.invalid_index;
        }
      } else if (card.columnName.length > 1) {
        if (card.relationType === "Logical and condition") {
          const fullname = card.columnName.join("+");
          const conditionRules = this.conditionRules[fullname] || [];

          // If condition rules exist, set first condition value as default
          if (conditionRules.length > 0) {
            this.selectedConditionValue = conditionRules[0].conditionValue;
            // Immediately update constraint value display
            this.updateConstraintValue();
          }
          card.sortedIndices = card.invalid_index;
          card.invalid_range = await api_extract_invalid_range(
            this.csvData,
            card.columnName
          );
        } else if (card.relationType === "Compare") {
          card.sortedIndices = card.invalid_index;
          card.invalid_range = card.ruleValue;
        } else if (card.relationType === "MultiDifference") {
          card.sortedIndices = await api_invalid_pairs_to_sorted_indices(
            card.invalid_pairs || []
          );
          card.invalid_range = card.ruleValue;
          card.sort_conditions = await api_get_multi_difference_sort_conditions(
            card.columnName
          );
        } else if (card.relationType === "MultipleDuplicate") {
          card.sortedIndices = card.invalid_index;
          card.invalid_range = [];
        } else if (card.relationType === "Lookup") {
          // Set available parent value list
          const lookupKey = `${card.columnName[0]}+${card.columnName[1]}`;
          const lookupList = this.lookupRules[lookupKey];
          if (lookupList.length > 0) {
            this.availableParentValues = lookupList.map(
              (item) => item.parentValue
            );
            this.selectedParentValue = this.availableParentValues[0] || "";

            // Update child value list
            this.updateChildValues();
          }
          card.sortedIndices = card.invalid_index;
          card.invalid_range = await api_extract_lookup_area(card.columnName);
        } else if (card.relationType === "MultipleCondition") {
          // Multi-condition logic handling (refactored for N dynamic condition columns)
          const fullname = card.columnName.join("+");
          const multiConditionRules = this.multiConditionRules[fullname] || [];

          // If multi-condition rules exist, set first condition value as default
          if (multiConditionRules.length > 0) {
            const firstRule = multiConditionRules[0];
            const numConditionColumns = card.columnName.length - 1; // Total columns - 1

            // Dynamically extract all condition values
            this.selectedMultiConditionValues = [];
            for (let i = 0; i < numConditionColumns; i++) {
              const conditionKey = `conditionValue${i + 1}`;
              this.selectedMultiConditionValues.push(
                firstRule[conditionKey] || ""
              );
            }

            // Immediately update constraint value display
            this.updateMultiConstraintValue();
          }
          card.sortedIndices = card.invalid_index;

          // For multicondition, use data from multiConditionRules directly without API call
          // Dynamically generate invalid_range to support arbitrary column counts
          card.invalid_range = multiConditionRules.map((rule) => {
            const numConditionColumns = card.columnName.length - 1;
            const rangeEntry: any = { constraintValue: rule.constraintValue };

            // Dynamically add all condition columns
            for (let i = 0; i < numConditionColumns; i++) {
              const conditionKey = `conditionContent${i + 1}`;
              const conditionValueKey = `conditionValue${i + 1}`;
              rangeEntry[conditionKey] = rule[conditionValueKey];
            }

            // If constraintValue is object (RangeBased), spread it
            if (
              typeof rule.constraintValue === "object" &&
              rule.constraintValue !== null &&
              !Array.isArray(rule.constraintValue)
            ) {
              Object.assign(rangeEntry, rule.constraintValue);
            }

            return rangeEntry;
          });
        }
      }
      // Ensure passing complete column name array
      const displayColumns =
        card.displayColumnOrder &&
        card.displayColumnOrder.length === card.columnName.length
          ? card.displayColumnOrder
          : card.columnName;

      this.$emit(
        "card-clicked",
        card.columnType,
        card.invalid_index || [],
        displayColumns,
        card.relationType,
        card.invalid_range,
        card.sort_conditions || [],
        card.invalid_pairs,
        card.sortedIndices,
        card.threeColumnRules || []
      );
    },
    async handleMultiConditionOrderUpdated(newOrder: string[]) {
      if (
        !this.chooseCard ||
        this.chooseCard.relationType !== "MultipleCondition"
      ) {
        return;
      }
      const normalizedOrder = Array.isArray(newOrder)
        ? [...newOrder]
        : [...this.chooseCard.columnName];
      if (normalizedOrder.length !== this.chooseCard.columnName.length) {
        return;
      }
      const key = this.getCardOrderKey(
        this.chooseCard.columnName,
        this.chooseCard.relationType
      );
      this.columnOrderOverrides[key] = [...normalizedOrder];
      this.chooseCard.displayColumnOrder = [...normalizedOrder];
      const matchedCard = this.validationCards.find(
        (card) =>
          this.getCardOrderKey(card.columnName, card.relationType) === key
      );
      if (matchedCard) {
        matchedCard.displayColumnOrder = [...normalizedOrder];
      }
      this.setCardList();
      if (this.chooseCard) {
        await this.handleCardClick(this.chooseCard);
      }
    },
    columnLine(columnName: string[]) {
      let final = "";
      for (let i = 0; i < columnName.length; i++) {
        if (i === 0) {
          final += columnName[i];
        } else {
          final += ", " + columnName[i];
        }
      }
      return final;
    },
    async readJsonFile(datasetLoadingId): Promise<void> {
      try {
        // Abandon loading if dataset has changed
        if (datasetLoadingId !== this.localDatasetLoadingId) {
          return;
        }

        const selectedCardIdentity = this.getCurrentCardIdentity();
        const jsonData = await api_get_finalValidation();
        await this.parseToValidationCards(
          jsonData,
          datasetLoadingId,
          selectedCardIdentity
        );
      } catch (error) {
        // console.error("Failed to read JSON file:", error);
      }
    },
    async parseToValidationCards(
      data: any,
      datasetLoadingId: number,
      selectedCardIdentity: {
        relationType: string;
        columnName: string[];
      } | null = null
    ) {
      // Abandon parsing if dataset has changed
      if (datasetLoadingId !== this.localDatasetLoadingId) {
        return;
      }

      // Reset card arrays
      this.validationCards = [];
      this.filterCards = [];
      this.sequenceRules = {};
      this.conditionRules = {};
      this.multiConditionRules = {};

      // Handle single column validation rules
      for (const columnName in data) {
        // Check if dataset has changed
        if (datasetLoadingId !== this.localDatasetLoadingId) {
          return;
        }

        if (
          columnName !== "conditionLogicColumnList" &&
          columnName !== "multiDifference" &&
          columnName !== "numericCompareList" &&
          columnName !== "dateCompareList" &&
          columnName !== "multipleDuplicateColumnsList" &&
          columnName !== "multipleConditionLogicColumnList" &&
          columnName !== "lookupList" &&
          columnName !== "domainDescription" &&
          columnName !== "substringList"
        ) {
          const columnData = data[columnName];
          const column_csv_Data = this.csvData.map((d) => d[columnName]);

          // Type validation card
          const typeCard = {
            columnName: [columnName],
            columnType: [columnData.type],
            relationClass: "Type",
            relationType: "Type",
            ruleValue: columnData.type,
            example: `The type of ${columnName} is ${columnData.type}.`,
            ifConflict: 0,
          };
          this.addCard(typeCard);

          // Missing validation card
          if (columnData.type == "character") {
            let missing_index: number[] = [];
            if (columnData.missingDetectFlag == true) {
              missing_index = await api_charactermissing_index(columnName);
            } else {
              missing_index = [];
            }
            const missingCard = {
              columnName: [columnName],
              columnType: [columnData.type],
              invalid_index: missing_index,
              relationClass: "Integrity",
              relationType: "Missing",
              ruleValue: {
                missingDetectFlag: columnData.missingDetectFlag,
                missingValueFlag: columnData.missingValueFlag,
                specialMissingValueList: columnData.specialMissingValueList,
              },
              example: columnData.missingValueFlag
                ? `The ${columnName} exists missing values.`
                : `The ${columnName} does not exist missing values.`,
              ifConflict: await api_detect_conflict_flag(missing_index),
            };
            if (columnData.missingDetectFlag == true) {
              this.addCard(missingCard);
            }
          } else if (columnData.type == "numeric") {
            let missing_index: number[] = [];
            if (columnData.missingDetectFlag == true) {
              missing_index = await api_numericmissing_index(columnName);
            } else {
              missing_index = [];
            }
            const missingCard = {
              columnName: [columnName],
              columnType: [columnData.type],
              invalid_index: missing_index,
              relationClass: "Integrity",
              relationType: "Missing",
              ruleValue: {
                missingDetectFlag: columnData.missingDetectFlag,
                missingValueFlag: columnData.missingValueFlag,
                specialMissingValueList: columnData.specialMissingValueList,
              },
              example: columnData.missingValueFlag
                ? `The ${columnName} exists missing values.`
                : `The ${columnName} does not exist missing values.`,
              ifConflict: await api_detect_conflict_flag(missing_index),
            };
            if (columnData.missingDetectFlag == true) {
              this.addCard(missingCard);
            }
          }

          // Duplicate validation card
          let duplicate_index: number[] = [];
          if (columnData.duplicateDetectFlag == true) {
            duplicate_index = await api_duplicate_index(column_csv_Data);
          } else {
            duplicate_index = [];
          }
          const duplicateCard = {
            columnName: [columnName],
            columnType: [columnData.type],
            invalid_index: duplicate_index,
            relationClass: "Duplicate",
            relationType: "Duplicate",
            ruleValue: {
              duplicateDetectFlag: columnData.duplicateDetectFlag,
              duplicateFlag: columnData.duplicateFlag,
            },
            example: columnData.duplicateFlag
              ? `The ${columnName} exists duplicate values.`
              : `The ${columnName} does not exist duplicate values.`,
            ifConflict: await api_detect_conflict_flag(duplicate_index),
          };
          if (columnData.duplicateDetectFlag == true) {
            this.addCard(duplicateCard);
          }

          // Outlier
          if (columnData.outlierRange) {
            const outlier_index = await api_detect_outliers(columnName);
            const outlierCard = {
              columnName: [columnName],
              columnType: [columnData.type],
              invalid_index: outlier_index,
              relationClass: "Statistical",
              relationType: "Outlier",
              ruleValue: columnData.outlierRange,
              example: await api_generate_card_example([columnName], "Outlier"),
              ifConflict: await api_detect_conflict_flag(outlier_index),
            };
            this.addCard(outlierCard);
          }

          // Range
          if (columnData.range) {
            const range_index = await api_detect_numeric_range(columnName);
            for (const range of columnData.range) {
              const rangeCard = {
                columnName: [columnName],
                columnType: [columnData.type],
                invalid_index: range_index,
                relationClass: "Range",
                relationType: "Range",
                ruleValue: range,
                example: await api_generate_card_example([columnName], "Range"),
                ifConflict: await api_detect_conflict_flag(range_index),
              };
              this.addCard(rangeCard);
            }
          }

          // Sequence Rule
          if (columnData.sequenceRule && columnData.sequenceRule.length > 0) {
            this.sequenceRules[columnName] = columnData.sequenceRule;
            const sequence_invalid_pairs = await api_detect_sequence(
              columnName
            );
            const sequence_invalid_index = await api_invalid_pairs_to_indices(
              sequence_invalid_pairs
            );
            if (columnData.sequenceRule.length > 0) {
              const sequenceCard = {
                columnName: [columnName],
                columnType: [columnData.type],
                invalid_pairs: sequence_invalid_pairs,
                invalid_index: sequence_invalid_index,
                relationClass: "Sequence",
                relationType: "Sequence",
                example: await api_generate_card_example(
                  [columnName],
                  "Sequence"
                ),
                ruleValue: columnData.sequenceRule[0],
                ifConflict: await api_detect_conflict_flag(
                  sequence_invalid_index
                ),
              };
              this.addCard(sequenceCard);
            }
          }

          // Difference Difference
          if (
            columnData.difference &&
            Object.keys(columnData.difference).length > 0
          ) {
            const difference_invalid_pairs =
              await api_detect_absolute_difference(columnName);
            const difference_invalid_index = await api_invalid_pairs_to_indices(
              difference_invalid_pairs
            );
            const differenceCard = {
              columnName: [columnName],
              columnType: [columnData.type],
              invalid_pairs: difference_invalid_pairs,
              invalid_index: difference_invalid_index,
              relationClass: "Difference",
              relationType: "Difference",
              ruleValue: columnData.difference.difference,
              example: await api_generate_card_example(
                [columnName],
                "Difference"
              ),
              ifConflict: await api_detect_conflict_flag(
                difference_invalid_index
              ),
            };
            this.addCard(differenceCard);
          }
        }
      }

      // Handle multi-column validation rules
      if (data.conditionLogicColumnList) {
        for (const conditionLogicColumn of data.conditionLogicColumnList) {
          if (
            !conditionLogicColumn.conditionColumns ||
            !conditionLogicColumn.constraintColumns
          ) {
            console.warn(
              "conditionLogicColumn missing required column info:",
              conditionLogicColumn
            );
            continue;
          }
          const fullname =
            conditionLogicColumn.conditionColumns.join("+") +
            "+" +
            conditionLogicColumn.constraintColumns.join("+");
          if (
            conditionLogicColumn.columnType[
              conditionLogicColumn.conditionColumns[0]
            ] === "EqualityBased" &&
            conditionLogicColumn.columnType[
              conditionLogicColumn.constraintColumns[0]
            ] === "EqualityBased"
          ) {
            this.conditionRules[fullname] =
              conditionLogicColumn.conditionAndLogicList.map((item) => ({
                conditionValue:
                  item.conditionColumnValue[0][
                    conditionLogicColumn.conditionColumns[0]
                  ][0],
                constraintValue:
                  item.constraintColumnValue[0][
                    conditionLogicColumn.constraintColumns[0]
                  ],
              }));
          } else if (
            conditionLogicColumn.columnType[
              conditionLogicColumn.conditionColumns[0]
            ] === "EqualityBased" &&
            conditionLogicColumn.columnType[
              conditionLogicColumn.constraintColumns[0]
            ] === "RangeBased"
          ) {
            this.conditionRules[fullname] =
              conditionLogicColumn.conditionAndLogicList.map((item) => ({
                conditionValue:
                  item.conditionColumnValue[0][
                    conditionLogicColumn.conditionColumns[0]
                  ][0],
                constraintValue: {
                  start:
                    item.constraintColumnValue[0][
                      conditionLogicColumn.constraintColumns[0]
                    ].start,
                  end: item.constraintColumnValue[0][
                    conditionLogicColumn.constraintColumns[0]
                  ].end,
                  startInclusive:
                    item.constraintColumnValue[0][
                      conditionLogicColumn.constraintColumns[0]
                    ].startInclusive,
                  endInclusive:
                    item.constraintColumnValue[0][
                      conditionLogicColumn.constraintColumns[0]
                    ].endInclusive,
                },
              }));
          }
          const condition_logic_invalid_index =
            await api_detect_condition_logic_index(this.csvData, [
              ...conditionLogicColumn.conditionColumns,
              ...conditionLogicColumn.constraintColumns,
            ]);
          const conditionCard = {
            columnName: [
              ...conditionLogicColumn.conditionColumns,
              ...conditionLogicColumn.constraintColumns,
            ],
            columnType: [
              ...conditionLogicColumn.conditionColumns.map(
                (col) => data[col].type
              ),
              ...conditionLogicColumn.constraintColumns.map(
                (col) => data[col].type
              ),
            ],
            relationClass: "Logical and condition",
            relationType: "Logical and condition",
            invalid_index: condition_logic_invalid_index,
            constraintType: conditionLogicColumn.constraintColumns.map(
              (column) => conditionLogicColumn.columnType[column]
            ),
            ruleValue:
              this.processConditionLogicRuleValue(conditionLogicColumn),
            example: await api_generate_card_example(
              [
                ...conditionLogicColumn.conditionColumns,
                ...conditionLogicColumn.constraintColumns,
              ],
              "Logical and condition"
            ),
            ifConflict: await api_detect_conflict_flag(
              condition_logic_invalid_index
            ),
          };
          this.addCard(conditionCard);
        }
      }

      // Handle multipleConditionLogicColumnList, generate multiConditionRules (refactored for N dynamic condition columns)
      if (data.multipleConditionLogicColumnList) {
        for (const multipleCondition of data.multipleConditionLogicColumnList) {
          const fullname =
            multipleCondition.conditionColumns.join("+") +
            "+" +
            multipleCondition.constraintColumns.join("+");

          this.multiConditionRules[fullname] =
            this.buildMultipleConditionRuleEntries(multipleCondition);
        }
      }

      // Lookup
      if (data.lookupList) {
        for (const lookup of data.lookupList) {
          const lookup_invalid_index = await api_detect_lookup([
            lookup.parentColumnName,
            lookup.childColumnName,
          ]);

          // Save lookup rule for later use
          const lookupKey = `${lookup.parentColumnName}+${lookup.childColumnName}`;
          console.log("Storing lookup rule for key:", lookupKey);
          this.lookupRules[lookupKey] = lookup.lookupList;

          const lookupCard = {
            columnName: [lookup.parentColumnName, lookup.childColumnName],
            columnType: [
              data[lookup.parentColumnName].type,
              data[lookup.childColumnName].type,
            ],
            invalid_index: lookup_invalid_index,
            relationClass: "Mapping and cardinality",
            relationType: "Lookup",
            ruleValue: {
              lookupList: lookup.lookupList[0],
            },
            example: await api_generate_card_example(
              [lookup.parentColumnName, lookup.childColumnName],
              "Lookup"
            ),
            ifConflict: await api_detect_conflict_flag(lookup_invalid_index),
          };

          this.addCard(lookupCard);
        }
      }

      if (data.multiDifference) {
        for (const multiDifference of data.multiDifference) {
          const multiDifference_invalid_pairs =
            await api_detect_multi_difference(multiDifference.columns);
          const multiDifference_invalid_index =
            await api_invalid_pairs_to_indices(multiDifference_invalid_pairs);
          const multiDifferenceCard = {
            columnName: multiDifference.columns,
            columnType: [
              ...multiDifference.columns.map((col) => data[col].type),
            ],
            invalid_pairs: multiDifference_invalid_pairs,
            invalid_index: multiDifference_invalid_index,
            relationClass: "Difference",
            relationType: "MultiDifference",
            ruleValue: multiDifference.differenceDict,
            example: `The multiDifference of ${
              multiDifference.columns
            } needs to be in ${this.rangeFormat(
              multiDifference.differenceDict
            )}.`,
            ifConflict: await api_detect_conflict_flag(
              multiDifference_invalid_index
            ),
          };
          this.addCard(multiDifferenceCard);
        }
      }

      // Compare
      const compareRules = [
        ...(data.numericCompareList || []),
        ...(data.dateCompareList || []),
      ];
      for (const compareRule of compareRules) {
        const columns = [compareRule.column1, compareRule.column2];
        const columnTypes = columns.map((col) => data[col]?.type || "unknown");
        const isDateCompare = columnTypes.every((type) => type === "datetime");
        const invalid_index = isDateCompare
          ? await api_detect_compare_date(columns)
          : await api_detect_compare_numeric(columns);

        const compareCard = {
          columnName: columns,
          columnType: columnTypes,
          invalid_index,
          relationClass: "Comparison",
          relationType: "Compare",
          ruleValue: compareRule.compareRelation,
          example: await api_generate_card_example(columns, "Compare"),
          ifConflict: await api_detect_conflict_flag(invalid_index),
        };
        this.addCard(compareCard);
      }

      // Multiple Duplicate
      if (data.multipleDuplicateColumnsList) {
        for (const multipleDuplicate of data.multipleDuplicateColumnsList) {
          const multipleDuplicate_invalid_index =
            await api_detect_multiple_duplicate(multipleDuplicate);
          const multipleDuplicateCard = {
            columnName: multipleDuplicate,
            columnType: [...multipleDuplicate.map((col) => data[col].type)],
            invalid_index: multipleDuplicate_invalid_index,
            relationClass: "Duplicate",
            relationType: "MultipleDuplicate",
            ruleValue: data[multipleDuplicate[0]].duplicateFlag,
            example: `The combination of ${multipleDuplicate} cannot be duplicated.`,
            ifConflict: await api_detect_conflict_flag(
              multipleDuplicate_invalid_index
            ),
          };
          this.addCard(multipleDuplicateCard);
        }
      }

      if (
        data.multipleConditionLogicColumnList &&
        !Array.isArray(data.multipleConditionLogicColumnList[0])
      ) {
        for (const multipleCondition of data.multipleConditionLogicColumnList) {
          // Add safety check
          if (
            !multipleCondition.conditionColumns ||
            !multipleCondition.constraintColumns
          ) {
            console.warn(
              "multipleCondition missing required column info:",
              multipleCondition
            );
            continue;
          }

          const {
            invalid_indices: multipleCondition_invalid_index,
            formatted_rules: multipleCondition_formatted_rules,
          } = await api_detect_multiple_logic_condition([
            ...multipleCondition.conditionColumns,
            ...multipleCondition.constraintColumns,
          ]);

          const multipleConditionCard = {
            columnName: [
              ...multipleCondition.conditionColumns,
              ...multipleCondition.constraintColumns,
            ],
            columnType: [
              ...(multipleCondition.conditionColumns || []).map(
                (col) => data[col]?.type || "unknown"
              ),
              ...(multipleCondition.constraintColumns || []).map(
                (col) => data[col]?.type || "unknown"
              ),
            ],
            threeColumnRules: multipleCondition_formatted_rules,
            invalid_index: multipleCondition_invalid_index,
            relationClass: "Logical and condition",
            relationType: "MultipleCondition",
            constraintType: (multipleCondition.constraintColumns || []).map(
              (column) => multipleCondition.columnType?.[column] || "unknown"
            ),
            ruleValue: multipleCondition,
            example: await api_generate_card_example(
              [
                ...(multipleCondition.conditionColumns || []),
                ...(multipleCondition.constraintColumns || []),
              ],
              "Logical and condition"
            ),
            ifConflict: await api_detect_conflict_flag(
              multipleCondition_invalid_index
            ),
          };

          this.addCard(multipleConditionCard);
        }
      }

      this.setCardList();
      await this.restoreSelectedCard(selectedCardIdentity);
    },
    addCard(card: ValidationCard): void {
      // Do not add card if dataset has changed
      if (this.localDatasetLoadingId !== this.currentDatasetLoadingId) {
        return;
      }

      // Set animation delay index for new card
      const defaultOrder =
        Array.isArray(card.displayColumnOrder) &&
        card.displayColumnOrder.length === card.columnName.length
          ? [...card.displayColumnOrder]
          : [...card.columnName];
      const key = this.getCardOrderKey(card.columnName, card.relationType);
      const overrideOrder = this.columnOrderOverrides[key];
      const resolvedOrder =
        Array.isArray(overrideOrder) &&
        overrideOrder.length === card.columnName.length
          ? [...overrideOrder]
          : defaultOrder;

      const cardWithIndex = {
        ...card,
        displayColumnOrder: resolvedOrder,
        style: {
          "--card-index": this.validationCards.length,
        },
      };

      // Add to total card list
      this.validationCards.push(cardWithIndex);

      // If no column selected, or new card contains all selected columns, update display list
      if (
        this.selectedColumns.length === 0 ||
        this.selectedColumns.every((selectedCol) =>
          card.columnName.includes(selectedCol)
        )
      ) {
        this.setCardList();
      }

      // Emit event to notify parent component that validationCards updated
      this.$emit("validation-cards-updated", this.validationCards);
    },
    processConditionLogicRuleValue(conditionLogicColumn: any): any {
      // Process new conditionAndLogicList format
      if (
        conditionLogicColumn.conditionAndLogicList &&
        conditionLogicColumn.conditionAndLogicList.length > 0
      ) {
        const firstCondition = conditionLogicColumn.conditionAndLogicList[0];
        if (!firstCondition) return {};

        // Get names of condition and constraint columns
        const conditionColumnName = conditionLogicColumn.conditionColumns[0];
        const constraintColumnName = conditionLogicColumn.constraintColumns[0];

        // Extract values from new format
        const conditionValue =
          firstCondition.conditionColumnValue[0][conditionColumnName][0];
        const constraintValue =
          firstCondition.constraintColumnValue[0][constraintColumnName];

        // Return appropriate format based on constraint type
        if (
          conditionLogicColumn.columnType[constraintColumnName] === "RangeBased"
        ) {
          return {
            conditionValue: conditionValue,
            constraintValue: this.rangeFormat(constraintValue),
          };
        }

        if (
          conditionLogicColumn.columnType[constraintColumnName] ===
          "EqualityBased"
        ) {
          return {
            conditionValue: conditionValue,
            constraintValue: Array.isArray(constraintValue)
              ? constraintValue
              : [String(constraintValue)],
          };
        }

        return {
          conditionValue: conditionValue,
          constraintValue: constraintValue,
        };
      }
      return {};
    },
    buildMultipleConditionRuleEntries(multipleCondition: any): any[] {
      if (
        !multipleCondition ||
        !Array.isArray(multipleCondition.conditionAndLogicList)
      ) {
        return [];
      }

      const conditionColumns = multipleCondition.conditionColumns || [];
      const constraintColumns = multipleCondition.constraintColumns || [];
      const columnTypeMap = multipleCondition.columnType || {};

      const extractConstraintValue = (
        item: any,
        columnName: string,
        columnType: string,
        valueIndex: number
      ) => {
        const valueList = item?.constraintColumnValue || [];
        const directMatch =
          valueList?.[valueIndex]?.[columnName] ??
          valueList.find((entry: any) => entry[columnName])?.[columnName] ??
          null;

        if (columnType === "RangeBased") {
          const rangeValue = directMatch || {};
          return {
            start: rangeValue.start,
            end: rangeValue.end,
            startInclusive: rangeValue.startInclusive,
            endInclusive: rangeValue.endInclusive,
          };
        }
        if (Array.isArray(directMatch)) {
          return directMatch.map((value) => String(value));
        }
        return directMatch == null ? null : [String(directMatch)];
      };

      return multipleCondition.conditionAndLogicList.map(
        (item: any, entryIndex: number) => {
          const rule: Record<string, any> = {
            ruleIndex: entryIndex,
          };

          const conditionValueMap: Record<string, string[]> = {};
          conditionColumns.forEach((colName: string, index: number) => {
            const conditionKey = `conditionValue${index + 1}`;
            const directMatch =
              item?.conditionColumnValue?.[index]?.[colName] ??
              item?.conditionColumnValue?.find(
                (entry: any) => entry[colName]
              )?.[colName] ??
              [];
            const normalizedValues = Array.isArray(directMatch)
              ? directMatch.map((value) => String(value))
              : directMatch != null
              ? [String(directMatch)]
              : [];

            conditionValueMap[colName] = normalizedValues;
            rule[conditionKey] = normalizedValues[0] ?? "";
          });
          rule.conditionValueMap = conditionValueMap;

          if (constraintColumns.length > 0) {
            const constraintValueMap: Record<string, any> = {};
            constraintColumns.forEach((constraintName: string, idx: number) => {
              const constraintType =
                columnTypeMap?.[constraintName] || "EqualityBased";
              constraintValueMap[constraintName] = extractConstraintValue(
                item,
                constraintName,
                constraintType,
                idx
              );
            });

            rule.constraintValueMap = constraintValueMap;
            const primaryConstraintName = constraintColumns[0];
            rule.constraintValue =
              constraintValueMap[primaryConstraintName] ?? null;
          }

          return rule;
        }
      );
    },
    getNormalizedColumnKey(columns: string[] = []): string {
      return [...columns].sort().join("||");
    },
    getCurrentCardIdentity(): {
      relationType: string;
      columnName: string[];
    } | null {
      if (!this.chooseCard) {
        return null;
      }
      return {
        relationType: this.chooseCard.relationType,
        columnName: [...this.chooseCard.columnName],
      };
    },
    findMatchingCardByIdentity(identity: {
      relationType: string;
      columnName: string[];
    }): ValidationCard | null {
      return (
        this.validationCards.find(
          (card) =>
            card.relationType === identity.relationType &&
            this.areColumnsEqual(card.columnName, identity.columnName)
        ) || null
      );
    },
    async restoreSelectedCard(
      identity: { relationType: string; columnName: string[] } | null
    ): Promise<void> {
      if (!identity) {
        return;
      }

      const matchedCard = this.findMatchingCardByIdentity(identity);
      if (matchedCard) {
        await this.handleCardClick(matchedCard);
        return;
      }

      this.clearVisualization();
    },
    normalizeColumns(column: string | string[] | undefined): string[] {
      if (!column && column !== "") {
        return [];
      }
      return Array.isArray(column) ? column : [column];
    },
    areColumnsEqual(
      columnsA: string[] = [],
      columnsBInput: string | string[] = []
    ): boolean {
      const columnsB = this.normalizeColumns(columnsBInput);
      if (columnsA.length !== columnsB.length) {
        return false;
      }
      const sortedA = [...columnsA].sort();
      const sortedB = [...columnsB].sort();
      return sortedA.every((value, index) => value === sortedB[index]);
    },
    findCardIndexByRule(
      column: string | string[] | undefined,
      ruleType: string
    ): number {
      const targetColumns = this.normalizeColumns(column);
      if (targetColumns.length === 0) {
        return -1;
      }
      return this.validationCards.findIndex(
        (card) =>
          card.relationType === ruleType &&
          this.areColumnsEqual(card.columnName, targetColumns)
      );
    },
    hasMultipleConditionDefinition(columns: string[] = []): boolean {
      if (!columns || columns.length === 0) {
        return false;
      }
      const targetKey = this.getNormalizedColumnKey(columns);
      return Object.keys(this.multiConditionRules).some((fullname) => {
        const keyColumns = fullname.split("+");
        return this.getNormalizedColumnKey(keyColumns) === targetKey;
      });
    },
    resolveRuleType(
      column: string | string[] | undefined,
      incomingType: string
    ): string {
      if (incomingType !== "Logical and condition") {
        return incomingType;
      }
      const columnsArr = this.normalizeColumns(column);
      if (columnsArr.length === 0) {
        return incomingType;
      }

      const matchesExistingMultiCard = this.validationCards.some(
        (card) =>
          card.relationType === "MultipleCondition" &&
          this.areColumnsEqual(card.columnName, columnsArr)
      );

      const matchesDefinition = this.hasMultipleConditionDefinition(columnsArr);
      const appearsMultiple = columnsArr.length >= 3;

      if (matchesExistingMultiCard || matchesDefinition || appearsMultiple) {
        return "MultipleCondition";
      }

      return incomingType;
    },
    getTypeIcon(type: string): string {
      if (type.toLowerCase() === "multidifference") {
        return "/cardpanel_icon/difference.svg";
      } else if (type.toLowerCase() === "multipleduplicate") {
        return "/cardpanel_icon/duplicate.svg";
      } else {
        // Return icon path based on type
        return `/cardpanel_icon/${type.toLowerCase()}.svg`;
      }
    },
    async loadSpecificRuleCard(columnName, ruleType) {
      try {
        // Ensure columnName is array
        if (typeof columnName === "string") {
          columnName = [columnName];
        }
        // Get latest JSON data
        const jsonData = await api_get_new_finalValidation();

        // Clear ChartView and TableComponent effects
        this.clearVisualization();

        let newCard: ValidationCard = {
          columnName: [],
          columnType: [],
          relationClass: "",
          relationType: "",
          ruleValue: {},
          ifConflict: 0,
        };

        if (columnName.length === 1) {
          const columnData = jsonData[columnName[0]];
          const column_csv_Data = this.csvData.map((d) => d[columnName[0]]);

          // Create corresponding card based on rule type
          if (ruleType === "Type") {
            // Type validation card
            const typeCard = {
              columnName: columnName,
              columnType: [columnData.type],
              relationClass: "Type",
              relationType: "Type",
              ruleValue: columnData.type,
              example: `The type of ${columnName} is ${columnData.type}.`,
              ifConflict: 0,
            };
            newCard = typeCard;
            this.addCard(typeCard);
          } else if (ruleType === "Missing") {
            // Missing validation card
            if (columnData.type == "character") {
              let missing_index: number[] = [];
              if (columnData.missingDetectFlag == true) {
                missing_index = await api_charactermissing_index(columnName[0]);
              } else {
                missing_index = [];
              }
              const missingCard = {
                columnName: columnName,
                columnType: [columnData.type],
                invalid_index: missing_index,
                relationClass: "Integrity",
                relationType: "Missing",
                ruleValue: {
                  missingDetectFlag: columnData.missingDetectFlag,
                  missingValueFlag: columnData.missingValueFlag,
                  specialMissingValueList: columnData.specialMissingValueList,
                },
                example: columnData.missingValueFlag
                  ? `The ${columnName} exists missing values.`
                  : `The ${columnName} does not exist missing values.`,
                ifConflict: await api_detect_conflict_flag(missing_index),
              };
              newCard = missingCard;
              this.addCard(missingCard);
            } else if (columnData.type == "numeric") {
              let missing_index: number[] = [];
              if (columnData.missingDetectFlag == true) {
                missing_index = await api_numericmissing_index(columnName[0]);
              } else {
                missing_index = [];
              }
              const missingCard = {
                columnName: columnName,
                columnType: [columnData.type],
                invalid_index: missing_index,
                relationClass: "Integrity",
                relationType: "Missing",
                ruleValue: {
                  missingDetectFlag: columnData.missingDetectFlag,
                  missingValueFlag: columnData.missingValueFlag,
                  specialMissingValueList: columnData.specialMissingValueList,
                },
                example: columnData.missingValueFlag
                  ? `The ${columnName} exists missing values.`
                  : `The ${columnName} does not exist missing values.`,
                ifConflict: await api_detect_conflict_flag(missing_index),
              };
              newCard = missingCard;
              this.addCard(missingCard);
            }
          } else if (ruleType === "Duplicate") {
            // Duplicate validation card
            let duplicate_index: number[] = [];
            if (columnData.duplicateDetectFlag == true) {
              duplicate_index = await api_duplicate_index(column_csv_Data);
            } else {
              duplicate_index = [];
            }
            const duplicateCard = {
              columnName: columnName,
              columnType: [columnData.type],
              invalid_index: duplicate_index,
              relationClass: "Duplicate",
              relationType: "Duplicate",
              ruleValue: {
                duplicateDetectFlag: columnData.duplicateDetectFlag,
                duplicateFlag: columnData.duplicateFlag,
              },
              example: columnData.duplicateFlag
                ? `The ${columnName} exists duplicate values.`
                : `The ${columnName} does not exist duplicate values.`,
              ifConflict: await api_detect_conflict_flag(duplicate_index),
            };
            newCard = duplicateCard;
            this.addCard(duplicateCard);
          } else if (ruleType === "Outlier" && columnData.outlierFunction) {
            // Outlier validation card
            const outlier_index = await api_detect_outliers(columnName[0]);
            const outlierCard = {
              columnName: columnName,
              columnType: [columnData.type],
              invalid_index: outlier_index,
              relationClass: "Statistical",
              relationType: "Outlier",
              ruleValue: columnData.outlierFunction,
              example: await api_generate_card_example(columnName, "Outlier"),
              ifConflict: await api_detect_conflict_flag(outlier_index),
            };
            newCard = outlierCard;
            this.addCard(outlierCard);
          } else if (ruleType === "Distribution" && columnData.distribution) {
            // Distribution validation card
            const distributionCard = {
              columnName: columnName,
              columnType: [columnData.type],
              relationClass: "Statistical",
              relationType: "Distribution",
              ruleValue: columnData.distribution,
              ifConflict: 0,
            };
            newCard = distributionCard;
            this.addCard(distributionCard);
          } else if (ruleType === "Range" && columnData.range) {
            // Range validation card
            const range_index = await api_detect_numeric_range(columnName[0]);
            for (const range of columnData.range) {
              const rangeCard = {
                columnName: columnName,
                columnType: [columnData.type],
                invalid_index: range_index,
                relationClass: "Range",
                relationType: "Range",
                ruleValue: range,
                example: await api_generate_card_example(columnName, "Range"),
                ifConflict: await api_detect_conflict_flag(range_index),
              };
              newCard = rangeCard; // Save last Range card
              this.addCard(rangeCard);
            }
          } else if (ruleType === "Sequence" && columnData.sequenceRule) {
            // Sequence validation card
            this.sequenceRules[columnName] = columnData.sequenceRule;
            const sequence_invalid_pairs = await api_detect_sequence(
              columnName[0]
            );
            const sequence_invalid_index = await api_invalid_pairs_to_indices(
              sequence_invalid_pairs
            );
            if (columnData.sequenceRule.length > 0) {
              const sequenceCard = {
                columnName: columnName,
                columnType: [columnData.type],
                invalid_pairs: sequence_invalid_pairs,
                invalid_index: sequence_invalid_index,
                relationClass: "Sequence",
                relationType: "Sequence",
                ruleValue: columnData.sequenceRule[0],
                example: await api_generate_card_example(
                  columnName,
                  "Sequence"
                ),
                ifConflict: await api_detect_conflict_flag(
                  sequence_invalid_index
                ),
              };
              newCard = sequenceCard;
              this.addCard(sequenceCard);
            }
          } else if (
            (ruleType === "Difference" || ruleType === "relativeDifference") &&
            columnData.difference
          ) {
            // Difference Difference validation card
            if (ruleType === "Difference") {
              const difference_invalid_pairs =
                await api_detect_absolute_difference(columnName[0]);
              const difference_invalid_index =
                await api_invalid_pairs_to_indices(difference_invalid_pairs);
              const differenceCard = {
                columnName: columnName,
                columnType: [columnData.type],
                invalid_pairs: difference_invalid_pairs,
                invalid_index: difference_invalid_index,
                relationClass: "Difference",
                relationType: "Difference",
                ruleValue: columnData.difference.difference,
                example: await api_generate_card_example(
                  columnName,
                  "Difference"
                ),
                ifConflict: await api_detect_conflict_flag(
                  difference_invalid_index
                ),
              };
              newCard = differenceCard;
              this.addCard(differenceCard);
            } else if (ruleType === "relativeDifference") {
              const relative_difference_invalid_pairs =
                await api_detect_relative_difference(columnName[0]);
              const relative_difference_invalid_index =
                await api_invalid_pairs_to_indices(
                  relative_difference_invalid_pairs
                );
              const relative_differenceCard = {
                columnName: columnName,
                columnType: [columnData.type],
                invalid_pairs: relative_difference_invalid_pairs,
                invalid_index: relative_difference_invalid_index,
                relationClass: "Difference",
                relationType: "relativeDifference",
                ruleValue: columnData.difference.relativeDifference,
                ifConflict: await api_detect_conflict_flag(
                  relative_difference_invalid_index
                ),
              };
              newCard = relative_differenceCard;
              this.addCard(relative_differenceCard);
            }
          }
        } else if (columnName.length > 1) {
          // Multi-column rule processing - requires extra logic
          if (ruleType === "Logical and condition") {
            // Process conditional logic rules
            for (const conditionLogicColumn of jsonData.conditionLogicColumnList) {
              if (
                !conditionLogicColumn.conditionColumns ||
                !conditionLogicColumn.constraintColumns
              ) {
                console.warn(
                  "conditionLogicColumn missing required column info:",
                  conditionLogicColumn
                );
                continue;
              }
              // Check if related to current columns
              if (
                [
                  ...conditionLogicColumn.conditionColumns,
                  ...conditionLogicColumn.constraintColumns,
                ].every((item) => columnName.includes(item))
              ) {
                const fullname =
                  conditionLogicColumn.conditionColumns.join("+") +
                  "+" +
                  conditionLogicColumn.constraintColumns.join("+");

                if (
                  conditionLogicColumn.columnType[
                    conditionLogicColumn.conditionColumns[0]
                  ] === "EqualityBased" &&
                  conditionLogicColumn.columnType[
                    conditionLogicColumn.constraintColumns[0]
                  ] === "EqualityBased"
                ) {
                  this.conditionRules[fullname] =
                    conditionLogicColumn.conditionAndLogicList.map((item) => ({
                      conditionValue:
                        item.conditionColumnValue[0][
                          conditionLogicColumn.conditionColumns[0]
                        ][0],
                      constraintValue:
                        item.constraintColumnValue[0][
                          conditionLogicColumn.constraintColumns[0]
                        ],
                    }));
                } else if (
                  conditionLogicColumn.columnType[
                    conditionLogicColumn.conditionColumns[0]
                  ] === "EqualityBased" &&
                  conditionLogicColumn.columnType[
                    conditionLogicColumn.constraintColumns[0]
                  ] === "RangeBased"
                ) {
                  this.conditionRules[fullname] =
                    conditionLogicColumn.conditionAndLogicList.map((item) => ({
                      conditionValue:
                        item.conditionColumnValue[0][
                          conditionLogicColumn.conditionColumns[0]
                        ][0],
                      constraintValue: {
                        start:
                          item.constraintColumnValue[0][
                            conditionLogicColumn.constraintColumns[0]
                          ].start,
                        end: item.constraintColumnValue[0][
                          conditionLogicColumn.constraintColumns[0]
                        ].end,
                        startInclusive:
                          item.constraintColumnValue[0][
                            conditionLogicColumn.constraintColumns[0]
                          ].startInclusive,
                        endInclusive:
                          item.constraintColumnValue[0][
                            conditionLogicColumn.constraintColumns[0]
                          ].endInclusive,
                      },
                    }));
                }
                const condition_logic_invalid_index =
                  await api_detect_condition_logic_index(
                    this.csvData,
                    columnName
                  );

                const conditionCard = {
                  columnName: [
                    ...conditionLogicColumn.conditionColumns,
                    ...conditionLogicColumn.constraintColumns,
                  ],
                  columnType: [
                    ...conditionLogicColumn.conditionColumns.map(
                      (col) => jsonData[col].type
                    ),
                    ...conditionLogicColumn.constraintColumns.map(
                      (col) => jsonData[col].type
                    ),
                  ],
                  relationClass: "Logical and condition",
                  relationType: "Logical and condition",
                  invalid_index: condition_logic_invalid_index,
                  constraintType: conditionLogicColumn.constraintColumns.map(
                    (column) => conditionLogicColumn.columnType[column]
                  ),
                  ruleValue:
                    this.processConditionLogicRuleValue(conditionLogicColumn),
                  example: await api_generate_card_example(
                    [
                      ...conditionLogicColumn.conditionColumns,
                      ...conditionLogicColumn.constraintColumns,
                    ],
                    "Logical and condition"
                  ),
                  ifConflict: await api_detect_conflict_flag(
                    condition_logic_invalid_index
                  ),
                };

                newCard = conditionCard;
                this.addCard(conditionCard);
              }
            }
          } else if (
            ruleType === "MultipleCondition" &&
            jsonData.multipleConditionLogicColumnList
          ) {
            const targetKey = this.getNormalizedColumnKey(columnName);
            for (const multipleCondition of jsonData.multipleConditionLogicColumnList) {
              if (
                !multipleCondition.conditionColumns ||
                !multipleCondition.constraintColumns
              ) {
                continue;
              }

              const combinedColumns = [
                ...multipleCondition.conditionColumns,
                ...multipleCondition.constraintColumns,
              ];
              const candidateKey = this.getNormalizedColumnKey(combinedColumns);
              if (candidateKey !== targetKey) {
                continue;
              }

              const fullname =
                multipleCondition.conditionColumns.join("+") +
                "+" +
                multipleCondition.constraintColumns.join("+");
              this.multiConditionRules[fullname] =
                this.buildMultipleConditionRuleEntries(multipleCondition);

              const {
                invalid_indices: multipleCondition_invalid_index,
                formatted_rules: multipleCondition_formatted_rules,
              } = await api_detect_multiple_logic_condition(combinedColumns);

              const multipleConditionCard = {
                columnName: combinedColumns,
                columnType: [
                  ...(multipleCondition.conditionColumns || []).map(
                    (col) => jsonData[col]?.type || "unknown"
                  ),
                  ...(multipleCondition.constraintColumns || []).map(
                    (col) => jsonData[col]?.type || "unknown"
                  ),
                ],
                threeColumnRules: multipleCondition_formatted_rules,
                invalid_index: multipleCondition_invalid_index,
                relationClass: "Logical and condition",
                relationType: "MultipleCondition",
                constraintType: (multipleCondition.constraintColumns || []).map(
                  (column) =>
                    multipleCondition.columnType?.[column] || "unknown"
                ),
                ruleValue: multipleCondition,
                example: await api_generate_card_example(
                  combinedColumns,
                  "Logical and condition"
                ),
                ifConflict: await api_detect_conflict_flag(
                  multipleCondition_invalid_index
                ),
              };

              newCard = multipleConditionCard;
              this.addCard(multipleConditionCard);
              break;
            }
          } else if (
            ruleType === "MultiDifference" &&
            jsonData.multiDifference
          ) {
            // Handle multi difference rule
            for (const multiDifference of jsonData.multiDifference) {
              // Check if includes current column
              if (multiDifference.columns.includes(columnName)) {
                const multiDifference_invalid_pairs =
                  await api_detect_multi_difference(multiDifference.columns);
                const multiDifference_invalid_index =
                  await api_invalid_pairs_to_indices(
                    multiDifference_invalid_pairs
                  );
                const multiDifferenceCard = {
                  columnName: multiDifference.columns,
                  columnType: [
                    ...multiDifference.columns.map((col) => jsonData[col].type),
                  ],
                  invalid_pairs: multiDifference_invalid_pairs,
                  invalid_index: multiDifference_invalid_index,
                  relationClass: "Difference",
                  relationType: "MultiDifference",
                  ruleValue: multiDifference.difference_range,
                  example: `The multiDifference of ${
                    multiDifference.columns
                  } needs to be in ${this.rangeFormat(
                    multiDifference.differenceDict
                  )}.`,
                  ifConflict: await api_detect_conflict_flag(
                    multiDifference_invalid_index
                  ),
                };

                newCard = multiDifferenceCard;
                this.addCard(multiDifferenceCard);
              }
            }
          } else if (ruleType === "Compare") {
            const compareRules = [
              ...(jsonData.numericCompareList || []),
              ...(jsonData.dateCompareList || []),
            ];
            for (const compareRule of compareRules) {
              if (
                compareRule.column1 === columnName[0] ||
                compareRule.column2 === columnName[0]
              ) {
                const columns = [compareRule.column1, compareRule.column2];
                const columnTypes = columns.map(
                  (col) => jsonData[col]?.type || "unknown"
                );
                const isDateCompare = columnTypes.every(
                  (type) => type === "datetime"
                );
                const invalid_index = isDateCompare
                  ? await api_detect_compare_date(columns)
                  : await api_detect_compare_numeric(columns);

                const compareCard = {
                  columnName: columns,
                  columnType: columnTypes,
                  invalid_index,
                  relationClass: "Comparison",
                  relationType: "Compare",
                  ruleValue: compareRule.compareRelation,
                  example: `The value of ${compareRule.column1} needs to be ${compareRule.compareRelation} than ${compareRule.column2}.`,
                  ifConflict: await api_detect_conflict_flag(invalid_index),
                };

                newCard = compareCard;
                this.addCard(compareCard);
              }
            }
          } else if (ruleType === "Lookup" && jsonData.lookupList) {
            for (const lookup of jsonData.lookupList) {
              // Check if related to current lookup rule
              if (
                (lookup.parentColumnName === columnName[0] &&
                  lookup.childColumnName === columnName[1]) ||
                (lookup.parentColumnName === columnName[1] &&
                  lookup.childColumnName === columnName[0])
              ) {
                const lookup_invalid_index = await api_detect_lookup([
                  lookup.parentColumnName,
                  lookup.childColumnName,
                ]);

                // Save lookup rule for later use
                const lookupKey = `${lookup.parentColumnName}+${lookup.childColumnName}`;
                this.lookupRules[lookupKey] = lookup.lookupList;

                // Set available parent value list
                this.availableParentValues = lookup.lookupList.map(
                  (item) => item.parentValue
                );

                const lookupCard = {
                  columnName: [lookup.parentColumnName, lookup.childColumnName],
                  columnType: [
                    jsonData[lookup.parentColumnName].type,
                    jsonData[lookup.childColumnName].type,
                  ],
                  invalid_index: lookup_invalid_index,
                  relationClass: "Mapping and cardinality",
                  relationType: "Lookup",
                  ruleValue: {
                    parentColumnName: lookup.parentColumnName,
                    childColumnName: lookup.childColumnName,
                    lookupList: lookup.lookupList[0],
                  },
                  example: await api_generate_card_example(
                    [lookup.parentColumnName, lookup.childColumnName],
                    "Lookup"
                  ),
                  ifConflict: await api_detect_conflict_flag(
                    lookup_invalid_index
                  ),
                };

                newCard = lookupCard;
                this.addCard(lookupCard);
              }
            }
          }
        }
        if (newCard) {
          // Wait for DOM update then simulate click
          this.$nextTick(() => {
            // Find corresponding card and simulate click
            const targetColumns = newCard.columnName;
            const cardIndex = this.filterCards.findIndex(
              (card) =>
                card.relationType === newCard.relationType &&
                this.areColumnsEqual(card.columnName, targetColumns)
            );

            if (cardIndex !== -1) {
              // Prepare card data to handle click event
              const card = this.filterCards[cardIndex];

              // Handle card click event
              this.handleCardClick(card);
            }
          });
        }
      } catch (error) {
        // console.error("Failed to add card", error);
      }
    },
    clearVisualization() {
      // Trigger event to notify parent to clear ChartView
      this.$emit("clear-visualization");

      // Clear highlight effects
      this.$emit("card-clicked", [], [], [], "", [], [], [], []);

      this.chooseCard = null;
    },
    showUpdateMessage(columnName, ruleType) {
      const message = document.createElement("div");
      message.textContent = `The ${ruleType} card of ${columnName} has been updated`;
      message.style.cssText = `
        position: absolute;
        top: 30%;
        left: 30%;
        transform: translate(-50%, -50%);
        color: #7a94a8;
        padding: 20px 30px;
        border-radius: 8px;
        z-index: 1000;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
      `;

      // Find ChartView component and append message
      const chartView = document.querySelector(".chart-view") || document.body;
      (chartView as HTMLElement).appendChild(message);

      // Fade in effect
      setTimeout(() => {
        message.style.opacity = "1";
      }, 100);

      // Fade out and remove after 3 seconds
      setTimeout(() => {
        message.style.opacity = "0";
        setTimeout(() => {
          (chartView as HTMLElement).removeChild(message);
        }, 300);
      }, 3000);
    },
    // Handle parent value selection change
    updateChildValues() {
      if (!this.chooseCard || this.chooseCard.relationType !== "Lookup") {
        return;
      }

      const lookupKey = `${this.chooseCard.columnName[0]}+${this.chooseCard.columnName[1]}`;

      // Get all unique values for child column
      const childColumnName = this.chooseCard.columnName[1];
      this.allPossibleChildValues = [
        ...new Set(this.csvData.map((row) => String(row[childColumnName]))),
      ].filter((value) => value && value.trim() !== "");

      const lookupList = this.lookupRules[lookupKey];

      // Find corresponding parent record
      const parentRecord = lookupList.find(
        (item) => item.parentValue === this.selectedParentValue
      );

      // Set selected child values
      this.selectedChildValues = parentRecord
        ? parentRecord.childValueList
        : [];
    },
    // Handle matrix cell click event
    handleMatrixCellClicked(event: CustomEvent) {
      const { category1, category2, isRightClick } = event.detail;

      if (
        this.chooseCard &&
        this.chooseCard.relationType === "Sequence" &&
        category1
      ) {
        if (isRightClick) {
          ElMessageBox.confirm(
            `There are sequence rules that can be updated, do you want to apply these updates?`,
            "rules update confirmation",
            {
              confirmButtonText: "confirm",
              cancelButtonText: "cancel",
              type: "warning",
            }
          ).then(() => {
            try {
              // Toggle validity: add missing pair (make valid) or remove existing pair (make invalid)
              this.selectedSequenceValue = category1;
              this.updateAllowedNext();

              const normalizedCategory2 = String(category2).toLowerCase();
              const alreadyAllowed = this.selectedAllowedNext.some(
                (value) => value.toLowerCase() === normalizedCategory2
              );

              if (alreadyAllowed) {
                this.selectedAllowedNext = this.selectedAllowedNext.filter(
                  (value) => value.toLowerCase() !== normalizedCategory2
                );
              } else {
                this.selectedAllowedNext = [
                  ...this.selectedAllowedNext,
                  category2,
                ];
              }

              this.allowedNext = [...this.selectedAllowedNext];
              this.syncToBackend();
              ElMessage({
                type: "success",
                message: "rules update success",
              });
            } catch (error) {
              ElMessage.error("rules update failed: " + error);
            }
          });
        } else {
          this.selectedSequenceValue = category1;
          this.updateAllowedNext();
        }
      }
    },
    // Handle condition area click event
    handleConditionAreaClicked(event: CustomEvent) {
      const { conditionValue, constraintValue, relationType, isRightClick } =
        event.detail;

      if (isRightClick) {
        if (relationType == "Logical and condition") {
          ElMessageBox.confirm(
            `There are Logical and condition rules that can be updated, do you want to apply these updates?`,
            "rules update confirmation",
            {
              confirmButtonText: "confirm",
              cancelButtonText: "cancel",
              type: "warning",
            }
          ).then(() => {
            try {
              this.selectedConditionValue = conditionValue;
              this.updateConstraintValue();
              this.constraintValue_Equality =
                this.constraintValue_Equality.filter(
                  (value) =>
                    value.toLowerCase() !== constraintValue.toLowerCase()
                );
              // Immediately sync to backend
              this.syncToBackend();
              ElMessage({
                type: "success",
                message: "rules update success",
              });
            } catch (error) {
              ElMessage.error("rules update failed: " + error);
            }
          });
        } else if (relationType == "Lookup") {
          ElMessageBox.confirm(
            `There are Lookup rules that can be updated, do you want to apply these updates?`,
            "rules update confirmation",
            {
              confirmButtonText: "confirm",
              cancelButtonText: "cancel",
              type: "warning",
            }
          ).then(() => {
            try {
              this.selectedParentValue = conditionValue;
              this.updateChildValues();

              const normalizedConstraint =
                String(constraintValue).toLowerCase();
              const alreadyAllowed = this.selectedChildValues.some(
                (value) => value.toLowerCase() === normalizedConstraint
              );

              // Toggle: if already allowed, remove; otherwise add to allow this pair
              if (alreadyAllowed) {
                this.selectedChildValues = this.selectedChildValues.filter(
                  (value) => value.toLowerCase() !== normalizedConstraint
                );
              } else {
                this.selectedChildValues = [
                  ...this.selectedChildValues,
                  constraintValue,
                ];
              }
              // Immediately sync to backend
              this.syncToBackend();
              ElMessage({
                type: "success",
                message: "rules update success",
              });
            } catch (error) {
              ElMessage.error("rules update failed: " + error);
            }
          });
        }
      } else {
        if (relationType == "Logical and condition") {
          // Only update if currently selected card is Logical and condition type
          if (
            this.chooseCard &&
            this.chooseCard.relationType === "Logical and condition" &&
            conditionValue
          ) {
            // Update selected condition value
            this.selectedConditionValue = conditionValue;
            // Update constraint value display
            this.updateConstraintValue();
          }
        } else if (relationType == "Lookup") {
          if (
            this.chooseCard &&
            this.chooseCard.relationType === "Lookup" &&
            conditionValue
          ) {
            // Update selected condition value
            this.selectedParentValue = conditionValue;
            // Update constraint value display
            this.updateChildValues();
          }
        }
      }
    },
    handleSpecialMissingValuesChange(values) {
      if (!this.chooseCard || !this.chooseCard.columnType) return;

      // If column type is numeric, convert entered special missing values to numbers
      if (this.chooseCard.columnType[0] === "numeric") {
        // Get last value from original list (assuming it is the newly added one)
        const lastValue = values[values.length - 1];

        // Try converting new value to number
        const numValue = Number(lastValue);

        // If valid number, replace last element
        if (!isNaN(numValue)) {
          // Create new array, keep existing values, only convert newly added value
          const newList = [...values];
          newList[newList.length - 1] = numValue;
          this.chooseCard.ruleValue.specialMissingValueList = newList;
        }
      }
      // If character type, keep string format, no extra processing needed
    },
    async handleDeleteCard(card: ValidationCard) {
      try {
        // Show confirmation dialog
        await ElMessageBox.confirm(
          `delete ${card.columnName.join(", ")} ${card.relationClass} rule?`,
          "delete confirmation",
          {
            confirmButtonText: "confirm",
            cancelButtonText: "cancel",
            type: "warning",
          }
        );

        // Remove from card list
        const cardIndex = this.validationCards.findIndex(
          (c) =>
            c.columnName.join("+") === card.columnName.join("+") &&
            c.relationType === card.relationType
        );

        if (cardIndex !== -1) {
          this.validationCards.splice(cardIndex, 1);
          this.handleRuleMutationSideEffects();
        }

        // Clear visualization effects
        this.clearVisualization();

        // Show success message
        ElMessage({
          type: "success",
          message: "rule deleted successfully",
        });
      } catch (error) {
        if (error !== "cancel") {
          ElMessage.error("delete rule failed");
        }
      }
    },
    async handleCreateRuleSubmit(data: {
      type: string;
      condition: string;
      columns: string[];
      parameters: any;
    }) {
      console.log("Create rule submitted:", data);
      this.showCreateRuleModal = false;
      const resolvedType = this.resolveRuleType(data.columns, data.type);
      try {
        await api_create_rule(data.type, data.columns, data.parameters);
        ElMessage.success(`Rule ${data.type} created successfully`);

        // Reload the specific rule card to update UI
        await this.loadSpecificRuleCard(data.columns, resolvedType);
        this.handleRuleMutationSideEffects();
      } catch (error) {
        console.error("Failed to create rule:", error);
        ElMessage.error("Failed to create rule");
      }
    },
    /**
     * New method: Get rule type name for display
     * Convert backend rule type to user-friendly display name
     */
    getDisplayRuleType(ruleType: string): string {
      const ruleTypeMap: { [key: string]: string } = {
        Lookup: "Mapping and cardinality",
        lookup: "Mapping and cardinality",
        "Logical and condition": "Logical and condition",
        MultipleCondition: "Logical and condition",
        Sequence: "Sequence",
        Missing: "Missing",
        Duplicate: "Duplicate",
        Type: "Type",
        Range: "Range",
        Outlier: "Outlier",
        Distribution: "Distribution",
        Compare: "Compare",
        Difference: "Difference",
        relativeDifference: "Relative Difference",
        MultiDifference: "Multi Difference",
        MultipleDuplicate: "Multiple Duplicate",
      };

      // Return mapped display name, or original name if not found
      return ruleTypeMap[ruleType] || ruleType;
    },
  },
  mounted(): void {
    if (this.chooseCard?.relationType === "Lookup") {
      const childColumnName = this.chooseCard.columnName[1];
      this.allPossibleChildValues = [
        ...new Set(this.csvData.map((row) => String(row[childColumnName]))),
      ].filter((value) => value && value.trim() !== "");
    }
    // Listen for matrix click events to update Sequence card selected value
    window.addEventListener(
      "matrix-cell-clicked",
      this.handleMatrixCellClicked
    );
    // Add listener for condition area click events
    window.addEventListener(
      "condition-area-clicked",
      this.handleConditionAreaClicked
    );
  },
  beforeUnmount() {
    // Remove event listeners
    window.removeEventListener(
      "matrix-cell-clicked",
      this.handleMatrixCellClicked
    );
    window.removeEventListener(
      "condition-area-clicked",
      this.handleConditionAreaClicked
    );
  },
});
</script>

<style scoped>
.difference-parameter-name {
  width: 6vw !important; /* Increased to 8vw for enough space */
  margin-left: 0.5vh;
  margin-right: 0.5vw !important;
  flex-shrink: 0;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: bold;
  font-size: 1.6vh;
  color: #42424b;
  display: flex;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
  gap: 0.5vh;
}

.difference-range {
  width: 18vw !important; /* Increase total width */
  display: flex;
  align-items: center;
  gap: 0.3vw;
  margin-left: 0vh;
}

.difference-range .range-input {
  width: 3.2vw !important; /* Increase input box width */
  height: 2.7vh;
  flex-shrink: 0;
}

.difference-range .range-input :deep(.el-input__wrapper) {
  height: 2.7vh;
}

.difference-range .range-input :deep(.el-input__inner) {
  height: 2.4vh !important;
  line-height: 2.4vh !important;
  font-size: 1.4vh;
  font-family: Roboto;
  color: black;
  text-align: center;
  box-sizing: border-box !important;
}

.difference-range .range-operator {
  width: 2.2vw !important; /* Restore normal operator width */
  height: 2.7vh;
  flex-shrink: 0;
}

.difference-range .range-operator :deep(.el-select__wrapper) {
  height: 2.7vh;
  padding: 0.3vh 0.2vh;
}

.difference-range .range-operator :deep(.el-select__placeholder),
.difference-range .range-operator :deep(.el-input__inner) {
  font-size: 1.4vh;
  font-family: Roboto;
  color: black;
  text-align: center;
  line-height: 2.4vh;
}

.difference-range .range-separator {
  width: 5.5vw !important; /* Increase middle label width */
  font-size: 1.4vh;
  font-family: Roboto;
  font-weight: 500;
  color: #42424b;
  text-align: center;
  line-height: 2.4vh;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
  background-color: #f8fafc;
  border-radius: 0.3vh;
  padding: 0.2vh 0.3vh;
  border: 1px solid #e5e7eb;
}

/* Overwrite potentially conflicting generic styles */
.parameter-name {
  font-weight: bold;
  width: 5vw; /* Keep original width for other types */
  font-size: 1.6vh;
  color: #42424b;
  margin-left: 0vh;
  margin-right: 1vw;
  flex-shrink: 0;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
  gap: 0.5vh;
}

/* Ensure Difference type is not overwritten by generic styles */
.difference-parameter-name {
  width: 6vw !important; /* Important: ensure not overwritten */
  margin-right: 0.5vw !important; /* Important: ensure not overwritten */
}

/* Ensure regular differenceRange does not affect difference-range */
.differenceRange:not(.difference-range) {
  width: 18.5vw;
  display: flex;
  align-items: center;
  gap: 0.3vw;
  margin-left: 0vh;
}

/* Regular range-input style (non-difference type) */
.differenceRange:not(.difference-range) .range-input {
  width: 3.3vw;
  height: 2.7vh;
  flex-shrink: 0;
}

/* Regular range-operator style (non-difference type) */
.differenceRange:not(.difference-range) .range-operator {
  width: 2.2vw;
  height: 2.7vh;
  flex-shrink: 0;
}

/* Regular range-separator style (non-difference type) */
.differenceRange:not(.difference-range) .range-separator {
  width: 6vw;
  font-size: 1.4vh;
  font-family: Roboto;
  font-weight: 500;
  color: #42424b;
  text-align: center;
  line-height: 2.4vh;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
  background-color: #f8fafc;
  border-radius: 0.3vh;
  padding: 0.2vh 0.3vh;
  border: 1px solid #e5e7eb;
}

.parameter-name-lookup {
  font-weight: bold;
  width: 100%;
  font-size: 1.6vh;
  color: #42424b;
  padding-right: 1vw;
  display: flex;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
}

.lookup-label {
  width: 5vw; /* Fixed width for label, including arrow position */
  margin-left: 0.5vh; /* Maintain spacing with arrow */
  flex-shrink: 0; /* Prevent shrinking */
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lookup-select {
  width: 18.5vw; /* Set select box width to align right with submit button */
  flex-shrink: 0; /* Prevent shrinking */
}

.lookup-select :deep(.el-select__wrapper) {
  height: 2.7vh;
  padding: 0.3vh 0.5vh 0.3vh 0.3vh;
}

.lookup-select :deep(.el-select__placeholder) {
  color: black;
  font-size: 1.4vh;
  font-family: Roboto;
  font-style: normal;
  line-height: 1.8vh;
  margin-top: 0vh;
}

.lookup-select :deep(.el-select__placeholder span) {
  background-color: #c7efed;
  border-radius: 0.46vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
  display: inline-block;
}

.lookup-select :deep(.el-select__selection.is-near) {
  margin-left: 0;
}

.lookup-select :deep(.el-tag.el-tag--info) {
  --el-tag-text-color: black;
  --el-tag-bg-color: #c7efed;
  --el-tag-border-color: #4570b6;
  --el-tag-hover-color: #c7efed;
  --el-tag-font-size: 1.4vh;
}

.lookup-select :deep(.el-tag .el-tag__close) {
  margin-left: 0vh;
}

.lookup-select :deep(.el-select__selected-item .el-tag) {
  height: 2.4vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
}

/* === RangeBased Style Adjustments === */
.differenceRange {
  width: 18.5vw; /* Total width consistent with lookup-select */
  display: flex;
  align-items: center;
  gap: 0.3vw; /* Unified element spacing */
  margin-left: 0vh; /* Left margin consistent with lookup-select */
}

/* Numeric Input Style */
.range-input {
  width: 3.3vw; /* Fixed width for numeric input */
  height: 2.7vh;
  flex-shrink: 0; /* Prevent shrinking */
}

.range-input :deep(.el-input__wrapper) {
  height: 2.7vh;
}

.range-input :deep(.el-input__inner) {
  height: 2.4vh !important; /* Consistent height with middle label and operator box */
  line-height: 2.4vh !important;
  font-size: 1.4vh;
  font-family: Roboto;
  color: black;
  text-align: center; /* Center align number */
  box-sizing: border-box !important;
}

/* Operator Select Style */
.range-operator {
  width: 2.2vw; /* Fixed width for operator */
  height: 2.7vh;
  flex-shrink: 0; /* Prevent shrinking */
}

.range-operator :deep(.el-select__wrapper) {
  height: 2.7vh;
  padding: 0.3vh 0.2vh;
}

.range-operator :deep(.el-select__placeholder),
.range-operator :deep(.el-input__inner) {
  font-size: 1.4vh;
  font-family: Roboto;
  color: black;
  text-align: center; /* Center align operator */
  line-height: 2.4vh;
}

/* Middle Label Style */
.range-separator {
  width: 6vw; /* Fixed width for middle label */
  font-size: 1.4vh;
  font-family: Roboto;
  font-weight: 500;
  color: #42424b;
  text-align: center;
  line-height: 2.4vh;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0; /* Prevent shrinking */
  background-color: #f8fafc;
  border-radius: 0.3vh;
  padding: 0.2vh 0.3vh;
  border: 1px solid #e5e7eb;
}

/* RangeBased Parameter Name Style Adjustment */
.parameter-name {
  font-weight: bold;
  width: 5vw; /* Fixed width consistent with lookup-label */
  font-size: 1.6vh;
  color: #42424b;
  margin-left: 0vh; /* Maintain spacing with arrow */
  margin-right: 1vw; /* Spacing with select box */
  flex-shrink: 0; /* Prevent shrinking */
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
  gap: 0.5vh;
}

/* MultipleCondition RangeBased Constraint Label Style */
.multiple-condition-label-constraint {
  width: 5vw; /* Consistent with other labels */
  margin-left: 0.5vh;
  flex-shrink: 0;
  font-weight: bold;
  font-size: 1.6vh;
  color: #42424b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  text-align: left;
  display: flex;
  align-items: center;
}

/* Ensure RangeBased consistency across different contexts */
.value-row .differenceRange,
.value-row-2 .differenceRange {
  margin-left: 0; /* Reset left margin in value-row, as parameter-name handles alignment */
}

/* RangeBased layout adjustment in Logical and condition */
.value-row-2 .parameter-name {
  width: 5vw;
  margin-left: 0vh;
  margin-right: 1.25vw; /* Spacing with select box */
}

/* RangeBased layout adjustment in MultipleCondition */
.multiple-condition-container .parameter-name {
  width: 5vw;
  margin-right: 1vw;
}

.multiple-condition-container .differenceRange {
  width: 18.5vw; /* Maintain consistent total width */
  margin-left: 0;
}

/* Range Operator Dropdown Item Style */
.range-operator :deep(.el-select-dropdown__item) {
  font-size: 1.4vh !important;
  font-family: Roboto;
  text-align: center;
  padding: 0.5vh 0.3vh;
}

/* Hover Effect */
.range-operator:hover :deep(.el-select__wrapper),
.range-input:hover :deep(.el-input__wrapper) {
  border-color: #4570b6;
}

/* Focus Effect */
.range-operator :deep(.el-select__wrapper.is-focused),
.range-input :deep(.el-input__wrapper.is-focus) {
  border-color: #4570b6;
  box-shadow: 0 0 0 2px rgba(69, 112, 182, 0.1);
}

/* MultipleCondition Container Style */
.multiple-condition-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1vh; /* Row gap */
  margin-top: 3vh; /* Consistent with other setting panel items */
  margin-left: 1vw; /* Consistent with other setting panel items */
}

/* MultipleCondition Row Style */
.multiple-condition-row {
  font-weight: bold;
  width: 100%;
  font-size: 1.6vh;
  color: #42424b;
  padding-right: 1vw;
  display: flex;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
  gap: 1vw; /* Column gap */
  margin-left: -1vw; /* Offset container left margin to align arrow */
  margin-bottom: 1vh; /* Add bottom margin, consistent with other setting panel items */
}

/* MultipleCondition Single Item Style */
.multiple-condition-item {
  display: flex;
  align-items: center;
  width: 11.5vw; /* Fixed width for each item, ensuring two items fit in one row */
  min-width: 11.5vw;
  flex-shrink: 0; /* Prevent shrinking */
}

/* Placeholder Item - Invisible, only takes up space */
.multiple-condition-item.placeholder-item {
  visibility: hidden;
}

/* Row with single item, using more compatible selector */
.multiple-condition-row .multiple-condition-item:only-child {
  width: 24vw; /* Single item takes up more width */
}

/* Ensure placeholder does not trigger only-child style */
.multiple-condition-row .multiple-condition-item:only-child.placeholder-item {
  width: 11.5vw;
}

.multiple-condition-row:last-child {
  margin-bottom: 0;
}

/* MultipleCondition Label Style */
.multiple-condition-label {
  width: 5vw; /* Label width */
  margin-left: 0.5vh; /* Spacing with arrow */
  margin-right: 0vw; /* Spacing with select box */
  flex-shrink: 0; /* Prevent shrinking */
  font-weight: bold;
  font-size: 1.6vh;
  color: #42424b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  text-align: left;
  display: flex;
  align-items: center;
}

/* Different style for label in single item row */
.multiple-condition-row
  .multiple-condition-item:only-child
  .multiple-condition-label {
  width: 5vw; /* Larger label width for single item */
}

/* MultipleCondition Select Box Style - Remove font related properties */
.multiple-condition-select {
  width: 6vw; /* Select box width to fit two column layout */
  flex-shrink: 0; /* Prevent shrinking */
}

/* Different style for select box in single item row */
.multiple-condition-row
  .multiple-condition-item:only-child
  .multiple-condition-select {
  width: 18.5vw; /* Larger select box width for single item */
}

/* MultipleCondition Select Box Internal Style */
.multiple-condition-select :deep(.el-select__wrapper) {
  height: 2.7vh;
  padding: 0.3vh 0.5vh 0.3vh 0.3vh;
}

.multiple-condition-select :deep(.el-select__placeholder) {
  color: black;
  font-size: 1.4vh;
  font-family: Roboto;
  font-style: normal;
  line-height: 1.8vh;
  margin-top: 0vh;
}

.multiple-condition-select :deep(.el-select__placeholder span) {
  background-color: #c7efed;
  border-radius: 0.46vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
  display: inline-block;
}

.multiple-condition-select :deep(.el-select__selection.is-near) {
  margin-left: 0;
}

.multiple-condition-select :deep(.el-tag.el-tag--info) {
  --el-tag-text-color: black;
  --el-tag-bg-color: #c7efed;
  --el-tag-border-color: #4570b6;
  --el-tag-hover-color: #c7efed;
  --el-tag-font-size: 1.4vh;
}

.multiple-condition-select :deep(.el-tag .el-tag__close) {
  margin-left: 0vh;
}

.multiple-condition-select :deep(.el-select__selected-item .el-tag) {
  height: 2.4vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
}

.card-container {
  width: 100%;
  height: 100%;
  background-color: #eff2fc;
  z-index: 10;
  position: relative;
}

.block-2 {
  height: 21.75vh;
  display: flex;
  flex-direction: column; /* Revert to vertical column layout */
  padding: 1vh;
  margin-top: 1vh;
  margin-bottom: 1vh;
  border-radius: 1vh;
  position: relative;
}

.info-row {
  display: flex;
  justify-content: flex-start;
  margin-top: 0.5vh;
  margin-left: 1vw;
  height: 2.7vh;
}

.type-row {
  display: flex;
  justify-content: flex-start;
  margin-top: 1vh;
  margin-left: 1vw;
  height: 2.7vh;
}

.paramater-row {
  display: flex;
  justify-content: flex-start;
  margin-top: 1vh;
  margin-left: 1vw;
  position: relative;
  align-items: center; /* Ensure all elements in row are vertically centered */
  height: 2.7vh;
}

.value-row {
  display: flex;
  justify-content: flex-start;
  margin-top: 1vh;
  margin-left: 1vw;
  position: relative;
  align-items: center; /* Ensure all elements in row are vertically centered */
  height: 2.7vh;
}

.value-row-2 {
  display: flex;
  justify-content: flex-start;
  margin-top: 1vh;
  margin-left: 1vw;
  position: relative;
  align-items: center;
  height: 2.7vh;
}

.info-group {
  display: flex;
  align-items: center;
}

.info-group > *:nth-child(1) {
  margin-right: 1.8vw;
}

.info-group > *:nth-child(n + 2) {
  margin-right: 1vw;
}

.info-group > *:last-child {
  margin-right: 0;
}

.info-group-2 {
  display: flex;
  align-items: center;
  gap: 1vw;
}

.label {
  font-size: 1.6vh;
  font-weight: 900;
  font-family: Roboto;
  font-style: normal;
  line-height: normal;
  text-decoration-line: underline;
  text-decoration-style: solid;
  text-decoration-skip-ink: auto;
  text-decoration-thickness: auto;
  text-underline-offset: auto;
  text-underline-position: from-font;
  color: #42424b;
}

.value-box {
  background-color: #d5dfff;
  padding: 0.5vh 1vh;
  border-radius: 0.46vh;
  font-size: 1.6vh;
  font-family: Roboto;
  font-style: normal;
  font-weight: 550;
  line-height: normal;
  color: black;
  margin-right: 0.5vw; /* Add right margin for spacing between multiple value-boxes */
}

.column-display-container {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  max-width: 100%;
  overflow: hidden;
}

.column-items-container {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  max-width: 100%;
  overflow: hidden;
}

.overflow-indicator {
  background-color: #d5dfff !important;
  color: #333 !important;
  font-weight: bold;
  cursor: help;
}

.type-container {
  display: flex;
  align-items: center;
  gap: 0.5vw;
}

.type-icon {
  width: 2vh;
  height: 2vh;
  object-fit: contain;
}

.type-text {
  font-size: 1.6vh;
  color: black;
  font-family: Roboto;
  font-style: normal;
  font-weight: 550;
  line-height: normal;
  display: inline-block;
}

.parameter-arrow {
  width: 1.5vh; /* Adjust icon size */
  height: 1.5vh;
  margin-right: 0.5vh; /* Spacing between icon and text */
  vertical-align: middle; /* Vertical alignment */
}

.unchange-value {
  background-color: #d5dfff;
  color: black;
  padding: 0.2vh 1vh;
  margin-left: 1vw;
  border-radius: 0.46vh;
  font-size: 1.6vh;
  line-height: 2.4vh;
  min-width: 5vw;
  font-family: Roboto;
  font-style: normal;
  font-weight: 550;
  line-height: normal;
  display: inline-block;
  user-select: none;
}

.missingValue {
  font-weight: bold;
  width: 100%;
  padding-right: 1vw;
  font-size: 1.6vh;
  color: #42424b;
  display: flex; /* Change to flex instead of inline-flex */
  justify-content: space-between; /* Align content at both ends */
  align-items: center; /* Vertically center align */
  align-items: left;
  transform: translateY(0.05vh); /* Fine tune position for center alignment */
}

.missingValue :deep(.el-select__wrapper) {
  width: 12vw;
  margin-left: auto;
  height: 2.7vh;
  padding: 0vh 0.5vh 0vh 0.5vh;
}

.missingValue :deep(.el-select__placeholder) {
  color: black;
  font-size: 1.5vh;
  font-family: Roboto;
  font-style: normal;
  line-height: 1.8vh;
  margin-top: 0vh;
}

.missingValue :deep(.el-select__placeholder span) {
  background-color: #c7efed;
  border-radius: 0.46vh;
  padding: 0.3vh 0.6vh 0.3vh 0.6vh; /* Increase padding for more space between text and background color */
  display: inline-block; /* Ensure padding applies correctly */
}

.missingValue :deep(.el-select__selection.is-near) {
  margin-left: 0;
}

.missingValue :deep(.el-tag.el-tag--info) {
  --el-tag-text-color: black;
  --el-tag-bg-color: #c7efed;
  --el-tag-border-color: #4570b6;
  --el-tag-hover-color: #c7efed;
  --el-tag-font-size: 1.5vh;
}

.missingValue :deep(.el-select__selected-item .el-tag) {
  height: 2.4vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
}

.option-text {
  width: 10vw;
  font-size: 1.5vh;
  font-family: Roboto;
  font-style: normal;
  font-weight: 550;
  line-height: normal;
}

.parameter-type {
  font-weight: bold;
  width: 6vw;
  font-size: 1.6vh;
  color: #42424b;
  padding-right: 1vw;
  display: flex; /* Change to flex instead of inline-flex */
  justify-content: left;
  align-items: center; /* Vertically center align */
  height: 1.8vh; /* Adjust text height */
  line-height: 1.8vh;
  transform: translateY(0.05vh); /* Fine tune position for center alignment */
}

.parameter-name :deep(.el-select__wrapper) {
  width: 15vw;
  margin-left: auto;
  height: 2.7vh;
  padding: 0vh 0.5vh 0vh 0.5vh;
}

.parameter-name :deep(.el-select__placeholder) {
  color: black;
  font-size: 1.5vh;
  font-family: Roboto;
  font-style: normal;
  line-height: 1.8vh;
  margin-top: 0vh;
}

.parameter-name :deep(.el-select__placeholder span) {
  background-color: #c7efed;
  border-radius: 0.46vh;
  padding: 0.3vh 0.6vh 0.3vh 0.6vh; /* Increase padding for more space between text and background color */
  display: inline-block; /* Ensure padding applies correctly */
}

.parameter-name :deep(.el-select__selection.is-near) {
  margin-left: 0;
}

.parameter-name :deep(.el-tag.el-tag--info) {
  --el-tag-text-color: black;
  --el-tag-bg-color: #c7efed;
  --el-tag-border-color: #4570b6;
  --el-tag-hover-color: #c7efed;
  --el-tag-font-size: 1.5vh;
}

.parameter-name :deep(.el-select__selected-item .el-tag) {
  height: 2.4vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
}

.parameter-name-two {
  font-weight: bold;
  width: 100%;
  font-size: 1.6vh;
  color: #42424b;
  padding-right: 1vw;
  display: flex; /* Change to flex instead of inline-flex */
  justify-content: space-between;
  align-items: center; /* Vertically center align */
  height: 1.8vh; /* Adjust text height */
  line-height: 1.8vh;
  transform: translateY(0.05vh); /* Fine tune position for center alignment */
}

.parameter-name-two :deep(.el-select__wrapper) {
  margin-left: auto;
  height: 2.7vh;
  padding: 0.3vh 0.5vh 0.3vh 0.3vh;
}

.parameter-name-two :deep(.el-select__placeholder) {
  color: black;
  font-size: 1.4vh;
  font-family: Roboto;
  font-style: normal;
  line-height: 1.8vh;
  margin-top: 0vh;
}

.parameter-name-two :deep(.el-select__placeholder span) {
  background-color: #c7efed;
  border-radius: 0.46vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh; /* Increase padding for more space between text and background color */
  display: inline-block; /* Ensure padding applies correctly */
}

.parameter-name-two :deep(.el-select__selection.is-near) {
  margin-left: 0;
}

.parameter-name-two :deep(.el-tag.el-tag--info) {
  --el-tag-text-color: black;
  --el-tag-bg-color: #c7efed;
  --el-tag-border-color: #4570b6;
  --el-tag-hover-color: #c7efed;
  --el-tag-font-size: 1.4vh;
}

.parameter-name-two :deep(.el-tag .el-tag__close) {
  margin-left: 0vh;
}

.parameter-name-two :deep(.el-select__selected-item .el-tag) {
  height: 2.4vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
}

.allowed_next_value {
  padding: 0.2vw 0.2vw;
  font-size: 1.7vh;
  font-family: Arial;
  height: 2.4vh; /* Adjust select box height */
  margin-left: 1vw;
  width: 10vw;
  display: inline-block;
  position: relative;
  vertical-align: middle;
}

/* Adjust internal el-select style */
.allowed_next_value :deep(.el-select__wrapper) {
  padding: 0 0.5vw;
  height: 2.4vh; /* Match external container height */
  line-height: 2.4vh;
  font-size: 1.7vh !important;
}

:deep(.allowed_next_value .el-input__inner) {
  height: 2.4vh; /* Match external container height */
  line-height: 2.4vh;
  font-size: 1.7vh !important;
  padding: 0;
}

/* Adjust dropdown option font size */
.allowed_next_value :deep(.el-select-dropdown__item) {
  font-size: 1.7vh !important; /* Increase dropdown option font size */
  height: 3vh; /* Appropriately increase option height for larger font */
  line-height: 3vh;
}

.allowed_next_value .el-select-dropdown__item {
  font-size: 1.7vh !important;
}

.block-3 {
  height: 71.82vh;
  overflow-y: hidden;
  padding-left: 1vw;
  padding-right: 1vw;
  padding-top: 1vh;
  padding-bottom: 1vh;
  border-radius: 1vh;
  /*display: flex;
  flex-direction: column;*/
}

.block-3 .text-editor {
  position: relative;
  width: 100%;
  margin-top: 0.92vh;
}

.custom-textarea {
  width: calc(100% - 0.4vw);
  min-height: 16.25vh;
  margin-top: 0.5vh;
  padding: 1vh;
  border: 2px solid transparent; /* Transparent for gradient */
  border-radius: 1vh; /* Rounded corners */
  resize: none;
  font-family: inherit;
  box-sizing: border-box;
  /* Add gradient border */
  background-image: linear-gradient(white, white),
    linear-gradient(to right, #a493b6, #4570b6);
  background-origin: border-box;
  background-clip: padding-box, border-box;
  color: #3e3e3f;
  font-size: 1.6vh;
  font-style: normal;
  line-height: normal;
  font-family: Roboto;
}

.custom-textarea::placeholder {
  color: #9ab7cd; /* Change to desired color */
}

.send-button {
  position: absolute;
  bottom: 1vh;
  right: 1vh;
  width: 3vh;
  height: 3vh;
  background-color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.send-icon {
  width: 2.5vh;
  height: 2.5vh;
}

.validation-list {
  max-height: 53vh;
  height: 53vh;
  padding-left: 0.5vw;
  padding-right: 0.5vw;
  background-color: #ffffff;
  border: 1px solid #ffffff;
  border-radius: 0.92vh;
  overflow-y: auto; /* Changed to auto to allow scrolling */
  perspective: 1000px; /* Add 3D perspective effect */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

/* Hide WebKit browser scrollbar (Chrome, Safari) */
.validation-list::-webkit-scrollbar {
  display: none;
}

.validation-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 0.46vh;
}

.validation-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 0.46vh;
}

.validation-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.validation-list .long-bar span {
  font-weight: bold; /* Bold */
  margin-left: 3vw;
}

/* Card Loading Animation */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.validation-card {
  height: 9.5vh;
  margin-left: 0.1vw;
  margin-top: 1vh;
  padding: 0vh 0.5vw 0vh 0.3vw;
  background-color: white;
  border: 1px solid #d8dee4;
  align-items: center;
  position: relative;
  border-radius: 0.6vh;
  animation: slideIn 0.2s ease-out forwards; /* Add animation effect */
  opacity: 0; /* Initial opacity 0 */
  will-change: transform, opacity; /* Optimize animation performance */
  backface-visibility: hidden;
}

/* Add style for selected card */
.validation-card.selected {
  box-shadow: 0px 0px 6px 0px rgba(44, 123, 182, 0.8); /* Blue shadow, consistent with other app parts */
  border: 1.5px solid #2c7bb6; /* Change border color */
  transform: translateY(-2px); /* Slight lift effect */
}

/* Keep original hover effect */
.validation-card:hover:not(.selected) {
  transform: translateY(-2px);
  transition: transform 0.2s ease;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  padding: 0.6vh;
  padding-left: 1.4vh;
  border-top-left-radius: 0.6vh;
  border-top-right-radius: 0.6vh;
}

.column-name {
  font-weight: bold;
  font-size: 1.5vh;
  color: black;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0; /* Allow shrinking */
}

.column-item {
  display: inline-block;
  background-color: #d5dfff;
  border-radius: 0.46vh;
  margin-right: 0.46vh;
  padding: 0.3vh 0.5vh 0.3vh 0.5vh;
  white-space: nowrap;
  /* Remove length limit for single column name, let them display naturally */
}

.relation-class {
  font-style: normal;
  font-family: Roboto;
  text-align: right;
  line-height: normal;
  font-weight: 550;
  font-size: 1.5vh;
  color: #4570b6;
}

.card-body {
  color: black;
  padding-top: 0.5vh;
  font-size: 1.5vh;
  text-align: left;
  padding-left: 1.4vh;
}

.type-icon-small {
  width: 2.2vh;
  height: 2.2vh;
  margin-right: 0.3vw;
  margin-bottom: 0.2vh;
  flex-shrink: 0;
  vertical-align: middle;
}

.relation-type,
.rule-value {
  display: flex;
  align-items: flex-start;
}

.text-content {
  flex-grow: 1;
}

.validation-card:not(.has-conflict)::before {
  content: "";
  position: absolute;
  top: -0.05vh;
  bottom: -0.05vh;
  left: 0vh;
  width: 0.5vw;
  height: calc(100% + 0.1vh);
  background-color: #4570b6;
  border-top-left-radius: 0.6vh;
  border-bottom-left-radius: 0.6vh;
  border-left: 0.2vh solid #4570b6;
}

.has-conflict::before {
  content: "";
  position: absolute;
  top: -0.05vh;
  bottom: -0.05vh;
  left: 0vh;
  width: 0.5vw;
  height: calc(100% + 0.1vh);
  background-color: #fdd0a2; /* Default conflict color (light red) - corresponds to ifConflict = 1 */
  border-top-left-radius: 0.6vh;
  border-bottom-left-radius: 0.6vh;
  border-left: 0.2vh solid #fdd0a2;
}

.has-conflict[data-conflict-level="2"]::before {
  background-color: #fdae6b;
  border-left: 0.2vh solid #fdae6b;
}

.has-conflict[data-conflict-level="3"]::before {
  background-color: #fd8d3c;
  border-left: 0.2vh solid #fd8d3c;
}

.has-conflict[data-conflict-level="4"]::before {
  background-color: #f16913;
  border-left: 0.2vh solid #f16913;
}

.default-message {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #7a94a8;
  font-size: 1.8vh;
  font-weight: bold;
}

/* Reduce right margin of first checkbox */
.range-checkbox:first-of-type {
  margin-right: 0;
}

.range-checkbox {
  height: 2.4vh;
  align-items: center;
  margin-right: 0.2vw;
}

.range-checkbox :deep(.el-checkbox__inner) {
  width: 1.6vh;
  height: 1.6vh;
  background-color: #fff;
  border-color: #dcdfe6;
}

/* Change selected background color to green */
.range-checkbox :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #67c23a; /* Green */
  border-color: #67c23a;
}

/* Increase checkmark size */
.range-checkbox :deep(.el-checkbox__inner::after) {
  border-width: 2px; /* Increase checkmark thickness */
  height: 0.9vh; /* Increase checkmark height */
  width: 0.5vh; /* Increase checkmark width */
  left: 0.45vh; /* Adjust checkmark position */
  top: 0.2vh; /* Adjust checkmark position */
  transform-origin: center;
}

/* Change hover border color to green */
.range-checkbox :deep(.el-checkbox__input.is-focus .el-checkbox__inner) {
  border-color: #67c23a;
}

.submit-button-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 1vh;
  margin-right: 1vw;
  position: absolute;
  bottom: 1vh;
  right: 1vh;
  z-index: 10; /* Ensure button is on top */
}

.submit-button {
  font-size: 1.5vh;
  padding: 0.5vh 1.5vh;
  background-color: #4570b6;
  border-color: #4570b6;
}

.submit-button:hover {
  background-color: #5a7a8e;
  border-color: #5a7a8e;
}

.truncate-option {
  max-width: 15.625vw;
}

.truncate-option :deep(.el-select-dropdown__item) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Ensure el-input-number and el-select height consistency */
:deep(.el-input-number),
:deep(.el-select) {
  height: 2.7vh;
  line-height: 2.7vh;
}

.empty-message {
  width: 100%;
  height: 20%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #7a94a8;
  font-size: 1.8vh;
  font-weight: bold;
}

.validation-card-empty {
  height: 9.5vh;
  margin-left: 0.1vw;
  margin-top: 1vh;
  padding: 0vh 0.5vw 0vh 0.3vw;
  background-color: white;
  border: 1px solid #d8dee4;
  align-items: center;
  position: relative;
  border-radius: 0.6vh;
  animation: slideIn 0.2s ease-out forwards; /* Add animation effect */
  opacity: 0; /* Initial opacity 0 */
  will-change: transform, opacity; /* Optimize animation performance */
  backface-visibility: hidden;
  display: flex; /* Add flex layout */
  justify-content: center; /* Center horizontally */
  align-items: center; /* Center vertically */
  color: #9ab7cd;
  font-family: Roboto;
  font-size: 1.6vh;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
}

.addcard-icon {
  width: 3vh;
  height: 3vh;
  margin-right: 0.5vh;
}

.delete-card-btn {
  position: absolute;
  bottom: 0.5vh;
  right: 1vh;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.3vh;
  border-radius: 0.3vh;
  transition: opacity 0.2s;
  opacity: 0; /* Hidden by default */
}

.validation-card:hover .delete-card-btn {
  opacity: 1; /* Show on hover */
}

.delete-card-btn:hover {
  opacity: 1;
  background-color: rgba(255, 255, 255, 0.2);
}

.delete-icon {
  width: 1.5vh;
  height: 1.5vh;
}

.example-container {
  display: -webkit-box;
  -webkit-line-clamp: 2; /* Limit to max 2 lines */
  line-clamp: 2; /* Standard property */
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
  line-height: 1.4;
  max-height: 2.8em; /* Max height for 2 lines */
}

.example-line {
  display: inline; /* Display inline to flow multiple lines */
  margin-right: 0.5em; /* Add spacing between lines */
}

.example-single {
  display: -webkit-box;
  -webkit-line-clamp: 2; /* Limit single example to max 2 lines */
  line-clamp: 2; /* Standard property */
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
  line-height: 1.4;
  max-height: 2.8em; /* Max height for 2 lines */
}

/* MultipleCondition Specific Style - Shorten select box width */
.MultipleCondition-row :deep(.el-select__wrapper) {
  margin-left: auto;
  height: 2.7vh;
  padding: 0.3vh 0.5vh 0.3vh 0.3vh;
}
</style>

<style>
/* Custom tooltip style */
.custom-tooltip {
  max-width: 500px !important; /* Set max width */
  word-wrap: break-word !important; /* Allow wrapping */
  white-space: normal !important; /* Allow auto wrap */
  background-color: #d5dfff !important; /* Set background color */
  color: black !important; /* Set font color to black */
  font-family: "Roboto", sans-serif !important; /* Set font to Roboto */
  font-size: 16px !important; /* Set appropriate font size */
  line-height: 1.4 !important; /* Set line height for better readability */
  border: 1px solid #b5d2f8 !important; /* Add border */
  border-radius: 6px !important; /* Set border radius */
  padding: 8px 10px !important; /* Set padding */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important; /* Add shadow effect */
}

/* Override tooltip arrow color */
.custom-tooltip .el-popper__arrow::before {
  background-color: #d5dfff !important;
  border: 1px solid #b5d2f8 !important;
}

/* Ensure tooltip content style */
.custom-tooltip .el-tooltip__content {
  background-color: #d5dfff !important;
  color: black !important;
  font-family: "Roboto", sans-serif !important;
}
</style>
