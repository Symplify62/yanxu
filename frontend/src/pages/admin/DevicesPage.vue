<script setup lang="ts">
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import TabletQueue from "../../components/TabletQueue.vue";
import RequestState from "../../components/RequestState.vue";
const { data, error, loading, refresh } = usePolling(api.device.get);
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">设备与容量</p>
      <h1>设备与存储</h1>
      <p class="muted">本场员工身份与设备后台任务相互独立。</p>
    </div>
  </div>
  <RequestState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="refresh"
  /><el-card v-else-if="data" shadow="never"
    ><template #header>会议室 A · 已配对设备（模拟）</template
    ><el-descriptions :column="1" border
      ><el-descriptions-item label="网络"
        ><el-tag :type="data.online ? 'success' : 'warning'">{{
          data.online ? "在线" : "离线"
        }}</el-tag></el-descriptions-item
      ><el-descriptions-item label="本场员工">{{
        data.employeeName || "已退出 / 等待扫码"
      }}</el-descriptions-item
      ><el-descriptions-item label="公司档案"
        >原录音与文字长期保留，不按期限自动删除</el-descriptions-item
      ><el-descriptions-item label="设备缓存"
        >归档、独立备份与批准清理条件满足后处理</el-descriptions-item
      ><el-descriptions-item label="录音时长"
        >不设业务截止；真实持续能力与资源边界需真机验证</el-descriptions-item
      ></el-descriptions
    ><TabletQueue :queue="data.queue"
  /></el-card>
</template>
