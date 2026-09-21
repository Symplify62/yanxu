<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { AudioLines, Mic, FileText, ChevronDown } from "@lucide/vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import RecordingPage from "./RecordingPage.vue";
import ResultsPage from "../records/ResultsPage.vue";
import DetailPage from "../records/DetailPage.vue";
import { usePhaseDemo, transcript, sampleAnalysis } from "./model";
const demo = usePhaseDemo();
const {
  records,
  now,
  scenario,
  phase,
  elapsed,
  lastId,
  notice,
  loading,
  active,
} = demo;
const hash = ref(location.hash),
  controls = ref(false);
function readRoute() {
  hash.value = location.hash;
}
onMounted(() => window.addEventListener("hashchange", readRoute));
onUnmounted(() => window.removeEventListener("hashchange", readRoute));
const route = computed(() =>
  hash.value.startsWith("#/records/")
    ? "detail"
    : hash.value === "#/results"
      ? "results"
      : "record",
);
const id = computed(() => {
  try {
    return decodeURIComponent(hash.value.slice("#/records/".length));
  } catch {
    return "";
  }
});
const record = computed(
  () => records.value.find((r) => r.id === id.value) || null,
);
function go(target: string) {
  location.hash = target;
}
const scenarios = [
  { value: "normal", label: "正常流程" },
  { value: "capture-error", label: "录音不可用" },
  { value: "save-error", label: "保存失败" },
  { value: "offline", label: "上传等待网络" },
  { value: "transcript-error", label: "转写失败" },
  { value: "analysis-error", label: "AI 分析失败" },
];
</script>
<template>
  <el-config-provider :locale="zhCn"
    ><div class="p1-app">
      <div class="p1-demo-bar">
        <span><i></i>演示 · 未采音 / AI 样例</span>
        <button @click="controls = !controls" :aria-expanded="controls">
          演示控制<ChevronDown :size="13" />
        </button>
      </div>
      <div v-if="controls" class="p1-demo-controls">
        <label>演示场景</label>
        <el-select v-model="scenario" aria-label="演示场景" :disabled="active"
          ><el-option
            v-for="s in scenarios"
            :key="s.value"
            :label="s.label"
            :value="s.value"
        /></el-select>
        <el-button @click="demo.recover">恢复异常（演示）</el-button>
        <el-button
          :disabled="active"
          @click="
            demo.reset(true);
            go('/results');
          "
          >查看空列表</el-button
        >
        <el-button
          :disabled="active"
          @click="
            demo.reset();
            go('/record');
          "
          >重置演示</el-button
        >
        <span>数据仅保存在当前浏览器</span
        ><a href="/prototype.html">历史方案</a>
      </div>
      <header class="p1-header">
        <a href="#/record" class="p1-brand"
          ><AudioLines :size="24" /><strong>言序</strong></a
        >
        <nav aria-label="主要导航">
          <button
            :class="{ active: route === 'record' }"
            @click="go('/record')"
          >
            <Mic :size="16" />快速录音<span
              v-if="active"
              class="p1-active-dot"
            ></span></button
          ><button
            :class="{ active: route !== 'record' }"
            @click="go('/results')"
          >
            <FileText :size="16" />公共记录
          </button>
        </nav>
      </header>
      <main class="p1-main">
        <p v-if="notice && route !== 'record'" role="alert" class="p1-error">
          {{ notice }}
        </p>
        <RecordingPage
          v-if="route === 'record'"
          :phase="phase"
          :elapsed="elapsed"
          :notice="notice"
          @start="demo.start"
          @pause="demo.pause"
          @resume="demo.resume"
          @finish="demo.finish()"
          @retry="demo.finish(true)"
          @next="demo.next"
          @view="go('/records/' + lastId)"
        /><ResultsPage
          v-else-if="route === 'results'"
          :records="records"
          :now="now"
          :loading="loading"
          @open="go('/records/' + $event)"
          @record="go('/record')"
        /><DetailPage
          :demo-analysis="sampleAnalysis"
          :demo-transcript="transcript"
          v-else
          :record="record"
          :now="now"
          @back="go('/results')"
        />
      </main></div
  ></el-config-provider>
</template>
