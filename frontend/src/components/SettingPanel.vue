<template>
  <div class="block-2">
    <template v-if="localCard">
      <div class="info-row">
        <div class="info-group">
          <div class="label">Column</div>
          <div class="column-display-container" ref="topColumnContainer">
            <span
              v-for="(col, index) in getVisibleColumnNames(
                displayColumnNames,
                'top'
              )"
              :key="index"
              :class="[
                'value-box',
                {
                  'value-box--draggable': canDragColumns,
                  'value-box--drag-over':
                    canDragColumns && dragOverColumnIndex === index,
                },
              ]"
              :ref="`topColumnItem-${index}`"
              :draggable="canDragColumns"
              @dragstart="onColumnChipDragStart(index)"
              @dragover.prevent="onColumnChipDragOver(index)"
              @drop.prevent="onColumnChipDrop(index)"
              @dragend="resetColumnDragState"
            >
              {{ col }}
            </span>
            <el-tooltip
              v-if="getHiddenColumnCount(displayColumnNames, 'top') > 0"
              effect="dark"
              placement="top"
              :show-after="2000"
              :content="
                getHiddenColumnNames(displayColumnNames, 'top').join(', ')
              "
              popper-class="custom-tooltip"
            >
              <span class="value-box overflow-indicator">
                +{{ getHiddenColumnCount(displayColumnNames, "top") }}
              </span>
            </el-tooltip>
          </div>
        </div>
      </div>
      <div class="type-row">
        <div class="info-group-2">
          <div class="label">Rule Type</div>
          <div class="type-container">
            <img
              :src="getTypeIcon(localCard.relationType)"
              :alt="localCard.relationType"
              class="type-icon"
            />
            <span class="type-text">{{
              getDisplayRuleType(localCard.relationType)
            }}</span>
          </div>
        </div>
      </div>
      <div class="paramater-row">
        <div class="label">Paramaters</div>
      </div>
      <div
        :class="[
          'value-row',
          {
            'value-row--multiple':
              localCard?.relationType === 'MultipleCondition',
          },
        ]"
      >
        <div v-if="localCard.relationType === 'Missing'" class="missingValue">
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          MissingDetectFlag
          <el-select
            v-model="localCard.ruleValue.missingDetectFlag"
            placeholder="Select value"
            placement="bottom"
          >
            <el-option
              v-for="item in [
                { value: true, label: 'true' },
                { value: false, label: 'false' },
              ]"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            >
              <span class="option-text">{{ item.label }}</span>
            </el-option>
          </el-select>
        </div>
        <div v-if="localCard.relationType === 'Duplicate'" class="missingValue">
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          DuplicateDetectFlag
          <el-select
            v-model="localCard.ruleValue.duplicateDetectFlag"
            placeholder="Select value"
            placement="bottom"
          >
            <el-option
              v-for="item in [
                { value: true, label: 'true' },
                { value: false, label: 'false' },
              ]"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            >
              <span class="option-text">{{ item.label }}</span>
            </el-option>
          </el-select>
        </div>
        <div
          v-if="localCard.relationType === 'MultipleDuplicate'"
          class="missingValue"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          DuplicateDetectFlag
          <el-select
            v-model="localCard.ruleValue"
            placeholder="Select value"
            placement="bottom"
          >
            <el-option
              v-for="item in [
                { value: true, label: 'true' },
                { value: false, label: 'false' },
              ]"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            >
              <span class="option-text">{{ item.label }}</span>
            </el-option>
          </el-select>
        </div>
        <div v-if="localCard.relationType === 'Type'" class="parameter-type">
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          ColumnType
        </div>
        <div v-if="localCard.relationType === 'Type'" class="unchange-value">
          {{ localCard.ruleValue }}
        </div>
        <div
          v-if="localCard.relationType === 'Difference'"
          class="parameter-name difference-parameter-name"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <el-tooltip
            effect="dark"
            placement="top"
            :content="'Difference'"
            :disabled="'Difference'.length <= getMaxLabelLength()"
            popper-class="custom-tooltip"
          >
            <span>Difference</span>
          </el-tooltip>
        </div>
        <div
          v-if="localCard.relationType === 'Difference'"
          class="differenceRange difference-range"
        >
          <el-input-number
            v-model="localCard.ruleValue.start"
            :precision="2"
            :controls="false"
            class="range-input"
          />
          <el-select
            v-model="localCard.ruleValue.startInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[0]"
            :disabled="localCard.columnName[0].length <= 10"
            popper-class="custom-tooltip"
          >
            <span class="range-separator">{{ localCard.columnName[0] }}</span>
          </el-tooltip>
          <el-select
            v-model="localCard.ruleValue.endInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-input-number
            v-model="localCard.ruleValue.end"
            :precision="2"
            :controls="false"
            class="range-input"
          />
        </div>

        <div
          v-if="localCard.relationType === 'relativeDifference'"
          class="missingValue"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          Relative Difference
        </div>
        <div
          v-if="localCard.relationType === 'relativeDifference'"
          class="differenceRange"
        >
          <el-input-number
            v-model="localCard.ruleValue.start"
            :precision="2"
            :controls="false"
            class="range-input"
          />
          <el-select
            v-model="localCard.ruleValue.startInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[0]"
            :disabled="localCard.columnName[0].length <= 10"
            popper-class="custom-tooltip"
          >
            <span class="range-separator">{{ localCard.columnName[0] }}</span>
          </el-tooltip>
          <el-select
            v-model="localCard.ruleValue.endInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-input-number
            v-model="localCard.ruleValue.end"
            :precision="2"
            :controls="false"
            class="range-input"
          />
        </div>
        <div v-if="localCard.relationType === 'Range'" class="parameter-name">
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <el-tooltip
            effect="dark"
            placement="top"
            :content="'Range'"
            :disabled="'Range'.length <= getMaxLabelLength()"
            popper-class="custom-tooltip"
          >
            <span class="range-label-text">Range</span>
          </el-tooltip>
        </div>
        <div v-if="localCard.relationType === 'Range'" class="differenceRange">
          <el-input-number
            v-model="localCard.ruleValue.start"
            :precision="2"
            :controls="false"
            class="range-input"
          />
          <el-select
            v-model="localCard.ruleValue.startInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[0]"
            :disabled="localCard.columnName[0].length <= 10"
            popper-class="custom-tooltip"
          >
            <span class="range-separator">{{ localCard.columnName[0] }}</span>
          </el-tooltip>
          <el-select
            v-model="localCard.ruleValue.endInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-input-number
            v-model="localCard.ruleValue.end"
            :precision="2"
            :controls="false"
            class="range-input"
          />
        </div>
        <div v-if="localCard.relationType === 'Outlier'" class="parameter-name">
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <el-tooltip
            effect="dark"
            placement="top"
            :content="'Outlier'"
            :disabled="'Outlier'.length <= getMaxLabelLength()"
            popper-class="custom-tooltip"
          >
            <span class="range-label-text">Outlier</span>
          </el-tooltip>
        </div>
        <div
          v-if="localCard.relationType === 'Outlier'"
          class="differenceRange"
        >
          <el-input-number
            v-model="localCard.ruleValue.start"
            :precision="2"
            :controls="false"
            class="range-input"
          />
          <el-select
            v-model="localCard.ruleValue.startInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[0]"
            :disabled="localCard.columnName[0].length <= 10"
            popper-class="custom-tooltip"
          >
            <span class="range-separator">{{ localCard.columnName[0] }}</span>
          </el-tooltip>
          <el-select
            v-model="localCard.ruleValue.endInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-input-number
            v-model="localCard.ruleValue.end"
            :precision="2"
            :controls="false"
            class="range-input"
          />
        </div>
        <div
          v-if="localCard.relationType === 'Distribution'"
          class="parameter-name"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          Distribution
        </div>
        <div
          v-if="localCard.relationType === 'Distribution'"
          class="unchange-value"
        >
          {{ localCard.ruleValue }}
        </div>
        <div v-if="localCard.relationType === 'Compare'" class="parameter-name">
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          Relation
          <el-select
            v-model="localCard.ruleValue"
            placeholder="Select relation"
            placement="bottom"
          >
            <el-option
              v-for="item in [
                { value: 'smaller', label: 'smaller' },
                { value: 'smaller_equal', label: 'smaller_equal' },
                { value: 'equal', label: 'equal' },
                { value: 'not_equal', label: 'not equal' },
                { value: 'larger', label: 'larger' },
                { value: 'larger_equal', label: 'larger_equal' },
              ]"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            >
              <span class="option-text">{{ item.label }}</span>
            </el-option>
          </el-select>
        </div>
        <div
          v-if="localCard.relationType === 'Sequence'"
          class="parameter-name-two sequence-parameter-name"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          CurrentValue
          <el-select
            id="sequenceValue"
            v-model="localSelectedSequenceValue"
            @change="updateAllowedNext"
            placeholder=""
            placement="bottom"
            class="sequence-select"
          >
            <el-option
              v-for="sequence in sequenceRules[String(localCard.columnName)] ||
              []"
              :key="sequence.value"
              :value="sequence.value"
            >
              <span class="option-text">{{ sequence.value }}</span>
            </el-option>
          </el-select>
        </div>
        <div
          v-if="localCard.relationType === 'Logical and condition'"
          class="parameter-name-lookup"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[0]"
            :disabled="localCard.columnName[0].length <= getMaxLabelLength()"
            popper-class="custom-tooltip"
          >
            <span class="lookup-label">{{
              truncateColumnName(localCard.columnName[0])
            }}</span>
          </el-tooltip>
          <el-select
            v-if="localCard.relationType === 'Logical and condition'"
            id="conditionValue"
            v-model="localSelectedConditionValue"
            @change="updateConstraintValue"
            placement="bottom"
            placeholder=""
            class="lookup-select"
          >
            <el-option
              v-for="condition in conditionRules[
                localCard.columnName.join('+')
              ]"
              :key="condition.conditionValue"
              :value="condition.conditionValue"
            >
              <span class="option-text">{{ condition.conditionValue }}</span>
            </el-option>
          </el-select>
        </div>
        <div
          v-if="localCard.relationType === 'MultipleCondition'"
          class="multiple-condition-container"
        >
          <div
            v-for="(row, rowIndex) in getMultipleConditionRows()"
            :key="rowIndex"
            class="multiple-condition-row"
          >
            <div
              v-for="(column, colIndex) in row"
              :key="colIndex"
              class="multiple-condition-item"
              :class="{ 'placeholder-item': column.type === 'placeholder' }"
            >
              <template v-if="column.type !== 'placeholder'">
                <img
                  src="/cardpanel_icon/parameter-arrow.svg"
                  class="parameter-arrow"
                />
                <el-tooltip
                  effect="dark"
                  placement="top"
                  :content="column.name"
                  :disabled="!column.needsTooltip"
                  popper-class="custom-tooltip"
                >
                  <span class="multiple-condition-label">{{
                    column.displayName
                  }}</span>
                </el-tooltip>
                <el-select
                  v-if="
                    column.type.startsWith('condition') &&
                    column.conditionIndex !== undefined
                  "
                  v-model="
                    localSelectedMultiConditionValues[column.conditionIndex]
                  "
                  @change="handleMultiConditionChange(column.conditionIndex)"
                  placement="bottom"
                  placeholder=""
                  class="multiple-condition-select"
                  :ref="`conditionSelect_${column.conditionIndex}`"
                >
                  <template
                    #prefix
                    v-if="
                      getConditionSelectionList(column.conditionIndex!).length
                    "
                  >
                    <div class="select-tag-container">
                      <span
                        v-for="tag in getVisibleConditionTags(
                          column.conditionIndex!
                        )"
                        :key="tag"
                        class="select-tag"
                      >
                        {{ tag }}
                      </span>
                      <span
                        v-if="getHiddenConditionTagCount(column.conditionIndex!) > 0"
                        class="select-tag select-tag--more"
                      >
                        +{{
                          getHiddenConditionTagCount(column.conditionIndex!)
                        }}
                      </span>
                    </div>
                  </template>
                  <el-option
                    v-for="condition in getUniqueConditionValues(
                      column.conditionIndex
                    )"
                    :key="condition"
                    :value="condition"
                  >
                    <div class="option-with-checkbox">
                      <el-checkbox
                        :model-value="
                          isConditionValueChecked(
                            column.conditionIndex!,
                            condition
                          )
                        "
                        @change="
                          (checked: boolean) =>
                            toggleConditionValueCheckbox(
                              column.conditionIndex!,
                              condition,
                              checked
                            )
                        "
                        @click.stop
                      />
                      <span class="option-text">{{ condition }}</span>
                    </div>
                  </el-option>
                </el-select>
                <template v-else-if="column.type === 'constraint'">
                  <div
                    v-if="column.constraintType === 'RangeBased'"
                    class="differenceRange"
                  >
                    <el-input-number
                      v-model="multiConstraintRangeValues[column.constraintIndex!].start"
                      :controls="false"
                      :precision="2"
                      class="range-input"
                    />
                    <el-select
                      v-model="multiConstraintRangeValues[column.constraintIndex!].startInclusive"
                      class="range-operator"
                      :popper-append-to-body="false"
                    >
                      <el-option :value="true" label="≤" />
                      <el-option :value="false" label="<" />
                    </el-select>
                    <span class="range-separator">
                      {{
                        getConstraintColumnNameByIndex(column.constraintIndex!)
                      }}
                    </span>
                    <el-select
                      v-model="multiConstraintRangeValues[column.constraintIndex!].endInclusive"
                      class="range-operator"
                      :popper-append-to-body="false"
                    >
                      <el-option :value="true" label="≤" />
                      <el-option :value="false" label="<" />
                    </el-select>
                    <el-input-number
                      v-model="multiConstraintRangeValues[column.constraintIndex!].end"
                      :controls="false"
                      :precision="2"
                      class="range-input"
                    />
                  </div>
                  <el-select
                    v-else
                    v-model="multiConstraintEqualityValues[column.constraintIndex!]"
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    placeholder="Select constraint values"
                    placement="bottom"
                    class="multiple-condition-select"
                    :ref="`constraintSelect_${column.constraintIndex}`"
                    :max-collapse-tags="
                      getMaxConstraintCollapseTags(column.constraintIndex!)
                    "
                    @change="handleMultiConstraintChange"
                  >
                    <el-option
                      v-for="value in getAvailableMultiConstraintValues(
                        column.constraintIndex!
                      )"
                      :key="value"
                      :label="value"
                      :value="value"
                      class="truncate-option"
                    >
                      <div class="option-with-checkbox">
                        <el-checkbox
                          :model-value="
                            isConstraintValueChecked(
                              column.constraintIndex!,
                              value
                            )
                          "
                          @change="
                            (checked: boolean) =>
                              toggleConstraintValueCheckbox(
                                column.constraintIndex!,
                                value,
                                checked
                              )
                          "
                          @click.stop
                        />
                        <span class="option-text">{{ value }}</span>
                      </div>
                    </el-option>
                  </el-select>
                </template>
              </template>
            </div>
          </div>
        </div>
        <div
          v-if="localCard.relationType === 'Lookup'"
          class="parameter-name-lookup"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <span class="lookup-label">ParentValue</span>
          <el-select
            v-if="localCard.relationType === 'Lookup'"
            v-model="localSelectedParentValue"
            placeholder="Select parent value"
            placement="bottom"
            @change="updateChildValues"
            class="lookup-select"
          >
            <el-option
              v-for="value in availableParentValues"
              :key="value"
              :label="value"
              :value="value"
            >
              <span class="option-text">{{ value }}</span>
            </el-option>
          </el-select>
        </div>
      </div>
      <div class="value-row-2">
        <div v-if="localCard.relationType === 'Missing'" class="missingValue">
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          SpecialMissingValues
          <el-select
            v-model="localCard.ruleValue.specialMissingValueList"
            multiple
            filterable
            allow-create
            default-first-option
            :reserve-keyword="false"
            placeholder="input special missing values"
            @change="handleSpecialMissingValuesChange"
            :collapse-tags="false"
            :collapse-tags-tooltip="false"
          >
            <el-option
              v-for="value in localCard.ruleValue.specialMissingValueList"
              :key="value"
              :label="value"
              :value="value"
            >
            </el-option>
          </el-select>
        </div>
        <div
          v-if="localCard.relationType === 'Sequence'"
          class="parameter-name-two sequence-parameter-name"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          allowed_next
          <el-select
            v-model="localSelectedAllowedNext"
            multiple
            :collapse-tags="true"
            :collapse-tags-tooltip="true"
            max-collapse-tags="2"
            placeholder="Select allowed_next values"
            placement="bottom"
            class="sequence-select"
          >
            <el-option
              v-for="value in allSequenceValues"
              :key="value"
              :label="value"
              :value="value"
            />
          </el-select>
        </div>
        <div
          v-if="
            localCard.relationType === 'Logical and condition' &&
            localCard.constraintType?.[0] === 'RangeBased'
          "
          class="parameter-name"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[1]"
            :disabled="localCard.columnName[1].length <= getMaxLabelLength()"
            popper-class="custom-tooltip"
          >
            <span class="range-label-text">{{
              truncateColumnName(localCard.columnName[1])
            }}</span>
          </el-tooltip>
        </div>
        <div
          v-if="
            localCard.relationType === 'Logical and condition' &&
            localCard.constraintType?.[0] === 'RangeBased'
          "
          class="differenceRange"
        >
          <el-input-number
            v-model="localConstraintValue_Range.start"
            :controls="false"
            :precision="2"
            class="range-input"
          />
          <el-select
            v-model="localConstraintValue_Range.startInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[1]"
            :disabled="localCard.columnName[1].length <= 10"
            popper-class="custom-tooltip"
          >
            <span class="range-separator">{{ localCard.columnName[1] }}</span>
          </el-tooltip>
          <el-select
            v-model="localConstraintValue_Range.endInclusive"
            class="range-operator"
            :popper-append-to-body="false"
          >
            <el-option :value="true" label="≤" />
            <el-option :value="false" label="<" />
          </el-select>
          <el-input-number
            v-model="localConstraintValue_Range.end"
            :controls="false"
            :precision="2"
            class="range-input"
          />
        </div>
        <div
          v-if="
            localCard.relationType === 'Logical and condition' &&
            localCard.constraintType?.[0] === 'EqualityBased'
          "
          class="parameter-name-lookup"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <el-tooltip
            effect="dark"
            placement="top"
            :content="localCard.columnName[1]"
            :disabled="localCard.columnName[1].length <= getMaxLabelLength()"
            popper-class="custom-tooltip"
          >
            <span class="lookup-label">{{
              truncateColumnName(localCard.columnName[1])
            }}</span>
          </el-tooltip>
          <el-select
            v-model="localConstraintValue_Equality"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="Select constraint values"
            placement="bottom"
            class="lookup-select"
            :max-collapse-tags="
              getMaxCollapseTags(localConstraintValue_Equality)
            "
          >
            <el-option
              v-for="value in availableConstraintValues"
              :key="value"
              :label="value"
              :value="value"
              class="truncate-option"
            >
              <span class="option-text">{{ value }}</span>
            </el-option>
          </el-select>
        </div>
        <div
          v-if="localCard.relationType === 'Lookup'"
          class="parameter-name-lookup"
        >
          <img
            src="/cardpanel_icon/parameter-arrow.svg"
            class="parameter-arrow"
          />
          <span class="lookup-label">ChildValues</span>
          <el-select
            v-if="localCard.relationType === 'Lookup'"
            v-model="localSelectedChildValues"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="Select child values"
            placement="bottom"
            class="lookup-select"
            :max-collapse-tags="getMaxCollapseTags(localSelectedChildValues)"
          >
            <el-option
              v-for="value in allPossibleChildValues"
              :key="value"
              :label="value"
              :value="value"
              class="truncate-option"
            >
              <span class="option-text">{{ value }}</span>
            </el-option>
          </el-select>
        </div>
      </div>
      <div class="submit-button-container">
        <el-button
          type="primary"
          size="small"
          @click="syncToBackend"
          class="submit-button"
        >
          Submit
        </el-button>
      </div>
    </template>
    <template v-else>
      <div class="default-message">Please Choose Validation Card</div>
    </template>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from "vue";
