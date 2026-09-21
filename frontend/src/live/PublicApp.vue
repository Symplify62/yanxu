<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { AudioLines } from "@lucide/vue";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import ResultsPage from "../records/ResultsPage.vue";
import DetailPage from "../records/DetailPage.vue";
import type { PublicRecord } from "../records/model";
const embedded = new URLSearchParams(location.search).get("app") === "1";
const query = ref(""),
  filter = ref("all");
const records = ref<PublicRecord[]>([]),
  selected = ref<PublicRecord | null>(null),
  error = ref(""),
  loading = ref(true),
  hash = ref(location.hash),
  now = ref(Date.now()),
  total = ref(0),
  offset = ref(0),
  busy = ref(false);
const isDetail = computed(() => hash.value.startsWith("#/records/"));
let timer: ReturnType<typeof setInterval>;
async function refresh() {
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
function page(delta: number) {
  offset.value = Math.max(0, offset.value + delta * 100);
  void refresh();
}
onMounted(() => {
  window.addEventListener("hashchange", route);
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
        ><a href="/app/yanxu-debug.apk" class="p1-secondary"
          >下载 Android 测试版</a
        >
      </header>
      <main class="p1-main">
        <div v-if="error" role="alert" class="p1-error">
          {{ error }}<el-button @click="refresh">重试</el-button>
        </div>
        <template v-else
          ><el-skeleton
            v-if="isDetail && loading"
            :rows="5"
            animated
          /><DetailPage
            v-else-if="isDetail"
            :record="selected"
            :now="now"
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
</style>
