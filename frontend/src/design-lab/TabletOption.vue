<script setup lang="ts">
import type { Component } from "vue";
import {
  Mic,
  ArrowUpRight,
  AudioLines,
  FileText,
  Sparkles,
  Send,
  Check,
  Wifi,
  RefreshCw,
  Pause,
  Play,
  Square,
  ShieldCheck,
} from "@lucide/vue";
import { useTabletDemo } from "./useTabletDemo";
import { api } from "../services/api";
import { duration, statusLabels } from "../domain/presentation";
const props = defineProps<{
  variant: string;
  kit: { Button: Component; Select: Component; Dialog: Component };
}>();
const UiButton = props.kit.Button,
  UiSelect = props.kit.Select,
  UiDialog = props.kit.Dialog;
const {
  device,
  error,
  loading,
  refresh,
  department,
  scanUser,
  dialog,
  busy,
  actionError,
  qr,
  expired,
  people,
  departments,
  run,
  scan,
} = useTabletDemo();
const steps = [
  { icon: AudioLines, name: "录音上传" },
  { icon: FileText, name: "文字转写" },
  { icon: Sparkles, name: "AI 整理" },
  { icon: Send, name: "自动发群" },
];
</script>
<template>
  <div class="tablet-app" :class="variant" :data-phase="device?.phase">
    <header class="device-header">
      <div class="wordmark">
        <span class="logo-mark"
          ><AudioLines :size="21" :stroke-width="1.8" /></span
        ><strong>言序</strong><span class="wordmark-divider"></span
        ><span class="room-name">会议室 A</span>
      </div>
      <div class="online">
        <Wifi :size="15" /><span>{{
          device?.online === false ? "设备离线" : "设备在线"
        }}</span>
      </div>
    </header>
    <main class="device-main">
      <div v-if="loading || error" class="state-center">
        <p>{{ error || "正在连接会议室设备…" }}</p>
        <UiButton v-if="error" secondary @click="refresh">重新加载</UiButton>
      </div>
      <template v-else-if="device">
        <p v-if="actionError && !dialog" role="alert" class="error-banner">
          {{ actionError }}
        </p>
        <section v-if="device.phase === 'scan'" class="scan-layout">
          <div class="intro">
            <p class="eyebrow">让每一次讨论，都有所留存</p>
            <h1>专心开会，<br class="title-break" />记录交给言序。</h1>
            <p class="intro-description">
              从一句话，到一份清晰的会议纪要。<br />录音结束，其余自动完成。
            </p>
            <div class="intro-footnote">
              <ShieldCheck :size="16" /><span
                >每场独立登录 · 保存后自动退出</span
              >
            </div>
          </div>
          <div class="scan-card">
            <div class="scan-heading">
              <div class="scan-icon">
                <Mic :size="22" :stroke-width="1.7" />
              </div>
              <h2>扫码开始这场会议</h2>
              <p>打开企业微信，扫描下方二维码</p>
            </div>
            <div class="qr-wrap">
              <img
                v-if="qr"
                :src="qr"
                alt="演示二维码，不能用于真实登录"
                width="220"
                height="220"
              />
              <div v-if="expired" class="qr-expired">
                <RefreshCw :size="24" /><strong>二维码已过期</strong>
              </div>
            </div>
            <p class="demo-qr-label">演示二维码 · 不能真实登录</p>
            <UiButton secondary :busy="busy" @click="run(api.device.refresh)"
              ><RefreshCw :size="15" />刷新二维码</UiButton
            >
          </div>
        </section>
        <section
          v-else-if="device.phase === 'ready'"
          class="state-center ready-state"
        >
          <div class="state-icon"><Check /></div>
          <p class="eyebrow">已登录本场会议</p>
          <h1>{{ device.employeeName }}，准备好了吗？</h1>
          <p class="state-description">点击开始录音，专注接下来的讨论。</p>
          <div class="department-field">
            <label>会议归属</label
            ><UiSelect
              v-model="department"
              label="会议归属"
              :options="departments"
              :disabled="busy"
            />
          </div>
          <p class="field-note">仅可选择已授权的部门</p>
          <div class="state-actions">
            <UiButton
              :busy="busy"
              @click="run(() => api.device.start(department))"
              ><Mic :size="18" />开始录音</UiButton
            ><UiButton
              secondary
              :disabled="busy"
              @click="run(() => api.device.action('next'))"
              >退出本场</UiButton
            >
          </div>
        </section>
        <section
          v-else-if="device.phase === 'recording' || device.phase === 'paused'"
          class="state-center recording-state"
        >
          <span
            class="record-indicator"
            :class="{ paused: device.phase === 'paused' }"
            ><i></i
            >{{
              device.phase === "paused" ? "录音已暂停" : "正在录音（模拟）"
            }}</span
          >
          <div class="record-time">{{ duration(device.elapsed) }}</div>
          <p class="state-description">
            {{ device.employeeName }} ·
            {{ departments.find((d) => d.value === device?.department)?.label }}
          </p>
          <AudioLines class="record-symbol" :size="60" :stroke-width="1" />
          <div class="state-actions">
            <UiButton
              secondary
              :busy="busy"
              @click="
                run(() =>
                  api.device.action(
                    device!.phase === 'paused' ? 'resume' : 'pause',
                  ),
                )
              "
              ><Play v-if="device.phase === 'paused'" :size="17" /><Pause
                v-else
                :size="17"
              />{{
                device.phase === "paused" ? "继续录音" : "暂停录音"
              }}</UiButton
            ><UiButton
              :disabled="busy"
              @click="run(() => api.device.action('end'))"
              ><Square :size="14" />结束并保存</UiButton
            >
          </div>
          <p class="field-note">
            {{
              device.online
                ? "保存成功后自动退出，后续处理由设备继续完成。"
                : "网络暂时断开，录音保留在本地，联网后自动补传。"
            }}
          </p>
        </section>
        <section
          v-else-if="device.phase === 'saving'"
          class="state-center"
          aria-live="polite"
        >
          <div class="state-icon"><RefreshCw class="spin" /></div>
          <h1>正在保存录音</h1>
          <p class="state-description">请稍候，保存成功后即可离开。</p>
        </section>
        <section v-else-if="device.phase === 'save-error'" class="state-center">
          <div class="state-icon error-icon">!</div>
          <h1>录音尚未保存成功</h1>
          <p class="state-description">
            请留在此页。已录片段正在保护，本场身份仍保留。
          </p>
          <UiButton
            :busy="busy"
            @click="run(() => api.device.action('retry-save'))"
            >模拟修复并重试保存</UiButton
          >
        </section>
        <section
          v-else
          class="state-center saved-state"
          data-testid="tablet-saved"
        >
          <div class="state-icon"><Check :size="30" /></div>
          <h1>已保存，你可以离开了。</h1>
          <p class="state-description">
            员工身份已自动退出。<br />我们会继续上传、整理，并将摘要发到指定群。
          </p>
          <div class="saved-jobs" aria-live="polite">
            <div v-for="job in device.queue" :key="job.id">
              <span>录音 {{ duration(job.duration) }}</span
              ><span>{{ statusLabels[job.state] }}</span>
            </div>
          </div>
          <UiButton :busy="busy" @click="run(() => api.device.action('next'))"
            >下一场扫码<ArrowUpRight :size="17"
          /></UiButton>
        </section>
      </template>
    </main>
    <footer class="device-footer">
      <div class="automation-flow">
        <span class="flow-label">会后自动完成</span
        ><template v-for="(step, index) in steps" :key="step.name"
          ><span class="flow-step"
            ><component :is="step.icon" :size="16" /><span>{{
              step.name
            }}</span></span
          ><span v-if="index < steps.length - 1" class="flow-connector"
            >→</span
          ></template
        >
      </div>
      <p
        v-if="device?.phase === 'scan' && device.queue.length"
        class="queue-note"
      >
        设备后台有 {{ device.queue.length }} 场任务 ·
        {{ statusLabels[device.queue[0]!.state] }}
      </p>
      <p v-else class="footer-note">会议资料可在员工手机端查阅</p>
    </footer>
    <UiDialog v-model="dialog"
      ><div class="scan-dialog-body">
        <p class="dialog-note">选择演示员工，体验扫码后的本场登录。</p>
        <label>扫码员工</label
        ><UiSelect
          v-model="scanUser"
          label="扫码员工"
          :options="people"
          :disabled="busy"
        />
        <p v-if="actionError" role="alert" class="error-banner">
          {{ actionError }}
        </p>
      </div>
      <template #footer
        ><div class="dialog-actions">
          <UiButton secondary :disabled="busy" @click="dialog = false"
            >取消</UiButton
          ><UiButton :busy="busy" @click="scan">确认模拟扫码</UiButton>
        </div></template
      ></UiDialog
    >
  </div>
</template>
