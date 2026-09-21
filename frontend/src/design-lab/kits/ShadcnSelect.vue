<script setup lang="ts">
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "../ui/select";
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
    :model-value="modelValue"
    :disabled="disabled"
    @update:model-value="emit('update:modelValue', String($event))"
    ><SelectTrigger :aria-label="label" class="w-full h-11"
      ><SelectValue /></SelectTrigger
    ><SelectContent
      ><SelectItem v-for="o in options" :key="o.value" :value="o.value">{{
        o.label
      }}</SelectItem></SelectContent
    ></Select
  >
</template>
