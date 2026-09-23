<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  ArrowLeft,
  Link,
  FileText,
  Sparkles,
  Check,
  ListChecks,
  LoaderCircle,
  AlertCircle,
  Headphones,
} from "@lucide/vue";
import { duration } from "../domain/presentation";
import { stageOf, stageLabels, type PublicRecord } from "./model";
const props = defineProps<{
  record: PublicRecord | null;
  now: number;
  live?: boolean;
  demoAnalysis?: {
    summary: string;
    points: string[];
    decisions: string[];
    tasks: Array<{
      text: string;
      owner: string | null;
      due: string | null;
      evidence: string | string[];
    }>;
  };
  demoTranscript?: Array<{ time: string; speaker: string; text: string }>;
}>();
defineEmits<{ back: [] }>();
const tab = ref("analysis"),
  linkDialog = ref(false),
  copyMessage = ref("");
watch(
  () => props.record?.id,
  () => {
    tab.value = "analysis";
    linkDialog.value = false;
    copyMessage.value = "";
  },
);
const stage = computed(() =>
    props.record ? stageOf(props.record, props.now) : "uploading",
  ),
  textReady = computed(() =>
    ["analyzing", "complete", "analysis-error"].includes(stage.value),
  ),
  analysisReady = computed(
    () =>
      stage.value === "complete" && (!props.live || !!props.record?.analysis),
  );
