<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { AudioLines, FileText, LayoutTemplate, LibraryBig } from "@lucide/vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import ResultsPage from "../records/ResultsPage.vue";
import DetailPage from "../records/DetailPage.vue";
import TemplateManagerPage from "../records/TemplateManagerPage.vue";
import TextImportPage from "./TextImportPage.vue";
import SampleLibraryPage from "./SampleLibraryPage.vue";
import type { PublicRecord } from "../records/model";
import {
  defaultBriefingTemplates,
  normalizeTemplateSections,
  type BriefingTemplate,
} from "../records/briefing";
const embedded = new URLSearchParams(location.search).get("app") === "1";
const query = ref(""),
  filter = ref("all");
const records = ref<PublicRecord[]>([]),
  selected = ref<PublicRecord | null>(null),
  templates = ref<BriefingTemplate[]>([...defaultBriefingTemplates]),
  error = ref(""),
  loading = ref(true),
  hash = ref(location.hash),
  now = ref(Date.now()),
  total = ref(0),
  offset = ref(0),
  busy = ref(false);
const isDetail = computed(() => hash.value.startsWith("#/records/"));
const isImport = computed(() => hash.value === "#/import");
const isTemplates = computed(() => hash.value === "#/templates");
const isSamples = computed(() => hash.value === "#/samples");
let timer: ReturnType<typeof setInterval>;
function normalizeRemoteTemplate(value: unknown): BriefingTemplate | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  if (
    typeof item.id !== "string" ||
    typeof item.name !== "string" ||
    !Array.isArray(item.sections)
  )
    return null;
  const sections = normalizeTemplateSections(item.sections);
  if (!sections.length) return null;
  return {
    id: item.id,
    name: item.name,
    description: typeof item.description === "string" ? item.description : "",
    sections,
    source: item.source === "custom" ? "custom" : "builtin",
    createdAt: typeof item.createdAt === "number" ? item.createdAt : undefined,
    updatedAt: typeof item.updatedAt === "number" ? item.updatedAt : undefined,
  };
}
async function loadTemplates() {
  try {
    const response = await fetch("/api/briefing/templates");
    if (!response.ok) throw new Error("templates");
    const data = await response.json();
    const items = Array.isArray(data.items)
      ? data.items
          .map((item: unknown) => normalizeRemoteTemplate(item))
          .filter((item: BriefingTemplate | null): item is BriefingTemplate =>
            Boolean(item),
          )
      : [];
    if (items.length) templates.value = items;
  } catch {
    templates.value = [...defaultBriefingTemplates];
  }
}
async function refresh() {
  if (isImport.value || isTemplates.value || isSamples.value) {
    loading.value = false;
    now.value = Date.now();
    return;
  }
  if (busy.value) return;
  busy.value = true;
  const requestedHash = hash.value;
  const requestedQuery = query.value;
  const requestedFilter = filter.value;
  const requestedOffset = offset.value;
  try {
    const id = decodeURIComponent(hash.value.slice(10));
    const response = await fetch(
      isDetail.value
        ? "/api/recordings/" + encodeURIComponent(id)
        : "/api/recordings?limit=100&offset=" +
            offset.value +
            "&q=" +
            encodeURIComponent(query.value) +
            "&filter=" +
            filter.value,
    );
    if (!response.ok) {
      if (response.status === 404) {
        selected.value = null;
        error.value = "";
        return;
      }
      throw new Error("记录暂时无法加载，请稍后重试");
    }
    const data = await response.json();
    if (
      hash.value !== requestedHash ||
      query.value !== requestedQuery ||
      filter.value !== requestedFilter ||
      offset.value !== requestedOffset
    )
      return;
    if (isDetail.value) selected.value = data;
    else {
      records.value = data.items;
      total.value = data.total;
    }
    error.value = "";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "记录暂时无法加载";
  } finally {
    busy.value = false;
    loading.value = false;
    now.value = Date.now();
  }
}
function route() {
  hash.value = location.hash;
  loading.value = true;
  selected.value = null;
  void refresh();
}
function search(value: string) {
  query.value = value;
  offset.value = 0;
  loading.value = true;
  void refresh();
}
function changeFilter(value: string) {
  filter.value = value;
  offset.value = 0;
  loading.value = true;
  void refresh();
}
function open(id: string) {
  location.hash = "/records/" + id;
}
function back() {
  location.hash = "/results";
}
function importText() {
  location.hash = "/import";
}
function manageTemplates() {
  location.hash = "/templates";
}
function openSamples() {
  location.hash = "/samples";
}
function updateTemplates(next: BriefingTemplate[]) {
  templates.value = next;
}
function page(delta: number) {
  offset.value = Math.max(0, offset.value + delta * 100);
  void refresh();
}
onMounted(() => {
  window.addEventListener("hashchange", route);
  void loadTemplates();
  void refresh();
  timer = setInterval(() => void refresh(), 1500);
});
onUnmounted(() => {
  window.removeEventListener("hashchange", route);
  clearInterval(timer);
});
</script>
<template>
  <el-config-provider :locale="zhCn"
    ><div class="p1-app" :class="{ 'p1-app--embedded': embedded }">
      <header v-if="!embedded" class="p1-header">
        <a href="#/results" class="p1-brand"
          ><AudioLines :size="24" /><strong>言序</strong></a
        >
        <nav class="live-links">
          <button class="p1-header-link" @click="manageTemplates">
            <LayoutTemplate :size="15" />纪要模板</button
          ><button class="p1-header-link" @click="openSamples">
            <LibraryBig :size="15" />样本文档</button
          ><button class="p1-header-link" @click="importText">
            <FileText :size="15" />导入文本</button
          >
          <a href="/account.html" class="p1-secondary">账号工作台</a
          ><a href="/app/yanxu-debug.apk" class="p1-secondary"
            >下载 Android 测试版</a
          >
        </nav>
      </header>
      <main class="p1-main">
        <div v-if="error" role="alert" class="p1-error">
          {{ error }}<el-button @click="refresh">重试</el-button>
        </div>
        <template v-else
          ><TextImportPage
            v-if="isImport"
            @open="open"
            @back="back"
          /><TemplateManagerPage
            v-else-if="isTemplates"
            :templates="templates"
            live
            @update="updateTemplates"
          /><SampleLibraryPage
            v-else-if="isSamples"
            @open="open"
            @back="back"
          /><el-skeleton
            v-else-if="isDetail && loading"
            :rows="5"
            animated
          /><DetailPage
            v-else-if="isDetail"
            :record="selected"
            :now="now"
            :briefing-templates="templates"
            live
            @back="back"
          /><template v-else
            ><ResultsPage
              :records="records"
              :now="now"
              :loading="loading"
              :embedded="embedded"
              :total="total"
              live
              @open="open"
              @search="search"
              @filter="changeFilter"
            />
            <div v-if="total > 100" class="live-pagination">
              <el-button :disabled="offset === 0" @click="page(-1)"
                >上一页</el-button
              ><span
                >{{ offset + 1 }}–{{ Math.min(offset + 100, total) }} /
                {{ total }}</span
              ><el-button :disabled="offset + 100 >= total" @click="page(1)"
                >下一页</el-button
              >
            </div></template
          ></template
        >
      </main>
    </div></el-config-provider
  >
