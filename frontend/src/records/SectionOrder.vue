<script setup lang="ts">
import { ref } from "vue";
import { briefingSectionOptions, type BriefingSectionId } from "./briefing";

const props = defineProps<{
  modelValue: BriefingSectionId[];
  disabled?: boolean;
}>();
const emit = defineEmits<{
  "update:modelValue": [value: BriefingSectionId[]];
}>();
const root = ref<HTMLElement>();
const dragging = ref<BriefingSectionId | null>(null);
const target = ref<BriefingSectionId | null>(null);
const floating = ref({
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  offsetX: 0,
  offsetY: 0,
  label: "",
});

function reorder(id: BriefingSectionId, destination: BriefingSectionId) {
  const from = props.modelValue.indexOf(id);
  const to = props.modelValue.indexOf(destination);
  if (props.disabled || from < 0 || to < 0 || from === to) return;
  const next = [...props.modelValue];
  next.splice(from, 1);
  next.splice(to, 0, id);
  emit("update:modelValue", next);
}

function start(event: PointerEvent, id: BriefingSectionId) {
  if (props.disabled || event.button !== 0) return;
  event.preventDefault();
  const element = event.currentTarget as HTMLElement;
  const rect = element.getBoundingClientRect();
  floating.value = {
    x: rect.left,
    y: rect.top,
    width: rect.width,
    height: rect.height,
    offsetX: event.clientX - rect.left,
    offsetY: event.clientY - rect.top,
    label: element.textContent?.trim() || "",
  };
  element.setPointerCapture(event.pointerId);
  dragging.value = id;
  target.value = id;
}

function move(event: PointerEvent) {
  if (!dragging.value) return;
  floating.value.x = event.clientX - floating.value.offsetX;
  floating.value.y = event.clientY - floating.value.offsetY;
  const row = document
    .elementFromPoint(event.clientX, event.clientY)
    ?.closest<HTMLElement>("[data-section-id]");
  if (row && root.value?.contains(row))
    target.value = row.dataset.sectionId as BriefingSectionId;
}

function finish() {
  if (dragging.value && target.value) reorder(dragging.value, target.value);
  cancel();
}

function cancel() {
  dragging.value = null;
  target.value = null;
}

function keyboard(event: KeyboardEvent, id: BriefingSectionId) {
  if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
  event.preventDefault();
  const destination =
    props.modelValue[
      props.modelValue.indexOf(id) + (event.key === "ArrowUp" ? -1 : 1)
    ];
  if (destination) reorder(id, destination);
}
</script>

<template>
  <div ref="root" class="section-order" role="list" aria-label="生成顺序">
    <div
      v-for="(id, index) in modelValue"
      :key="id"
      :data-section-id="id"
      class="section-order-row"
      role="listitem"
      :class="{
        dragging: dragging === id,
        'drop-target': target === id && dragging !== id,
      }"
    >
      <button
        type="button"
        :disabled="disabled"
        class="section-order-handle"
        :aria-label="`拖动排序：${briefingSectionOptions.find((option) => option.id === id)?.label}`"
        title="拖动排序"
        @pointerdown="start($event, id)"
        @pointermove="move"
        @pointerup="finish"
        @pointercancel="cancel"
        @lostpointercapture="cancel"
        @keydown="keyboard($event, id)"
      >
        {{ index + 1 }}.
        {{ briefingSectionOptions.find((option) => option.id === id)?.label }}
      </button>
    </div>
  </div>
  <Teleport to="body">
    <div
      v-if="dragging"
      class="section-order-floating"
      aria-hidden="true"
      :style="{
        left: `${floating.x}px`,
        top: `${floating.y}px`,
        width: `${floating.width}px`,
        minHeight: `${floating.height}px`,
      }"
    >
      {{ floating.label }}
    </div>
  </Teleport>
</template>

<style scoped>
.section-order-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 44px;
  padding: 0;
  margin: 6px 0;
  border: 1px solid var(--p1-line);
  border-radius: 8px;
  font-size: 13px;
  color: #63745c;
}
.section-order-row > span {
  min-width: 0;
  overflow-wrap: anywhere;
}
.section-order-row.dragging {
  opacity: 0.3;
}
.section-order-row.drop-target {
  background: #eef4e9;
  box-shadow: inset 0 -2px #52775b;
}
.section-order-handle {
  width: 100%;
  min-height: 44px;
  display: block;
  padding: 10px 12px;
  border-radius: 8px;
  font: inherit;
  text-align: left;
  border: 0;
  background: transparent;
  color: #63745c;
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.section-order-handle:active {
  cursor: grabbing;
}
.section-order-handle:focus-visible {
  outline: 2px solid #52775b;
  outline-offset: -2px;
}
.section-order-handle:disabled {
  cursor: default;
  opacity: 0.4;
}
.section-order-floating {
  position: fixed;
  z-index: 10000;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #86a38a;
  border-radius: 8px;
  background: #fff;
  color: #45654b;
  font-size: 13px;
  box-shadow: 0 8px 24px #223b2826;
  pointer-events: none;
  overflow-wrap: anywhere;
}
</style>
