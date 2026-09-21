<script setup lang="ts">
import { Checkbox } from "../ui/checkbox";
import { useId } from "vue";
defineProps<{ modelValue: boolean; label: string }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
const id = useId();
</script>
<template>
  <div class="check-item">
    <Checkbox
      :id="id"
      :model-value="modelValue"
      @update:model-value="emit('update:modelValue', $event === true)"
    /><label :for="id">{{ label }}</label>
  </div>
</template>
