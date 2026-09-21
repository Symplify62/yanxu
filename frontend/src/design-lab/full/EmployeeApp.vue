<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  AudioLines,
  Search,
  ArrowLeft,
  ArrowUpRight,
  Clock,
  FileText,
  Share2,
  Pencil,
  ChevronRight,
  CheckCircle2,
} from "@lucide/vue";
import { useKit } from "./context";
import { accounts, signOut } from "./account";
import AccountLogin from "./AccountLogin.vue";
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import { duration, statusLabels } from "../../domain/presentation";
import type {
  Meeting,
  RevisionInput,
  Employee,
  Group,
} from "../../domain/types";
const { Button, Input, Select, Dialog } = useKit();
const query = ref(""),
  filter = ref("all"),
  selected = ref(""),
  tab = ref("summary"),
  modal = ref(""),
  busy = ref(false),
  actionError = ref("");
const { data, error, loading, refresh } = usePolling(async () => {
  if (!accounts.employee)
    return { list: [] as Meeting[], meeting: null as Meeting | null };
  if (selected.value)
    return {
      list: [] as Meeting[],
      meeting: await api.meetings.get(selected.value),
    };
  return {
    list: await api.meetings.list(query.value),
    meeting: null as Meeting | null,
  };
}, 1100);
const meeting = computed(() => data.value?.meeting),
  own = computed(() => meeting.value?.owner === accounts.employee?.id);
const meetings = computed(
  () =>
    data.value?.list.filter(
      (m) =>
        filter.value === "all" ||
        (filter.value === "own"
          ? m.owner === accounts.employee?.id
          : m.owner !== accounts.employee?.id),
    ) || [],
);
watch([() => accounts.employee?.id, query, selected], () => {
  void refresh();
});
watch(
  () => accounts.employee?.id,
  () => {
    selected.value = "";
    modal.value = "";
  },
);
watch(error, (v) => {
  if (v) {
    modal.value = "";
    segments.value = [];
  }
});
function open(id: string) {
  selected.value = id;
  tab.value = "summary";
}
const segments = ref<
    { id: string; time: string; speaker: string; text: string }[]
  >([]),
  transcriptError = ref("");
