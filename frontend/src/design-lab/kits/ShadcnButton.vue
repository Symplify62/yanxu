<script setup lang="ts">
import { Button } from "../ui/button";
defineProps<{ secondary?: boolean; busy?: boolean; disabled?: boolean }>();
</script>
<template>
  <Button
    :variant="secondary ? 'outline' : 'default'"
    size="lg"
    :disabled="busy || disabled"
    ><slot /><span v-if="busy" aria-label="处理中">…</span></Button
  >
</template>
