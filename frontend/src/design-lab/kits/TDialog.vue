<script setup lang="ts">
import { Dialog } from "tdesign-vue-next";
defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
</script>
<template>
  <Dialog
    :visible="modelValue"
    header="模拟企业微信扫码"
    width="min(440px, calc(100vw - 32px))"
    placement="center"
    :close-on-overlay-click="false"
    @update:visible="emit('update:modelValue', $event)"
    ><slot /><template #footer><slot name="footer" /></template
  ></Dialog>
</template>
