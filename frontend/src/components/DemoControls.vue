<script setup lang="ts">
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import { api } from "../services/api";
import type { DemoConfig, Scenario } from "../domain/types";
import { clearSession } from "../composables/session";
const visible = defineModel<boolean>({ default: false }),
  router = useRouter(),
  config = ref<DemoConfig>(),
  error = ref(""),
  busy = ref(false);
watch(visible, async (v) => {
  if (v) {
    error.value = "";
    try {
      config.value = await api.demo.config();
    } catch (e) {
      error.value = (e as Error).message;
    }
  }
});
async function scenario(value: Scenario) {
  busy.value = true;
  try {
    await api.demo.settings({ scenario: value });
    config.value = await api.demo.config();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function network(value: boolean) {
  try {
    await api.demo.settings({ online: value });
    config.value = await api.demo.config();
  } catch (e) {
    error.value = (e as Error).message;
  }
}
async function reset() {
  busy.value = true;
  try {
    await api.demo.reset();
    clearSession("employee");
    clearSession("admin");
    visible.value = false;
    await router.push("/tablet");
    window.location.reload();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <el-drawer v-model="visible" title="演示控制台" size="min(420px, 100vw)"
    ><p class="muted">
      这些控件仅供原型评审，通过独立模拟接口注入状态，不是员工业务操作。
    </p>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      class="block-gap"
    /><el-form v-if="config" label-position="top" class="block-gap"
      ><el-form-item label="故障场景"
        ><el-select
          aria-label="故障场景"
          :model-value="config.settings.scenario"
          :disabled="busy"
          @change="scenario"
          ><el-option
            v-for="[value, label] in [
              ['normal', '正常全自动'],
              ['offline', '网络离线'],
              ['save-failure', '本地保存失败'],
              ['ai-failure', 'AI 自动重试耗尽'],
              ['missing-route', '缺少接收群'],
              ['unknown', '发送结果不明'],
            ]"
            :key="value"
            :value="value"
            :label="label" /></el-select></el-form-item
      ><el-form-item label="设备网络"
        ><el-switch
          :model-value="config.settings.online"
          active-text="在线"
          inactive-text="离线"
          @change="
            (v: string | number | boolean) => network(Boolean(v))
          " /></el-form-item></el-form
    ><el-divider />
    <p class="small muted">
      “重置”会还原本浏览器中的合成资料、注销演示身份，不操作真实账号。
    </p>
    <el-button :loading="busy" type="danger" plain @click="reset"
      >重置全部演示数据</el-button
    ></el-drawer
  >
</template>