import {
  ValidationCard,
  SequenceRule,
  ConditionRule,
  ConstraintValue,
  Row,
} from "@/types/types";
import { api } from "@/utils/callapi";
import { ElMessage, ElMessageBox } from "element-plus";

export default defineComponent({
  name: "SettingPanel",
  props: {
    chooseCard: {
      type: Object as PropType<ValidationCard | null>,
      default: null,
    },
    // Controls whether to listen for matrix events to avoid duplicate responses with DetailView
    enableMatrixListeners: {
      type: Boolean,
      default: false,
    },
    sequenceRules: {
      type: Object as PropType<{ [key: string]: SequenceRule[] }>,
      default: () => ({}),
    },
    conditionRules: {
      type: Object as PropType<{ [key: string]: ConditionRule[] }>,
      default: () => ({}),
    },
    multiConditionRules: {
      type: Object as PropType<{ [key: string]: any[] }>,
      default: () => ({}),
    },
    lookupRules: {
      type: Object as PropType<{ [key: string]: any[] }>,
      default: () => ({}),
    },
    csvData: {
      type: Array as PropType<Row[]>,
      default: () => [],
    },
  },
  computed: {
    displayColumnNames(): string[] {
      if (
        this.localCard &&
        this.localCard.relationType === "MultipleCondition" &&
        this.localDisplayColumnOrder.length === this.localCard.columnName.length
      ) {
        return this.localDisplayColumnOrder;
      }
      return this.localCard?.columnName || [];
    },
    canDragColumns(): boolean {
      return (
        !!this.localCard &&
        this.localCard.relationType === "MultipleCondition" &&
        this.localDisplayColumnOrder.length > 1
      );
    },
  },
  emits: ["update-rule", "multi-condition-order-updated"],
  data() {
    return {
      localCard: null as ValidationCard | null,
      localSelectedSequenceValue: "",
      localSelectedAllowedNext: [] as string[],
      allSequenceValues: [] as string[],
      localSelectedConditionValue: "",
      localConstraintValue_Range: {
        start: 0,
        end: 0,
        startInclusive: false,
        endInclusive: false,
      } as ConstraintValue,
      localConstraintValue_Equality: [] as string[],
      availableConstraintValues: [] as string[],
      localSelectedParentValue: "",
      localSelectedChildValues: [] as string[],
      availableParentValues: [] as string[],
      allPossibleChildValues: [] as string[],
      localSelectedMultiConditionValues: [] as string[],
      multiConstraintRangeValues: {} as Record<number, ConstraintValue>,
      multiConstraintEqualityValues: {} as Record<number, string[]>,
      availableMultiConstraintValuesMap: {} as Record<number, string[]>,
      conditionValueSelections: {} as Record<number, string[]>,
      activeMultiConditionRuleIndex: -1,
      activeMultiConditionRule: null as any,
      localDisplayColumnOrder: [] as string[],
      initialDisplayColumnOrder: [] as string[],
      draggedColumnIndex: null as number | null,
      dragOverColumnIndex: null as number | null,
      conditionSelectWidths: {} as Record<number, number>,
      constraintSelectWidths: {} as Record<number, number>,
    };
  },
  watch: {
    chooseCard: {
      handler(newCard) {
        this.resetMultiConstraintState();
        if (newCard) {
          const cardCopy = JSON.parse(
            JSON.stringify(newCard)
          ) as ValidationCard;
          this.localCard = cardCopy;
          this.initializeCardState(cardCopy);
          this.initializeDisplayColumnOrder(cardCopy);
          this.$nextTick(() => {
            this.measureConditionSelectWidths();
          });
        } else {
          this.localCard = null;
          this.initializeDisplayColumnOrder(null);
        }
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    onColumnChipDragStart(index: number) {
      if (!this.canDragColumns) return;
      this.startColumnDrag(index);
    },
    onColumnChipDragOver(index: number) {
      if (!this.canDragColumns) return;
      this.handleColumnDragOver(index);
    },
    onColumnChipDrop(index: number) {
      if (!this.canDragColumns) return;
      this.handleColumnDrop(index);
    },
    initializeDisplayColumnOrder(card: ValidationCard | null) {
      if (!card) {
        this.localDisplayColumnOrder = [];
        this.initialDisplayColumnOrder = [];
        return;
      }
      const sourceOrder =
        Array.isArray(card.displayColumnOrder) &&
        card.displayColumnOrder.length === card.columnName.length
          ? [...card.displayColumnOrder]
          : [...card.columnName];
      this.localDisplayColumnOrder = sourceOrder;
      this.initialDisplayColumnOrder = [...sourceOrder];
    },
    startColumnDrag(index: number) {
      this.draggedColumnIndex = index;
      this.dragOverColumnIndex = index;
    },
    handleColumnDragOver(index: number) {
      if (this.draggedColumnIndex == null) return;
      this.dragOverColumnIndex = index;
    },
    handleColumnDrop(index: number) {
      if (this.draggedColumnIndex == null) {
        return;
      }
      this.reorderDisplayColumns(this.draggedColumnIndex, index);
      this.resetColumnDragState();
    },
    resetColumnDragState() {
      this.draggedColumnIndex = null;
      this.dragOverColumnIndex = null;
    },
    reorderDisplayColumns(fromIndex: number, toIndex: number) {
      if (
        fromIndex === toIndex ||
        fromIndex == null ||
        toIndex == null ||
        fromIndex < 0 ||
        toIndex < 0 ||
        fromIndex >= this.localDisplayColumnOrder.length ||
        toIndex >= this.localDisplayColumnOrder.length
      ) {
        return;
      }
      const updated = [...this.localDisplayColumnOrder];
      const [moved] = updated.splice(fromIndex, 1);
      updated.splice(toIndex, 0, moved);
      this.localDisplayColumnOrder = updated;
      if (this.localCard) {
        this.localCard.displayColumnOrder = [...updated];
      }
    },
    measureConditionSelectWidths() {
      if (
        !this.localCard ||
        this.localCard.relationType !== "MultipleCondition"
      ) {
        return;
      }
      const widths: Record<number, number> = {};
      const constraintWidths: Record<number, number> = {};
      const conditionCount = this.getConditionColumnCount();
      for (let i = 0; i < conditionCount; i++) {
        const refKey = `conditionSelect_${i}`;
        const refEl = (this.$refs as any)[refKey];
        const el = Array.isArray(refEl) ? refEl[0] : refEl;
        const width =
          el?.$el?.offsetWidth ||
          el?.$el?.clientWidth ||
          el?.offsetWidth ||
          el?.clientWidth;
        if (width) {
          widths[i] = width;
        }
      }
      const constraintCount = this.getConstraintColumnCount();
      for (let i = 0; i < constraintCount; i++) {
        const refKey = `constraintSelect_${i}`;
        const refEl = (this.$refs as any)[refKey];
        const el = Array.isArray(refEl) ? refEl[0] : refEl;
        const width =
          el?.$el?.offsetWidth ||
          el?.$el?.clientWidth ||
          el?.offsetWidth ||
          el?.clientWidth;
        if (width) {
          constraintWidths[i] = width;
        }
      }
      this.conditionSelectWidths = widths;
      this.constraintSelectWidths = constraintWidths;
    },
    getConditionSelectAvailableWidth(conditionIndex: number): number {
      const measured = this.conditionSelectWidths[conditionIndex];
      if (measured) return measured;
      // Fallback to CSS width: 6vw baseline for paired layout.
      const baseWidthVw = 6;
      return (window.innerWidth * baseWidthVw) / 100;
    },
    getConstraintSelectAvailableWidth(constraintIndex: number): number {
      const measured = this.constraintSelectWidths[constraintIndex];
      if (measured) return measured;
      // Fallback to CSS width: 6vw baseline for paired layout.
      const baseWidthVw = 6;
      return (window.innerWidth * baseWidthVw) / 100;
    },
    getVisibleConditionTags(conditionIndex: number): string[] {
      const values = this.getConditionSelectionList(conditionIndex);
      if (!values.length) return [];
      const available =
        this.getConditionSelectAvailableWidth(conditionIndex) - 24; // leave room for caret/padding
      let used = 0;
      const visible: string[] = [];
      values.forEach((val) => {
        const w = this.estimateTagWidth(val) + 18; // tag padding + gap
        if (used + w <= available) {
          visible.push(val);
          used += w;
        }
      });
      return visible;
    },
    getHiddenConditionTagCount(conditionIndex: number): number {
      const values = this.getConditionSelectionList(conditionIndex);
      const visible = this.getVisibleConditionTags(conditionIndex);
      return Math.max(0, values.length - visible.length);
    },
    getMaxConstraintCollapseTags(constraintIndex: number): number {
      const values = this.multiConstraintEqualityValues[constraintIndex] || [];
      if (!values.length) return 1;
      const available =
        this.getConstraintSelectAvailableWidth(constraintIndex) - 24;
      let used = 0;
      let count = 0;
      values.forEach((val) => {
        const w = this.estimateTagWidth(val) + 30; // include padding and close icon space
        if (used + w <= available) {
          used += w + 5;
          count += 1;
        }
      });
      return Math.max(1, count);
    },
    hasDisplayOrderChanged(): boolean {
      if (
        this.localDisplayColumnOrder.length === 0 &&
        this.initialDisplayColumnOrder.length === 0
      ) {
        return false;
      }
      if (
        this.localDisplayColumnOrder.length !==
        this.initialDisplayColumnOrder.length
      ) {
        return false;
      }
      return this.localDisplayColumnOrder.some(
        (column, index) => column !== this.initialDisplayColumnOrder[index]
      );
    },
    resetMultiConstraintState() {
      this.multiConstraintEqualityValues = {};
      this.multiConstraintRangeValues = {};
      this.availableMultiConstraintValuesMap = {};
      this.conditionValueSelections = {};
      this.activeMultiConditionRuleIndex = -1;
      this.activeMultiConditionRule = null;
      this.conditionSelectWidths = {};
      this.constraintSelectWidths = {};
    },
    getConstraintColumnCount(card?: ValidationCard | null): number {
      const targetCard = card || this.localCard;
      if (!targetCard) {
        return 0;
      }
      if (targetCard.constraintType && targetCard.constraintType.length > 0) {
        return targetCard.constraintType.length;
      }
      const ruleConstraintColumns = targetCard.ruleValue?.constraintColumns;
      if (
        Array.isArray(ruleConstraintColumns) &&
        ruleConstraintColumns.length
      ) {
        return ruleConstraintColumns.length;
      }
      return targetCard.columnName.length > 1 ? 1 : 0;
    },
    getConditionColumnCount(card?: ValidationCard | null): number {
      const targetCard = card || this.localCard;
      if (!targetCard) {
        return 0;
      }
      const constraintCount = this.getConstraintColumnCount(targetCard);
      return Math.max(0, targetCard.columnName.length - constraintCount);
    },
    getConditionColumnNameByIndex(index: number): string {
      if (!this.localCard || index == null || index < 0) {
        return "";
      }
      const conditionColumns = this.localCard.ruleValue?.conditionColumns;
      if (Array.isArray(conditionColumns) && conditionColumns[index]) {
        return conditionColumns[index];
      }
      return this.localCard.columnName[index] || "";
    },
    getConstraintTypeByIndex(index: number): string {
      return this.localCard?.constraintType?.[index] || "EqualityBased";
    },
    getConstraintColumnNameByIndex(index: number): string {
      if (!this.localCard) {
        return "";
      }
      const constraintColumns = this.localCard.ruleValue?.constraintColumns;
      if (Array.isArray(constraintColumns) && constraintColumns[index]) {
        return constraintColumns[index];
      }
      const conditionCount = this.getConditionColumnCount();
      return this.localCard.columnName[conditionCount + index] || "";
    },
    getConstraintValueFromRule(rule: any, columnName: string) {
      if (!rule) {
        return null;
      }
      if (
        rule.constraintValueMap &&
        Object.prototype.hasOwnProperty.call(
          rule.constraintValueMap,
          columnName
        )
      ) {
        return rule.constraintValueMap[columnName];
      }
      if (
        this.getConstraintColumnCount() === 1 &&
        (rule.constraintValue || rule.constraintValue === 0)
      ) {
        return rule.constraintValue;
      }
      return null;
    },
    getAvailableMultiConstraintValues(index: number): string[] {
      return this.availableMultiConstraintValuesMap[index] || [];
    },
    initializeCardState(card: ValidationCard) {
      if (card.relationType === "Sequence") {
        const rules = this.sequenceRules[String(card.columnName)] || [];
        if (rules.length > 0) {
          this.localSelectedSequenceValue = rules[0].value;
          this.updateAllowedNext();
        }
      } else if (card.relationType === "Logical and condition") {
        const fullname = card.columnName.join("+");
        const rules = this.conditionRules[fullname] || [];
        if (rules.length > 0) {
          this.localSelectedConditionValue = rules[0].conditionValue;
          this.updateConstraintValue();
        }
      } else if (card.relationType === "Lookup") {
        const lookupKey = `${card.columnName[0]}+${card.columnName[1]}`;
        const lookupList = this.lookupRules[lookupKey];
        if (lookupList && lookupList.length > 0) {
          this.availableParentValues = lookupList.map(
            (item) => item.parentValue
          );
          this.localSelectedParentValue = this.availableParentValues[0] || "";
          this.updateChildValues();
        }
      } else if (card.relationType === "MultipleCondition") {
        const fullname = card.columnName.join("+");
        const rules = this.multiConditionRules[fullname] || [];
        if (rules.length > 0) {
          const firstRule = rules[0];
          const numConditionColumns = this.getConditionColumnCount(card);
          this.ensureConstraintState(card);
          this.localSelectedMultiConditionValues = [];
          for (let i = 0; i < numConditionColumns; i++) {
            const conditionKey = `conditionValue${i + 1}`;
            this.localSelectedMultiConditionValues.push(
              firstRule[conditionKey] || ""
            );
          }
          this.updateMultiConstraintValue();
        }
      }
    },
    getTypeIcon(type: string): string {
      if (type.toLowerCase() === "multidifference") {
        return "/cardpanel_icon/difference.svg";
      } else if (type.toLowerCase() === "multipleduplicate") {
        return "/cardpanel_icon/duplicate.svg";
      } else {
        return `/cardpanel_icon/${type.toLowerCase()}.svg`;
      }
    },
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
      return ruleTypeMap[ruleType] || ruleType;
    },
    checkColumnOverflow(
      columnNames: string[],
      containerKey: string
    ): { visibleCount: number; totalCount: number } {
      const totalChars = columnNames.reduce(
        (sum, name) => sum + name.length,
        0
      );
      const maxChars = containerKey.includes("top") ? 40 : 30;
      if (totalChars <= maxChars) {
        return {
          visibleCount: columnNames.length,
          totalCount: columnNames.length,
        };
      }
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
      if (visibleCount === 0) visibleCount = 1;
      return { visibleCount, totalCount: columnNames.length };
    },
    getVisibleColumnNames(
      columnNames: string[],
      containerKey: string
    ): string[] {
      const result = this.checkColumnOverflow(columnNames, containerKey);
      return columnNames.slice(0, result.visibleCount);
    },
    getHiddenColumnCount(columnNames: string[], containerKey: string): number {
      const result = this.checkColumnOverflow(columnNames, containerKey);
      return result.totalCount - result.visibleCount;
    },
    getHiddenColumnNames(
      columnNames: string[],
      containerKey: string
    ): string[] {
      const result = this.checkColumnOverflow(columnNames, containerKey);
      return columnNames.slice(result.visibleCount);
    },
    getMaxLabelLength(): number {
      return 12;
    },
    truncateColumnName(columnName: string): string {
      const maxLength = this.getMaxLabelLength();
      if (columnName.length <= maxLength) {
        return columnName;
      }
      return columnName.substring(0, maxLength - 3) + "...";
    },
    getMaxCollapseTags(selectedValues: string[]): number {
      if (!selectedValues || selectedValues.length === 0) {
        return 1;
      }
      const selectWidth = window.innerWidth * 0.185;
      const availableWidth = selectWidth - 40;
      let totalWidth = 0;
      let maxTags = 0;
      for (let i = 0; i < selectedValues.length; i++) {
        const value = selectedValues[i];
        const estimatedTagWidth = this.estimateTagWidth(value) + 30;
        if (totalWidth + estimatedTagWidth > availableWidth) {
          break;
        }
        totalWidth += estimatedTagWidth + 5;
        maxTags++;
      }
      return Math.max(1, maxTags);
    },
    estimateTagWidth(text: string): number {
      let width = 0;
      for (let i = 0; i < text.length; i++) {
        const char = text.charAt(i);
        if (/[\u4e00-\u9fa5]/.test(char)) {
          width += 16;
        } else {
          width += 8;
        }
      }
      return width;
    },
    updateAllowedNext() {
      const currentRules =
        this.sequenceRules[this.localCard!.columnName[0]] || [];
      const selectedRule = currentRules.find(
        (rule: SequenceRule) => rule.value === this.localSelectedSequenceValue
      );
      this.localSelectedAllowedNext = selectedRule
        ? [...selectedRule.allowed_next]
        : [];
      this.allSequenceValues = currentRules
        .map((rule) => rule.value)
        .filter((value) => value !== this.localSelectedSequenceValue);
    },
    updateConstraintValue() {
      if (this.localCard?.constraintType?.[0] === "RangeBased") {
        const selectedRange = (
          this.localCard?.invalid_range as Array<any>
        )?.find(
          (range) => range.conditionContent === this.localSelectedConditionValue
        );
        if (selectedRange) {
          this.localConstraintValue_Range = {
            start: selectedRange.start,
            end: selectedRange.end,
            startInclusive: selectedRange.startInclusive,
            endInclusive: selectedRange.endInclusive,
          };
        } else {
          this.localConstraintValue_Range = {
            start: 0,
            end: 0,
            startInclusive: false,
            endInclusive: false,
          };
        }
      } else {
        if (this.localCard!.constraintType?.[0] === "EqualityBased") {
          const columnName = this.localCard!.columnName[1];
          const uniqueValues = [
            ...new Set(this.csvData.map((row) => String(row[columnName]))),
          ];
          this.availableConstraintValues = uniqueValues.filter(
            (value) => value && value.trim() !== ""
          );
          const fullname = this.localCard!.columnName.join("+");
          const selectedCondition = this.conditionRules[fullname]?.find(
            (condition) =>
              condition.conditionValue === this.localSelectedConditionValue
          );
          if (selectedCondition && selectedCondition.constraintValue) {
            this.localConstraintValue_Equality = Array.isArray(
              selectedCondition.constraintValue
            )
              ? selectedCondition.constraintValue.map((value) => String(value))
              : [String(selectedCondition.constraintValue)];
          } else {
            this.localConstraintValue_Equality = [];
          }
        } else {
          this.localConstraintValue_Range = {
            start: 0,
            end: 0,
            startInclusive: false,
            endInclusive: false,
          };
        }
      }
    },
    updateChildValues() {
      if (!this.localCard || this.localCard.relationType !== "Lookup") {
        return;
      }
      const lookupKey = `${this.localCard.columnName[0]}+${this.localCard.columnName[1]}`;
      const childColumnName = this.localCard.columnName[1];
      this.allPossibleChildValues = [
        ...new Set(this.csvData.map((row) => String(row[childColumnName]))),
      ].filter((value) => value && value.trim() !== "");
      const lookupList = this.lookupRules[lookupKey];
      const parentRecord = lookupList?.find(
        (item) => item.parentValue === this.localSelectedParentValue
      );
      this.localSelectedChildValues = parentRecord
        ? parentRecord.childValueList
        : [];
    },
    ensureConstraintState(card: ValidationCard) {
      const constraintCount = this.getConstraintColumnCount(card);
      for (let i = 0; i < constraintCount; i++) {
        const constraintType = card.constraintType?.[i] || "EqualityBased";
        if (constraintType === "EqualityBased") {
          if (!this.multiConstraintEqualityValues[i]) {
            this.multiConstraintEqualityValues[i] = [];
          }
        } else {
          if (!this.multiConstraintRangeValues[i]) {
            this.multiConstraintRangeValues[i] = {
              start: 0,
              end: 0,
              startInclusive: false,
              endInclusive: false,
            };
          }
        }
      }
    },
    getMultipleConditionRows() {
      if (
        !this.localCard ||
        this.localCard.relationType !== "MultipleCondition"
      ) {
        return [];
      }
      const columnNames = this.localCard.columnName;
      const totalColumns = columnNames.length;
      if (totalColumns < 3) {
        return [];
      }
      const conditionCount = this.getConditionColumnCount();
      const rows: any[] = [];
      for (let i = 0; i < totalColumns; i += 2) {
        const rowColumns = columnNames.slice(i, i + 2);
        const row = rowColumns.map((colName, colIndex) => {
          const globalIndex = i + colIndex;
          const isConstraintColumn = globalIndex >= conditionCount;
          const constraintIndex = isConstraintColumn
            ? globalIndex - conditionCount
            : undefined;
          return {
            name: colName,
            displayName: this.truncateColumnName(colName),
            needsTooltip: colName.length > this.getMaxLabelLength(),
            type: isConstraintColumn
              ? "constraint"
              : `condition${globalIndex + 1}`,
            conditionIndex: isConstraintColumn ? undefined : globalIndex,
            constraintIndex,
            constraintType: isConstraintColumn
              ? this.localCard?.constraintType?.[constraintIndex!]
              : undefined,
          };
        });
        rows.push(row);
      }
      return rows;
    },
    getUniqueConditionValues(conditionIndex: number): string[] {
      if (
        !this.localCard ||
        this.localCard.relationType !== "MultipleCondition"
      ) {
        return [];
      }
      const fullname = this.localCard.columnName.join("+");
      const rules = this.multiConditionRules[fullname] || [];
      const conditionKey = `conditionValue${conditionIndex + 1}`;
      return [
        ...new Set(
          rules.map((rule) => rule[conditionKey]).filter((val) => val != null)
        ),
      ] as string[];
    },
    getConditionSelectionList(conditionIndex: number): string[] {
      return this.conditionValueSelections[conditionIndex] || [];
    },
    isConditionValueChecked(conditionIndex: number, value: string): boolean {
      return this.getConditionSelectionList(conditionIndex).includes(value);
    },
    toggleConditionValueCheckbox(
      conditionIndex: number,
      value: string,
      checked: boolean
    ) {
      if (conditionIndex == null || !this.localCard) {
        return;
      }
      const current = new Set(this.getConditionSelectionList(conditionIndex));
      if (checked) {
        current.add(value);
      } else {
        current.delete(value);
      }
      const updatedList = Array.from(current);
      this.conditionValueSelections = {
        ...this.conditionValueSelections,
        [conditionIndex]: updatedList,
      };
      this.applyConditionSelectionToRule(conditionIndex, updatedList);
    },
    applyConditionSelectionToRule(conditionIndex: number, values: string[]) {
      if (!this.localCard || conditionIndex == null || conditionIndex < 0) {
        return;
      }
      const columnName = this.getConditionColumnNameByIndex(conditionIndex);
      if (!columnName) {
        return;
      }
      const normalizedValues = values
        .filter((val) => val != null && String(val).trim() !== "")
        .map((val) => String(val));

      if (this.activeMultiConditionRule) {
        if (!this.activeMultiConditionRule.conditionValueMap) {
          this.activeMultiConditionRule.conditionValueMap = {};
        }
        this.activeMultiConditionRule.conditionValueMap[columnName] = [
          ...normalizedValues,
        ];
        this.activeMultiConditionRule[`conditionValue${conditionIndex + 1}`] =
          normalizedValues[0] ?? "";
      }

      if (
        this.activeMultiConditionRuleIndex == null ||
        this.activeMultiConditionRuleIndex < 0
      ) {
        return;
      }

      const ruleValue = this.localCard.ruleValue;
      if (
        !ruleValue ||
        !Array.isArray(ruleValue.conditionAndLogicList) ||
        !ruleValue.conditionAndLogicList[this.activeMultiConditionRuleIndex]
      ) {
        return;
      }

      const targetRule =
        ruleValue.conditionAndLogicList[this.activeMultiConditionRuleIndex];
      if (!Array.isArray(targetRule.conditionColumnValue)) {
        targetRule.conditionColumnValue = [];
      }
      while (targetRule.conditionColumnValue.length <= conditionIndex) {
        targetRule.conditionColumnValue.push({});
      }
      const columnEntry = targetRule.conditionColumnValue[conditionIndex] || {};
      columnEntry[columnName] = [...normalizedValues];
      targetRule.conditionColumnValue[conditionIndex] = columnEntry;
    },
    isConstraintValueChecked(constraintIndex: number, value: string): boolean {
      const current = this.multiConstraintEqualityValues[constraintIndex] || [];
      return current.includes(value);
    },
    toggleConstraintValueCheckbox(
      constraintIndex: number,
      value: string,
      checked: boolean
    ) {
      const currentValues = new Set(
        this.multiConstraintEqualityValues[constraintIndex] || []
      );
      if (checked) {
        currentValues.add(value);
      } else {
        currentValues.delete(value);
      }
      const updatedList = Array.from(currentValues);
      this.multiConstraintEqualityValues = {
        ...this.multiConstraintEqualityValues,
        [constraintIndex]: updatedList,
      };
      this.applyConstraintSelectionToRule(constraintIndex, updatedList);
    },
    applyConstraintSelectionToRule(constraintIndex: number, values: string[]) {
      if (!this.localCard || constraintIndex == null || constraintIndex < 0) {
        return;
      }
      const columnName = this.getConstraintColumnNameByIndex(constraintIndex);
      if (!columnName) {
        return;
      }
      const normalizedValues = values.map((val) => String(val));

      if (this.activeMultiConditionRule) {
        if (!this.activeMultiConditionRule.constraintValueMap) {
          this.activeMultiConditionRule.constraintValueMap = {};
        }
        this.activeMultiConditionRule.constraintValueMap[columnName] = [
          ...normalizedValues,
        ];
        if (constraintIndex === 0) {
          this.activeMultiConditionRule.constraintValue = [...normalizedValues];
        }
      }

      if (
        this.activeMultiConditionRuleIndex == null ||
        this.activeMultiConditionRuleIndex < 0
      ) {
        return;
      }

      const ruleValue = this.localCard.ruleValue;
      if (
        !ruleValue ||
        !Array.isArray(ruleValue.conditionAndLogicList) ||
        !ruleValue.conditionAndLogicList[this.activeMultiConditionRuleIndex]
      ) {
        return;
      }

      const targetRule =
        ruleValue.conditionAndLogicList[this.activeMultiConditionRuleIndex];
      if (!Array.isArray(targetRule.constraintColumnValue)) {
        targetRule.constraintColumnValue = [];
      }
      while (targetRule.constraintColumnValue.length <= constraintIndex) {
        targetRule.constraintColumnValue.push({});
      }
      const columnEntry =
        targetRule.constraintColumnValue[constraintIndex] || {};
      columnEntry[columnName] = [...normalizedValues];
      targetRule.constraintColumnValue[constraintIndex] = columnEntry;
    },
    handleMultiConditionChange(changedIndex: number) {
      if (!this.localCard) return;
      const fullname = this.localCard.columnName.join("+");
      const multiConditionRules = this.multiConditionRules[fullname] || [];
      const numConditionColumns = this.getConditionColumnCount();
      const changedValue = this.localSelectedMultiConditionValues[changedIndex];
      if (!changedValue || changedValue.trim() === "") return;
      const matchedRule = multiConditionRules.find((rule) => {
        const conditionKey = `conditionValue${changedIndex + 1}`;
        return rule[conditionKey] === changedValue;
      });
      if (matchedRule) {
        for (let i = 0; i < numConditionColumns; i++) {
          if (i !== changedIndex) {
            const conditionKey = `conditionValue${i + 1}`;
            this.localSelectedMultiConditionValues[i] =
              matchedRule[conditionKey] || "";
          }
        }
        this.updateMultiConstraintValue();
      }
    },
    updateMultiConstraintValue() {
      if (!this.localCard) return;
      const numConditionColumns = this.getConditionColumnCount();
      const constraintCount = this.getConstraintColumnCount();
      if (constraintCount === 0) return;

      for (let idx = 0; idx < constraintCount; idx++) {
        const constraintType = this.getConstraintTypeByIndex(idx);
        const columnName = this.getConstraintColumnNameByIndex(idx);
        if (constraintType === "EqualityBased") {
          const uniqueValues = [
            ...new Set(
              this.csvData
                .map((row) => {
                  const value = row[columnName];
                  if (value === undefined || value === null) {
                    return "";
                  }
                  return String(value);
                })
                .filter((value) => value && value.trim() !== "")
            ),
          ];
          this.availableMultiConstraintValuesMap[idx] = uniqueValues;
        }
      }

      if (this.localSelectedMultiConditionValues.length < numConditionColumns)
        return;
      const allConditionsSelected = this.localSelectedMultiConditionValues
        .slice(0, numConditionColumns)
        .every((val) => val && val.trim() !== "");
      if (!allConditionsSelected) {
        for (let idx = 0; idx < constraintCount; idx++) {
          const constraintType = this.getConstraintTypeByIndex(idx);
          if (constraintType === "EqualityBased") {
            this.multiConstraintEqualityValues[idx] = [];
          } else {
            this.multiConstraintRangeValues[idx] = {
              start: 0,
              end: 0,
              startInclusive: false,
              endInclusive: false,
            };
          }
        }
        return;
      }

      const fullname = this.localCard!.columnName.join("+");
      const selectedCondition = this.multiConditionRules[fullname]?.find(
        (condition) => {
          for (let i = 0; i < numConditionColumns; i++) {
            const conditionKey = `conditionValue${i + 1}`;
            if (
              condition[conditionKey] !==
              this.localSelectedMultiConditionValues[i]
            ) {
              return false;
            }
          }
          return true;
        }
      );

      for (let idx = 0; idx < constraintCount; idx++) {
        const constraintType = this.getConstraintTypeByIndex(idx);
        const columnName = this.getConstraintColumnNameByIndex(idx);
        const rawValue = this.getConstraintValueFromRule(
          selectedCondition,
          columnName
        );

        if (!selectedCondition || rawValue == null) {
          if (constraintType === "EqualityBased") {
            this.multiConstraintEqualityValues[idx] = [];
          } else {
            this.multiConstraintRangeValues[idx] = {
              start: 0,
              end: 0,
              startInclusive: false,
              endInclusive: false,
            };
          }
          continue;
        }

        if (constraintType === "EqualityBased") {
          if (Array.isArray(rawValue)) {
            this.multiConstraintEqualityValues[idx] = rawValue.map((value) =>
              String(value)
            );
          } else {
            this.multiConstraintEqualityValues[idx] = [String(rawValue)];
          }
        } else {
          this.multiConstraintRangeValues[idx] = {
            start: rawValue.start ?? 0,
            end: rawValue.end ?? 0,
            startInclusive: rawValue.startInclusive ?? false,
            endInclusive: rawValue.endInclusive ?? false,
          };
        }
      }
    },
    handleMultiConstraintChange() {
      // User edited constraint value
    },
    handleSpecialMissingValuesChange(values) {
      if (!this.localCard || !this.localCard.columnType) return;
      if (this.localCard.columnType[0] === "numeric") {
        const lastValue = values[values.length - 1];
        const numValue = Number(lastValue);
        if (!isNaN(numValue)) {
          const newList = [...values];
          newList[newList.length - 1] = numValue;
          this.localCard.ruleValue.specialMissingValueList = newList;
        }
      }
    },
    async syncToBackend() {
      try {
        const shouldEmitOrderUpdate =
          this.localCard?.relationType === "MultipleCondition" &&
          this.hasDisplayOrderChanged();
        let updatedRuleValue;
        if (this.localCard!.relationType === "Sequence") {
          updatedRuleValue = {
            value: this.localSelectedSequenceValue,
            allowed_next: this.localSelectedAllowedNext,
          };
        } else if (this.localCard!.relationType === "Logical and condition") {
          if (this.localCard!.constraintType?.[0] === "RangeBased") {
            updatedRuleValue = {
              conditionValue: this.localSelectedConditionValue,
              constraintValue: this.localConstraintValue_Range,
            };
          } else if (this.localCard!.constraintType?.[0] === "EqualityBased") {
            updatedRuleValue = {
              conditionValue: this.localSelectedConditionValue,
              constraintValue: this.localConstraintValue_Equality as string[],
            };
          }
        } else if (this.localCard!.relationType === "Lookup") {
          updatedRuleValue = {
            parentColumnName: this.localCard!.ruleValue.parentColumnName,
            childColumnName: this.localCard!.ruleValue.childColumnName,
            lookupList: [
              {
                parentValue: this.localSelectedParentValue,
                childValueList: this.localSelectedChildValues,
              },
            ],
          };
        } else {
          updatedRuleValue = this.localCard!.ruleValue;
        }

        await api.post("/api/update-rule", {
          columnName: this.localCard!.columnName,
          ruleType: this.localCard!.relationType,
          ruleValue: updatedRuleValue,
        });

        if (shouldEmitOrderUpdate) {
          this.$emit("multi-condition-order-updated", [
            ...this.localDisplayColumnOrder,
          ]);
          this.initialDisplayColumnOrder = [...this.localDisplayColumnOrder];
          if (this.localCard) {
            this.localCard.displayColumnOrder = [
              ...this.localDisplayColumnOrder,
            ];
          }
        }

        this.$emit("update-rule", {
          columnName: this.localCard!.columnName,
          ruleType: this.localCard!.relationType,
        });
      } catch (error) {
        console.error("Failed to update value", error);
      }
    },
    handleMatrixCellClicked(event: CustomEvent) {
      const { category1, category2, isRightClick } = event.detail;

      if (
        this.localCard &&
        this.localCard.relationType === "Sequence" &&
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
              // Toggle validity for the clicked pair: add when missing, remove when present
              this.localSelectedSequenceValue = category1;
              this.updateAllowedNext();

              const normalizedCategory2 = String(category2).toLowerCase();
              const alreadyAllowed = this.localSelectedAllowedNext.some(
                (value) => value.toLowerCase() === normalizedCategory2
              );

              if (alreadyAllowed) {
                this.localSelectedAllowedNext =
                  this.localSelectedAllowedNext.filter(
                    (value) => value.toLowerCase() !== normalizedCategory2
                  );
              } else {
                this.localSelectedAllowedNext = [
                  ...this.localSelectedAllowedNext,
                  category2,
                ];
              }

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
          this.localSelectedSequenceValue = category1;
          this.updateAllowedNext();
        }
      }
    },
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
              this.localSelectedConditionValue = conditionValue;
              this.updateConstraintValue();
              this.localConstraintValue_Equality =
                this.localConstraintValue_Equality.filter(
                  (value) =>
                    value.toLowerCase() !== constraintValue.toLowerCase()
                );
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
              this.localSelectedParentValue = conditionValue;
              this.updateChildValues();

              const normalizedConstraint =
                String(constraintValue).toLowerCase();
              const alreadyAllowed = this.localSelectedChildValues.some(
                (value) => value.toLowerCase() === normalizedConstraint
              );

              if (alreadyAllowed) {
                this.localSelectedChildValues =
                  this.localSelectedChildValues.filter(
                    (value) => value.toLowerCase() !== normalizedConstraint
                  );
              } else {
                this.localSelectedChildValues = [
                  ...this.localSelectedChildValues,
                  constraintValue,
                ];
              }
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
          if (
            this.localCard &&
            this.localCard.relationType === "Logical and condition" &&
            conditionValue
          ) {
            this.localSelectedConditionValue = conditionValue;
            this.updateConstraintValue();
          }
        } else if (relationType == "Lookup") {
          if (
            this.localCard &&
            this.localCard.relationType === "Lookup" &&
            conditionValue
          ) {
            this.localSelectedParentValue = conditionValue;
            this.updateChildValues();
          }
        }
      }
    },
  },
  mounted() {
    if (this.enableMatrixListeners) {
      window.addEventListener(
        "matrix-cell-clicked",
        this.handleMatrixCellClicked as any
      );
      window.addEventListener(
        "condition-area-clicked",
        this.handleConditionAreaClicked as any
      );
    }
    window.addEventListener("resize", this.measureConditionSelectWidths as any);
    this.$nextTick(() => this.measureConditionSelectWidths());
  },
  beforeUnmount() {
    if (this.enableMatrixListeners) {
      window.removeEventListener(
        "matrix-cell-clicked",
        this.handleMatrixCellClicked as any
      );
      window.removeEventListener(
        "condition-area-clicked",
        this.handleConditionAreaClicked as any
      );
    }
    window.removeEventListener(
      "resize",
      this.measureConditionSelectWidths as any
    );
  },
});
</script>

