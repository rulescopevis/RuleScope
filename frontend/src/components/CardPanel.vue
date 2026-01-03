<template>
  <div class="validation-list">
    <div
      class="validation-card"
      v-for="(card, cellsIndex) in filterCards"
      :key="cellsIndex"
      :class="{
        'has-conflict': card.ifConflict,
        selected:
          chooseCard &&
          card.columnName.join('+') === chooseCard.columnName.join('+') &&
          card.relationType === chooseCard.relationType,
      }"
      :data-conflict-level="card.ifConflict"
      @click="$emit('card-click', card)"
    >
      <div class="card-header">
        <span class="column-name">
          <img
            :src="getTypeIcon(card.relationType)"
            :alt="card.relationType"
            class="type-icon-small"
          />
          <span
            class="column-items-container"
            :ref="`cardColumnContainer-${cellsIndex}`"
          >
            <span
              v-for="(col, index) in getVisibleColumnNames(
                getDisplayColumnNames(card),
                `card-${cellsIndex}`
              )"
              :key="index"
              class="column-item"
              :ref="`cardColumnItem-${cellsIndex}-${index}`"
            >
              {{ col }}
            </span>
            <el-tooltip
              v-if="
                getHiddenColumnCount(
                  getDisplayColumnNames(card),
                  `card-${cellsIndex}`
                ) > 0
              "
              effect="dark"
              placement="top"
              :show-after="2000"
              :content="
                getHiddenColumnNames(
                  getDisplayColumnNames(card),
                  `card-${cellsIndex}`
                ).join(', ')
              "
              popper-class="custom-tooltip"
            >
              <span class="column-item overflow-indicator">
                +{{
                  getHiddenColumnCount(
                    getDisplayColumnNames(card),
                    `card-${cellsIndex}`
                  )
                }}
              </span>
            </el-tooltip>
          </span>
        </span>
        <span class="relation-class">{{ card.relationClass }}</span>
      </div>
      <div class="card-body">
        <span class="relation-type">
          <span class="text-content">
            <template v-if="card.example && card.example.includes(';')">
              <el-tooltip
                effect="dark"
                placement="top"
                :show-after="2000"
                :content="
                  card.example
                    .split(';')
                    .map((line) => line.trim())
                    .join(' ')
                "
                popper-class="custom-tooltip"
              >
                <div class="example-container">
                  <div
                    v-for="(line, idx) in card.example.split(';')"
                    :key="idx"
                    class="example-line"
                  >
                    {{ line.trim() }}
                  </div>
                </div>
              </el-tooltip>
            </template>
            <template v-else>
              <el-tooltip
                effect="dark"
                placement="top"
                :show-after="2000"
                :content="card.example"
                :disabled="!card.example || card.example.length <= 50"
                popper-class="custom-tooltip"
              >
                <div class="example-single">
                  {{ card.example }}
                </div>
              </el-tooltip>
            </template>
          </span>
        </span>
        <button
          class="delete-card-btn"
          @click.stop="$emit('delete-card', card)"
        >
          <img
            src="/cardpanel_icon/delete.svg"
            alt="delete"
            class="delete-icon"
          />
        </button>
      </div>
    </div>
    <div
      v-if="filterCards.length >= 1"
      class="validation-card-empty"
      @click="$emit('create-rule')"
    >
      <img src="/cardpanel_icon/addcard.svg" class="addcard-icon" />
      Create Validation Rule
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from "vue";
import { ValidationCard } from "@/types/types";

