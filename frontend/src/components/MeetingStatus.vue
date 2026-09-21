<script setup lang="ts">
import { computed } from "vue";
import type { JobState } from "../domain/types";
import { statusLabels, isException } from "../domain/presentation";
const props = defineProps<{
  state: JobState;
  mobile?: boolean;
  manual?: boolean;
}>();
const type = computed(() =>
  props.state === "ACCEPTED"
    ? "success"
    : isException(props.state)
      ? "warning"
      : "info",
);
</script>
<template>
  <van-tag v-if="mobile" :type="type === 'info' ? 'primary' : type" plain>{{
    manual ? "管理员已核查接收" : statusLabels[state]
  }}</van-tag
  ><el-tag v-else :type="type" effect="light" round>{{
    manual ? "管理员已核查接收" : statusLabels[state]
  }}</el-tag>
</template>