<style scoped>
/* Copy styles from block-2 and related classes */
.block-2 {
  height: 21.75vh;
  display: flex;
  flex-direction: column;
  padding: 1vh;
  margin-top: 1vh;
  margin-bottom: 1vh;
  border-radius: 1vh;
  position: relative;
}
.info-row,
.type-row,
.paramater-row,
.value-row,
.value-row-2 {
  display: flex;
  justify-content: flex-start;
  margin-top: 0.5vh; /* Adjusted for info-row */
  margin-left: 1vw;
  height: 2.7vh;
  position: relative;
  align-items: center;
}
.value-row--multiple {
  height: auto;
  min-height: 2.7vh;
  align-items: flex-start;
  flex-direction: column;
  padding-bottom: 1.5vh;
}
.column-order-editor {
  width: 100%;
  background-color: #f5f7ff;
  border: 1px dashed #9ab7cd;
  border-radius: 0.6vh;
  padding: 1vh 1vw;
  margin-bottom: 1vh;
}
.column-order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5vh;
}
.order-label {
  font-size: 1.4vh;
  font-weight: 600;
  color: #0c4672;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.order-change-indicator {
  font-size: 1.2vh;
  color: #d46b08;
  font-weight: 600;
}
.column-order-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5vw;
}
.order-chip {
  display: flex;
  align-items: center;
  padding: 0.3vh 0.8vw;
  border: 1px solid #4570b6;
  border-radius: 0.5vh;
  background-color: #fff;
  cursor: grab;
  user-select: none;
  min-width: 5vw;
  justify-content: space-between;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}
