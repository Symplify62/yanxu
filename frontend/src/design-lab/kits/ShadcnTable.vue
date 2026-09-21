<script setup lang="ts">
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "../ui/table";
import type { Column } from "../full/context";
defineProps<{
  rows: Record<string, unknown>[];
  columns: Column[];
  caption?: string;
}>();
</script>
<template>
  <Table :aria-label="caption" class="full-data-table"
    ><TableHeader
      ><TableRow
        ><TableHead
          v-for="c in columns"
          :key="c.key"
          :style="{ minWidth: (c.width || 130) + 'px' }"
          >{{ c.label }}</TableHead
        ></TableRow
      ></TableHeader
    ><TableBody
      ><TableRow v-for="(row, i) in rows" :key="String(row.id ?? i)"
        ><TableCell v-for="c in columns" :key="c.key"
          ><slot :name="c.key" :row="row">{{ row[c.key] }}</slot></TableCell
        ></TableRow
      ><TableRow v-if="!rows.length"
        ><TableCell :colspan="columns.length" class="table-empty"
          >暂无记录</TableCell
        ></TableRow
      ></TableBody
    ></Table
  >
</template>
