<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ElMessageBox } from "element-plus";
import {
  account,
  errorMessage,
  hasPermission,
  onSessionClear,
  request,
} from "./api";
import { voiceLabels, type Person, type VoiceProfile } from "./types";
import VoiceEnrollmentPanel from "./VoiceEnrollmentPanel.vue";
const people = ref<Person[]>([]),
  profiles = ref<VoiceProfile[]>([]),
  query = ref(""),
  status = ref(""),
  error = ref(""),
  loading = ref(false),
  editing = ref<Person | null>(null),
  saving = ref(false);
const audioUrl = ref(""),
  playingName = ref(""),
  playingId = ref("");
let alive = true,
  audioGeneration = 0;
const rows = computed(() =>
  people.value
    .map((person) => ({
      ...person,
      profile: profiles.value.find((p) => p.personId === person.id),
    }))
    .filter(
      (p) =>
        p.name.includes(query.value) &&
        (!status.value || (p.profile?.status || "missing") === status.value),
    ),
);
const mayEnroll = (person: Person) =>
  person.id === account.value?.personId ||
  hasPermission("record") ||
  hasPermission("voices");
const mayRevoke = (person: Person) =>
  person.id === account.value?.personId || hasPermission("voices");
function release() {
  audioGeneration++;
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
  audioUrl.value = "";
  playingName.value = "";
  playingId.value = "";
}
const off = onSessionClear(release);
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [directory, voices] = await Promise.all([
      request<{ items: Person[] }>("/api/people"),
      request<{ items: VoiceProfile[] }>("/api/voice-profiles"),
    ]);
    if (!alive) return;
    people.value = directory.items.filter((person) =>
      voices.items.some((profile) => profile.personId === person.id),
    );
    profiles.value = voices.items;
  } catch (e) {
    people.value = [];
    profiles.value = [];
    release();
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
async function play(person: Person) {
  release();
  const generation = audioGeneration;
  error.value = "";
  try {
    const blob = await request<Blob>(
      `/api/people/${person.id}/voice-profile/audio`,
      { headers: { Accept: "audio/wav" } },
    );
    if (!alive || generation !== audioGeneration) return;
    audioUrl.value = URL.createObjectURL(blob);
    playingName.value = person.name;
    playingId.value = person.id;
  } catch (e) {
    error.value = errorMessage(e);
  }
}
async function revoke(person: Person) {
  try {
    await ElMessageBox.confirm(
      `撤回“${person.name}”的声音档案？后续会议将不再使用该档案。`,
      "撤回声音档案",
      { confirmButtonText: "撤回", cancelButtonText: "取消", type: "warning" },
    );
  } catch {
    return;
  }
  try {
    await request(`/api/people/${person.id}/voice-profile/revoke`, {
      method: "POST",
    });
    if (playingId.value === person.id) release();
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  }
}
function saved() {
  editing.value = null;
  release();
  void load();
}
async function close(done: () => void) {
  if (saving.value) return;
  try {
    await ElMessageBox.confirm("放弃本次声音登记？", "关闭登记", {
      confirmButtonText: "放弃",
      cancelButtonText: "继续登记",
    });
    done();
  } catch {
    /* Keep draft. */
  }
}
onMounted(load);
onUnmounted(() => {
  alive = false;
  release();
  off();
});
</script>
<template>
  <section aria-label="声音档案">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <div class="workspace-toolbar">
      <el-input
        v-model="query"
        placeholder="搜索人员"
        aria-label="搜索声音档案"
        clearable
      /><el-select
        v-model="status"
        aria-label="声音状态"
        placeholder="全部状态"
        clearable
        style="width: 150px"
        ><el-option label="可用" value="ready" /><el-option
          label="未登记"
          value="missing" /><el-option
          label="需重录"
          value="failed" /><el-option
          label="已撤回"
          value="revoked" /></el-select
      ><span class="toolbar-spacer" /><el-button
        :loading="loading"
        @click="load"
        >刷新</el-button
      >
    </div>
    <div
      v-if="audioUrl"
      class="workspace-surface"
      style="padding: 16px; margin-bottom: 16px"
    >
      <strong>{{ playingName }} · 登记样本</strong
      ><audio :src="audioUrl" controls autoplay class="voice-audio" /><el-button
        text
        @click="release"
        >关闭试听</el-button
      >
    </div>
    <div class="workspace-surface">
      <el-table v-loading="loading" :data="rows" empty-text="暂无声音档案"
        ><el-table-column label="人员" min-width="190"
          ><template #default="{ row }"
            ><div class="person-cell">
              <span class="account-avatar">{{ row.name.slice(0, 1) }}</span>
              <div>
                <strong>{{ row.name }}</strong
                ><small>{{
                  row.departmentName || row.detail || "未分配部门"
                }}</small>
              </div>
            </div></template
          ></el-table-column
        ><el-table-column label="状态" min-width="140"
          ><template #default="{ row }"
            ><span class="status-text" :class="row.profile?.status">{{
              voiceLabels[row.profile?.status || "missing"] ||
              row.profile?.status
            }}</span>
            <p v-if="row.profile?.error" class="panel-note">
              {{ row.profile.error }}
            </p></template
          ></el-table-column
        ><el-table-column label="登记时间" min-width="170"
          ><template #default="{ row }">{{
            row.profile?.recordedAt
              ? new Date(row.profile.recordedAt).toLocaleString("zh-CN", {
                  hour12: false,
                })
              : "—"
          }}</template></el-table-column
        ><el-table-column label="操作" width="240" fixed="right"
          ><template #default="{ row }"
            ><el-button
              v-if="mayEnroll(row as Person)"
              text
              type="primary"
              @click="editing = row as Person"
              >{{
                row.profile?.status === "ready" ? "更新" : "登记"
              }}</el-button
            ><el-button
              v-if="mayRevoke(row as Person)"
              text
              :disabled="row.profile?.status !== 'ready'"
              @click="play(row as Person)"
              >试听</el-button
            ><el-button
              v-if="mayRevoke(row as Person)"
              text
              :disabled="!row.profile || row.profile.status === 'revoked'"
              @click="revoke(row as Person)"
              >撤回</el-button
            ></template
          ></el-table-column
        ></el-table
      >
    </div>
    <el-dialog
      :model-value="Boolean(editing)"
      title="登记声音"
      width="520px"
      class="account-dialog"
      :close-on-click-modal="false"
      :before-close="close"
      destroy-on-close
      @update:model-value="
        (value) => {
          if (!value) editing = null;
        }
      "
      ><VoiceEnrollmentPanel
        v-if="editing"
        :person="editing"
        @saved="saved"
        @busy="saving = $event"
    /></el-dialog>
  </section>
</template>
