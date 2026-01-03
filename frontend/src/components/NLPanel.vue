<template>
  <div class="text-editor">
    <textarea
      class="custom-textarea"
      placeholder="Input rules or describe valid/invalid examples "
      v-model="nlText"
    ></textarea>
    <button
      class="send-button"
      @click="handleSend"
      :disabled="loading || !nlText.trim()"
    >
      <span v-if="loading" class="spinner" aria-label="sending"></span>
      <img v-else src="/cardpanel_icon/send.svg" alt="send" class="send-icon" />
    </button>
    <div v-if="loading" class="loading-hint">Sending…</div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from "vue";
import { api_nlpanel_handle } from "@/utils/callapi";
import { ValidationCard } from "@/types/types";

export default defineComponent({
  name: "NLPanel",
  props: {
    chooseCard: {
      type: Object as PropType<ValidationCard | null>,
      required: false,
      default: null,
    },
  },
  emits: ["rules-updated", "preview-refine"],
  data() {
    return {
      nlText: "",
      loading: false,
    };
  },
  methods: {
    buildRuleContext() {
      if (!this.chooseCard) return null;
      return {
        ruleType: this.chooseCard.relationType,
        columnsList: this.chooseCard.columnName,
        validationRule: this.chooseCard.ruleValue,
      };
    },
    async handleSend() {
      if (!this.nlText.trim()) return;
      this.loading = true;
      try {
        console.log("[NLPanel] sending NL payload");
        const payload: any = {
          naturalLanguage: this.nlText,
          previewOnly: true,
        };

        const ruleContext = this.buildRuleContext();
        if (ruleContext) {
          payload.ruleContext = ruleContext;
          console.log("[NLPanel] include ruleContext", ruleContext);
        }

        const res = await api_nlpanel_handle(payload);
        console.log("[NLPanel] response", res);
        if (res && res.refineResult) {
          console.log("[NLPanel] emitting preview-refine", res.refineResult);
          this.$emit("preview-refine", res);
        }
        // emit refresh when backend updated validation
        if (res && res.updatedValidationPath) {
          console.log("[NLPanel] backend wrote validation, trigger refresh");
          this.$emit("rules-updated");
        }
        console.log("NL panel response", res);
      } catch (error) {
        console.error("NL panel send failed", error);
      } finally {
        this.loading = false;
      }
    },
  },
});
</script>

<style scoped>
.text-editor {
  position: relative;
  width: 100%;
  margin-top: 0.92vh;
}

.custom-textarea {
  width: calc(100% - 0.4vw);
  min-height: 16.25vh;
  margin-top: 0.5vh;
  padding: 1vh;
  border: 2px solid transparent;
  border-radius: 1vh;
  resize: none;
  font-family: inherit;
  box-sizing: border-box;
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
  color: #9ab7cd;
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

.spinner {
  width: 2.5vh;
  height: 2.5vh;
  aspect-ratio: 1 / 1;
  border: 0.3vh solid #d0d8e2;
  border-top-color: #4570b6;
  border-radius: 50%;
  box-sizing: border-box;
  display: block;
  animation: spin 0.8s linear infinite;
}

.loading-hint {
  position: absolute;
  bottom: 1vh;
  right: 4.2vh;
  display: flex;
  align-items: center;
  font-size: 1.3vh;
  color: #4570b6;
  white-space: nowrap;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
