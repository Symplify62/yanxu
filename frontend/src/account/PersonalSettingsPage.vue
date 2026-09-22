<script setup lang="ts">
import { onUnmounted, reactive, ref } from "vue";
import {
  ApiError,
  account,
  clearSession,
  errorMessage,
  onSessionClear,
  request,
} from "./api";

const oldPassword = ref(""),
  newPassword = ref(""),
  confirmPassword = ref("");
const saving = ref(false),
  error = ref("");
const fields = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});
let alive = true;
function clearInputs() {
  oldPassword.value = "";
  newPassword.value = "";
  confirmPassword.value = "";
}
const removeCleanup = onSessionClear(clearInputs);
async function save() {
  if (saving.value) return;
  error.value = "";
  fields.oldPassword = oldPassword.value ? "" : "请输入旧密码";
  fields.newPassword =
    Array.from(newPassword.value).length >= 6 ? "" : "新密码至少6位";
  fields.confirmPassword =
    confirmPassword.value === newPassword.value && confirmPassword.value
      ? ""
      : "两次输入的新密码不一致";
  if (Object.values(fields).some(Boolean)) return;
  saving.value = true;
  try {
    await request<{ ok: boolean }>("/api/auth/password", {
      method: "POST",
      body: JSON.stringify({
        oldPassword: oldPassword.value,
        newPassword: newPassword.value,
        confirmPassword: confirmPassword.value,
      }),
    });
    clearInputs();
    clearSession("密码已修改，请重新登录", "success");
  } catch (e) {
    if (!alive) return;
    if (e instanceof ApiError && e.status === 400)
      fields.oldPassword = e.message;
    else error.value = errorMessage(e);
  } finally {
    saving.value = false;
  }
}
onUnmounted(() => {
  alive = false;
  clearInputs();
  removeCleanup();
});
</script>

<template>
  <section class="personal-settings workspace-surface" aria-label="修改密码">
    <header class="personal-settings-heading">
      <h2>修改密码</h2>
      <span class="status-text">{{ account?.username }}</span>
    </header>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <el-form label-position="top" @submit.prevent="save">
      <el-form-item
        label="旧密码"
        for="self-old-password"
        :error="fields.oldPassword"
        required
      >
        <el-input
          id="self-old-password"
          v-model="oldPassword"
          type="password"
          show-password
          autocomplete="current-password"
          :disabled="saving"
          @input="fields.oldPassword = ''"
        />
      </el-form-item>
      <el-form-item
        label="新密码"
        for="self-new-password"
        :error="fields.newPassword"
        required
      >
        <el-input
          id="self-new-password"
          v-model="newPassword"
          type="password"
          show-password
          autocomplete="new-password"
          placeholder="至少6位"
          :disabled="saving"
          @input="
            fields.newPassword = '';
            fields.confirmPassword = '';
          "
        />
      </el-form-item>
      <el-form-item
        label="确认新密码"
        for="self-confirm-password"
        :error="fields.confirmPassword"
        required
      >
        <el-input
          id="self-confirm-password"
          v-model="confirmPassword"
          type="password"
          show-password
          autocomplete="new-password"
          :disabled="saving"
          @input="fields.confirmPassword = ''"
        />
      </el-form-item>
      <p class="panel-note">修改后需重新登录。</p>
      <el-button type="primary" native-type="submit" :loading="saving"
        >修改密码</el-button
      >
    </el-form>
  </section>
</template>

<style scoped>
.personal-settings {
  max-width: 560px;
  padding: 28px;
}
.personal-settings-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}
.personal-settings-heading h2 {
  margin: 0;
  font-size: 18px;
}
.personal-settings-heading .status-text {
  overflow-wrap: anywhere;
  font-size: 13px;
}
.personal-settings :deep(.el-input__wrapper) {
  min-height: 42px;
}
.personal-settings .panel-note {
  margin: 0 0 20px;
}
.personal-settings .el-button {
  min-height: 44px;
  min-width: 120px;
}
@media (max-width: 650px) {
  .personal-settings {
    padding: 20px;
  }
  .personal-settings .el-button {
    width: 100%;
  }
}
</style>
