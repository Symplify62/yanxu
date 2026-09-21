<script setup lang="ts">
import { computed, ref } from "vue";
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import { isException, statusLabels } from "../../domain/presentation";
import type { AdminData } from "../../domain/types";
import MeetingStatus from "../../components/MeetingStatus.vue";
import RequestState from "../../components/RequestState.vue";
const { data, error, loading, refresh } = usePolling(api.admin.get),
  selected = ref<AdminData["jobs"][number]>(),
  dialog = ref(false),
  reason = ref(""),
  busy = ref(false),
  mutationError = ref("");
const jobs = computed(
  () => data.value?.jobs.filter((m) => isException(m.state)) ?? [],
);
function open(id: string) {
  selected.value = { ...data.value!.jobs.find((j) => j.id === id)! };
  reason.value = "";
  mutationError.value = "";
  dialog.value = true;
}
async function recover() {
  if (!reason.value.trim()) {
    mutationError.value = "请填写处理依据";
    return;
  }
  busy.value = true;
  try {
    await api.admin.recover(selected.value!.id, reason.value);
    dialog.value = false;
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
      <p class="eyebrow">异常接管</p>
      <h1>异常处理</h1>
      <p class="muted">
        系统先自动恢复；超限、未配置或结果不明时由管理员处理。
      </p>
    </div>
  </div>
  <RequestState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="refresh"
  /><template v-else
    ><el-alert
      title="不向员工派发维护步骤。诊断默认只有编号与任务元数据，无会议正文。"
      type="warning"
      :closable="false"
    /><el-empty
      v-if="!jobs.length"
      description="没有需要人工接管的异常"
    /><el-table v-else :data="jobs" class="block-gap"
      ><el-table-column
        prop="id"
        label="记录编号"
        min-width="140"
      /><el-table-column label="状态" min-width="230"
        ><template #default="{ row }"
          ><MeetingStatus :state="row.state" /></template></el-table-column
      ><el-table-column
        prop="attempts"
        label="自动尝试"
        width="100"
      /><el-table-column label="处理" width="180"
        ><template #default="{ row }"
          ><el-button size="small" @click="open(String(row.id))">{{
            row.state === "UNKNOWN" ? "记录渠道核查" : "重新检查并恢复"
          }}</el-button></template
        ></el-table-column
      ></el-table
    ></template
  >
  <el-dialog
    v-model="dialog"
    title="管理员处理异常"
    width="min(500px,94vw)"
    :close-on-click-modal="false"
    ><el-alert
      :title="selected ? statusLabels[selected.state] : ''"
      type="warning"
      :closable="false"
    />
    <p class="small muted block-gap">
      {{
        selected?.state === "UNKNOWN"
          ? "请求可能已经送达，不能盲目重发。这里只记录管理员查到渠道接收的依据，不伪造服务回执。"
          : "模拟依赖恢复后重新校验，只继续失败阶段，不重做成功阶段。"
      }}
    </p>
    <el-form label-position="top"
      ><el-form-item label="处理依据（必填）" :error="mutationError"
        ><el-input
          v-model="reason"
          aria-label="处理依据"
          type="textarea"
          :rows="3" /></el-form-item></el-form
    ><template #footer
      ><el-button @click="dialog = false">取消</el-button
      ><el-button type="primary" :loading="busy" @click="recover">{{
        selected?.state === "UNKNOWN" ? "记录人工已核对接收" : "确认恢复该阶段"
      }}</el-button></template
    ></el-dialog
  >
</template>
