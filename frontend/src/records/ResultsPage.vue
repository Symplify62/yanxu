<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Search, FileText, ArrowUpRight, Plus, Clock } from "@lucide/vue";
import { duration } from "../domain/presentation";
import { stageOf, stageLabels, isProcessed, type PublicRecord } from "./model";
const props = defineProps<{
  records: PublicRecord[];
  now: number;
  loading: boolean;
  live?: boolean;
  embedded?: boolean;
  total?: number;
}>();
const emit = defineEmits<{
  open: [id: string];
  record: [];
  search: [value: string];
  filter: [value: string];
}>();
const search = ref(""),
  filter = ref("all");
watch(search, (value) => {
  if (props.live) emit("search", value);
});
watch(filter, (value) => {
  if (props.live) emit("filter", value);
});
const items = computed(() =>
  props.records.filter(
    (r) =>
      r.title.toLowerCase().includes(search.value.trim().toLowerCase()) &&
      (filter.value === "all" ||
        (filter.value === "complete"
          ? isProcessed(stageOf(r, props.now))
          : !isProcessed(stageOf(r, props.now)))),
  ),
);
</script>
<template>
  <section
    class="p1-results"
    :class="{ 'is-live': live }"
    aria-label="公共记录"
  >
    <header v-if="!embedded" class="p1-section-head">
      <div>
        <h1>公共记录</h1>
      </div>
      <el-button
        v-if="!live"
        type="primary"
        size="large"
        @click="$emit('record')"
        ><Plus :size="16" />新录音</el-button
      >
    </header>
    <div class="p1-list-toolbar">
      <div class="p1-filters" aria-label="记录状态">
        <button
          v-for="f in [
            ['all', '全部记录'],
            ['complete', '已完成'],
            ['processing', '处理中 / 异常'],
          ]"
          :key="f[0]"
          :class="{ active: filter === f[0] }"
          :aria-pressed="filter === f[0]"
          @click="filter = f[0]!"
        >
          {{ f[1] }}
        </button>
      </div>
      <el-input
        v-model="search"
        aria-label="搜索公共记录"
        placeholder="搜索记录标题"
        :maxlength="120"
        clearable
        ><template #prefix><Search :size="16" /></template>
        <template v-if="live" #suffix>
          <span class="p1-toolbar-count" role="status" aria-live="polite">{{
            loading ? "…" : `${total ?? items.length} 条`
          }}</span>
        </template>
      </el-input>
    </div>
    <el-skeleton v-if="loading" :rows="4" animated class="p1-list-empty" />
    <div v-else-if="!items.length" class="p1-list-empty">
      <FileText :size="38" :stroke-width="1.3" />
      <h2>
        {{ search || filter !== "all" ? "没有符合条件的记录" : "暂无记录" }}
      </h2>
      <el-button
        v-if="!live && !search && filter === 'all'"
        type="primary"
        @click="$emit('record')"
        >开始第一段录音</el-button
      ><el-button
        v-else-if="search || filter !== 'all'"
        @click="
          search = '';
          filter = 'all';
        "
        >清除筛选</el-button
      >
    </div>
    <template v-else
      ><p v-if="!live" class="p1-result-count">{{ items.length }} 条记录</p>
      <button
        v-for="r in items"
        :key="r.id"
        class="p1-result-row"
        @click="$emit('open', r.id)"
      >
        <div class="p1-file-mark">
          <FileText :size="22" :stroke-width="1.5" />
        </div>
        <div class="p1-result-main">
          <span class="p1-row-date">{{
            new Date(r.createdAt).toLocaleString("zh-CN", {
              month: "long",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            })
          }}</span>
          <h2>{{ r.title }}</h2>
          <div class="p1-row-meta">
            <Clock :size="13" />{{ duration(r.duration) }}
          </div>
        </div>
        <span
          class="p1-status"
          :class="{
            done: stageOf(r, now) === 'complete',
            failed: stageOf(r, now).includes('error'),
          }"
          >{{ stageLabels[stageOf(r, now)] }}</span
        ><ArrowUpRight :size="19" class="p1-row-arrow" /></button
    ></template>
  </section>
</template>
