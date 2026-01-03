<template>
  <div class="modal-overlay">
    <div class="modal-container">
      <button class="close-btn" @click="closeModal">
        <span class="close-icon">×</span>
      </button>
      <div class="modal-header">
        <span class="title-text">Create Validation Rule</span>
      </div>
      <div class="modal-content">
        <div class="form-item">
          <div class="form-label">
            <img src="/cardpanel_icon/parameter-arrow.svg" class="label-icon" />
            Column(s)
          </div>
          <el-select
            v-model="selectedColumns"
            multiple
            placeholder="Select Column(s)"
            class="custom-select"
          >
            <el-option
              v-for="col in columns"
              :key="col"
              :label="col"
              :value="col"
            />
          </el-select>
        </div>

        <div class="form-item">
          <div class="form-label">
            <img src="/cardpanel_icon/parameter-arrow.svg" class="label-icon" />
            Validation Rule Type
          </div>
          <el-select
            v-model="ruleType"
            placeholder="Select Rule Type"
            class="custom-select"
            :disabled="selectedColumns.length === 0"
          >
            <el-option
              v-for="type in filteredRuleTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
              :disabled="type.disabled"
            />
          </el-select>
        </div>

        <div class="form-item">
          <div class="form-label">
            <img src="/cardpanel_icon/parameter-arrow.svg" class="label-icon" />
            Validation Rule Parameter
          </div>
          <div v-if="ruleType === 'Type'" class="parameter-container">
            <span class="parameter-label">Type :</span>
            <el-select
              v-model="ruleParameters.type"
              placeholder="Select Type"
              class="custom-select parameter-input"
            >
              <el-option label="character" value="character" />
              <el-option label="numeric" value="numeric" />
              <el-option label="date" value="datetime" />
            </el-select>
          </div>
          <div v-else-if="ruleType === 'Format'" class="parameter-container">
            <span class="parameter-label">Format :</span>
            <el-select
              v-model="ruleParameters.format"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="Please specify the regular expression"
              class="custom-select parameter-input"
            >
              <el-option
                v-for="item in ruleParameters.format"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </div>
          <div v-else-if="ruleType === 'Range'" class="parameter-container">
            <span class="parameter-label">Range :</span>
            <div class="range-group">
              <el-input
                v-model="ruleParameters.range_min"
                placeholder="min"
                class="range-input"
              />
              <el-select
                v-model="ruleParameters.range_min_op"
                class="range-select"
              >
                <el-option label="<" value="<" />
                <el-option label="≤" value="<=" />
              </el-select>
              <span class="range-column-name">{{
                selectedColumns[0] || "Column"
              }}</span>
              <el-select
                v-model="ruleParameters.range_max_op"
                class="range-select"
              >
                <el-option label="<" value="<" />
                <el-option label="≤" value="<=" />
              </el-select>
              <el-input
                v-model="ruleParameters.range_max"
                placeholder="max"
                class="range-input"
              />
            </div>
          </div>
          <div v-else-if="ruleType === 'Integrity'">
            <div class="parameter-container">
              <span class="parameter-label parameter-label-aligned"
                >Detect Missing Value :</span
              >
              <el-select
                v-model="ruleParameters.integrity_missingDetect"
                class="custom-select parameter-input"
              >
                <el-option :value="true" label="true" />
                <el-option :value="false" label="false" />
              </el-select>
            </div>
            <div class="parameter-container" style="margin-top: 1vh">
              <span class="parameter-label parameter-label-aligned"
                >Specific Missing Value (Optional) :</span
              >
              <el-select
                v-model="ruleParameters.integrity_specialMissing"
                multiple
                filterable
                allow-create
                default-first-option
                :reserve-keyword="false"
                placeholder="Please input special missing values"
                class="custom-select parameter-input"
              >
                <el-option
                  v-for="item in ruleParameters.integrity_specialMissing"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </div>
          </div>
          <div
            v-else-if="ruleType === 'Domain consistency (same entity)'"
            class="domain-consistency-group"
          >
            <div
              v-for="(item, index) in ruleParameters.domain_sameEntity"
              :key="index"
              class="domain-pair-wrapper"
            >
              <div class="parameter-container">
                <span class="parameter-label domain-label">Main Entity :</span>
                <el-select
                  v-model="item.mainEntity"
                  placeholder="Select Main Entity"
                  class="custom-select parameter-input"
                  @change="handleMainEntityChange(index)"
                >
                  <el-option
                    v-for="val in getAvailableValues(index, 'main')"
                    :key="val"
                    :label="val"
                    :value="val"
                  />
                </el-select>
              </div>
              <div class="parameter-container" style="margin-top: 1vh">
                <span class="parameter-label domain-label">Same Entity :</span>
                <el-select
                  v-model="item.sameEntityList"
                  multiple
                  filterable
                  placeholder="Select Same Entities"
                  class="custom-select parameter-input"
                >
                  <el-option
                    v-for="val in getAvailableValues(index, 'same')"
                    :key="val"
                    :label="val"
                    :value="val"
                  />
                </el-select>
              </div>
              <div class="remove-btn-wrapper domain-remove">
                <button
                  class="remove-btn"
                  @click="removeSameEntityPair(index)"
                  v-if="ruleParameters.domain_sameEntity.length > 0"
                >
                  Remove
                </button>
              </div>
            </div>
            <button class="add-btn" @click="addSameEntityPair">
              + Add Entity Pair
            </button>
          </div>
          <div
            v-else-if="ruleType === 'Domain consistency (different domain)'"
            class="parameter-container"
          >
            <span class="parameter-label">Different Domain Entity :</span>
            <el-select
              v-model="ruleParameters.domain_differentDomain"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="Select or input different domain entities"
              class="custom-select parameter-input"
            >
              <el-option
                v-for="val in columnValues[selectedColumns[0]] || []"
                :key="val"
                :label="val"
                :value="val"
              />
            </el-select>
          </div>
          <div v-else-if="ruleType === 'Outlier'" class="parameter-container">
            <span class="parameter-label">Outlier Range :</span>
            <div class="range-group">
              <el-input
                v-model="ruleParameters.outlier_min"
                placeholder="min"
                class="range-input"
              />
              <el-select
                v-model="ruleParameters.outlier_min_op"
                class="range-select"
              >
                <el-option label="<" value="<" />
                <el-option label="≤" value="<=" />
              </el-select>
              <span class="range-column-name">{{
                selectedColumns[0] || "Column"
              }}</span>
              <el-select
                v-model="ruleParameters.outlier_max_op"
                class="range-select"
              >
                <el-option label="<" value="<" />
                <el-option label="≤" value="<=" />
              </el-select>
              <el-input
                v-model="ruleParameters.outlier_max"
                placeholder="max"
                class="range-input"
              />
            </div>
          </div>
          <div
            v-else-if="ruleType === 'Difference'"
            class="parameter-container"
          >
            <span class="parameter-label">Difference Range :</span>
            <div class="range-group">
              <el-input
                v-model="ruleParameters.difference_min"
                placeholder="min"
                class="range-input"
              />
              <el-select
                v-model="ruleParameters.difference_min_op"
                class="range-select"
              >
                <el-option label="<" value="<" />
                <el-option label="≤" value="<=" />
              </el-select>

              <div
                v-if="selectedColumns.length > 1"
                class="difference-columns-wrapper"
              >
                <span
                  v-for="col in selectedColumns"
                  :key="col"
                  class="range-column-name difference-column-item"
                >
                  {{ col }}
                </span>
              </div>
              <span v-else class="range-column-name">{{
                selectedColumns[0] || "Column"
              }}</span>

              <el-select
                v-model="ruleParameters.difference_max_op"
                class="range-select"
              >
                <el-option label="<" value="<" />
                <el-option label="≤" value="<=" />
              </el-select>
              <el-input
                v-model="ruleParameters.difference_max"
                placeholder="max"
                class="range-input"
              />
            </div>
          </div>
          <div v-else-if="ruleType === 'Duplicate'" class="parameter-container">
            <span class="parameter-label">Detect Duplicate :</span>
            <el-select
              v-model="ruleParameters.duplicate_detect"
              class="custom-select parameter-input"
            >
              <el-option :value="true" label="true" />
              <el-option :value="false" label="false" />
            </el-select>
          </div>
          <div
            v-else-if="ruleType === 'Comparison relation (compare)'"
            class="parameter-container"
          >
            <span class="parameter-label">Compare Relation :</span>
            <div class="range-group">
              <span class="range-column-name">{{
                selectedColumns[0] || "Column 1"
              }}</span>
              <el-select
                v-model="ruleParameters.compare_operator"
                class="range-select"
              >
                <el-option label="<" value="<" />
                <el-option label="≤" value="<=" />
                <el-option label="=" value="=" />
                <el-option label="≥" value=">=" />
                <el-option label=">" value=">" />
              </el-select>
              <span class="range-column-name">{{
                selectedColumns[1] || "Column 2"
              }}</span>
            </div>
          </div>
          <div
            v-else-if="ruleType === 'Comparison relation (substring)'"
            class="parameter-container"
          >
            <span class="parameter-label">Substring Relation :</span>
            <div class="range-group">
              <el-select
                v-model="ruleParameters.substring_column"
                placeholder="Select Column"
                class="custom-select"
                style="flex: 2"
              >
                <el-option
                  v-for="col in selectedColumns"
                  :key="col"
                  :label="col"
                  :value="col"
                />
              </el-select>
              <span
                class="parameter-label"
                style="white-space: nowrap; margin: 0 0.5vw"
                >is substring of</span
              >
              <span class="range-column-name">{{
                selectedColumns.find(
                  (c) => c !== ruleParameters.substring_column
                ) || "Other Column"
              }}</span>
            </div>
          </div>
          <div
            v-else-if="ruleType === 'Computational relation'"
            class="parameter-container"
          >
            <span class="parameter-label">Computational Relation :</span>
            <el-input
              v-model="ruleParameters.computational_relation"
              placeholder="Please input computational relation"
              class="custom-input parameter-input"
            />
          </div>
          <div
            v-else-if="ruleType === 'Logical and condition'"
            class="logical-group-container"
          >
            <div
              class="parameter-container"
              v-if="filteredLogicalRuleTemplates.length"
            >
              <span
                class="parameter-label parameter-label-aligned"
                style="flex: none"
              >
                Load Existing Rule :
              </span>
              <el-select
                v-model="selectedLogicalTemplateKey"
                placeholder="Select rule to preload"
                class="custom-select parameter-input"
                clearable
                @change="handleLogicalTemplateChange"
              >
                <el-option
                  v-for="tpl in filteredLogicalRuleTemplates"
                  :key="tpl.key"
                  :label="tpl.label"
                  :value="tpl.key"
                />
              </el-select>
              <button
                class="clear-template-btn"
                type="button"
                @click="clearLogicalTemplate"
                :disabled="!selectedLogicalTemplateKey"
              >
                Clear
              </button>
            </div>
            <div
              v-if="showLogicalTemplateReminder"
              class="logical-template-hint"
            >
              Current selection already matches an existing logical rule. Please
              add new columns or adjust the condition/constraint setup before
              submitting.
            </div>
            <div class="parameter-container">
              <span class="parameter-label parameter-label-aligned"
                >Condition Column(s) :</span
              >
              <el-select
                v-model="ruleParameters.logical_and_condition.conditionColumns"
                multiple
                placeholder="Select Condition Columns"
                class="custom-select parameter-input"
              >
                <el-option
                  v-for="col in selectedColumns"
                  :key="col"
                  :label="col"
                  :value="col"
                  :disabled="
                    ruleParameters.logical_and_condition.constraintColumns.includes(
                      col
                    )
                  "
                />
              </el-select>
            </div>
            <div class="parameter-container" style="margin-top: 1vh">
              <span class="parameter-label parameter-label-aligned"
                >Constraint Column(s) :</span
              >
              <el-select
                v-model="ruleParameters.logical_and_condition.constraintColumns"
                multiple
                placeholder="Select Constraint Columns"
                class="custom-select parameter-input"
              >
                <el-option
                  v-for="col in selectedColumns"
                  :key="col"
                  :label="col"
                  :value="col"
                  :disabled="
                    ruleParameters.logical_and_condition.conditionColumns.includes(
                      col
                    )
                  "
                />
              </el-select>
            </div>

            <div class="logical-relations-area">
              <div
                v-for="(relation, index) in ruleParameters.logical_and_condition
                  .relations"
                :key="index"
                class="logical-pair-wrapper"
              >
                <!-- Condition Part -->
                <div class="parameter-container" style="margin-bottom: 0.5vh">
                  <span
                    class="logical-section-label"
                    style="margin-bottom: 0; width: 8vw; display: inline-block"
                    >Condition Column(s)</span
                  >
                </div>
                <div
                  v-for="col in ruleParameters.logical_and_condition
                    .conditionColumns"
                  :key="'cond-' + col"
                  class="parameter-container"
                  style="margin-bottom: 0.5vh"
                >
                  <template v-if="relation[col]">
                    <span class="parameter-label logical-col-label" :title="col"
                      >{{ col }} :</span
                    >
                    <div v-if="isNumericOrDate(col)" class="range-group">
                      <el-input
                        v-model="relation[col].min"
                        placeholder="min"
                        class="range-input"
                      />
                      <el-select
                        v-model="relation[col].min_op"
                        class="range-select"
                      >
                        <el-option label="<" value="<" />
                        <el-option label="≤" value="<=" />
                      </el-select>
                      <span class="range-column-name">{{ col }}</span>
                      <el-select
                        v-model="relation[col].max_op"
                        class="range-select"
                      >
                        <el-option label="<" value="<" />
                        <el-option label="≤" value="<=" />
                      </el-select>
                      <el-input
                        v-model="relation[col].max"
                        placeholder="max"
                        class="range-input"
                      />
                    </div>
                    <el-select
                      v-else
                      v-model="relation[col].value"
                      :multiple="isCharacterColumn(col)"
                      :collapse-tags="
                        isCharacterColumn(col) &&
                        shouldCollapseTags(relation[col].value)
                      "
                      :max-collapse-tags="
                        getMaxVisibleTags(relation[col].value)
                      "
                      collapse-tags-tooltip
                      class="custom-select parameter-input logical-value-select"
                      placeholder="Select Value"
                    >
                      <el-option
                        v-for="val in getAvailableLogicalValues(index, col)"
                        :key="val"
                        :label="val"
                        :value="val"
                      />
                    </el-select>
                  </template>
                </div>

                <!-- Constraint Part -->
                <div
                  class="parameter-container"
                  style="
                    margin-top: 1vh;
                    margin-bottom: 0.5vh;
                    border-top: 1px solid #e0e0e0;
                    padding-top: 1vh;
                  "
                >
                  <span
                    class="logical-section-label"
                    style="margin-bottom: 0; width: 8vw; display: inline-block"
                    >Constraint Column(s)</span
                  >
                </div>
                <div
                  v-for="col in ruleParameters.logical_and_condition
                    .constraintColumns"
                  :key="'cons-' + col"
                  class="parameter-container"
                  style="margin-bottom: 0.5vh"
                >
                  <template v-if="relation[col]">
                    <span class="parameter-label logical-col-label" :title="col"
                      >{{ col }} :</span
                    >
                    <div v-if="isNumericOrDate(col)" class="range-group">
                      <el-input
                        v-model="relation[col].min"
                        placeholder="min"
                        class="range-input"
                      />
                      <el-select
                        v-model="relation[col].min_op"
                        class="range-select"
                      >
                        <el-option label="<" value="<" />
                        <el-option label="≤" value="<=" />
                      </el-select>
                      <span class="range-column-name">{{ col }}</span>
                      <el-select
                        v-model="relation[col].max_op"
                        class="range-select"
                      >
                        <el-option label="<" value="<" />
                        <el-option label="≤" value="<=" />
                      </el-select>
                      <el-input
                        v-model="relation[col].max"
                        placeholder="max"
                        class="range-input"
                      />
                    </div>
                    <el-select
                      v-else
                      v-model="relation[col].value"
                      :multiple="isCharacterColumn(col)"
                      :collapse-tags="
                        isCharacterColumn(col) &&
                        shouldCollapseTags(relation[col].value)
                      "
                      :max-collapse-tags="
                        getMaxVisibleTags(relation[col].value)
                      "
                      collapse-tags-tooltip
                      class="custom-select parameter-input logical-value-select"
                      placeholder="Select Value"
                    >
                      <el-option
                        v-for="val in columnValues[col] || []"
                        :key="val"
                        :label="val"
                        :value="val"
                      />
                    </el-select>
                  </template>
                </div>

                <div class="remove-btn-wrapper logical-remove">
                  <button
                    class="remove-btn"
                    @click="removeLogicalRelation(index)"
                  >
                    Remove
                  </button>
                </div>
              </div>
              <button class="add-btn" @click="addLogicalRelation">
                + Add Relation
              </button>
            </div>
          </div>
          <div v-else-if="ruleType === 'Sequence'" class="sequence-group">
            <div
              v-for="(item, index) in ruleParameters.sequence"
              :key="index"
              class="sequence-pair-wrapper"
            >
              <div class="parameter-container">
                <span class="parameter-label sequence-label"
                  >Current Value :</span
                >
                <el-select
                  v-model="item.currentValue"
                  placeholder="Select Current Value"
                  class="custom-select parameter-input"
                >
                  <el-option
                    v-for="val in getAvailableSequenceValues(index, 'current')"
                    :key="val"
                    :label="val"
                    :value="val"
                  />
                </el-select>
              </div>
              <div class="parameter-container" style="margin-top: 1vh">
                <span class="parameter-label sequence-label">
                  Allowed Next Value :
                </span>
                <el-select
                  v-model="item.nextValues"
                  multiple
                  filterable
                  placeholder="Select Allowed Next Values"
                  class="custom-select parameter-input"
                >
                  <el-option
                    v-for="val in getAvailableSequenceValues(index, 'next')"
                    :key="val"
                    :label="val"
                    :value="val"
                  />
                </el-select>
              </div>
              <div class="remove-btn-wrapper sequence-remove">
                <button
                  class="remove-btn"
                  @click="removeSequencePair(index)"
                  v-if="ruleParameters.sequence.length > 0"
                >
                  Remove
                </button>
              </div>
            </div>
            <button class="add-btn" @click="addSequencePair">
              + Add Sequence Pair
            </button>
          </div>
          <div
            v-else-if="ruleType === 'Mapping and cardinality'"
            class="sequence-group"
          >
            <div
              v-for="(pair, index) in ruleParameters.mapping_cardinality"
              :key="index"
              class="sequence-pair-wrapper"
            >
              <div
                v-for="col in selectedColumns"
                :key="col"
                class="parameter-container"
                style="margin-bottom: 1vh"
              >
                <span class="parameter-label sequence-label" :title="col"
                  >{{ col }} :</span
                >
                <el-select
                  v-model="pair[col]"
                  multiple
                  placeholder="Select Value"
                  class="custom-select parameter-input"
                >
                  <el-option
                    v-for="val in getAvailableMappingValues(index, col)"
                    :key="val"
                    :label="val"
                    :value="val"
                  />
                </el-select>
              </div>
              <div class="remove-btn-wrapper sequence-remove">
                <button class="remove-btn" @click="removeMappingPair(index)">
                  Remove
                </button>
              </div>
            </div>
            <button class="add-btn" @click="addMappingPair">
              + Add Mapping Pair
            </button>
          </div>
          <div v-else class="placeholder-box">
            <span v-if="ruleType"
              >Parameters for {{ ruleType }} (To be implemented)</span
            >
            <span v-else>Please select a rule type first</span>
          </div>
        </div>

        <div
          class="form-item"
          v-if="['Sequence', 'Difference'].includes(ruleType)"
        >
          <div class="form-label">
            <img src="/cardpanel_icon/parameter-arrow.svg" class="label-icon" />
            Order Condition
          </div>
          <div class="order-condition-container">
            <!-- First Order -->
            <div class="order-row">
              <span class="order-label">First Order:</span>
              <el-select
                v-model="ruleParameters.orderCondition.firstOrderColumn"
                placeholder="Column"
                class="custom-select order-col-select"
                clearable
              >
                <el-option
                  v-for="col in columns"
                  :key="col"
                  :label="col"
                  :value="col"
                />
              </el-select>
              <el-select
                v-model="ruleParameters.orderCondition.firstOrderType"
                class="custom-select order-type-select"
              >
                <el-option label="Asc" value="Asc" />
                <el-option label="Desc" value="Desc" />
                <el-option label="Disorder" value="Disorder" />
              </el-select>
            </div>
            <!-- Second Order -->
            <div class="order-row">
              <span class="order-label">Second Order:</span>
              <el-select
                v-model="ruleParameters.orderCondition.secondOrderColumn"
                placeholder="Column"
                class="custom-select order-col-select"
                clearable
              >
                <el-option
                  v-for="col in columns"
                  :key="col"
                  :label="col"
                  :value="col"
                />
              </el-select>
              <el-select
                v-model="ruleParameters.orderCondition.secondOrderType"
                class="custom-select order-type-select"
              >
                <el-option label="Asc" value="Asc" />
                <el-option label="Desc" value="Desc" />
                <el-option label="Disorder" value="Disorder" />
              </el-select>
            </div>
            <!-- Third Order -->
            <div class="order-row">
              <span class="order-label">Third Order:</span>
              <el-select
                v-model="ruleParameters.orderCondition.thirdOrderColumn"
                placeholder="Column"
                class="custom-select order-col-select"
                clearable
              >
                <el-option
                  v-for="col in columns"
                  :key="col"
                  :label="col"
                  :value="col"
                />
              </el-select>
              <el-select
                v-model="ruleParameters.orderCondition.thirdOrderType"
                class="custom-select order-type-select"
              >
                <el-option label="Asc" value="Asc" />
                <el-option label="Desc" value="Desc" />
                <el-option label="Disorder" value="Disorder" />
              </el-select>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="submit-btn" @click="submitModal">Submit</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { api_get_rule_creation_info } from "@/utils/callapi";

