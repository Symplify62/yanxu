<script setup lang="ts">
defineProps<{
  modelValue: string;
  options: { value: string; label: string }[];
  label: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
</script>
<template>
  <el-select
    :model-value="modelValue"
    :aria-label="label"
    size="large"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', $event)"
    ><el-option
      v-for="o in options"
      :key="o.value"
      :value="o.value"
      :label="o.label"
  /></el-select>
</template>