const noSpeech = computed(() => stage.value === "no-speech");
const analysisData = computed(() =>
  props.live ? props.record?.analysis : props.demoAnalysis,
);
const segments = computed(() =>
  props.live
    ? (props.record?.transcript?.segments || []).map((s) => ({
        ...s,
        time: duration(s.start),
        speaker: s.speaker || "未识别",
      }))
    : props.demoTranscript || [],
);
const detailTabs = computed(() =>
  noSpeech.value
    ? [["audio", "原始录音"]]
    : [
        ["analysis", "AI 分析"],
        ["transcript", "逐字稿"],
        ["tasks", "行动事项"],
        ...(props.live ? [["audio", "原始录音"]] : []),
      ],
);
const progress = computed(() =>
  stage.value === "complete"
    ? 4
    : ["analyzing", "analysis-error"].includes(stage.value)
      ? 4
      : ["queued", "transcribing", "transcript-error"].includes(stage.value)
        ? 3
        : 2,
);
const url = computed(() =>
  props.record
    ? location.origin +
      location.pathname +
      "#/records/" +
      encodeURIComponent(props.record.id)
    : "",
);
function evidenceLabel(value: string | string[]) {
  if (!Array.isArray(value)) return value;
  return value
    .map((id) => {
      const segment = props.record?.transcript?.segments.find(
        (s) => s.id === id,
      );
      return segment ? duration(segment.start) : "原文";
    })
    .join("、");
}
async function copy() {
  try {
    await navigator.clipboard.writeText(url.value);
    copyMessage.value = props.live ? "链接已复制" : "演示链接已复制";
  } catch {
    copyMessage.value = "复制未完成，请选择上面的链接手动复制。";
  }
}
</script>
<template>
  <section class="p1-detail">
    <button class="p1-back" @click="$emit('back')">
      <ArrowLeft :size="16" />返回公共记录
    </button>
    <div v-if="!record" class="p1-list-empty">
      <FileText :size="38" />
      <h1>这条记录暂时不可用</h1>
      <p class="p1-secondary">链接可能无效，或演示记录已被重置。</p>
      <el-button @click="$emit('back')">查看公共记录</el-button>
    </div>
    <template v-else
      ><header class="p1-detail-head">
        <div>
          <h1>{{ record.title }}</h1>
          <p class="p1-secondary">
            {{ new Date(record.createdAt).toLocaleString("zh-CN")
            }}<span> · </span>{{ duration(record.duration) }}
          </p>
        </div>
        <el-button
          @click="
            linkDialog = true;
            copyMessage = '';
          "
          aria-label="复制结果链接"
          ><Link :size="15" />结果链接</el-button
        >
      </header>
      <p v-if="live && record.interrupted" role="status" class="p1-notice">
        录音曾中断，以下为已保留内容。
      </p>
      <div v-if="noSpeech" class="p1-no-speech" role="status">
        <strong>未检测到语音</strong>
        <p>录音已保留，已跳过 AI 分析。</p>
      </div>
      <p v-else-if="analysisReady" class="p1-complete-status" role="status">
        <Check :size="15" />已完成
      </p>
      <div v-else class="p1-progress" aria-label="处理进度">
        <div
          v-for="(label, i) in [
            '录音已保存',
            '上传录音',
            '文字转写',
            'AI 分析',
          ]"
          :key="label"
          :class="{
            complete: i < progress - 1 || analysisReady,
            current: i === progress - 1 && !analysisReady,
          }"
        >
          <span
            ><Check
              v-if="i < progress - 1 || analysisReady"
              :size="13"
            /><template v-else>{{ i + 1 }}</template></span
          >{{ label }}
        </div>
      </div>
      <p v-if="stage === 'waiting'" role="status" class="p1-notice">
        录音已保存，联网后自动继续。
      </p>
      <p v-else-if="stage.includes('error')" role="alert" class="p1-error">
        <AlertCircle :size="18" /><template v-if="live">{{
          record.error || "处理暂未完成"
        }}</template
        ><template v-else
          >{{
            stage === "transcript-error" ? "转写暂未完成" : "AI 分析暂未完成"
          }}，录音已保留。{{
            textReady ? "你可以先查看逐字稿。" : "恢复后自动继续。"
          }}
        </template>
      </p>
      <div class="p1-detail-grid">
        <main class="p1-reading">
          <nav class="p1-detail-tabs" aria-label="结果内容">
            <button
              v-for="t in detailTabs"
              :key="t[0]"
              :class="{ active: tab === t[0] || noSpeech }"
              @click="tab = t[0]!"
            >
              <Sparkles v-if="t[0] === 'analysis'" :size="15" /><FileText
                v-else-if="t[0] === 'transcript'"
                :size="15"
              /><Headphones
                v-else-if="t[0] === 'audio'"
                :size="15"
              /><ListChecks v-else :size="15" />{{ t[1] }}
            </button>
          </nav>
          <div class="p1-reading-body">
            <template v-if="tab === 'analysis' && analysisReady"
              ><p class="p1-content-kicker">会议摘要</p>
              <p class="p1-summary">{{ analysisData?.summary }}</p>
              <h2>讨论重点</h2>
              <ul class="p1-points">
                <li v-for="p in analysisData?.points" :key="p">{{ p }}</li>
              </ul>
              <h2>主要决定</h2>
              <p v-if="!analysisData?.decisions.length" class="p1-secondary">
                未提取到明确决定
              </p>
              <ol class="p1-decisions">
                <li v-for="p in analysisData?.decisions" :key="p">{{ p }}</li>
              </ol></template
            ><template v-else-if="tab === 'transcript' && textReady"
              ><h2>逐字稿</h2>
              <p
                v-if="record?.speakerStatus === 'waiting'"
                class="p1-secondary"
              >
                正在识别发言人
              </p>
              <p
                v-else-if="record?.speakerStatus === 'failed'"
                class="p1-secondary"
              >
                发言人识别未完成，逐字稿已保留
              </p>
              <article
                v-for="t in segments"
                :key="t.time"
                class="p1-transcript"
              >
                <span>{{ t.time }}</span>
                <div>
                  <strong>{{ t.speaker }}</strong>
                  <p>{{ t.text }}</p>
                </div>
              </article></template
            ><template v-else-if="tab === 'tasks' && analysisReady"
              ><h2>行动事项</h2>
              <p v-if="!analysisData?.tasks.length" class="p1-secondary">
                未提取到行动事项
              </p>
              <article
                v-for="(t, i) in analysisData?.tasks"
                :key="t.text"
                class="p1-task"
              >
                <span>{{ String(i + 1).padStart(2, "0") }}</span>
                <div>
                  <h3>{{ t.text }}</h3>
                  <p>
                    {{ t.owner || "负责人未明确" }} ·
                    {{ t.due || "期限未明确" }}
                  </p>
                  <small>依据：{{ evidenceLabel(t.evidence) }}</small>
                </div>
              </article></template
            >
            <div v-else-if="tab === 'audio' || noSpeech" class="live-audio">
              <h2>原始录音</h2>
              <audio
                v-if="record.hasAudio"
                controls
                preload="metadata"
                :src="'/api/recordings/' + record.id + '/audio'"
                aria-label="原始录音播放器"
              ></audio>
              <a
                v-if="record.hasAudio"
                :href="'/api/recordings/' + record.id + '/audio?download=true'"
                class="live-download"
                >下载录音</a
              >
              <p v-else class="p1-secondary">录音尚未归档</p>
            </div>
            <div v-else class="p1-pending">
              <AlertCircle
                v-if="stage.includes('error')"
                :size="32"
              /><LoaderCircle v-else :size="32" class="p1-spin" />
              <h2>
                {{
                  stage.includes("error")
                    ? stageLabels[stage]
                    : tab === "transcript"
                      ? stage === "transcribing"
                        ? "文字还在转写中"
                        : "等待文字转写"
                      : stage === "analyzing"
                        ? "AI 正在整理内容"
                        : "等待 AI 分析"
                }}
              </h2>

              <el-button
                v-if="textReady && tab !== 'transcript'"
                @click="tab = 'transcript'"
                >先看逐字稿</el-button
              >
            </div>
          </div>
        </main>
        <aside class="p1-detail-aside">
          <h3>记录信息</h3>
          <dl>
            <div>
              <dt>处理状态</dt>
              <dd>{{ stageLabels[stage] }}</dd>
            </div>
            <div>
              <dt>查看范围</dt>
              <dd>公共可见</dd>
            </div>
          </dl>
        </aside>
      </div></template
    ><el-dialog
      v-model="linkDialog"
      title="结果链接"
      width="min(480px, calc(100vw - 32px))"
      align-center
      ><p class="p1-secondary">
        {{
          live
            ? "持有链接即可查看和下载。"
            : "演示链接仅限当前浏览器，暂不支持跨设备。"
        }}
      </p>
      <el-input :model-value="url" readonly aria-label="结果链接地址" />
      <p v-if="copyMessage" role="status" class="p1-secondary">
        {{ copyMessage }}
      </p>
      <template #footer
        ><el-button @click="linkDialog = false">关闭</el-button
        ><el-button type="primary" @click="copy">{{
          live ? "复制链接" : "复制演示链接"
        }}</el-button></template
      ></el-dialog
    >
  </section>
</template>
