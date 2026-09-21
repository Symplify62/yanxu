<script setup lang="ts">
import { Button } from "tdesign-vue-next";
defineProps<{ secondary?: boolean; busy?: boolean; disabled?: boolean }>();
</script>
<template>
  <Button
    :theme="secondary ? 'default' : 'primary'"
    :variant="secondary ? 'outline' : 'base'"
    :loading="busy"
    :disabled="disabled || busy"
    size="large"
    ><slot
  /></Button>
</template>
