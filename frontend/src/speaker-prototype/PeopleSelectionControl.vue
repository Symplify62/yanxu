<script setup lang="ts">
import { computed } from "vue";
import { ElCheckbox } from "element-plus";
import type { Person, PrototypeModel } from "./model";

const props = defineProps<{
  model: PrototypeModel;
  people: Person[];
  scope: "current" | "filtered";
}>();
const count = computed(
  () =>
    props.people.filter((p) => props.model.selectedIds.value.includes(p.id))
      .length,
);
const all = computed(
  () => props.people.length > 0 && count.value === props.people.length,
);
const mixed = computed(() => count.value > 0 && !all.value);
const label = computed(
  () =>
    `${all.value ? "取消全选" : "全选"}${props.scope === "current" ? "当前人员" : "筛选结果"}`,
);
const reason = computed(() => {
  if (!props.model.can("record")) return "当前身份没有发起会议权限";
  if (!props.people.length) return "当前没有可选人员";
  if (!["setup", "recording", "paused"].includes(props.model.phase.value))
    return "会议正在整理，请稍后操作";
  if (props.model.phase.value !== "setup" && all.value)
    return "录音中不能取消已加入的参会者";
  return "";
});
</script>
<template>
  <ElCheckbox
    class="people-select-all"
    :model-value="all"
    :indeterminate="mixed"
    :disabled="!!reason"
    :aria-label="label"
    :title="
      reason ||
      (scope === 'current'
        ? '仅作用于下方展示的人员'
        : '仅作用于当前搜索和部门筛选结果')
    "
    @change="
      (value) =>
        model.setPeopleSelected(
          people.map((p) => p.id),
          Boolean(value),
        )
    "
    >{{ label }}</ElCheckbox
  >
</template>
