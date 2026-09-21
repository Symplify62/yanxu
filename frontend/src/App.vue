<script setup lang="ts">
import { ref } from "vue";
import { useRoute } from "vue-router";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import DemoControls from "./components/DemoControls.vue";
const route = useRoute(),
  controls = ref(false);
</script>
<template>
  <el-config-provider :locale="zhCn"
    ><van-config-provider
      :theme-vars="{
        primaryColor: '#18745a',
        buttonPrimaryBackground: '#18745a',
        buttonPrimaryBorderColor: '#18745a',
      }"
    >
      <div class="prototype-shell">
        <header class="review-header">
          <router-link class="brand" to="/tablet"
            ><span class="brand-glyph">言</span
            ><span
              ><strong>言序</strong><small>正式组件原型 · v0.4</small></span
            ></router-link
          >
          <nav class="surface-nav" aria-label="原型评审端切换">
            <router-link
              to="/tablet"
              :class="{ active: route.path.startsWith('/tablet') }"
              >平板录音端</router-link
            ><router-link
              to="/employee"
              :class="{ active: route.path.startsWith('/employee') }"
              >员工手机端</router-link
            ><router-link
              to="/admin"
              :class="{ active: route.path.startsWith('/admin') }"
              >管理后台</router-link
            ><router-link
              to="/components"
              :class="{ active: route.path === '/components' }"
              >组件与状态</router-link
            >
          </nav>
          <el-button class="demo-trigger" size="small" @click="controls = true"
            >演示控制</el-button
          >
        </header>
        <div class="review-caption">
          <span>评审导航 · 不属于正式平板 App</span
          ><span>模拟接口 · 不采音、不连接企业微信、不发真实消息</span>
        </div>
        <main><router-view :key="route.path" /></main>
        <footer class="review-footer">
          业务基线 U-11 ·
          界面使用正式组件，数据与外部能力均为模拟。正式服务端权限和真机可靠性尚未验证。
        </footer>
        <DemoControls v-model="controls" />
      </div> </van-config-provider
  ></el-config-provider>
</template>
