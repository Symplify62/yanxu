<script setup lang="ts">
import { ref } from "vue";
import MeetingStatus from "../components/MeetingStatus.vue";
import RequestState from "../components/RequestState.vue";
const dialog = ref(false),
  name = ref(""),
  form = ref(),
  notice = ref(false);
async function validate() {
  try {
    await form.value.validate();
    notice.value = true;
  } catch {
    notice.value = false;
  }
}
</script>
<template>
  <section class="component-workshop">
    <div class="page-heading">
      <div>
        <p class="eyebrow">组件与状态展示</p>
        <h1>同一套规范，真实组件呈现</h1>
        <p class="muted">
          这里直接复用页面使用的组件，用于评审常见状态。不是图片或静态控件仿制。
        </p>
      </div>
    </div>
    <div class="component-grid">
      <el-card shadow="never"
        ><template #header><strong>Element Plus · 按钮和表单</strong></template>
        <div class="actions">
          <el-button type="primary">主要操作</el-button
          ><el-button>次要操作</el-button
          ><el-button disabled>无操作资格</el-button
          ><el-button loading>处理中</el-button>
        </div>
        <el-form
          ref="form"
          :model="{ name }"
          label-position="top"
          class="block-gap"
          ><el-form-item
            label="必填字段"
            prop="name"
            :rules="[
              { required: true, message: '请填写名称', trigger: 'blur' },
            ]"
            ><el-input
              v-model="name"
              placeholder="验证错误提示与输入保留" /></el-form-item
          ><el-button @click="validate">验证表单</el-button></el-form
        ><el-alert
          v-if="notice"
          title="校验通过（仅展示，不保存业务数据）"
          type="success"
          class="block-gap"
          :closable="false"
      /></el-card>
      <el-card shadow="never"
        ><template #header><strong>共享业务组件 · 处理状态</strong></template>
        <div class="status-gallery">
          <MeetingStatus
            v-for="state in [
              'QUEUED',
              'ARCHIVED',
              'TRANSCRIBED',
              'ACCEPTED',
              'FAILED',
              'UNKNOWN',
            ] as const"
            :key="state"
            :state="state"
          />
        </div>
        <el-divider />
        <p class="small muted">
          生成哪项可看哪项，自动发送不是人工审核完成；渠道接收也不是已读。
        </p>
        <el-button @click="dialog = true">查看确认弹窗</el-button></el-card
      >
      <el-card shadow="never"
        ><template #header><strong>Vant · 手机组件</strong></template>
        <div class="mobile-component-demo">
          <van-cell-group inset
            ><van-field
              label="手机号展示"
              model-value="员工企业身份"
              readonly /><van-cell
              title="只读共享"
              label="不授下载或编辑资格"
              is-link /></van-cell-group
          ><van-button type="primary" block class="block-gap"
            >手机主要操作</van-button
          ><van-notice-bar
            text="数据处理中，已有资料可以先查看。"
            wrapable
            class="block-gap"
          />
          <div class="actions">
            <MeetingStatus state="ACCEPTED" mobile /><MeetingStatus
              state="UNKNOWN"
              mobile
            />
          </div></div
      ></el-card>
      <el-card shadow="never"
        ><template #header><strong>空、错误与加载</strong></template
        ><el-skeleton :rows="2" animated /><RequestState
          empty
          message="暂无有权查看的资料" /><el-alert
          title="请求失败时保留输入，不把错误伪装成空数据。"
          type="error"
          :closable="false"
      /></el-card>
    </div>
    <el-dialog v-model="dialog" title="操作范围确认" width="min(460px,94vw)"
      ><p>
        真实 ElDialog
        支持焦点管理和键盘关闭。业务动作仍由独立接口验证权限与版本。
      </p>
      <template #footer
        ><el-button @click="dialog = false">取消</el-button
        ><el-button type="primary" @click="dialog = false"
          >知道了</el-button
        ></template
      ></el-dialog
    >
  </section>
</template>