export default defineComponent({
  name: "CreateRuleModal",
  emits: ["close", "submit"],
  data() {
    return {
      ruleType: "",
      ruleCondition: "",
      logicalValueWidth: 260,
      ruleParameters: {
        type: "",
        format: [] as string[],
        integrity_missingDetect: true,
        integrity_specialMissing: [] as string[],
        range_min: "",
        range_min_op: "<",
        range_max_op: "<",
        range_max: "",
        domain_sameEntity: [
          {
            mainEntity: "",
            sameEntityList: [],
          },
        ] as {
          mainEntity: string;
          sameEntityList: string[];
        }[],
        domain_differentDomain: [] as string[],
        outlier_min: "",
        outlier_min_op: "<",
        outlier_max_op: "<",
        outlier_max: "",
        difference_min: "",
        difference_min_op: "<",
        difference_max_op: "<",
        difference_max: "",
        duplicate_detect: true,
        compare_operator: "<",
        substring_column: "",
        computational_relation: "",
        logical_and_condition: {
          conditionColumns: [] as string[],
          constraintColumns: [] as string[],
          relations: [] as any[],
        },
        sequence: [
          {
            currentValue: "",
            nextValues: [],
          },
        ] as {
          currentValue: string;
          nextValues: string[];
        }[],
        mapping_cardinality: [] as Array<Record<string, string[]>>,
        orderCondition: {
          firstOrderColumn: "",
          firstOrderType: "",
          secondOrderColumn: "",
          secondOrderType: "",
          thirdOrderColumn: "",
          thirdOrderType: "",
          dateColumns: [] as string[],
        },
      },
      columns: [] as string[],
      existingRules: {} as any,
      columnValues: {} as Record<string, string[]>,
      selectedColumns: [] as string[],
      ruleTypes: [
        "Type",
        "Format",
        "Integrity",
        "Range",
        "Comparison relation",
        "Computational relation",
        "Logical and condition",
        "Mapping and cardinality",
        "Domain consistency (same entity)",
        "Domain consistency (different domain)",
        "Outlier",
        "Difference",
        "Duplicate",
        "Order",
        "Sequence",
      ],
      selectedLogicalTemplateKey: "",
      logicalTemplateApplied: false,
    };
  },
  computed: {
    filteredRuleTypes() {
      const singleColumnRules = [
        "Type",
        "Format",
        "Integrity",
        "Range",
        "Domain consistency (same entity)",
        "Domain consistency (different domain)",
        "Outlier",
        "Order",
        "Sequence",
      ];
      const bothRules = ["Difference", "Duplicate"];

      if (this.selectedColumns.length > 1) {
        const rulesList: { label: string; value: string; disabled: boolean }[] =
          [];
        const getColType = (col: string) => this.existingRules[col]?.type;
        const firstType = getColType(this.selectedColumns[0]);
        const allTypesIdentical = this.selectedColumns.every(
          (c) => getColType(c) === firstType
        );
        const allNumeric = this.selectedColumns.every(
          (c) => getColType(c) === "numeric"
        );

        // 1. Comparison relation (compare)
        if (this.selectedColumns.length === 2) {
          const isNumericOrDate =
            firstType === "numeric" || firstType === "datetime";
          if (allTypesIdentical && isNumericOrDate) {
            let disabled = false;
            let label = "Comparison relation (compare)";
            const list = this.existingRules.numericCompareList || [];
            const match = list.some((item) => {
              const cols = [item.column1, item.column2];
              return (
                cols.length === this.selectedColumns.length &&
                cols.every((c) => this.selectedColumns.includes(c))
              );
            });
            if (match) {
              disabled = true;
              label += " (Existing rule cannot be created)";
            }
            rulesList.push({
              label,
              value: "Comparison relation (compare)",
              disabled,
            });
          }
        }

        // 2. Comparison relation (substring)
        if (this.selectedColumns.length === 2) {
          if (allTypesIdentical && firstType === "character") {
            let disabled = false;
            let label = "Comparison relation (substring)";
            const list = this.existingRules.substringList || [];
            const match = list.some((item) => {
              const cols = [item.column1, item.column2];
              return (
                cols.length === this.selectedColumns.length &&
                cols.every((c) => this.selectedColumns.includes(c))
              );
            });
            if (match) {
              disabled = true;
              label += " (Existing rule cannot be created)";
            }
            rulesList.push({
              label,
              value: "Comparison relation (substring)",
              disabled,
            });
          }
        }

        // 3. Computational relation
        {
          let disabled = false;
          let label = "Computational relation";
          if (!allNumeric) {
            disabled = true;
            label += " (Current selected columns types are not identical)";
          } else {
            const list = this.existingRules.formulaList || [];
            const match = list.some((item) => {
              const cols = item.variableList || [];
              if (cols.length !== this.selectedColumns.length) return false;
              return cols.every((c) => this.selectedColumns.includes(c));
            });
            if (match) {
              disabled = true;
              label += " (Existing rule cannot be created)";
            }
          }
          rulesList.push({ label, value: "Computational relation", disabled });
        }

        // 4. Logical and condition
        {
          let disabled = false;
          let label = "Logical and condition";
          let match = false;
          if (this.selectedColumns.length === 2) {
            const list = this.existingRules.conditionLogicColumnList || [];
            match = list.some((item) => {
              const cols = [
                ...(item.conditionColumns || []),
                ...(item.constraintColumns || []),
              ];
              const uniqueCols = [...new Set(cols)];
              if (uniqueCols.length !== this.selectedColumns.length)
                return false;
              return uniqueCols.every((c) => this.selectedColumns.includes(c));
            });
          } else {
            const list =
              this.existingRules.multipleConditionLogicColumnList || [];
            match = list.some((item) => {
              const cols = [
                ...(item.conditionColumns || []),
                ...(item.constraintColumns || []),
              ];
              const uniqueCols = [...new Set(cols)];
              if (uniqueCols.length !== this.selectedColumns.length)
                return false;
              return uniqueCols.every((c) => this.selectedColumns.includes(c));
            });
          }
          if (match) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
          rulesList.push({ label, value: "Logical and condition", disabled });
        }

        // 5. Mapping and cardinality
        if (this.selectedColumns.length === 2) {
          let disabled = false;
          let label = "Mapping and cardinality";
          const list = this.existingRules.lookupList || [];
          const match = list.some((item) => {
            const cols = [item.parentColumnName, item.childColumnName];
            return (
              cols.length === this.selectedColumns.length &&
              cols.every((c) => this.selectedColumns.includes(c))
            );
          });
          if (match) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
          rulesList.push({ label, value: "Mapping and cardinality", disabled });
        }

        // 6. Difference
        {
          let disabled = false;
          let label = "Difference";
          if (!allNumeric) {
            disabled = true;
            label +=
              " (Difference rule does not support current selected types)";
          } else {
            const list = this.existingRules.multiDifference || [];
            const match = list.some((item) => {
              const cols = item.columns || [];
              if (cols.length !== this.selectedColumns.length) return false;
              return cols.every((c) => this.selectedColumns.includes(c));
            });
            if (match) {
              disabled = true;
              label += " (Existing rule cannot be created)";
            }
          }
          rulesList.push({ label, value: "Difference", disabled });
        }

        // 7. Duplicate
        {
          let disabled = false;
          let label = "Duplicate";
          const list = this.existingRules.multipleDuplicateColumnsList || [];
          const match = list.some((cols) => {
            if (cols.length !== this.selectedColumns.length) return false;
            return cols.every((c) => this.selectedColumns.includes(c));
          });
          if (match) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
          rulesList.push({ label, value: "Duplicate", disabled });
        }

        return rulesList;
      }

      let availableRules = [...singleColumnRules, ...bothRules];

      if (this.selectedColumns.length === 0) {
        return availableRules.map((r) => ({
          label: r,
          value: r,
          disabled: false,
        }));
      }

      const col = this.selectedColumns[0];
      const rules = this.existingRules[col];

      if (!rules) {
        return availableRules.map((r) => ({
          label: r,
          value: r,
          disabled: false,
        }));
      }

      return availableRules.map((rule) => {
        let disabled = false;
        let label = rule;

        if (rule === "Type") {
          if (rules.type) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Format") {
          if (rules.type !== "character" && rules.type !== "datetime") {
            disabled = true;
            label += " (Current data type cannot create format rule)";
          } else if (rules.format && rules.format.length > 0) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Integrity") {
          if (rules.missingDetectFlag === true) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Range") {
          if (rules.type !== "numeric" && rules.type !== "datetime") {
            disabled = true;
            label += " (Current data type cannot create range rule)";
          } else if (rules.range && rules.range.length > 0) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Domain consistency (same entity)") {
          if (rules.type !== "character") {
            disabled = true;
            label +=
              " (Current data type cannot create Domain consistency (same entity) rule)";
          } else if (rules.sameEntityList && rules.sameEntityList.length > 0) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Domain consistency (different domain)") {
          if (rules.type !== "character") {
            disabled = true;
            label +=
              " (Current data type cannot create Domain consistency (different domain) rule)";
          } else if (
            rules.differentDomainList &&
            Array.isArray(rules.differentDomainList) &&
            rules.differentDomainList.length > 0
          ) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Outlier") {
          if (rules.type !== "numeric") {
            disabled = true;
            label += " (Current data type cannot create Outlier rule)";
          } else if (
            rules.outlierRange &&
            Object.keys(rules.outlierRange).length > 0
          ) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Difference") {
          if (rules.type !== "numeric") {
            disabled = true;
            label += " (Current data type cannot create Difference rule)";
          } else if (
            rules.difference &&
            rules.difference.difference &&
            Object.keys(rules.difference.difference).length > 0
          ) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Duplicate") {
          if (rules.duplicateDetectFlag === true) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        } else if (rule === "Order") {
          disabled = true;
          label += " (Existing rule cannot be created)";
        } else if (rule === "Sequence") {
          if (rules.type !== "character") {
            disabled = true;
            label += " (Current data type cannot create Sequence rule)";
          } else if (rules.sequenceRule && rules.sequenceRule.length > 0) {
            disabled = true;
            label += " (Existing rule cannot be created)";
          }
        }

        return { label, value: rule, disabled };
      });
    },
    logicalRuleTemplates() {
      const templates: {
        key: string;
        label: string;
        rule: any;
        allColumns: string[];
      }[] = [];
      const singleList = Array.isArray(
        this.existingRules.conditionLogicColumnList
      )
        ? this.existingRules.conditionLogicColumnList
        : [];
      singleList.forEach((rule: any, index: number) => {
        const conditionColumns = rule?.conditionColumns || [];
        const constraintColumns = rule?.constraintColumns || [];
        if (!conditionColumns.length || !constraintColumns.length) {
          return;
        }
        templates.push({
          key: `single-${index}`,
          label: `${conditionColumns.join(", ")} -> ${constraintColumns.join(
            ", "
          )}`,
          rule,
          allColumns: [...conditionColumns, ...constraintColumns],
        });
      });

      const multiList = Array.isArray(
        this.existingRules.multipleConditionLogicColumnList
      )
        ? this.existingRules.multipleConditionLogicColumnList
        : [];
      multiList.forEach((rule: any, index: number) => {
        const conditionColumns = rule?.conditionColumns || [];
        const constraintColumns = rule?.constraintColumns || [];
        if (!conditionColumns.length || !constraintColumns.length) {
          return;
        }
        templates.push({
          key: `multi-${index}`,
          label: `${conditionColumns.join(", ")} -> ${constraintColumns.join(
            ", "
          )}`,
          rule,
          allColumns: [...conditionColumns, ...constraintColumns],
        });
      });

      return templates;
    },
    showLogicalTemplateReminder() {
      const vm = this as any;
      return (
        vm.ruleType === "Logical and condition" &&
        vm.logicalTemplateApplied &&
        vm.isExistingLogicalCombination()
      );
    },
    filteredLogicalRuleTemplates() {
      const vm = this as any;
      if (!vm.selectedColumns.length) {
        return [];
      }
      const selectedSet = new Set(vm.selectedColumns);
      const templates = vm.logicalRuleTemplates as {
        key: string;
        label: string;
        rule: any;
        allColumns: string[];
      }[];
      return templates.filter((tpl) =>
        tpl.allColumns.every((col) => selectedSet.has(col))
      );
    },
  },
  watch: {
    "ruleParameters.logical_and_condition.conditionColumns": {
      handler() {
        this.updateLogicalRelations();
      },
      deep: true,
    },
    "ruleParameters.logical_and_condition.constraintColumns": {
      handler() {
        this.updateLogicalRelations();
      },
      deep: true,
    },
    ruleType(newVal: string) {
      if (newVal !== "Logical and condition") {
        this.logicalTemplateApplied = false;
        this.selectedLogicalTemplateKey = "";
      }
    },
    selectedColumns() {
      if (this.selectedColumns.length === 0) {
        this.ruleType = "";
        this.logicalTemplateApplied = false;
      }

      if (this.ruleType) {
        const currentRule = this.filteredRuleTypes.find(
          (r) => r.value === this.ruleType
        );
        const isDisabled = !currentRule || currentRule.disabled;
        if (isDisabled) {
          const canBypass =
            this.ruleType === "Logical and condition" &&
            this.logicalTemplateApplied;
          if (!canBypass) {
            this.ruleType = "";
          }
        }
      }

      if (this.selectedColumns.length > 0) {
        const col = this.selectedColumns[0];
        const existing = this.existingRules[col]?.orderCondition;
        if (existing) {
          this.ruleParameters.orderCondition = JSON.parse(
            JSON.stringify(existing)
          );
        } else {
          this.ruleParameters.orderCondition = {
            firstOrderColumn: "",
            firstOrderType: "",
            secondOrderColumn: "",
            secondOrderType: "",
            thirdOrderColumn: "",
            thirdOrderType: "",
            dateColumns: [],
          };
        }
      }

      if (
        this.selectedLogicalTemplateKey &&
        !this.filteredLogicalRuleTemplates.some(
          (tpl) => tpl.key === this.selectedLogicalTemplateKey
        )
      ) {
        this.clearLogicalTemplate();
      }
    },
  },
  methods: {
    measureLogicalValueWidth() {
      this.$nextTick(() => {
        const el = this.$el?.querySelector?.(
          ".logical-value-select .el-select__tags"
        ) as HTMLElement | null;
        // Fallback to the select itself if tags container is not yet rendered
        const selectEl = this.$el?.querySelector?.(
          ".logical-value-select"
        ) as HTMLElement | null;
        const width = el?.clientWidth || selectEl?.clientWidth;
        if (width) {
          // Reserve a small padding for caret and spacing
          this.logicalValueWidth = Math.max(140, width - 8);
        }
      });
    },
    estimateTagWidth(text: string) {
      const safeText = String(text || "");
      // Approximate: padding/border 18px + 6px per character
      return 18 + safeText.length * 6;
    },
    getMaxVisibleTags(values: any) {
      if (!Array.isArray(values) || !values.length) return 1;
      const available = this.logicalValueWidth || 240;
      let used = 0;
      let count = 0;
      values.forEach((v: any) => {
        const w = this.estimateTagWidth(v) + 6; // include small gap between tags
        if (used + w <= available) {
          used += w;
          count += 1;
        }
      });
      return Math.max(1, count);
    },
    shouldCollapseTags(values: any) {
      if (!Array.isArray(values) || values.length <= 1) return false;
      return this.getMaxVisibleTags(values) < values.length;
    },
    handleLogicalTemplateChange(value: string) {
      if (!value) {
        this.clearLogicalTemplate();
        return;
      }
      const template = this.logicalRuleTemplates.find(
        (tpl) => tpl.key === value
      );
      if (!template) {
        return;
      }
      this.applyLogicalTemplate(template);
    },
    clearLogicalTemplate() {
      this.selectedLogicalTemplateKey = "";
      this.logicalTemplateApplied = false;
    },
    applyLogicalTemplate(template: { rule: any; allColumns: string[] }) {
      if (!template || !template.rule) {
        return;
      }
      this.logicalTemplateApplied = true;
      const mergedColumns = [...this.selectedColumns];
      template.allColumns.forEach((col: string) => {
        if (!mergedColumns.includes(col)) {
          mergedColumns.push(col);
        }
      });
      this.selectedColumns = mergedColumns;
      const conditionColumns = [...(template.rule.conditionColumns || [])];
      const constraintColumns = [...(template.rule.constraintColumns || [])];
      this.ruleParameters.logical_and_condition.conditionColumns =
        conditionColumns;
      this.ruleParameters.logical_and_condition.constraintColumns =
        constraintColumns;
      const relations = this.transformTemplateRelations(template.rule);
      this.ruleParameters.logical_and_condition.relations = relations.length
        ? relations
        : [];
      if (!relations.length) {
        this.addLogicalRelation();
      }
      this.$nextTick(() => {
        this.ruleType = "Logical and condition";
      });
    },
    transformTemplateRelations(rule: any) {
      const conditionColumns = rule?.conditionColumns || [];
      const constraintColumns = rule?.constraintColumns || [];
      const columnTypeMap = rule?.columnType || {};
      const relationList = Array.isArray(rule?.conditionAndLogicList)
        ? rule.conditionAndLogicList
        : [];
      const normalized = relationList.map((entry: any) => {
        const relation: Record<string, any> = {};
        conditionColumns.forEach((col: string, idx: number) => {
          const rawValue = this.extractLogicalColumnValue(
            entry?.conditionColumnValue,
            col,
            idx
          );
          relation[col] = this.normalizeLogicalValue(
            col,
            rawValue,
            columnTypeMap[col]
          );
        });
        constraintColumns.forEach((col: string, idx: number) => {
          const rawValue = this.extractLogicalColumnValue(
            entry?.constraintColumnValue,
            col,
            idx
          );
          relation[col] = this.normalizeLogicalValue(
            col,
            rawValue,
            columnTypeMap[col]
          );
        });
        return relation;
      });

      // Only merge when there is a single condition column.
      // Merging multi-column conditions can fabricate cross-combinations
      // (e.g., [a][b]->[x,y] + [aa][bb]->[x,y] would wrongly imply [aa][b]->[x,y]).
      if (conditionColumns.length === 1 && normalized.length > 0) {
        return this.mergeRelationsByConstraint(
          normalized,
          conditionColumns,
          constraintColumns
        );
      }

      return normalized;
    },
    extractLogicalColumnValue(
      collection: any[],
      columnName: string,
      index: number
    ) {
      if (!Array.isArray(collection)) {
        return null;
      }
      const direct = collection?.[index]?.[columnName];
      if (direct !== undefined) {
        return direct;
      }
      const fallback = collection.find(
        (item: Record<string, any>) => item && columnName in item
      );
      return fallback ? fallback[columnName] : null;
    },
    normalizeLogicalValue(
      columnName: string,
      rawValue: any,
      columnType?: string
    ) {
      const inferredType =
        columnType ||
        (this.isNumericOrDate(columnName) ? "RangeBased" : "EqualityBased");
      if (inferredType === "RangeBased") {
        const start = rawValue?.start ?? rawValue?.min ?? null;
        const end = rawValue?.end ?? rawValue?.max ?? null;
        return {
          min: start == null ? "" : String(start),
          min_op: rawValue?.startInclusive ? "<=" : "<",
          max: end == null ? "" : String(end),
          max_op: rawValue?.endInclusive ? "<=" : "<",
        };
      }
      const toArray = (val: any) => {
        if (Array.isArray(val)) {
          return val
            .filter((v) => v !== undefined && v !== null && v !== "")
            .map((v) => String(v));
        }
        if (val === undefined || val === null || val === "") return [];
        return [String(val)];
      };
      const equalityValue =
        rawValue && typeof rawValue === "object" && "value" in rawValue
          ? rawValue.value
          : rawValue;
      return { value: toArray(equalityValue) };
    },
    validateLogicalAndConditionFields() {
      const { logical_and_condition } = this.ruleParameters;
      const { conditionColumns, constraintColumns, relations } =
        logical_and_condition;
      if (!relations.length) {
        alert(
          "Please add at least one logical relation entry before submitting."
        );
        return false;
      }

      const missingFields: string[] = [];

      const checkColumnValue = (
        relation: Record<string, any>,
        col: string,
        relationIndex: number,
        columnRole: string
      ) => {
        const valueObj = relation[col];
        if (!valueObj) {
          missingFields.push(
            `Relation #${relationIndex + 1} ${columnRole} column "${col}"`
          );
          return;
        }
        if (this.isNumericOrDate(col)) {
          const hasMin = valueObj.min !== undefined && valueObj.min !== "";
          const hasMax = valueObj.max !== undefined && valueObj.max !== "";
          if (!hasMin || !hasMax) {
            missingFields.push(
              `Relation #${
                relationIndex + 1
              } ${columnRole} column "${col}" requires both min and max values`
            );
          }
        } else {
          const valueField = valueObj.value;
          const hasValue = Array.isArray(valueField)
            ? valueField.length > 0
            : valueField !== undefined &&
              valueField !== null &&
              valueField !== "";
          if (!hasValue) {
            missingFields.push(
              `Relation #${
                relationIndex + 1
              } ${columnRole} column "${col}" value is empty`
            );
          }
        }
      };

      relations.forEach((relation, index) => {
        conditionColumns.forEach((col) =>
          checkColumnValue(relation, col, index, "condition")
        );
        constraintColumns.forEach((col) =>
          checkColumnValue(relation, col, index, "constraint")
        );
      });

      if (missingFields.length > 0) {
        alert(
          `Logical and condition inputs are incomplete:\n${missingFields.join(
            "\n"
          )}`
        );
        return false;
      }

      return true;
    },
    // Merge multiple condition entries that share identical constraint values
    // so they render as a single relation with combined condition values.
    // Note: used only when a single condition column exists to avoid
    // fabricating cross-combinations for multi-column rules.
    mergeRelationsByConstraint(
      relations: Record<string, any>[] = [],
      conditionColumns: string[] = [],
      constraintColumns: string[] = []
    ) {
      const mergedList: Record<string, any>[] = [];
      const keyMap = new Map<string, Record<string, any>>();

      const buildConstraintKey = (rel: Record<string, any>) => {
        const keyParts = constraintColumns.map((col) => {
          const valObj = rel[col];
          if (this.isNumericOrDate(col)) {
            return `${col}:${JSON.stringify(valObj || {})}`;
          }
          const vals = Array.isArray(valObj?.value)
            ? [...valObj.value].sort()
            : [];
          return `${col}:${JSON.stringify(vals)}`;
        });
        return keyParts.join("||");
      };

      relations.forEach((rel) => {
        const key = buildConstraintKey(rel);
        if (!keyMap.has(key)) {
          // Clone to avoid mutating the original reference
          const clone = JSON.parse(JSON.stringify(rel));
          // Ensure constraint side is deduped
          constraintColumns.forEach((col) => {
            if (
              !this.isNumericOrDate(col) &&
              Array.isArray(clone[col]?.value)
            ) {
              clone[col].value = this.dedupeValues(clone[col].value);
            }
          });
          keyMap.set(key, clone);
          mergedList.push(clone);
          return;
        }

        const target = keyMap.get(key) as Record<string, any>;
        conditionColumns.forEach((col) => {
          if (this.isNumericOrDate(col)) {
            // Range-based: keep the first populated range
            if (!target[col] && rel[col]) {
              target[col] = JSON.parse(JSON.stringify(rel[col]));
            }
          } else {
            const combined = this.dedupeValues([
              ...(target[col]?.value || []),
              ...(rel[col]?.value || []),
            ]);
            target[col] = { value: combined };
          }
        });

        constraintColumns.forEach((col) => {
          if (!this.isNumericOrDate(col)) {
            const combined = this.dedupeValues([
              ...(target[col]?.value || []),
              ...(rel[col]?.value || []),
            ]);
            target[col] = { value: combined };
          }
        });
      });

      return mergedList;
    },
    dedupeValues(values: any[]) {
      const seen = new Set<string>();
      const result: string[] = [];
      (values || []).forEach((v) => {
        const s = String(v);
        if (!seen.has(s)) {
          seen.add(s);
          result.push(s);
        }
      });
      return result;
    },
    isExistingLogicalCombination() {
      if (this.selectedColumns.length === 0) {
        return false;
      }
      return this.logicalRuleTemplates.some((tpl) => {
        if (tpl.allColumns.length !== this.selectedColumns.length) {
          return false;
        }
        return tpl.allColumns.every((col) =>
          this.selectedColumns.includes(col)
        );
      });
    },
    closeModal() {
      this.$emit("close");
    },
    submitModal() {
      if (this.ruleType === "Logical and condition") {
        const { conditionColumns, constraintColumns } =
          this.ruleParameters.logical_and_condition;
        const usedCols = new Set([...conditionColumns, ...constraintColumns]);
        const missing = this.selectedColumns.filter((c) => !usedCols.has(c));

        if (missing.length > 0) {
          alert(
            `All selected columns must be assigned to either Condition or Constraint columns. Missing: ${missing.join(
              ", "
            )}`
          );
          return;
        }
        if (conditionColumns.length === 0 || constraintColumns.length === 0) {
          alert(
            "Please select at least one Condition column and one Constraint column."
          );
          return;
        }
        if (this.isExistingLogicalCombination()) {
          alert(
            "A logical rule already exists for the selected columns. Please add new columns or adjust the selection before submitting."
          );
          return;
        }
        if (!this.validateLogicalAndConditionFields()) {
          return;
        }
      }

      let parameters = this.ruleParameters;

      // Expand merged multi-condition relations back into individual combinations for storage
      if (this.ruleType === "Logical and condition") {
        parameters = JSON.parse(JSON.stringify(this.ruleParameters));
        const expanded = this.expandLogicalRelationsForSubmit();
        parameters.logical_and_condition.relations = expanded;
      }

      this.$emit("submit", {
        type: this.ruleType,
        condition: this.ruleCondition,
        columns: this.selectedColumns,
        parameters,
      });
    },
    addSameEntityPair() {
      this.ruleParameters.domain_sameEntity.push({
        mainEntity: "",
        sameEntityList: [],
      });
    },
    removeSameEntityPair(index: number) {
      this.ruleParameters.domain_sameEntity.splice(index, 1);
    },
    handleMainEntityChange(index: number) {
      this.ruleParameters.domain_sameEntity[index].sameEntityList = [];
    },
    getAvailableValues(index: number, type: "main" | "same") {
      const col = this.selectedColumns[0];
      if (!col || !this.columnValues[col]) return [];
      const allValues = this.columnValues[col];

      const used = new Set<string>();
      this.ruleParameters.domain_sameEntity.forEach((item, idx) => {
        if (idx === index) {
          if (type === "main" && item.sameEntityList) {
            item.sameEntityList.forEach((v) => used.add(v));
          }
          if (type === "same" && item.mainEntity) {
            used.add(item.mainEntity);
          }
        } else {
          if (item.mainEntity) used.add(item.mainEntity);
          if (item.sameEntityList)
            item.sameEntityList.forEach((v) => used.add(v));
        }
      });

      return allValues.filter((v) => !used.has(v));
    },
    getAvailableSequenceValues(index: number, type: "current" | "next") {
      const col = this.selectedColumns[0];
      if (!col || !this.columnValues[col]) return [];
      const allValues = this.columnValues[col];

      if (type === "current") {
        const usedCurrentValues = new Set<string>();
        this.ruleParameters.sequence.forEach((item, idx) => {
          if (idx !== index && item.currentValue) {
            usedCurrentValues.add(item.currentValue);
          }
        });
        return allValues.filter((v) => !usedCurrentValues.has(v));
      } else {
        return allValues;
      }
    },
    addSequencePair() {
      this.ruleParameters.sequence.push({
        currentValue: "",
        nextValues: [],
      });
    },
    removeSequencePair(index: number) {
      this.ruleParameters.sequence.splice(index, 1);
    },
    addMappingPair() {
      const newPair: Record<string, string[]> = {};
      this.selectedColumns.forEach((col) => {
        newPair[col] = [];
      });
      this.ruleParameters.mapping_cardinality.push(newPair);
    },
    removeMappingPair(index: number) {
      this.ruleParameters.mapping_cardinality.splice(index, 1);
    },
    getAvailableMappingValues(index: number, col: string) {
      const allValues = this.columnValues[col] || [];
      const usedValues = new Set<string>();
      this.ruleParameters.mapping_cardinality.forEach((pair, idx) => {
        if (idx !== index && pair[col]) {
          if (Array.isArray(pair[col])) {
            pair[col].forEach((v) => usedValues.add(v));
          }
        }
      });
      return allValues.filter((v) => !usedValues.has(v));
    },
    isNumericOrDate(col: string) {
      const type = this.existingRules[col]?.type;
      return type === "numeric" || type === "datetime";
    },
    isCharacterColumn(col: string) {
      return this.existingRules[col]?.type === "character";
    },
    addLogicalRelation() {
      const newRelation: any = {};
      const allCols = [
        ...this.ruleParameters.logical_and_condition.conditionColumns,
        ...this.ruleParameters.logical_and_condition.constraintColumns,
      ];
      allCols.forEach((col) => {
        if (this.isNumericOrDate(col)) {
          newRelation[col] = { min: "", min_op: "<", max: "", max_op: "<" };
        } else {
          newRelation[col] = { value: [] };
        }
      });
      this.ruleParameters.logical_and_condition.relations.push(newRelation);
    },
    removeLogicalRelation(index: number) {
      this.ruleParameters.logical_and_condition.relations.splice(index, 1);
    },
    updateLogicalRelations() {
      const allCols = [
        ...this.ruleParameters.logical_and_condition.conditionColumns,
        ...this.ruleParameters.logical_and_condition.constraintColumns,
      ];
      this.ruleParameters.logical_and_condition.relations.forEach((rel) => {
        allCols.forEach((col) => {
          if (!rel[col]) {
            if (this.isNumericOrDate(col)) {
              rel[col] = { min: "", min_op: "<", max: "", max_op: "<" };
            } else {
              rel[col] = { value: [] };
            }
          } else if (!this.isNumericOrDate(col)) {
            const currentVal = rel[col].value;
            if (!Array.isArray(currentVal)) {
              rel[col].value =
                currentVal === undefined ||
                currentVal === null ||
                currentVal === ""
                  ? []
                  : [currentVal];
            }
          }
        });
      });
    },
    getAvailableLogicalValues(index: number, col: string) {
      const allValues = this.columnValues[col] || [];
      // Only filter for character types in Condition columns
      if (
        this.isNumericOrDate(col) ||
        !this.ruleParameters.logical_and_condition.conditionColumns.includes(
          col
        )
      ) {
        return allValues;
      }
      return allValues;
    },
    expandLogicalRelationsForSubmit() {
      const { logical_and_condition } = this.ruleParameters;
      const { conditionColumns, constraintColumns, relations } =
        logical_and_condition;

      if (!Array.isArray(relations) || !conditionColumns.length) {
        return relations || [];
      }

      const expandedRelations: Record<string, any>[] = [];

      relations.forEach((rel) => {
        // Build cartesian product over condition columns (equality-based) while keeping constraints intact.
        const buildCombinations = (idx: number, acc: Record<string, any>) => {
          if (idx >= conditionColumns.length) {
            // Attach constraint side (unchanged) and store
            constraintColumns.forEach((col) => {
              acc[col] = JSON.parse(JSON.stringify(rel[col]));
            });
            expandedRelations.push(acc);
            return;
          }

          const col = conditionColumns[idx];
          const valObj = rel[col] || {};

          if (this.isNumericOrDate(col)) {
            // Range-based: keep as-is
            buildCombinations(
              idx + 1,
              Object.assign({}, acc, {
                [col]: JSON.parse(JSON.stringify(valObj)),
              })
            );
            return;
          }

          const values = Array.isArray(valObj.value) ? valObj.value : [];
          const safeValues = values.length ? values : [""];
          safeValues.forEach((v) => {
            buildCombinations(
              idx + 1,
              Object.assign({}, acc, {
                [col]: { value: [v] },
              })
            );
          });
        };

        buildCombinations(0, {});
      });

      return expandedRelations;
    },
  },
  async mounted() {
    const info = await api_get_rule_creation_info();
    this.columns = info.columns || [];
    this.existingRules = info.rules || {};
    this.columnValues = info.columnValues || {};
    this.measureLogicalValueWidth();
    window.addEventListener("resize", this.measureLogicalValueWidth);
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.measureLogicalValueWidth);
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
  z-index: 2000;
}

.modal-container {
  width: 38vw;
  padding-bottom: 2vh;
  border-radius: 0.92vh;
  border: 0.23vh solid #cce2f0;
  background: #f7f9fe;
  box-shadow: 0px 0px 10px 0px rgba(149, 149, 149, 0.25);
  display: flex;
  flex-direction: column;
  position: relative;
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
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: all 0.2s ease;
  background-color: #ffffff;
}

.close-icon {
  color: #5e5e5e;
  font-size: 2vh;
  font-weight: bold;
  line-height: 1;
  display: block;
  margin-top: 0.2vh;
}

.modal-header {
  height: 6vh;
  display: flex;
  align-items: center;
  padding-left: 1.5vw;
  border-bottom: 1px solid #e0e0e0;
}

.title-text {
  color: #4570b6;
  font-family: Roboto;
  font-size: 2vh;
  font-weight: 900;
}

.modal-content {
  padding: 2vh 1.5vw;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2.5vh;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 1vh;
}

.form-label {
  font-size: 1.5vh;
  font-weight: bold;
  color: #304166;
  font-family: Roboto;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.label-icon {
  width: 1.5vh;
  height: 1.5vh;
  margin-right: 0.5vh;
}

.parameter-container {
  display: flex;
  align-items: center;
  gap: 0.5vh;
}

.parameter-label {
  font-size: 1.4vh;
  font-weight: bold;
  color: #304166;
  font-family: Roboto;
  white-space: nowrap;
}

.parameter-label-aligned {
  width: 12vw;
  text-align: left;
}

.parameter-input {
  flex: 1;
}

.modal-footer {
  height: 6vh;
  display: flex;
  justify-content: flex-end;
  padding-right: 1.5vw;
  align-items: center;
  border-top: 1px solid #e0e0e0;
  margin-top: 1vh;
}

.submit-btn {
  background-color: #4570b6;
  padding: 0.8vh 2.5vh;
  border-radius: 0.46vh;
  color: #fff;
  font-family: Roboto;
  font-size: 1.6vh;
  font-weight: 600;
  cursor: pointer;
  border: none;
  display: flex;
  align-items: center;
  gap: 0.5vw;
}

.submit-btn:hover {
  background-color: #355a96;
}

.placeholder-box {
  padding: 1.5vh;
  background: #fff;
  border: 1px dashed #ccc;
  border-radius: 4px;
  color: #999;
  font-size: 1.4vh;
  min-height: 5vh;
  display: flex;
  align-items: center;
}

.custom-select {
  width: 100%;
}

.custom-input {
  width: 100%;
}

.range-group {
  display: flex;
  align-items: center;
  gap: 0.5vw;
  flex: 1;
}

.range-input {
  flex: 1;
  min-width: 0;
  height: 32px;
}

.range-select {
  width: 4.5vw;
  height: 32px;
}

.range-column-name {
  font-size: 1.4vh;
  font-weight: bold;
  color: #304166;
  padding: 0 0.5vw;
  background: #eef2f7;
  border-radius: 4px;
  height: 32px;
  line-height: 32px;
  flex: 2;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.same-entity-pair {
  display: flex;
  flex-direction: column;
  gap: 1vh;
  border: 1px solid #d1e7dd;
  border-radius: 0.5vh;
  padding: 1.5vh;
  background: #fff;
}

.remove-pair-container {
  display: flex;
  justify-content: flex-end;
}

.remove-pair-btn {
  background: #f8d7da;
  color: #842029;
  border: none;
  padding: 0.5vh 1.5vw;
  border-radius: 0.5vh;
  cursor: pointer;
  font-size: 1.4vh;
}

.add-pair-btn {
  background: #d1e7dd;
  color: #0f5132;
  border: none;
  padding: 0.5vh 1.5vw;
  border-radius: 0.5vh;
  cursor: pointer;
  font-size: 1.4vh;
  margin-top: 1vh;
}

.domain-consistency-group {
  display: flex;
  flex-direction: column;
}

.domain-pair-wrapper {
  border: 1px solid #e0e0e0;
  padding: 1vh;
  border-radius: 4px;
  margin-bottom: 1vh;
  background-color: #fff;
  box-sizing: border-box;
}

.add-btn {
  background-color: #4570b6;
  color: white;
  border: none;
  padding: 0.5vh 1vh;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.4vh;
  margin-top: 0.5vh;
  align-self: flex-start;
  font-family: Roboto;
  font-weight: bold;
}

.remove-btn {
  background-color: #ff4d4f;
  color: white;
  border: none;
  padding: 0.5vh 1vh;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.4vh;
  margin-top: 1vh;
}

.domain-label {
  width: 6vw;
  text-align: left;
}

.sequence-group {
  display: flex;
  flex-direction: column;
  max-height: 40vh;
  overflow-y: auto;
  padding-right: 0.5vw;
}

.sequence-pair-wrapper {
  border: 1px solid #e0e0e0;
  padding: 1vh;
  border-radius: 4px;
  margin-bottom: 1vh;
  background-color: #fff;
  box-sizing: border-box;
}

.sequence-label {
  width: 9vw;
  text-align: left;
}

.remove-btn-wrapper {
  display: flex;
}

.domain-remove {
  margin-left: calc(6vw + 0.5vh);
}

.sequence-remove {
  margin-left: calc(9vw + 0.5vh);
}

.difference-columns-wrapper {
  display: flex;
  gap: 0.5vh;
  flex: 2;
  overflow-x: auto;
  align-items: center;
  justify-content: flex-start;
  height: 42px;
  padding-bottom: 4px;
}

.difference-columns-wrapper::-webkit-scrollbar {
  height: 4px;
}

.difference-columns-wrapper::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 2px;
}

.difference-columns-wrapper::-webkit-scrollbar-track {
  background: transparent;
}

.difference-column-item {
  flex: 0 0 auto;
  max-width: 10vw;
  height: 32px;
  line-height: 32px;
}

.logical-group-container {
  display: flex;
  flex-direction: column;
  gap: 1vh;
}

.logical-relations-area {
  display: flex;
  flex-direction: column;
  max-height: 40vh;
  overflow-y: auto;
  padding-right: 0.5vw;
  margin-top: 1vh;
}

.logical-pair-wrapper {
  border: 1px solid #e0e0e0;
  padding: 1vh;
  border-radius: 4px;
  margin-bottom: 1vh;
  background-color: #fff;
  box-sizing: border-box;
}

.logical-section-label {
  font-size: 1.4vh;
  font-weight: bold;
  color: #4570b6;
  margin-bottom: 0.5vh;
}

.logical-remove {
  justify-content: flex-end;
  margin-top: 0.5vh;
}

.logical-col-label {
  width: 8vw;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
}

.clear-template-btn {
  background-color: #f4f6fb;
  color: #304166;
  border: 1px solid #d3d9f3;
  padding: 0.5vh 1vw;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1.3vh;
  margin-left: 0.5vw;
}

.clear-template-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.logical-template-hint {
  font-size: 1.3vh;
  color: #c05621;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 4px;
  padding: 0.8vh 1vw;
  margin-bottom: 1vh;
}

.order-condition-container {
  display: flex;
  flex-direction: column;
  gap: 1vh;
  padding: 1vh;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.order-row {
  display: flex;
  align-items: center;
  gap: 0.5vw;
}

.order-label {
  font-size: 1.4vh;
  font-weight: bold;
  color: #304166;
  width: 7vw;
}

.order-col-select {
  flex: 2;
}

.order-type-select {
  flex: 1;
}
</style>