</template>
<style>
.live-links {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.p1-header-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
  border: 1px solid var(--p1-line);
  background: white;
  color: var(--p1-accent);
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 13px;
}
.live-audio audio {
  width: 100%;
  margin: 20px 0;
}
.live-download {
  display: inline-block;
  border: 1px solid var(--p1-line);
  padding: 9px 17px;
  border-radius: 8px;
  color: var(--p1-accent) !important;
}
.live-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 18px;
  padding: 25px;
  font-size: 12px;
}
.p1-detail-tabs {
  flex-wrap: wrap;
}
.live-audio {
  min-height: 180px;
}
.p1-text-import {
  max-width: 1060px;
  margin: 0 auto;
}
.p1-text-import-grid {
  border: 1px solid var(--p1-line);
  border-radius: 10px;
  background: white;
  padding: 22px;
}
.p1-text-import-form {
  display: grid;
  gap: 18px;
}
.p1-text-import-form label {
  display: grid;
  gap: 8px;
  font-size: 12px;
  color: var(--p1-muted);
}
.p1-text-import-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.p1-text-import-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.p1-text-import-actions p {
  margin: 0;
  color: #b54747;
  font-size: 12px;
}
.p1-text-file-button {
  width: fit-content;
  display: inline-flex !important;
  grid-template-columns: none !important;
  align-items: center;
  gap: 8px !important;
  border: 1px solid var(--p1-line);
  border-radius: 8px;
  padding: 8px 13px;
  color: var(--p1-accent) !important;
  background: #fbfcf8;
  cursor: pointer;
}
.p1-text-file-button input {
  display: none;
}
@media (max-width: 760px) {
  .p1-text-import-row {
    grid-template-columns: 1fr;
  }
}
</style>
