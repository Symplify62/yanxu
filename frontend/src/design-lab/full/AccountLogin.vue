<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { AudioLines, ShieldCheck } from "@lucide/vue";
import { useKit } from "./context";
import { signIn } from "./account";
import { api } from "../../services/api";
import type { DemoConfig } from "../../domain/types";
const props = defineProps<{ scope: "employee" | "admin" }>();
const { Button, Select } = useKit();
const selected = ref(props.scope === "admin" ? "admin" : "lin"),
  config = ref<DemoConfig>(),
  error = ref(""),
  busy = ref(false);
const options = computed(
  () =>
    config.value?.people
      .filter((p) => (props.scope === "admin" ? p.admin : !p.admin))
      .map((p) => ({ value: p.id, label: p.name })) || [],
);
onMounted(() => {
  void api.demo
    .config()
    .then((c) => (config.value = c))
    .catch((e) => (error.value = e.message));
});
async function login() {
  busy.value = true;
  error.value = "";
  try {
    await signIn(selected.value, props.scope);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="account-login">
    <div class="login-emblem"><AudioLines :size="28" /></div>
    <p class="overline">
      {{ scope === "employee" ? "言序 · 随时查阅" : "言序 · 管理工作台" }}
    </p>
    <h1>
      {{ scope === "employee" ? "每场讨论，都在这里。" : "让记录，自动有序。" }}
    </h1>
    <p class="support-copy">
      {{
        scope === "employee"
          ? "纪要、逐字稿、录音和行动事项，一处查看。"
          : "管理成员、设备与分发规则，处理需要关注的异常。"
      }}
    </p>
    <div class="account-form">
      <h2>{{ scope === "employee" ? "员工登录" : "管理员登录" }}</h2>
      <label class="field-label">{{
        scope === "employee" ? "演示员工" : "演示管理身份"
      }}</label
      ><Select
        v-model="selected"
        :options="options"
        :label="scope === 'employee' ? '演示员工' : '演示管理身份'"
      />
      <p v-if="error" role="alert" class="error-banner">{{ error }}</p>
      <Button :busy="busy" class="full-button" @click="login">{{
        scope === "employee" ? "模拟企业微信登录" : "进入演示管理员"
      }}</Button>
      <p class="support-copy tiny">
        <ShieldCheck :size="13" />{{
          scope === "employee"
            ? "仅查看本人发起或明确授权的会议"
            : "管理员不自动获得会议正文访问权"
        }}
      </p>
    </div>
    <p class="login-demo-note">演示身份 · 未连接企业微信</p>
  </section>
</template>
