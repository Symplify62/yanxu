<script setup lang="ts">
defineProps<{ modelValue: boolean; label: string }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
</script>
<template>
  <el-checkbox
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', Boolean($event))"
    >{{ label }}</el-checkbox
  >
</template>
