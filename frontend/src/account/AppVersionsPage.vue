<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessageBox } from "element-plus";
import { errorMessage, request } from "./api";
interface Release {
  sha256: string;
  versionCode: number;
  versionName: string;
  minSdk: number;
  packageName: string;
  size: number;
  notes?: string;
  uploadedAt?: number | null;
}
interface AuditEvent {
  action: string;
  sha256: string;
  fromSha256?: string | null;
  actor: string;
  at: number;
}
interface Data {
  environment: string;
  packageName: string;
  current: Release | null;
  versions: Release[];
  events: AuditEvent[];
}
const data = ref<Data | null>(null),
  error = ref(""),
  busy = ref(false),
  file = ref<File | null>(null),
  notes = ref("");
const name = computed(() =>
  data.value?.environment === "production"
    ? "生产环境"
    : data.value?.environment === "testing"
      ? "测试环境"
      : "本地环境",
);
async function load() {
  try {
    data.value = await request<Data>("/api/admin/app-versions");
    error.value = "";
  } catch (e) {
    error.value = errorMessage(e);
  }
}
function pick(event: Event) {
  const input = event.target as HTMLInputElement;
  file.value = input.files?.[0] || null;
}
async function upload() {
  if (!file.value || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    data.value = await request<Data>(
      `/api/admin/app-versions/candidate?notes=${encodeURIComponent(notes.value)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/vnd.android.package-archive" },
        body: file.value,
      },
    );
    file.value = null;
    notes.value = "";
    const input = document.querySelector<HTMLInputElement>("#version-apk");
    if (input) input.value = "";
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
async function switchTo(release: Release, rollback: boolean) {
  if (!data.value || busy.value) return;
  const action = rollback ? "回退" : "发布";
  try {
    await ElMessageBox.confirm(
      `${action}${name.value}更新清单至 ${release.versionName}（${release.versionCode}）？${rollback ? "已安装较新版本的设备不会自动降级。" : "设备下次检查更新时可获取此版本。"}`,
      `${action} App 版本`,
      { type: "warning", confirmButtonText: action, cancelButtonText: "取消" },
    );
  } catch {
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    data.value = await request<Data>(
      `/api/admin/app-versions/${rollback ? "rollback" : "publish"}`,
      {
        method: "POST",
        body: JSON.stringify({
          sha256: release.sha256,
          expectedCurrentSha: data.value.current?.sha256 || null,
        }),
      },
    );
  } catch (e) {
    error.value = errorMessage(e);
    await load();
  } finally {
    busy.value = false;
  }
}
onMounted(load);
</script>
<template>
  <section aria-label="App 版本管理">
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div class="workspace-toolbar">
      <span class="status-text">{{ name }} · {{ data?.packageName }}</span
      ><span class="toolbar-spacer" /><el-button @click="load">刷新</el-button>
    </div>
    <div class="version-current workspace-surface">
      <small>当前发布</small
      ><strong>{{
        data?.current
          ? `${data.current.versionName} · ${data.current.versionCode}`
          : "未发布"
      }}</strong
      ><span v-if="data?.current" class="version-hash"
        >SHA-256 {{ data.current.sha256 }}</span
      >
    </div>
    <div class="workspace-surface version-upload">
      <h2>上传候选 APK</h2>
      <input
        id="version-apk"
        type="file"
        accept=".apk,application/vnd.android.package-archive"
        aria-label="选择 APK"
        @change="pick"
      /><el-input
        v-model="notes"
        placeholder="更新说明（可选）"
        maxlength="2000"
      /><el-button
        type="primary"
        :loading="busy"
        :disabled="!file || (file?.size || 0) > 100 * 1024 * 1024"
        @click="upload"
        >上传并校验</el-button
      >
    </div>
    <div class="workspace-surface version-list">
      <h2>版本记录</h2>
      <div v-if="!data?.versions.length" class="version-row">暂无版本</div>
      <div
        v-for="release in data?.versions || []"
        :key="release.sha256"
        class="version-row"
      >
        <div>
          <strong>{{ release.versionName }} · {{ release.versionCode }}</strong
          ><small
            >{{ (release.size / 1024 / 1024).toFixed(1) }} MB ·
            {{ release.sha256.slice(0, 12) }}
            <span v-if="data?.current?.sha256 === release.sha256"
              >· 当前发布</span
            ></small
          >
        </div>
        <el-button
          v-if="data?.current?.sha256 !== release.sha256"
          :disabled="busy"
          @click="
            switchTo(
              release,
              !!data?.current && release.versionCode < data.current.versionCode,
            )
          "
          >{{
            data?.current && release.versionCode < data.current.versionCode
              ? "回退至此"
              : "发布"
          }}</el-button
        >
      </div>
    </div>
    <div v-if="data?.events.length" class="version-events">
      <h2>操作记录</h2>
      <p v-for="event in data.events" :key="`${event.at}-${event.sha256}`">
        {{ new Date(event.at * 1000).toLocaleString() }} · {{ event.actor }} ·
        {{
          {
            upload: "上传",
            publish: "发布",
            rollback: "回退",
            publish_attempt: "开始发布",
            rollback_attempt: "开始回退",
          }[
            event.action as
              | "upload"
              | "publish"
              | "rollback"
              | "publish_attempt"
              | "rollback_attempt"
          ] || event.action
        }}
        · {{ event.sha256.slice(0, 12) }}
      </p>
    </div>
  </section>
</template>
