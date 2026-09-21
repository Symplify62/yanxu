<script setup lang="ts">
import { computed, ref } from "vue";
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import RequestState from "../../components/RequestState.vue";
const { data, error, loading, refresh } = usePolling(api.admin.get),
  dialog = ref(false),
  department = ref(""),
  target = ref(""),
  version = ref(0),
  busy = ref(false),
  mutationError = ref(""),
  pauseDialog = ref(false);
const rows = computed(
  () =>
    data.value?.departments
      .filter((d) => d.id !== "ops")
      .map((d) => ({
        ...d,
        target: data.value!.settings.routes[d.id] || "",
      })) ?? [],
);
function edit(id: string) {
  department.value = id;
  target.value = data.value!.settings.routes[id] || "";
  version.value = data.value!.settings.routeVersion;
  mutationError.value = "";
  dialog.value = true;
}
async function save() {
  busy.value = true;
  try {
    await api.admin.route(department.value, target.value, version.value);
    dialog.value = false;
    await refresh();
  } catch (e) {
    mutationError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function pause() {
  busy.value = true;
  try {
    await api.admin.pause(!data.value!.settings.paused);
    pauseDialog.value = false;
    await refresh();
  } catch (e) {
    mutationError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">自动分发配置</p>
      <h1>部门与接收群</h1>
      <p class="muted">正常会议自动发送；员工不必核对、选群或确认发布。</p>
    </div>
  </div>
  <RequestState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="refresh"
  /><template v-else-if="data"
    ><div class="table-toolbar">
      <el-button
        :type="data.settings.paused ? 'primary' : 'default'"
        @click="
          mutationError = '';
          pauseDialog = true;
        "
        >{{ data.settings.paused ? "恢复自动发送" : "应急停止发送" }}</el-button
      ><el-tag :type="data.settings.paused ? 'warning' : 'success'">{{
        data.settings.paused ? "已应急停发" : "自动发送已启用"
      }}</el-tag>
    </div>
    <el-table :data="rows"
      ><el-table-column prop="name" label="归属" width="150" /><el-table-column
        label="接收群"
        min-width="230"
        ><template #default="{ row }">{{
          row.target || "未配置"
        }}</template></el-table-column
      ><el-table-column label="模式" min-width="200"
        ><template #default
          ><el-tag>AUTO · 无人工核对</el-tag></template
        ></el-table-column
      ><el-table-column label="操作" width="140"
        ><template #default="{ row }"
          ><el-button size="small" @click="edit(row.id)"
            >配置接收群</el-button
          ></template
        ></el-table-column
      ></el-table
    >
    <p class="small muted block-gap">
      新规则只作用后续会议；既有异常由管理员显式处理，不批量重路由或重发历史。
    </p></template
  >
  <el-dialog v-model="dialog" title="配置部门接收群" width="min(480px,94vw)"
    ><el-alert
      title="仅使用允许的虚构连接名。这里不接收真实Webhook。"
      type="info"
      :closable="false"
    /><el-form label-position="top" class="block-gap"
      ><el-form-item label="群连接"
        ><el-select v-model="target" aria-label="群连接"
          ><el-option
            v-for="name in [
              '',
              '销售管理群（模拟）',
              '财务管理群（模拟）',
              '项目协作群（模拟）',
            ]"
            :key="name"
            :label="name || '未配置'"
            :value="name" /></el-select></el-form-item></el-form
    ><el-alert
      v-if="mutationError"
      :title="mutationError"
      type="error"
      :closable="false"
    /><template #footer
      ><el-button @click="dialog = false">取消</el-button
      ><el-button type="primary" :loading="busy" @click="save"
        >保存新规则</el-button
      ></template
    ></el-dialog
  >
  <el-dialog v-model="pauseDialog" title="全局发送开关" width="min(460px,94vw)"
    ><p>
      该操作影响尚未提交的外发任务；原件继续保留。已发送目标不重复，未知结果仍需核查。
    </p>
    <el-alert
      v-if="mutationError"
      :title="mutationError"
      type="error"
      :closable="false"
    /><template #footer
      ><el-button @click="pauseDialog = false">取消</el-button
      ><el-button type="primary" :loading="busy" @click="pause"
        >确认{{ data?.settings.paused ? "恢复" : "停发" }}</el-button
      ></template
    ></el-dialog
  >
</template>
