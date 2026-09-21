<script setup lang="ts">
defineProps<{ secondary?: boolean; busy?: boolean; disabled?: boolean }>();
</script>
<template>
  <el-button
    :type="secondary ? undefined : 'primary'"
    :loading="busy"
    :disabled="disabled || busy"
    size="large"
    ><slot
  /></el-button>
</template>
