<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { api } from "../services/api";
import { login } from "../composables/session";
import type { DemoConfig } from "../domain/types";
const props = defineProps<{ scope: "employee" | "admin" }>(),
  router = useRouter(),
  route = useRoute(),
  config = ref<DemoConfig>(),
  selected = ref(props.scope === "admin" ? "admin" : "lin"),
  error = ref(""),
  busy = ref(false);
const options = computed(
  () =>
    config.value?.people
      .filter((u) => (props.scope === "admin" ? u.admin : !u.admin))
      .map((u) => ({
        text: u.name + (u.registered ? "" : " · 首次登录"),
        value: u.id,
      })) ?? [],
);
const chosen = computed(
    () =>
      options.value.find((o) => o.value === selected.value)?.text ||
      "选择演示身份",
  ),
  picker = ref(false);
onMounted(async () => {
  try {
    config.value = await api.demo.config();
  } catch (e) {
    error.value = (e as Error).message;
  }
});
async function submit() {
  busy.value = true;
  error.value = "";
  try {
    await login(selected.value, props.scope);
    const prefix = props.scope === "admin" ? "/admin/" : "/employee";
    const target =
      typeof route.query.returnTo === "string" &&
      route.query.returnTo.startsWith(prefix) &&
      !route.query.returnTo.includes("//")
        ? route.query.returnTo
        : props.scope === "admin"
          ? "/admin/overview"
          : "/employee";
    await router.replace(target);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="login-layout">
    <div class="login-copy">
      <p class="eyebrow">
        {{ scope === "admin" ? "管理与运维" : "自己的记录，随时查阅" }}
      </p>
      <h1>
        {{
          scope === "admin"
            ? "维护自动运行，\n不增加日常步骤。"
            : "会议结束以后，\n资料自动到位。"
        }}
      </h1>
      <p class="muted lead">
        {{
          scope === "admin"
            ? "管理账号、设备、接收群和无法自动恢复的异常。"
            : "通过企业微信身份，查看本人或明确授权的原录音、逐字稿、纪要和行动事项。"
        }}
      </p>
    </div>
    <div class="login-card">
      <template v-if="scope === 'employee'"
        ><div class="login-card-title">
          <h2>员工手机登录</h2>
          <van-tag plain type="primary">Vant</van-tag>
        </div>
        <van-notice-bar
          v-if="route.query.expired"
          text="登录已过期或账号不可用，请重新登录。" /><van-form
          @submit="submit"
          ><van-field
            :model-value="chosen"
            name="identity"
            label="演示员工"
            readonly
            is-link
            @click="picker = true"
          />
          <div class="mobile-form-actions">
            <van-button
              block
              type="primary"
              native-type="submit"
              :loading="busy"
              >模拟企业微信登录</van-button
            >
          </div></van-form
        ><van-popup v-model:show="picker" position="bottom" round
          ><van-picker
            title="选择演示员工"
            :columns="options"
            @confirm="
              ({ selectedValues }: any) => {
                selected = String(selectedValues[0]);
                picker = false;
              }
            "
            @cancel="picker = false" /></van-popup
        ><van-notice-bar
          v-if="error"
          :text="error"
          wrapable
          color="#a33f37"
          background="#fff0ee"
      /></template>
      <template v-else
        ><div class="login-card-title">
          <h2>管理工作台</h2>
          <el-tag>Element Plus</el-tag>
        </div>
        <el-form label-position="top" @submit.prevent="submit"
          ><el-form-item label="演示管理身份"
            ><el-select v-model="selected" aria-label="演示管理身份"
              ><el-option
                v-for="o in options"
                :key="o.value"
                :value="o.value"
                :label="o.text" /></el-select></el-form-item
          ><el-button
            type="primary"
            :loading="busy"
            native-type="submit"
            class="full-width"
            >进入演示管理员</el-button
          ></el-form
        ><el-alert
          v-if="error"
          :title="error"
          type="error"
          :closable="false"
          class="block-gap"
      /></template>
      <p class="small muted block-gap">
        身份由模拟接口提供，不连接企业微信或收集真实密码。新员工自动取得基础权限；管理员不自动获得会议正文。
      </p>
    </div>
  </section>
</template>