watch(
  [tab, () => meeting.value?.id, () => meeting.value?.progress],
  async () => {
    if (
      tab.value === "transcript" &&
      meeting.value &&
      meeting.value.progress >= 2
    ) {
      const id = meeting.value.id;
      try {
        const values = await api.meetings.transcript(id);
        if (selected.value === id) {
          segments.value = values;
          transcriptError.value = "";
        }
      } catch (e) {
        transcriptError.value = (e as Error).message;
      }
    }
  },
);
const draft = ref<RevisionInput>({
  expectedVersion: 1,
  summary: "",
  tasks: [],
  reason: "",
});
function edit() {
  if (!meeting.value || !own.value) return;
  draft.value = {
    expectedVersion: meeting.value.version,
    summary: meeting.value.summary,
    tasks: meeting.value.tasks.map((t) => ({ ...t })),
    reason: "",
  };
  actionError.value = "";
  modal.value = "edit";
}
async function mutate(fn: () => Promise<unknown>, close = false) {
  if (busy.value) return;
  busy.value = true;
  actionError.value = "";
  try {
    await fn();
    await refresh();
    if (close) modal.value = "";
  } catch (e) {
    actionError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function save() {
  if (
    !draft.value.summary.trim() ||
    !draft.value.reason.trim() ||
    draft.value.tasks.some((t) => !t.text.trim())
  ) {
    actionError.value = "请填写纪要、事项说明和更正原因";
    return;
  }
  await mutate(() => api.meetings.revise(selected.value, draft.value), true);
}
const people = ref<Employee[]>([]),
  groups = ref<Group[]>([]),
  subject = ref("");
const shareOptions = computed(() => [
  ...people.value
    .filter((p) => p.id !== meeting.value?.owner)
    .map((p) => ({ value: p.id, label: p.name })),
  ...groups.value.map((g) => ({
    value: "group:" + g.id,
    label: g.name + "（组）",
  })),
]);
async function share() {
  actionError.value = "";
  modal.value = "share";
  try {
    const values = await api.meetings.people();
    people.value = values.people;
    groups.value = values.groups;
    subject.value = shareOptions.value[0]?.value || "";
  } catch (e) {
    actionError.value = (e as Error).message;
  }
}
const modalTitle = computed(
  () =>
    ({
      edit: "主动更正纪要与事项",
      share: "共享会议查看权",
      snapshot: "自动发送快照",
    })[modal.value] || "",
);
const tabs = [
  ["summary", "纪要"],
  ["transcript", "逐字稿"],
  ["tasks", "事项"],
  ["audio", "录音"],
  ["versions", "版本"],
];
</script>
<template>
  <div class="employee-app">
    <AccountLogin v-if="!accounts.employee" scope="employee" />
    <template v-else>
      <header class="mobile-header">
        <button
          v-if="selected"
          class="icon-link"
          aria-label="返回我的会议"
          @click="selected = ''"
        >
          <ArrowLeft :size="19" />
        </button>
        <div v-else class="mobile-brand">
          <AudioLines :size="22" /><strong>言序</strong>
        </div>
        <span>{{ selected ? "会议资料" : "我的会议" }}</span
        ><button class="text-link" @click="signOut('employee')">退出</button>
      </header>
      <div v-if="!selected" class="mobile-home">
        <div class="welcome-row">
          <div>
            <p class="overline">
              {{ accounts.employee.name }} ·
              {{
                accounts.employee.department === "sales" ? "销售部" : "财务部"
              }}
            </p>
            <h1>会议结束，<br />重点留下。</h1>
          </div>
          <div class="personal-avatar">
            {{ accounts.employee.name.slice(0, 1) }}
          </div>
        </div>
        <div class="search-field">
          <Search :size="17" /><Input
            v-model="query"
            label="搜索会议"
            placeholder="搜索会议标题或纪要"
          />
        </div>
        <nav class="content-tabs" aria-label="会议范围">
          <button
            v-for="f in [
              ['all', '全部'],
              ['own', '我发起的'],
              ['shared', '共享给我'],
            ]"
            :key="f[0]"
            :class="{ active: filter === f[0] }"
            @click="filter = f[0]!"
          >
            {{ f[1] }}
          </button>
        </nav>
        <div class="list-caption">
          <span>会议资料</span><span>{{ meetings.length }} 场</span>
        </div>
        <p v-if="loading" class="empty-content">正在加载会议…</p>
        <p v-else-if="error" role="alert" class="error-banner">
          {{ error }}<Button secondary @click="refresh">重试</Button>
        </p>
        <div v-else-if="!meetings.length" class="empty-content">
          <FileText :size="32" />
          <h3>{{ query ? "没有找到相关会议" : "这里还没有会议" }}</h3>
          <p>录音结束后，资料会自动出现在这里。</p>
        </div>
        <button
          v-for="m in meetings"
          :key="m.id"
          class="meeting-item"
          @click="open(m.id)"
        >
          <div class="meeting-item-top">
            <span class="item-date"
              >{{ m.createdAt.slice(0, 10) }} · {{ duration(m.duration) }}</span
            ><span
              class="status-pill"
              :class="{ pending: m.state !== 'ACCEPTED' }"
              >{{ statusLabels[m.state] }}</span
            >
          </div>
          <h2>{{ m.title }}</h2>
          <p>
            {{
              m.progress >= 3
                ? m.summary
                : "会议资料正在自动整理中，可先查看已完成的部分。"
            }}
          </p>
          <div class="meeting-item-bottom">
            <span><FileText :size="13" />{{ m.tasks.length }} 项行动事项</span
            ><span
              >{{ m.owner === accounts.employee.id ? "我发起的" : "只读共享"
              }}<ChevronRight :size="15"
            /></span>
          </div>
        </button>
        <p class="mobile-footnote">只展示本人发起或明确授权的会议</p>
      </div>
      <div v-else-if="error" class="empty-content">
        <FileText :size="32" />
        <h2>记录不可用或你没有查看权限</h2>
        <Button secondary @click="selected = ''">返回我的会议</Button>
      </div>
      <template v-else-if="meeting"
        ><div class="detail-heading">
          <p class="overline">{{ own ? "我发起的会议" : "只读共享" }}</p>
          <h1>{{ meeting.title }}</h1>
          <p class="meta-line">
            <Clock :size="14" />{{ duration(meeting.duration) }}<span>·</span
            >{{ meeting.createdAt.slice(0, 10) }}
          </p>
          <div class="detail-status">
            <span
              class="status-pill"
              :class="{ pending: meeting.state !== 'ACCEPTED' }"
              >{{ statusLabels[meeting.state] }}</span
            ><span class="small-muted">{{
              meeting.department === "sales" ? "销售部" : "财务部"
            }}</span>
          </div>
        </div>
        <nav class="content-tabs detail-tabs" aria-label="会议资料类型">
          <button
            v-for="t in tabs"
            :key="t[0]"
            :class="{ active: tab === t[0] }"
            @click="tab = t[0]!"
          >
            {{ t[1] }}
          </button>
        </nav>
        <div class="detail-body">
          <template v-if="tab === 'summary'"
            ><div class="section-title">
              <h2>会议纪要</h2>
              <span>v{{ meeting.version }}</span>
            </div>
            <template v-if="meeting.progress >= 3"
              ><p class="summary-content">{{ meeting.summary }}</p>
              <div class="ai-note">
                <CheckCircle2 :size="16" />
                <p>AI 自动整理，内容可能存在误差。可对照逐字稿和录音查阅。</p>
              </div>
              <div class="version-line">
                当前 v{{ meeting.version
                }}<span v-if="meeting.publication"
                  >群快照 v{{ meeting.publication.version }}</span
                >
              </div>
              <div v-if="own" class="detail-actions">
                <Button secondary @click="edit"
                  ><Pencil :size="15" />主动更正</Button
                ><Button secondary @click="share"
                  ><Share2 :size="15" />共享查看权</Button
                >
              </div></template
            >
            <p v-else class="empty-content">
              纪要正在自动整理，可先查看已完成的资料。
            </p></template
          >
          <template v-else-if="tab === 'transcript'"
            ><h2>逐字稿</h2>
            <p class="small-muted">AI 转写合成样例 · 保留发言依据</p>
            <p v-if="transcriptError" role="alert" class="error-banner">
              {{ transcriptError }}
            </p>
            <p v-if="meeting.progress < 2" class="empty-content">
              逐字稿尚未生成
            </p>
            <article
              v-for="s in segments"
              v-else
              :key="s.id"
              class="transcript-item"
            >
              <span>{{ s.time }} · {{ s.speaker }}</span>
              <p>{{ s.text }}</p>
            </article></template
          >
          <template v-else-if="tab === 'tasks'"
            ><h2>行动事项</h2>
            <p v-if="meeting.progress < 3" class="empty-content">
              事项正在自动整理
            </p>
            <template v-else
              ><article
                v-for="(t, index) in meeting.tasks"
                :key="t.id"
                class="action-item"
              >
                <span class="item-index">{{
                  String(index + 1).padStart(2, "0")
                }}</span>
                <div>
                  <h3>{{ t.text }}</h3>
                  <p>
                    {{ t.owner || "负责人未明确" }} ·
                    {{ t.due || "期限未明确" }}
                  </p>
                  <small>依据 {{ t.evidence }} · 仅内容整理，不自动派单</small>
                </div>
              </article>
              <Button v-if="own" secondary class="full-button" @click="edit"
                >主动更正事项</Button
              ></template
            ></template
          >
          <template v-else-if="tab === 'audio'"
            ><h2>原始录音</h2>
            <div class="audio-panel">
              <AudioLines :size="44" /><strong>{{
                duration(meeting.duration)
              }}</strong>
              <p>
                {{
                  meeting.progress < 1
                    ? "等待设备上传，尚未归档"
                    : "原件已归档（模拟）"
                }}
              </p>
            </div>
            <p class="small-muted">合成样例未附真实音频，不能播放。</p>
            <Button disabled class="full-button">播放 · 无音频样本</Button
            ><Button secondary disabled class="full-button"
              >下载 · 需独立授权</Button
            ></template
          >
          <template v-else
            ><h2>内容与发送版本</h2>
            <article
              v-for="v in [...meeting.versions].reverse()"
              :key="v.version"
              class="version-entry"
            >
              <div class="section-title">
                <h3>
                  v{{ v.version }} ·
                  {{ v.version === 1 ? "AI 原稿" : "主动更正版" }}
                </h3>
                <span v-if="v.version === meeting.version">当前</span>
              </div>
              <p>{{ v.summary }}</p>
              <small>{{ v.reason }}</small>
            </article>
            <Button
              v-if="meeting.publication"
              secondary
              class="full-button"
              @click="modal = 'snapshot'"
              >查看自动发送快照<ArrowUpRight :size="15" /></Button
          ></template></div
      ></template>
      <p v-else class="empty-content">正在加载会议资料…</p>
    </template>
    <Dialog
      :model-value="!!modal"
      :title="modalTitle"
      @update:model-value="!$event && (modal = '')"
      ><div v-if="modal === 'edit'" class="dialog-form">
        <p class="notice">保存新版本，不重复发群。AI 原稿与已发送快照保留。</p>
        <label class="field-label">会议纪要</label
        ><Input v-model="draft.summary" label="纪要" multiline />
        <div v-for="(t, i) in draft.tasks" :key="t.id" class="task-edit">
          <h3>事项 {{ i + 1 }}</h3>
          <label class="field-label">事项说明</label
          ><Input v-model="t.text" :label="'事项说明' + i" />
          <div class="form-two">
            <div>
              <label class="field-label">负责人</label
              ><Input
                v-model="t.owner"
                :label="'负责人' + i"
                placeholder="未明确可留空"
              />
            </div>
            <div>
              <label class="field-label">期限原文</label
              ><Input
                v-model="t.due"
                :label="'期限' + i"
                placeholder="未明确可留空"
              />
            </div>
          </div>
        </div>
        <label class="field-label">更正原因（必填）</label
        ><Input
          v-model="draft.reason"
          label="更正原因"
          placeholder="说明核对依据"
        />
      </div>
      <div v-else-if="modal === 'share'" class="dialog-form">
        <p class="notice">
          仅授予只读查看权，不授编辑、下载或管理权，也不发送群消息。
        </p>
        <label class="field-label">授权对象</label
        ><Select
          v-model="subject"
          label="授权对象"
          :options="shareOptions"
        /><Button
          class="full-button"
          :busy="busy"
          :disabled="!subject"
          @click="mutate(() => api.meetings.share(selected, subject))"
          >添加只读授权</Button
        >
        <h3>当前授权</h3>
        <div
          v-for="g in meeting?.grants.filter((g) => g.active)"
          :key="g.id"
          class="grant-row"
        >
          <span>{{
            shareOptions.find((o) => o.value === g.subject)?.label || g.subject
          }}</span
          ><Button
            v-if="g.grantedBy === accounts.employee?.id"
            secondary
            :disabled="busy"
            @click="mutate(() => api.meetings.revoke(selected, g.id))"
            >撤销</Button
          ><span v-else class="small-muted">其他授权来源</span>
        </div>
        <p v-if="!meeting?.grants.some((g) => g.active)" class="small-muted">
          尚未共享
        </p>
      </div>
      <div v-else-if="modal === 'snapshot'">
        <p class="small-muted">
          {{ meeting?.publication?.target }} · v{{
            meeting?.publication?.version
          }}
        </p>
        <p class="summary-content">{{ meeting?.publication?.summary }}</p>
        <p class="notice">保存更正不改写此快照，也不会重复发群。</p>
      </div>
      <p v-if="actionError" role="alert" class="error-banner">
        {{ actionError }}
      </p>
      <template #footer
        ><div class="dialog-actions">
          <Button secondary :disabled="busy" @click="modal = ''">{{
            modal === "edit" ? "取消修改" : "关闭"
          }}</Button
          ><Button v-if="modal === 'edit'" :busy="busy" @click="save"
            >保存更正，不重发</Button
          >
        </div></template
      ></Dialog
    >
  </div>
</template>