export default defineComponent({
  name: "CardPanel",
  props: {
    filterCards: {
      type: Array as PropType<ValidationCard[]>,
      default: () => [],
    },
    chooseCard: {
      type: Object as PropType<ValidationCard | null>,
      default: null,
    },
  },
  emits: ["card-click", "delete-card", "create-rule"],
  data() {
    return {
      overflowInfo: {} as Record<
        string,
        { visibleCount: number; totalCount: number }
      >,
      measureContext: null as CanvasRenderingContext2D | null,
    };
  },
  watch: {
    filterCards: {
      handler() {
        this.scheduleOverflowUpdate();
      },
      immediate: true,
      deep: true,
    },
  },
  mounted() {
    this.scheduleOverflowUpdate();
    window.addEventListener("resize", this.handleResize);
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.handleResize);
  },
  methods: {
    handleResize() {
      this.scheduleOverflowUpdate();
    },
    scheduleOverflowUpdate() {
      this.$nextTick(() => {
        this.updateAllOverflow();
      });
    },
    updateAllOverflow() {
      const next: Record<string, { visibleCount: number; totalCount: number }> =
        {};
      this.filterCards.forEach((card, index) => {
        const containerKey = `card-${index}`;
        next[containerKey] = this.measureOverflow(
          this.getDisplayColumnNames(card),
          containerKey
        );
      });
      this.overflowInfo = next;
    },
    getMeasureContext(): CanvasRenderingContext2D | null {
      if (!this.measureContext) {
        const canvas = document.createElement("canvas");
        this.measureContext = canvas.getContext("2d");
      }
      return this.measureContext;
    },
    measureOverflow(
      columnNames: string[],
      containerKey: string
    ): {
      visibleCount: number;
      totalCount: number;
    } {
      const containerRef = this.$refs[containerKey] as
        | HTMLElement
        | HTMLElement[]
        | undefined;
      const container = Array.isArray(containerRef)
        ? containerRef[0]
        : containerRef;
      const ctx = this.getMeasureContext();

      if (container && ctx) {
        const style = window.getComputedStyle(container);
        const fontWeight = style.fontWeight || "600";
        const fontSize = style.fontSize || "14px";
        const fontFamily = style.fontFamily || "Roboto, sans-serif";
        ctx.font = `${fontWeight} ${fontSize} ${fontFamily}`;

        const availableWidth = Math.max(container.clientWidth - 4, 0);
        const badgePadding = 14; // padding + border + horizontal gap
        const badgeGap = 6;
        const overflowBadgeWidth = 26; // space for +x badge when needed
        let usedWidth = 0;
        let visibleCount = 0;

        for (let i = 0; i < columnNames.length; i++) {
          const textWidth = ctx.measureText(columnNames[i]).width;
          const badgeWidth = textWidth + badgePadding;
          const nextWidth = usedWidth + badgeWidth + badgeGap;
          const hasRemaining = i < columnNames.length - 1;
          const reserve = hasRemaining ? overflowBadgeWidth : 0;

          if (nextWidth + reserve > availableWidth && visibleCount > 0) {
            break;
          }

          usedWidth = nextWidth;
          visibleCount++;
        }

        if (visibleCount === 0) visibleCount = 1;
        return { visibleCount, totalCount: columnNames.length };
      }

      return this.simpleOverflow(columnNames, containerKey);
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
    simpleOverflow(
      columnNames: string[],
      containerKey: string
    ): { visibleCount: number; totalCount: number } {
      const totalChars = columnNames.reduce(
        (sum, name) => sum + name.length,
        0
      );
      const maxChars = containerKey.includes("top") ? 40 : 28;
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
    checkColumnOverflow(
      columnNames: string[],
      containerKey: string
    ): { visibleCount: number; totalCount: number } {
      return (
        this.overflowInfo[containerKey] ||
        this.measureOverflow(columnNames, containerKey)
      );
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
    getDisplayColumnNames(card: ValidationCard): string[] {
      if (
        card.displayColumnOrder &&
        card.displayColumnOrder.length === card.columnName.length
      ) {
        return card.displayColumnOrder;
      }
      return card.columnName;
    },
  },
});
</script>

<style scoped>
.validation-list {
  max-height: 53vh;
  height: 53vh;
  padding-left: 0.5vw;
  padding-right: 0.5vw;
  background-color: #ffffff;
  border: 1px solid #ffffff;
  border-radius: 0.92vh;
  overflow-y: auto;
  perspective: 1000px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.validation-list::-webkit-scrollbar {
  display: none;
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
  animation: slideIn 0.2s ease-out forwards;
  opacity: 0;
  will-change: transform, opacity;
  backface-visibility: hidden;
}
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
.validation-card.selected {
  box-shadow: 0px 0px 6px 0px rgba(44, 123, 182, 0.8);
  border: 1.5px solid #2c7bb6;
  transform: translateY(-2px);
}
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
  min-width: 0;
}
.column-item {
  display: inline-block;
  background-color: #d5dfff;
  border-radius: 0.46vh;
  margin-right: 0.46vh;
  padding: 0.3vh 0.5vh 0.3vh 0.5vh;
  white-space: nowrap;
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
  background-color: #fdd0a2;
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
  animation: slideIn 0.2s ease-out forwards;
  opacity: 0;
  will-change: transform, opacity;
  backface-visibility: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #9ab7cd;
  font-family: Roboto;
  font-size: 1.6vh;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  cursor: pointer;
}
.validation-card-empty:hover {
  transform: translateY(-2px);
  transition: transform 0.2s ease;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
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
  opacity: 0;
}
.validation-card:hover .delete-card-btn {
  opacity: 1;
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
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
  line-height: 1.4;
  max-height: 2.8em;
}
.example-line {
  display: inline;
  margin-right: 0.5em;
}
.example-single {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
  line-height: 1.4;
  max-height: 2.8em;
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
</style>
