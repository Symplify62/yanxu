<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import {
  AudioLines,
  Mic,
  FileText,
  Settings,
  ShieldCheck,
  ArrowLeft,
  Plus,
  Fingerprint,
  Check,
  X,
  RotateCcw,
  Info,
  ChevronRight,
} from "@lucide/vue";
import { ElInput } from "element-plus";
import Button from "../design-lab/kits/ElementButton.vue";
import Dialog from "../design-lab/kits/ElementDialog.vue";
import RecorderSurface from "./RecorderSurface.vue";
import PeoplePicker from "./PeoplePicker.vue";
import UserEditor from "./UserEditor.vue";
import AdminWorkspace from "./AdminWorkspace.vue";
import SettingsPage from "./SettingsPage.vue";
import VoiceEnrollment from "./VoiceEnrollment.vue";
import SamplePlayer from "./SamplePlayer.vue";
import MeetingSession from "./MeetingSession.vue";
import {
  useSpeakerPrototype,
  voiceLabels,
  voiceState,
  voiceReady,
  type Permission,
  type Person,
  type Meeting,
} from "./model";
const m = useSpeakerPrototype();
const {
  phase,
  pending,
  selected,
  activeMeeting,
  result,
  seconds,
  actor,
  actorId,
  storageError,
} = m;
const readPage = () => location.hash.replace("#/", "") || "record";
const page = ref(readPage()),
  picker = ref(false),
  addingGuest = ref(false),
  help = ref(false),
  resetting = ref(false),
  warning = ref(false);
const toast = ref(""),
  error = ref(""),
  voiceError = ref(""),
  enrollId = ref<string | null>(null),
  profileId = ref<string | null>(null),
  revoke = ref(false);
const historyQuery = ref(""),
  historyDetail = ref<Meeting | null>(null);
