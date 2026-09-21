<script setup lang="ts">
import { ref } from "vue";
import { useKit } from "./context";
import { statusLabels } from "../../domain/presentation";
const { Button, Input, Select, Checkbox, Dialog } = useKit();
const name = ref(""),
  department = ref("sales"),
  checked = ref(true),
  dialog = ref(false),
  showError = ref(false);
</script>
<template>
  <section class="component-gallery">
    <p class="overline">设计基础 · 真实组件</p>
    <h1>组件与交互状态</h1>
    <p class="support-copy">当前方案的常用控件、反馈和弹窗，可直接操作。</p>
    <div class="gallery-grid">
      <article>
        <h2>按钮</h2>
        <div class="component-line">
          <Button>主要操作</Button><Button secondary>次要操作</Button
          ><Button disabled>不可操作</Button><Button busy>处理中</Button>
        </div>
      </article>
      <article>
        <h2>表单与校验</h2>
        <label class="field-label">姓名</label
        ><Input v-model="name" label="姓名" placeholder="输入姓名" />
        <p v-if="showError && !name.trim()" class="error-banner" role="alert">
          请填写姓名
        </p>
        <label class="field-label">部门</label
        ><Select
          v-model="department"
          label="部门"
          :options="[
            { value: 'sales', label: '销售部' },
            { value: 'finance', label: '财务部' },
          ]"
        />
        <div class="component-line">
          <Checkbox v-model="checked" label="接收状态提醒（样例）" /><Button
            secondary
            @click="showError = true"
            >验证表单</Button
          >
        </div>
      </article>
      <article>
        <h2>任务状态</h2>
        <div class="component-line">
          <span
            v-for="(label, key) in statusLabels"
            :key="key"
            class="status-pill"
            :class="{ pending: key !== 'ACCEPTED' }"
            >{{ label }}</span
          >
        </div>
      </article>
      <article>
        <h2>弹窗与结果</h2>
        <p class="notice">取消关闭窗口，确认后显示本地结果；不写入业务数据。</p>
        <Button @click="dialog = true">打开确认弹窗</Button>
        <p v-if="showError && name.trim()" class="success-banner">
          表单校验通过
        </p>
      </article>
    </div>
    <Dialog v-model="dialog" title="组件确认样例"
      ><p class="support-copy">检查当前方案的弹窗间距、按钮和键盘操作。</p>
      <template #footer
        ><div class="dialog-actions">
          <Button secondary @click="dialog = false">取消</Button
          ><Button @click="dialog = false">确认</Button>
        </div></template
      ></Dialog
    >
  </section>
</template>
