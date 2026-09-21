<script setup lang="ts">
defineProps<{ modelValue: boolean; title?: string }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
</script>
<template>
  <el-dialog
    class="lab-dialog-content"
    :model-value="modelValue"
    :title="title || '模拟企业微信扫码'"
    width="min(440px, calc(100vw - 32px))"
    align-center
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
    ><slot /><template #footer><slot name="footer" /></template
  ></el-dialog>
</template>
