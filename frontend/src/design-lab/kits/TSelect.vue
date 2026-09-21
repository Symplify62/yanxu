<script setup lang="ts">
import { Select } from "tdesign-vue-next";
defineProps<{
  modelValue: string;
  options: { value: string; label: string }[];
  label: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
</script>
<template>
  <Select
    :value="modelValue"
    :options="options"
    :aria-label="label"
    :disabled="disabled"
    size="large"
    @change="emit('update:modelValue', String($event))"
  />
</template>
