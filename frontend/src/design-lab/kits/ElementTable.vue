<script setup lang="ts">
import type { Column } from "../full/context";
defineProps<{
  rows: Record<string, unknown>[];
  columns: Column[];
  caption?: string;
}>();
</script>
<template>
  <el-table
    :data="rows"
    :aria-label="caption"
    empty-text="暂无记录"
    class="full-data-table"
    ><el-table-column
      v-for="c in columns"
      :key="c.key"
      :prop="c.key"
      :label="c.label"
      :min-width="c.width || 130"
      ><template #default="{ row }"
        ><slot :name="c.key" :row="row">{{ row[c.key] }}</slot></template
      ></el-table-column
    ></el-table
  >
</template>
