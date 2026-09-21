<script setup lang="ts">
import { ref, watch } from "vue";
import { api } from "../services/api";
import { usePolling } from "../composables/usePolling";
import { duration } from "../domain/presentation";
import type { DemoConfig, DeviceView } from "../domain/types";
import TabletQueue from "../components/TabletQueue.vue";
import RequestState from "../components/RequestState.vue";
const {
  data: device,
  error,
  loading,
  refresh,
} = usePolling(api.device.get, 900);
const config = ref<DemoConfig>(),
  department = ref(""),
  dialog = ref(false),
  scanUser = ref("lin"),
  scanError = ref(""),
  actionError = ref(""),
  busy = ref(false);
void api.demo
  .config()
  .then((v) => (config.value = v))
  .catch((e) => (actionError.value = e.message));
watch(
  () => device.value?.employee,
  (id) => {
    if (id) department.value = device.value!.department;
  },
);
const departmentName = (id: string) =>
  config.value?.departments.find((d) => d.id === id)?.name || id;
async function run(fn: () => Promise<DeviceView>) {
  busy.value = true;
  actionError.value = "";
  try {
    device.value = await fn();
  } catch (e) {
    actionError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function scan() {
  if (!device.value) return;
  busy.value = true;
  scanError.value = "";
  try {
    device.value = await api.device.scan(
      device.value.challenge,
      scanUser.value,
    );
    department.value = device.value.department;
    dialog.value = false;
  } catch (e) {
    scanError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
function openScan() {
  scanError.value = "";
  dialog.value = true;
}
</script>
<template>
  <section class="tablet-stage">
    <div class="surface-label">
      <span>会议室 A · 共享设备</span
      ><el-tag :type="device?.online ? 'success' : 'warning'">{{
        device?.online ? "设备在线" : "设备离线"
      }}</el-tag>
    </div>
    <div class="tablet-device">
      <div class="tablet-top">
        <strong>会议室 A</strong
        ><span class="muted small">设备已配对 · 不设业务录音时长上限</span>
      </div>
      <RequestState
        v-if="loading || error"
        :loading="loading"
        :error="error"
        @retry="refresh"
      />
      <template v-else-if="device">
        <el-alert
          v-if="actionError"
          :title="actionError"
          type="error"
          :closable="false"
          class="action-error"
        />
        <div v-if="device.phase === 'scan'" class="tablet-columns">
          <div>
            <p class="eyebrow">每场扫码，记录属于发起人</p>
            <h1>扫码开始这场会议</h1>
            <p class="muted lead">
              使用企业微信员工身份。<br />保存成功后自动退出，后续处理交给系统。
            </p>
            <div
              class="scan-tile"
              :class="{ expired: device.expiresAt < Date.now() }"
              aria-label="模拟二维码，不可实际扫描"
            >
              <span>{{
                device.expiresAt < Date.now() ? "二维码已过期" : "扫码示意"
              }}</span>
            </div>
            <p class="small muted">不可实际扫码 · 真实认证尚未接入</p>
            <div class="actions">
              <el-button
                type="primary"
                size="large"
                :disabled="!device.online || device.expiresAt < Date.now()"
                @click="openScan"
                >模拟手机扫码</el-button
              ><el-button :loading="busy" @click="run(api.device.refresh)"
                >刷新二维码</el-button
              ><el-button text @click="run(() => api.device.action('expire'))"
                >模拟过期</el-button
              >
            </div>
            <el-alert
              v-if="!device.online"
              title="新场扫码需要联网；已保存任务仍会保留。"
              type="warning"
              :closable="false"
              class="block-gap"
            />
          </div>
          <aside class="tablet-guide">
            <h3>员工只需三步</h3>
            <ol>
              <li>手机扫码登录本场</li>
              <li>开始录音</li>
              <li>结束后离开</li>
            </ol>
            <p class="small muted">
              系统自动上传、转写、总结和发群。手机查阅本人及授权资料。
            </p>
            <TabletQueue :queue="device.queue" />
          </aside>
        </div>
        <div v-else-if="device.phase === 'ready'" class="tablet-columns">
          <div>
            <p class="eyebrow">本场发起人</p>
            <h1>{{ device.employeeName }}</h1>
            <el-form label-position="top" class="ready-form"
              ><el-form-item label="会议归属"
                ><el-select v-model="department" aria-label="会议归属"
                  ><el-option
                    v-for="id in device.allowedDepartments"
                    :key="id"
                    :value="id"
                    :label="departmentName(id)" /></el-select></el-form-item
            ></el-form>
            <p class="small muted">
              默认本人部门，只能改到获授权范围；归属不自动开放部门资料。
            </p>
            <div class="actions">
              <el-button
                class="record-button"
                size="large"
                type="primary"
                :loading="busy"
                @click="run(() => api.device.start(department))"
                >开始录音</el-button
              ><el-button
                text
                :disabled="busy"
                @click="run(() => api.device.action('next'))"
                >退出本场</el-button
              >
            </div>
          </div>
          <aside class="tablet-guide">
            <h3>结束以后自动完成</h3>
            <p class="lead">录音归档 → 文字转写<br />AI 纪要与事项 → 群摘要</p>
            <p class="small muted">
              接收群由管理员按会议归属配置；员工不任意选择目标。
            </p>
            <TabletQueue :queue="device.queue" />
          </aside>
        </div>
        <div
          v-else-if="['recording', 'paused'].includes(device.phase)"
          class="recording-surface"
        >
          <el-tag :type="device.phase === 'recording' ? 'danger' : 'warning'">{{
            device.phase === "recording" ? "● 正在录音（模拟）" : "录音已暂停"
          }}</el-tag>
          <div class="record-clock mono">{{ duration(device.elapsed) }}</div>
          <p class="muted">
            {{ device.employeeName }} · {{ departmentName(device.department) }}
          </p>
          <div
            class="sound-wave"
            :class="{ paused: device.phase === 'paused' }"
          />
          <p class="small muted">示意输入活动，不采集麦克风</p>
          <div class="actions">
            <el-button
              size="large"
              :loading="busy"
              @click="
                run(() =>
                  api.device.action(
                    device!.phase === 'paused' ? 'resume' : 'pause',
                  ),
                )
              "
              >{{
                device.phase === "paused" ? "继续录音" : "暂停录音"
              }}</el-button
            ><el-button
              size="large"
              type="primary"
              :disabled="busy"
              @click="run(() => api.device.action('end'))"
              >结束并保存</el-button
            >
          </div>
          <el-alert
            :title="
              device.online
                ? '保存后自动退出员工身份，设备继续上传和处理。'
                : '本场已断网，录音仍在本地保存；结束后等待补传。'
            "
            :type="device.online ? 'info' : 'warning'"
            :closable="false"
          />
        </div>
        <div v-else-if="device.phase === 'saving'" class="saved-surface">
          <el-skeleton :rows="2" animated />
          <h1>正在保护本地录音</h1>
          <p class="muted">尚未确认保存成功，请稍候。</p>
        </div>
        <div v-else-if="device.phase === 'save-error'" class="saved-surface">
          <el-result
            icon="error"
            title="本地保存失败"
            sub-title="已录片段正在保护，本场身份仍绑定，不会归给下一位员工。"
            ><template #extra
              ><el-button
                type="primary"
                :loading="busy"
                @click="run(() => api.device.action('retry-save'))"
                >模拟修复并重试保存</el-button
              ></template
            ></el-result
          >
        </div>
        <div v-else class="saved-surface" data-testid="tablet-saved">
          <div class="success-seal">✓</div>
          <h1>已保存，你可以离开了</h1>
          <p class="muted">员工身份已自动退出。设备继续上传、整理并发群。</p>
          <TabletQueue :queue="device.queue" /><el-button
            size="large"
            type="primary"
            :loading="busy"
            @click="run(() => api.device.action('next'))"
            >下一场扫码</el-button
          >
        </div>
      </template>
      <div class="tablet-bottom">
        <span>长期保留公司档案 · 平板不展示历史正文</span
        ><span>Element Plus 组件预览</span>
      </div>
    </div>
    <el-dialog
      v-model="dialog"
      title="模拟企业微信扫码"
      width="min(460px, 94vw)"
      :close-on-click-modal="false"
      ><el-alert
        title="这里只模拟本场身份绑定，不连接企业微信。"
        type="info"
        :closable="false"
      /><el-form label-position="top" class="block-gap"
        ><el-form-item label="扫码员工"
          ><el-select v-model="scanUser" aria-label="扫码员工"
            ><el-option
              v-for="person in config?.people.filter((p) => !p.admin)"
              :key="person.id"
              :value="person.id"
              :label="
                person.name + (person.registered ? '' : ' · 首次登录')
              " /></el-select></el-form-item></el-form
      ><el-alert
        v-if="scanError"
        :title="scanError"
        type="error"
        :closable="false"
      /><template #footer
        ><el-button @click="dialog = false">取消</el-button
        ><el-button type="primary" :loading="busy" @click="scan"
          >确认模拟扫码</el-button
        ></template
      ></el-dialog
    >
  </section>
</template>
