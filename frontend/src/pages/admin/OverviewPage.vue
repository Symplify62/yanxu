<script setup lang="ts">
import { computed } from "vue";
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import { isException } from "../../domain/presentation";
import MeetingStatus from "../../components/MeetingStatus.vue";
import RequestState from "../../components/RequestState.vue";
const { data, error, loading, refresh } = usePolling(api.admin.get);
const metrics = computed(() =>
  data.value
    ? [
        ["会议记录", data.value.jobs.length],
        [
          "自动完成",
          data.value.jobs.filter((m) => m.state === "ACCEPTED").length,
        ],
        [
          "处理中",
          data.value.jobs.filter(
            (m) => m.state !== "ACCEPTED" && !isException(m.state),
          ).length,
        ],
        [
          "管理员异常",
          data.value.jobs.filter((m) => isException(m.state)).length,
        ],
      ]
    : [],
);
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">运行概览</p>
      <h1>自动处理概览</h1>
      <p class="muted">关注真实处理状态，正常会议无需人工步骤。</p>
    </div>
    <el-tag>合成数据</el-tag>
  </div>
  <RequestState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="refresh"
  /><template v-else-if="data"
    ><div class="metric-grid">
      <el-card
        v-for="[label, value] in metrics"
        :key="String(label)"
        shadow="never"
        ><el-statistic :title="String(label)" :value="Number(value)"
      /></el-card>
    </div>
    <el-alert
      title="维护者只看编号、归属和任务状态，会议正文另需授权。"
      type="info"
      :closable="false"
      class="block-gap" /><el-table :data="data.jobs" class="block-gap" stripe
      ><el-table-column
        prop="id"
        label="记录编号"
        min-width="150" /><el-table-column
        prop="department"
        label="归属"
        width="130" /><el-table-column label="自动状态" min-width="220"
        ><template #default="{ row }"
          ><MeetingStatus
            :state="row.state"
            :manual="row.resolvedManually" /></template></el-table-column
      ><el-table-column
        prop="attempts"
        label="失败尝试"
        width="110" /><el-table-column
        prop="sendCount"
        label="模拟发送次数"
        width="130" /></el-table
  ></template>
</template>
