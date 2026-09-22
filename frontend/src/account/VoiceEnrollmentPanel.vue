<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { errorMessage, request } from "./api";
import type { Person } from "./types";
const props = defineProps<{ person: Person }>();
const emit = defineEmits<{ saved: []; busy: [value: boolean] }>();
const file = ref<File | null>(null),
  preview = ref(""),
  nameConfirmed = ref(false),
  voiceConfirmed = ref(false),
  cloudConsent = ref(false),
  saving = ref(false),
  error = ref("");
let clientId = crypto.randomUUID();
let alive = true;
const allowed = computed(
  () =>
    file.value &&
    nameConfirmed.value &&
    voiceConfirmed.value &&
    cloudConsent.value &&
    !saving.value,
);
function release() {
  if (preview.value) URL.revokeObjectURL(preview.value);
  preview.value = "";
}
function selectFile(event: Event) {
  const selected = (event.target as HTMLInputElement).files?.[0];
  release();
  file.value = null;
  voiceConfirmed.value = false;
  nameConfirmed.value = false;
  cloudConsent.value = false;
  error.value = "";
  clientId = crypto.randomUUID();
  if (!selected) return;
  if (!selected.name.toLowerCase().endsWith(".wav")) {
    error.value = "请选择 WAV 声音文件";
    return;
  }
  if (selected.size > 10 * 1024 * 1024) {
    error.value = "声音样本请控制在10 MB以内";
    return;
  }
  file.value = selected;
  preview.value = URL.createObjectURL(selected);
}
async function save() {
  if (!allowed.value || !file.value) return;
  saving.value = true;
  emit("busy", true);
  error.value = "";
  try {
    const raw = await file.value.arrayBuffer();
    if (!alive) return;
    const hash = [...new Uint8Array(await crypto.subtle.digest("SHA-256", raw))]
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    if (!alive) return;
    const enrollment = await request<{ id: string; status: string }>(
      `/api/people/${props.person.id}/voice-enrollments`,
      {
        method: "POST",
        body: JSON.stringify({
          clientId,
          sha256: hash,
          totalBytes: raw.byteLength,
          nameConfirmed: true,
          voiceConfirmed: true,
          cloudConsent: true,
          confirmedName: props.person.name,
        }),
      },
    );
    if (enrollment.status === "uploading")
      await request(`/api/voice-enrollments/${enrollment.id}/audio`, {
        method: "PUT",
        body: raw,
        headers: { "Content-Type": "audio/wav" },
      });
    await request(`/api/voice-enrollments/${enrollment.id}/complete`, {
      method: "POST",
    });
    emit("saved");
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    saving.value = false;
    emit("busy", false);
  }
}
watch(
  () => props.person.id,
  () => {
    release();
    file.value = null;
    nameConfirmed.value = false;
    voiceConfirmed.value = false;
    cloudConsent.value = false;
  },
);
onUnmounted(() => {
  alive = false;
  release();
});
</script>
<template>
  <div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <p>
      <strong>{{ person.name }}</strong
      ><span class="status-text">
        · {{ person.departmentName || person.detail || "未分配部门" }}</span
      >
    </p>
    <label for="voice-file">选择本人声音（WAV）</label
    ><input
      id="voice-file"
      type="file"
      accept=".wav,audio/wav"
      :disabled="saving"
      @change="selectFile"
      style="display: block; margin-top: 12px; max-width: 100%"
    />
    <audio
      v-if="preview"
      :src="preview"
      controls
      class="voice-audio"
      preload="metadata"
    />
    <div class="voice-checks">
      <el-checkbox v-model="nameConfirmed" :disabled="saving"
        >本人确认姓名为“{{ person.name }}”</el-checkbox
      ><el-checkbox v-model="voiceConfirmed" :disabled="!file || saving"
        >已试听，确认是本人声音</el-checkbox
      ><el-checkbox v-model="cloudConsent" :disabled="saving"
        >本人同意将此声音保存为云端档案，用于会议发言识别</el-checkbox
      >
    </div>
    <p class="panel-note">登记样本私有保存，可在声音档案中撤回。</p>
    <el-button
      type="primary"
      :disabled="!allowed"
      :loading="saving"
      @click="save"
      style="margin-top: 16px"
      >保存声音档案</el-button
    >
  </div>
</template>
