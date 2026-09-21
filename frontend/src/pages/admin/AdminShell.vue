<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { logout, sessions } from "../../composables/session";
const route = useRoute(),
  router = useRouter();
const items = [
  ["overview", "自动处理概览"],
  ["people", "用户与身份"],
  ["organization", "组织部门"],
  ["roles", "角色权限"],
  ["groups", "业务访问组"],
  ["routes", "部门与接收群"],
  ["exceptions", "异常处理"],
  ["audit", "操作记录"],
  ["devices", "设备与存储"],
];
async function signOut() {
  await logout("admin");
  await router.replace("/admin/login");
}
</script>
<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="sidebar-title">
        言序工作台<small>单公司 · 内部试点</small>
      </div>
      <el-menu :default-active="route.path" router
        ><el-menu-item
          v-for="[path, label] in items"
          :key="path"
          :index="'/admin/' + path"
          >{{ label }}</el-menu-item
        ></el-menu
      >
      <div class="sidebar-footer">
        <el-tag size="small">{{ sessions.admin?.name }}</el-tag
        ><el-button size="small" text @click="signOut">退出</el-button>
        <p class="small muted">维护身份不自动获得正文查看权。</p>
      </div>
    </aside>
    <div class="admin-workspace"><router-view :key="route.path" /></div>
  </div>
</template>
