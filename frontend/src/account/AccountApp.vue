<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { ElMessageBox } from "element-plus";
import {
  Users,
  ShieldCheck,
  Network,
  AudioLines,
  Files,
  LogOut,
} from "@lucide/vue";
import {
  account,
  errorMessage,
  hasPermission,
  restoreSession,
  onSessionClear,
  sessionNotice,
  signIn,
  signOut,
} from "./api";
import UsersPage from "./UsersPage.vue";
import RolesPage from "./RolesPage.vue";
import DepartmentsPage from "./DepartmentsPage.vue";
import VoicesPage from "./VoicesPage.vue";
import RecordsPage from "./RecordsPage.vue";
const clearDialogs = onSessionClear(() => ElMessageBox.close());
const booting = ref(true),
  busy = ref(false),
  error = ref("");
const username = ref(""),
  password = ref("");
const route = ref(location.hash.slice(2) || "records");
const menus = computed(() =>
  [
    {
      id: "records",
      label: "我的录音",
      icon: Files,
      visible: true,
    },
    {
      id: "users",
      label: "用户管理",
      icon: Users,
      visible: hasPermission("users"),
    },
    {
      id: "roles",
      label: "角色管理",
      icon: ShieldCheck,
      visible: hasPermission("roles"),
    },
    {
      id: "departments",
      label: "部门管理",
      icon: Network,
      visible: hasPermission("departments"),
    },
    {
      id: "voices",
      label: hasPermission("voices") ? "声纹管理" : "声音档案",
      icon: AudioLines,
      visible: true,
    },
  ].filter((m) => m.visible),
);
const active = computed(
  () => menus.value.find((m) => m.id === route.value) || menus.value[0]!,
);
function changed() {
  route.value = location.hash.slice(2) || "records";
}
async function login() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await signIn(username.value.trim(), password.value);
    password.value = "";
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
onMounted(async () => {
  window.addEventListener("hashchange", changed);
  await restoreSession();
  booting.value = false;
});
onUnmounted(() => {
  window.removeEventListener("hashchange", changed);
  clearDialogs();
});
</script>
<template>
  <div class="account-app full-app">
    <div v-if="booting" class="login-wrap" role="status">正在连接…</div>
    <div v-else-if="!account" class="login-wrap">
      <form class="login-panel" @submit.prevent="login">
        <a class="account-brand" href="/">言序</a>
        <h1>登录工作台</h1>
        <el-alert
          v-if="sessionNotice || error"
          :title="error || sessionNotice"
          type="error"
          :closable="false"
          show-icon
        />
        <label for="account-username">账号</label
        ><el-input
          id="account-username"
          v-model="username"
          autocomplete="username"
          autofocus
          :disabled="busy"
        />
        <label for="account-password">密码</label
        ><el-input
          id="account-password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          show-password
          :disabled="busy"
        />
        <el-button
          type="primary"
          native-type="submit"
          :loading="busy"
          :disabled="!username.trim() || !password"
          >登录</el-button
        >
        <a class="muted-link" href="/">查看公共记录</a>
      </form>
    </div>
    <div v-else class="account-shell">
      <aside class="account-nav">
        <a class="account-brand" href="/">言序<span>工作台</span></a>
        <nav aria-label="工作台导航">
          <a
            v-for="menu in menus"
            :key="menu.id"
            :href="`#/${menu.id}`"
            :class="{ selected: active.id === menu.id }"
            :aria-current="active.id === menu.id ? 'page' : undefined"
            ><component :is="menu.icon" :size="18" />{{ menu.label }}</a
          >
        </nav>
        <div class="account-person">
          <span class="account-avatar">{{
            account.displayName.slice(0, 1)
          }}</span>
          <div>
            <strong>{{ account.displayName }}</strong
            ><small>{{ account.username }}</small>
          </div>
          <el-button text aria-label="退出登录" @click="signOut"
            ><LogOut :size="18"
          /></el-button>
        </div>
      </aside>
      <main
        class="account-workspace"
        :key="`${account.id}:${account.permissions.join(',')}`"
      >
        <header class="workspace-heading">
          <div>
            <small>言序工作台</small>
            <h1>{{ active.label }}</h1>
          </div>
          <a href="/" class="muted-link">公共记录 ↗</a>
        </header>
        <UsersPage v-if="active.id === 'users'" />
        <RolesPage v-else-if="active.id === 'roles'" />
        <DepartmentsPage v-else-if="active.id === 'departments'" />
        <VoicesPage v-else-if="active.id === 'voices'" />
        <RecordsPage v-else />
      </main>
    </div>
  </div>
</template>
