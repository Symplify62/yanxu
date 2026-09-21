<script setup lang="ts">
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import RequestState from "../../components/RequestState.vue";
const { data, error, loading, refresh } = usePolling(api.admin.get);
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">追溯与责任</p>
      <h1>操作记录</h1>
      <p class="muted">区分系统自动处理、员工主动操作与管理员恢复。</p>
    </div>
  </div>
  <RequestState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="refresh"
  /><el-table v-else :data="data?.audit" empty-text="暂无本次演示操作"
    ><el-table-column label="时间" width="120"
      ><template #default="{ row }">{{
        new Date(row.time).toLocaleTimeString("zh-CN")
      }}</template></el-table-column
    ><el-table-column
      prop="action"
      label="动作"
      min-width="190" /><el-table-column
      prop="detail"
      label="对象与说明"
      min-width="320"
      show-overflow-tooltip
  /></el-table>
</template>
