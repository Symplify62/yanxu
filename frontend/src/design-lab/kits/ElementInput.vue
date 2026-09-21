<script setup lang="ts">
defineProps<{
  modelValue: string;
  label: string;
  placeholder?: string;
  multiline?: boolean;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
</script>
<template>
  <el-input
    :model-value="modelValue"
    :aria-label="label"
    :placeholder="placeholder"
    :type="multiline ? 'textarea' : 'text'"
    :rows="4"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', $event)"
  />
</template>
