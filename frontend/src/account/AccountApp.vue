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
  Settings,
  LayoutDashboard,
  Smartphone,
  Menu,
} from "@lucide/vue";
import {
  account,
  errorMessage,
  hasPermission,
  restoreSession,
  onSessionClear,
  sessionNotice,
  sessionNoticeType,
  signIn,
  signOut,
  request,
} from "./api";
import UsersPage from "./UsersPage.vue";
import RolesPage from "./RolesPage.vue";
import DepartmentsPage from "./DepartmentsPage.vue";
import VoicesPage from "./VoicesPage.vue";
import RecordsPage from "./RecordsPage.vue";
import PersonalSettingsPage from "./PersonalSettingsPage.vue";
import OverviewPage from "./OverviewPage.vue";
import AppVersionsPage from "./AppVersionsPage.vue";
import AdminRecordingsPage from "./AdminRecordingsPage.vue";
const clearDialogs = onSessionClear(() => ElMessageBox.close());
const booting = ref(true),
  busy = ref(false),
  error = ref("");
const username = ref(""),
  password = ref("");
const environment = ref("");
const mobileMenu = ref(false);
const route = ref(location.hash.slice(2) || "records");
const menus = computed(() =>
  [
    {
      id: "overview",
      label: "管理概览",
      icon: LayoutDashboard,
      visible: account.value?.systemAdmin || false,
    },
    {
      id: "all-recordings",
      label: "所有录音",
      icon: Files,
      visible: account.value?.systemAdmin || false,
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
    {
      id: "app-versions",
      label: "App 版本",
      icon: Smartphone,
      visible: account.value?.systemAdmin || false,
    },
    {
      id: "records",
      label: "我的录音",
      icon: Files,
      visible: !account.value?.systemAdmin,
    },
    {
      id: "settings",
      label: "个人设置",
      icon: Settings,
      visible: !account.value?.systemAdmin,
    },
  ].filter((m) => m.visible),
);
const adminMenus = computed(() =>
  menus.value.filter(
    (m) =>
      !["records", "settings"].includes(m.id) &&
      (m.id !== "voices" || hasPermission("voices")),
  ),
);
const personalMenus = computed(() =>
  menus.value.filter(
    (m) =>
      ["records", "settings"].includes(m.id) ||
      (m.id === "voices" && !hasPermission("voices")),
  ),
);
const active = computed(
  () =>
    menus.value.find((m) => m.id === route.value) ||
    menus.value.find(
      (m) => m.id === (account.value?.systemAdmin ? "overview" : "records"),
    )!,
);
function ensureAllowedRoute() {
  if (!account.value) return;
  if (!menus.value.some((m) => m.id === route.value))
    location.hash = account.value.systemAdmin ? "#/overview" : "#/records";
}
function changed() {
  route.value = location.hash.slice(2) || "records";
  mobileMenu.value = false;
  ensureAllowedRoute();
}
async function login() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await signIn(username.value.trim(), password.value);
    ensureAllowedRoute();
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
  ensureAllowedRoute();
  try {
    environment.value = (
      await request<{ environment: string }>("/api/environment")
    ).environment;
  } catch {
    environment.value = "";
  }
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
        <span v-if="environment" class="environment-badge">{{
          environment === "production"
            ? "生产环境"
            : environment === "testing"
              ? "测试环境"
              : "本地环境"
        }}</span>
        <h1>登录工作台</h1>
        <el-alert
          v-if="sessionNotice || error"
          :title="error || sessionNotice"
          :type="error ? 'error' : sessionNoticeType"
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
        <div class="nav-top">
          <a class="account-brand" href="/"
            >言序<span>{{
              account.systemAdmin ? "管理后台" : "个人中心"
            }}</span></a
          ><button
            class="mobile-nav-toggle"
            type="button"
            :aria-expanded="mobileMenu"
            aria-label="打开导航"
            @click="mobileMenu = !mobileMenu"
          >
            <Menu :size="22" />
          </button>
        </div>
        <span
          v-if="environment"
          class="environment-badge"
          :class="environment"
          >{{
            environment === "production"
              ? "生产环境"
              : environment === "testing"
                ? "测试环境"
                : "本地环境"
          }}</span
        >
        <nav aria-label="工作台导航" :class="{ 'mobile-open': mobileMenu }">
          <span v-if="adminMenus.length" class="nav-section-title">管理</span>
          <a
            v-for="menu in adminMenus"
            :key="menu.id"
            :href="`#/${menu.id}`"
            :class="{ selected: active.id === menu.id }"
            :aria-current="active.id === menu.id ? 'page' : undefined"
            ><component :is="menu.icon" :size="18" />{{ menu.label }}</a
          >
          <span v-if="personalMenus.length" class="nav-section-title"
            >个人</span
          >
          <a
            v-for="menu in personalMenus"
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
        :key="`${account.id}:${account.systemAdmin}:${account.permissions.join(',')}`"
      >
        <header class="workspace-heading">
          <div>
            <small>{{ account.systemAdmin ? "管理后台" : "个人中心" }}</small>
            <h1>{{ active.label }}</h1>
          </div>
          <a href="/" class="muted-link">公共记录 ↗</a>
        </header>
        <UsersPage v-if="active.id === 'users'" />
        <OverviewPage v-else-if="active.id === 'overview'" />
        <AdminRecordingsPage v-else-if="active.id === 'all-recordings'" />
        <AppVersionsPage v-else-if="active.id === 'app-versions'" />
        <RolesPage v-else-if="active.id === 'roles'" />
        <DepartmentsPage v-else-if="active.id === 'departments'" />
        <VoicesPage v-else-if="active.id === 'voices'" />
        <PersonalSettingsPage v-else-if="active.id === 'settings'" />
        <RecordsPage v-else-if="active.id === 'records'" />
        <OverviewPage v-else />
      </main>
    </div>
  </div>
</template>