.order-chip--drag-over {
  border-color: #fd8d3c;
  background-color: #fff7ed;
}
.chip-index {
  font-weight: 700;
  margin-right: 0.5vw;
  color: #4570b6;
}
.chip-label {
  flex-grow: 1;
  font-size: 1.4vh;
  color: #42424b;
  padding-right: 0.5vw;
}
.chip-hint {
  font-size: 1.2vh;
  color: #9ab7cd;
}
.order-helper-text {
  margin-top: 0.6vh;
  font-size: 1.2vh;
  color: #6b7280;
}
.value-row--multiple + .value-row-2 {
  margin-top: 2vh;
}
.type-row,
.paramater-row,
.value-row,
.value-row-2 {
  margin-top: 1vh;
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
  color: #42424b;
  text-decoration: underline;
}
.value-box {
  background-color: #d5dfff;
  padding: 0.5vh 1vh;
  border-radius: 0.46vh;
  font-size: 1.6vh;
  font-family: Roboto;
  font-weight: 550;
  color: black;
  margin-right: 0.5vw;
}
.column-display-container {
  display: flex;
  align-items: center;
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
  font-weight: 550;
}
.parameter-arrow {
  width: 1.5vh;
  height: 1.5vh;
  margin-right: 0.5vh;
  vertical-align: middle;
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
  font-weight: 550;
  display: inline-block;
}
.missingValue {
  font-weight: bold;
  width: 100%;
  padding-right: 1vw;
  font-size: 1.6vh;
  color: #42424b;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transform: translateY(0.05vh);
}
.missingValue :deep(.el-select__wrapper) {
  width: 12vw;
  margin-left: auto;
  height: 2.7vh;
  padding: 0 0.5vh;
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
  padding: 0.3vh 0.6vh 0.3vh 0.6vh;
  display: inline-block;
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
.parameter-type {
  font-weight: bold;
  width: 6vw;
  font-size: 1.6vh;
  color: #42424b;
  padding-right: 1vw;
  display: flex;
  justify-content: left;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
}
.parameter-name {
  font-weight: bold;
  width: 5vw;
  font-size: 1.6vh;
  color: #42424b;
  margin-right: 1vw;
  display: flex;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
  gap: 0.5vh;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.parameter-name :deep(.el-select__wrapper) {
  width: 15vw;
  margin-left: auto;
  height: 2.7vh;
  padding: 0 0.5vh;
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
  padding: 0.3vh 0.6vh 0.3vh 0.6vh;
  display: inline-block;
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 1.8vh;
  line-height: 1.8vh;
  transform: translateY(0.05vh);
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
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
  display: inline-block;
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
  width: 5vw;
  margin-left: 0.5vh;
  flex-shrink: 0;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lookup-select {
  width: 18.5vw;
  flex-shrink: 0;
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
.sequence-select {
  width: 18.5vw;
  flex-shrink: 0;
}
.sequence-select :deep(.el-select__wrapper) {
  height: 2.7vh;
  padding: 0.3vh 0.5vh 0.3vh 0.3vh;
}
.sequence-select :deep(.el-select__placeholder) {
  color: black;
  font-size: 1.4vh;
  font-family: Roboto;
  font-style: normal;
  line-height: 1.8vh;
  margin-top: 0vh;
}
.sequence-select :deep(.el-select__placeholder span) {
  background-color: #c7efed;
  border-radius: 0.46vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
  display: inline-block;
}
.sequence-select :deep(.el-select__selection.is-near) {
  margin-left: 0;
}
.sequence-select :deep(.el-tag.el-tag--info) {
  --el-tag-text-color: black;
  --el-tag-bg-color: #c7efed;
  --el-tag-border-color: #4570b6;
  --el-tag-hover-color: #c7efed;
  --el-tag-font-size: 1.4vh;
}
.sequence-select :deep(.el-tag .el-tag__close) {
  margin-left: 0vh;
}
.sequence-select :deep(.el-select__selected-item .el-tag) {
  height: 2.4vh;
  padding: 0.3vh 0.3vh 0.3vh 0.3vh;
}
.differenceRange {
  width: 18.5vw; /* align with equality-based select width for Logical and condition */
  display: flex;
  align-items: center;
  gap: 0.25vw;
  margin-left: 0.35vw; /* nudge to align with equality-based while keeping labels in view */
  flex-wrap: nowrap;
  box-sizing: border-box;
}
.range-input {
  width: clamp(60px, 3.6vw, 74px);
  height: 2.7vh;
  flex-shrink: 0;
}
.range-operator {
  width: clamp(46px, 2.5vw, 62px);
  height: 2.7vh;
  flex-shrink: 0;
}
.range-operator :deep(.el-select__wrapper) {
  padding: 0 0.4vw;
  justify-content: center;
}
.range-operator :deep(.el-select__placeholder),
.range-operator :deep(.el-select__selected-item) {
  font-size: 1.5vh;
  line-height: 2.4vh;
  text-align: center;
}
.range-separator {
  flex: 1 1 5.5vw;
  max-width: 6.5vw;
  min-width: 4.5vw;
  font-size: 1.4vh;
  font-family: Roboto;
  font-weight: 500;
  color: #42424b;
  text-align: center;
  line-height: 2.4vh;
  background-color: #f8fafc;
  border-radius: 0.3vh;
  padding: 0.2vh 0.3vh;
  border: 1px solid #e5e7eb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.submit-button-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 1vh;
  margin-right: 1vw;
  position: absolute;
  bottom: 1vh;
  right: 1vh;
  z-index: 10;
}
.submit-button {
  font-size: 1.5vh;
  padding: 0.5vh 1.5vh;
  background-color: #4570b6;
  border-color: #4570b6;
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
.multiple-condition-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1vh;
  margin-top: 3vh;
  margin-left: 1vw;
  position: relative;
  z-index: 2;
}
.value-row--multiple .multiple-condition-container {
  margin-top: 1vh;
}
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
  gap: 1vw;
  margin-left: -1vw;
  margin-bottom: 1vh;
}
.multiple-condition-item {
  display: flex;
  align-items: center;
  width: 11.5vw;
  min-width: 11.5vw;
  flex-shrink: 0;
}
.multiple-condition-item.placeholder-item {
  visibility: hidden;
}
.multiple-condition-row .multiple-condition-item:only-child {
  width: 24vw;
}
.multiple-condition-row .multiple-condition-item:only-child.placeholder-item {
  width: 11.5vw;
}
.multiple-condition-row:last-child {
  margin-bottom: 0;
}
.multiple-condition-label {
  width: 5vw;
  margin-left: 0.5vh;
  margin-right: 0vw;
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
.multiple-condition-row
  .multiple-condition-item:only-child
  .multiple-condition-label {
  width: 5vw;
}
.multiple-condition-select {
  width: 6vw;
  flex-shrink: 0;
}
.multiple-condition-row
  .multiple-condition-item:only-child
  .multiple-condition-select {
  width: 18.5vw;
}
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
.multiple-condition-select :deep(.el-select__prefix) {
  display: flex;
  align-items: center;
  gap: 0.3vw;
  max-width: 8vw;
  flex-wrap: wrap;
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
.option-text {
  width: 10vw;
  font-size: 1.5vh;
  font-family: Roboto;
  font-weight: 550;
}
.option-with-checkbox {
  display: flex;
  align-items: center;
  gap: 0.4vw;
}
.select-tag-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3vw;
}
.select-tag {
  background-color: #c7efed;
  border: 1px solid #4570b6;
  border-radius: 0.4vh;
  padding: 0.1vh 0.4vh;
  font-size: 1.2vh;
  color: #1f2a37;
  white-space: nowrap;
}
.select-tag--more {
  background-color: #eef2f7;
  border-style: dashed;
}
</style>