const enrolling = computed(
  () => m.people.value.find((p) => p.id === enrollId.value) || null,
);
const profile = computed(() =>
  m.people.value.find((p) => p.id === profileId.value),
);
const admin = computed(() => page.value.startsWith("admin/"));
const adminSection = computed(() => page.value.split("/")[1] as Permission);
const adminSections: Permission[] = ["users", "roles", "departments", "voices"];
const hasAdmin = computed(() => adminSections.some((x) => m.can(x)));
const busy = computed(() =>
  ["recording", "paused", "processing"].includes(phase.value),
);
const history = computed(() =>
  m.state.value.history.filter((r) => r.title.includes(historyQuery.value)),
);
function navigate(to: string) {
  if (busy.value && to !== "record") {
    error.value = "请先结束本场录音。";
    return;
  }
  page.value = to;
  location.hash = "/" + to;
  error.value = "";
  toast.value = "";
  historyDetail.value = null;
}
function onHash() {
  const target = readPage();
  if (busy.value && target !== "record") {
    location.hash = "/record";
    return;
  }
  page.value = target;
}
window.addEventListener("hashchange", onHash);
onUnmounted(() => window.removeEventListener("hashchange", onHash));
watch(actorId, () => {
  picker.value = false;
  profileId.value = null;
  enrollId.value = null;
  page.value = "record";
  location.hash = "/record";
});
function enroll(id: string, keepPicker = false) {
  const person = m.people.value.find((p) => p.id === id);
  if (!person) return;
  const blocked = m.voiceEnrollmentBlock(person);
  if (blocked) {
    error.value = blocked;
    return;
  }
  enrollId.value = id;
  voiceError.value = "";
  profileId.value = null;
  if (!keepPicker) picker.value = false;
}
function saveVoice(
  name: string,
  length: number,
  consent: boolean,
  next: boolean,
) {
  try {
    if (!enrollId.value) return;
    m.saveVoice(enrollId.value, name, length, consent);
    toast.value = `${name}的声音已保存，正在生成声纹`;
    enrollId.value = next
      ? pending.value.find(
          (p) => p.id !== enrollId.value && voiceState(p) !== "generating",
        )?.id || null
      : null;
    voiceError.value = "";
  } catch (e) {
    voiceError.value = (e as Error).message;
  }
}
function start() {
  if (pending.value.length) warning.value = true;
  else m.start();
}
function revokeVoice() {
  try {
    if (profileId.value) m.changeVoice(profileId.value, "revoked");
    revoke.value = false;
    toast.value = "声纹已撤回，历史会议保留";
  } catch (e) {
    error.value = (e as Error).message;
  }
}
function flagVoice() {
  try {
    if (profileId.value) m.changeVoice(profileId.value, "review");
    toast.value = "已标记需重新录入";
  } catch (e) {
    error.value = (e as Error).message;
  }
}
function newMeeting() {
  m.nextMeeting();
  navigate("record");
}
</script>
<template>
  <div class="speaker-prototype redesign" :class="{ 'is-admin': admin }">
    <div class="review-strip">
      <span><span class="review-dot"></span>交互原型</span
      ><span class="demo-boundary">录音与声纹识别均为演示</span>
      <div class="review-actions">
        <label
          >演示身份<select
            v-model="actorId"
            aria-label="演示身份"
            :disabled="busy"
          >
            <option
              v-for="p in m.members.value.filter((p) => p.active)"
              :key="p.id"
              :value="p.id"
            >
              {{ p.name }} · {{ m.roleName(p.roleId) }}
            </option>
          </select></label
        ><button aria-label="原型说明" @click="help = true">
          <Info :size="14" /></button
        ><button
          aria-label="重置演示"
          :disabled="busy"
          @click="resetting = true"
        >
          <RotateCcw :size="14" />
        </button>
      </div>
    </div>
    <header class="product-header">
      <button class="product-brand" @click="navigate('record')">
        <span><AudioLines :size="23" /></span><strong>言序</strong>
      </button>
      <nav v-if="!admin" aria-label="主导航">
        <button
          :class="{ active: page === 'record' }"
          @click="navigate('record')"
        >
          <Mic :size="17" />录音</button
        ><button
          :class="{ active: page === 'records' }"
          :disabled="busy"
          @click="navigate('records')"
        >
          <FileText :size="17" />会议记录
        </button>
      </nav>
      <span v-else class="admin-brand-label">管理控制台</span>
      <div class="header-tools">
        <button
          v-if="!admin"
          :class="{ active: page === 'settings' }"
          aria-label="打开设置"
          :disabled="busy"
          @click="navigate('settings')"
        >
          <Settings :size="18" /></button
        ><button
          v-if="hasAdmin && !admin"
          aria-label="管理后台"
          :disabled="busy"
          @click="navigate('admin/' + adminSections.find((x) => m.can(x)))"
        >
          <ShieldCheck :size="18" /><span>管理后台</span></button
        ><button v-if="admin" @click="navigate('record')">
          <ArrowLeft :size="16" /><span>返回录音</span></button
        ><span class="current-user" :title="actor?.name">{{
          actor?.name.slice(-2)
        }}</span>
      </div>
    </header>
    <p v-if="storageError || error" class="global-alert" role="alert">
      {{ storageError || error
      }}<button
        aria-label="关闭错误"
        @click="
          error = '';
          storageError = '';
        "
      >
        ×
      </button>
    </p>
    <p v-if="toast" class="global-toast" role="status">
      <Check :size="15" />{{ toast
      }}<button aria-label="关闭提示" @click="toast = ''">
        <X :size="14" />
      </button>
    </p>

    <template v-if="page === 'record'">
      <RecorderSurface
        v-if="['setup', 'recording', 'paused'].includes(phase)"
        :model="m"
        @picker="picker = true"
        @enroll="enroll"
        @start="start"
        @finish="m.finish"
        @settings="navigate('settings')"
      />
      <MeetingSession
        v-else-if="activeMeeting"
        :phase="phase"
        :meeting="result || activeMeeting"
        :seconds="seconds"
        @next="newMeeting"
      />
    </template>
    <SettingsPage
      v-else-if="page === 'settings'"
      :model="m"
      @enroll="enroll"
      @voice="profileId = $event.id"
    />
    <AdminWorkspace
      v-else-if="admin && adminSections.includes(adminSection)"
      :model="m"
      :section="adminSection"
      @navigate="navigate('admin/' + $event)"
      @back="navigate('record')"
      @voice="profileId = $event.id"
      @enroll="enroll"
    />
    <main v-else-if="page === 'records'" class="history-page">
      <template v-if="!historyDetail"
        ><div class="record-heading">
          <div>
            <span class="section-eyebrow">言序 / 记录</span>
            <h1>会议记录</h1>
          </div>
          <Button secondary @click="newMeeting"
            ><Plus :size="16" />新录音</Button
          >
        </div>
        <ElInput
          v-model="historyQuery"
          class="history-search"
          aria-label="搜索会议记录"
          placeholder="搜索会议"
          clearable />
        <div v-if="!history.length" class="history-empty">
          <FileText :size="38" />
          <h2>
            {{
              m.state.value.history.length ? "没有匹配的会议" : "还没有会议记录"
            }}
          </h2>
          <p>结束一场录音后，结果会出现在这里。</p>
          <Button secondary @click="navigate('record')">去录音</Button>
        </div>
        <button
          v-for="r in history"
          :key="r.id"
          class="history-item"
          @click="historyDetail = r"
        >
          <span class="history-icon"><FileText :size="22" /></span>
          <div>
            <strong>{{ r.title }}</strong>
            <p>{{ r.date }} · {{ r.people.length }} 人</p>
          </div>
          <span class="status-tag ready">已完成</span
          ><ChevronRight :size="18" /></button></template
      ><template v-else
        ><button class="text-action history-back" @click="historyDetail = null">
          <ArrowLeft :size="16" />全部会议</button
        ><MeetingSession
          phase="result"
          :meeting="historyDetail"
          :seconds="historyDetail.seconds"
          @next="newMeeting"
      /></template>
    </main>
    <div v-else class="empty-state">
      <h1>页面不存在</h1>
      <Button @click="navigate('record')">返回录音</Button>
    </div>

    <PeoplePicker
      :model="m"
      :open="picker"
      @close="picker = false"
      @add="addingGuest = true"
      @enroll="enroll($event, true)"
    />
    <UserEditor
      :model="m"
      :open="addingGuest"
      guest
      @close="addingGuest = false"
      @saved="toast = '来宾已加入本场，可点待录入状态补充声音'"
    />
    <VoiceEnrollment
      :person="enrolling"
      :error="voiceError"
      :next-name="
        page === 'record' && !picker
          ? pending.find(
              (p) => p.id !== enrollId && voiceState(p) !== 'generating',
            )?.name
          : undefined
      "
      @close="
        enrollId = null;
        voiceError = '';
      "
      @save="saveVoice"
    />
    <Dialog
      :model-value="!!profile"
      title="声音档案"
      @update:model-value="profileId = null"
      ><div v-if="profile" class="profile-body">
        <div class="voice-person">
          <span class="person-avatar large">{{ profile.name.slice(-2) }}</span>
          <div>
            <strong>{{ profile.name }}</strong>
            <p>
              {{ m.departmentName(profile.departmentId) }} ·
              {{ profile.detail }}
            </p>
          </div>
          <span class="status-tag" :class="voiceState(profile)">{{
            voiceLabels[voiceState(profile)]
          }}</span>
        </div>
        <div class="voice-facts">
          <div>
            <span>保存范围</span
            ><strong>{{
              profile.scope === "guest" ? "仅本场" : "长期档案"
            }}</strong>
          </div>
          <div>
            <span>最近登记</span
            ><strong>{{ profile.voice?.recordedAt || "尚未登记" }}</strong>
          </div>
          <div>
            <span>本人授权</span
            ><strong>{{
              profile.voice?.consent
                ? "已同意"
                : profile.scope === "guest"
                  ? "本场使用"
                  : "未授权 / 已撤回"
            }}</strong>
          </div>
        </div>
        <template v-if="profile.voice && voiceState(profile) !== 'revoked'"
          ><SamplePlayer />
          <p class="simulation-note">合成示例，不是该用户的真实声音。</p>
          <div class="profile-operations">
            <button
              v-if="m.can('voices') && voiceState(profile) === 'ready'"
              class="text-action"
              @click="flagVoice"
            >
              标记需重录</button
            ><button
              v-if="m.can('voices') || actorId === profile.id"
              class="danger-text"
              @click="revoke = true"
            >
              撤回声纹
            </button>
          </div></template
        >
      </div>
      <template #footer
        ><Button secondary @click="profileId = null">关闭</Button
        ><Button
          v-if="profile && (m.can('voices') || actorId === profile.id)"
          :disabled="voiceState(profile) === 'generating'"
          @click="enroll(profile.id)"
          >重新录入</Button
        ></template
      ></Dialog
    >
    <Dialog
      :model-value="revoke"
      title="撤回该声纹？"
      @update:model-value="revoke = false"
      ><p>撤回后不再用于新会议识别；已有会议记录保留。</p>
      <template #footer
        ><Button secondary @click="revoke = false">取消</Button
        ><Button @click="revokeVoice">确认撤回</Button></template
      ></Dialog
    >
    <Dialog
      :model-value="warning"
      title="部分参会者声纹尚未就绪"
      @update:model-value="warning = false"
      ><p>{{ pending.map((p) => p.name).join("、") }}暂不能按姓名匹配。</p>
      <p class="quiet-note">可先录入，或继续并以说话人编号展示。</p>
      <template #footer
        ><Button
          secondary
          @click="
            warning = false;
            enroll(pending[0]!.id);
          "
          >先录入声音</Button
        ><Button
          @click="
            warning = false;
            m.start();
          "
          >仍然开始</Button
        ></template
      ></Dialog
    >
    <Dialog
      :model-value="help"
      title="原型体验说明"
      @update:model-value="help = false"
      ><div class="prototype-help">
        <p>
          录音页点头像选人；设置页维护本人声音与设备；管理后台维护用户、角色、部门和声纹。
        </p>
        <p>
          声音、计时和识别均为演示，试听是合成音频，不会开启麦克风或上传数据。
        </p>
        <p>
          顶部演示身份用于体验不同权限，不代表真实登录。成员、配置和示例结果只保存于本浏览器，正式权限和数据范围需由后端实现。
        </p>
      </div>
      <template #footer
        ><Button @click="help = false">知道了</Button></template
      ></Dialog
    >
    <Dialog
      :model-value="resetting"
      title="重置本地原型？"
      @update:model-value="resetting = false"
      ><p>恢复示例人员、角色、部门和声音状态，清除本原型的示例会议。</p>
      <template #footer
        ><Button secondary @click="resetting = false">取消</Button
        ><Button
          @click="
            m.reset();
            resetting = false;
            navigate('record');
          "
          >确认重置</Button
        ></template
      ></Dialog
    >
  </div>
</template>
