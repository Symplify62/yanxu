<script setup lang="ts">
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
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
  <component
    :is="multiline ? Textarea : Input"
    :model-value="modelValue"
    :aria-label="label"
    :placeholder="placeholder"
    :rows="4"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', String($event))"
  />
</template>
