<script setup lang="ts">
import { onMounted, ref } from "vue";
import { errorMessage, request } from "./api";
const data = ref<{
  counts: Record<string, number>;
  appVersion: { versionName: string; versionCode: number } | null;
} | null>(null);
const error = ref("");
async function load() {
  try {
    data.value = await request("/api/admin/overview");
    error.value = "";
  } catch (e) {
    error.value = errorMessage(e);
  }
}
onMounted(load);
</script>
<template>
  <section aria-label="管理概览">
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div class="workspace-toolbar">
      <span class="status-text">当前服务数据</span
      ><span class="toolbar-spacer" /><el-button @click="load">刷新</el-button>
    </div>
    <div v-if="data" class="overview-grid">
      <a class="overview-card" href="#/all-recordings"
        ><small>录音</small><strong>{{ data.counts.recordings }}</strong></a
      >
      <div class="overview-card">
        <small>处理中</small><strong>{{ data.counts.processing }}</strong>
      </div>
      <div class="overview-card" :class="{ alert: data.counts.failed }">
        <small>处理失败</small><strong>{{ data.counts.failed }}</strong>
      </div>
      <div class="overview-card">
        <small>云端待同步</small><strong>{{ data.counts.cloudPending }}</strong>
      </div>
      <div class="overview-card" :class="{ alert: data.counts.cloudFailed }">
        <small>云端同步失败</small
        ><strong>{{ data.counts.cloudFailed }}</strong>
      </div>
      <a class="overview-card" href="#/users"
        ><small>人员</small><strong>{{ data.counts.users }}</strong></a
      >
      <a class="overview-card" href="#/voices"
        ><small>声音任务待处理</small
        ><strong>{{ data.counts.voicePending }}</strong></a
      >
      <a class="overview-card" href="#/app-versions"
        ><small>App 当前版本</small
        ><strong>{{
          data.appVersion
            ? `${data.appVersion.versionName} (${data.appVersion.versionCode})`
            : "未发布"
        }}</strong></a
      >
    </div>
  </section>
</template>
