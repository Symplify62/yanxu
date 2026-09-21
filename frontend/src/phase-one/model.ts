import { computed, onUnmounted, ref } from "vue";
export type Scenario =
  | "normal"
  | "capture-error"
  | "save-error"
  | "offline"
  | "transcript-error"
  | "analysis-error";
export interface PublicRecord {
  status?: Stage;
  hasAudio?: boolean;
  interrupted?: boolean;
  error?: string | null;
  transcript?: {
    text: string;
    segments: Array<{
      id: string;
      start: number;
      end: number;
      text: string;
      speaker: string | null;
    }>;
  } | null;
  analysis?: {
    summary: string;
    points: string[];
    decisions: string[];
    tasks: Array<{
      text: string;
      owner: string | null;
      due: string | null;
      evidence: string[];
    }>;
  } | null;
  id: string;
  title: string;
  createdAt: number;
  duration: number;
  scenario: Scenario;
  readyAt: number;
  seed?: boolean;
}
export type Stage =
  | "queued"
  | "uploading"
  | "waiting"
  | "transcribing"
  | "analyzing"
  | "complete"
  | "transcript-error"
  | "analysis-error";
const storageKey = "yanxu.phase-one.page-demo.v1";
const seed = (): PublicRecord[] => [
  {
    id: "sample-weekly",
    title: "产品周会 · 本周重点与下一步",
    createdAt: Date.now() - 86400000,
    duration: 1824,
    scenario: "normal",
    readyAt: Date.now() - 86400000,
    seed: true,
  },
  {
    id: "sample-delivery",
    title: "流程评审 · 录音与结果展示",
    createdAt: Date.now() - 172800000,
    duration: 1435,
    scenario: "normal",
    readyAt: Date.now() - 172800000,
    seed: true,
  },
];
export const stageLabels: Record<Stage, string> = {
  queued: "等待转写",
  uploading: "正在上传",
  waiting: "等待网络",
  transcribing: "正在转写",
  analyzing: "AI 分析中",
  complete: "已完成",
  "transcript-error": "转写未完成",
  "analysis-error": "分析未完成",
};
export function stageOf(r: PublicRecord, now: number): Stage {
  if (r.status) return r.status;
  if (r.scenario === "offline") return "waiting";
  const elapsed = now - r.readyAt;
  if (elapsed < 1200) return "uploading";
  if (elapsed < 3000) return "transcribing";
  if (r.scenario === "transcript-error") return "transcript-error";
  if (elapsed < 5200) return "analyzing";
  if (r.scenario === "analysis-error") return "analysis-error";
  return "complete";
}
export function usePhaseDemo() {
  const records = ref<PublicRecord[]>([]),
    now = ref(Date.now()),
    scenario = ref<Scenario>("normal"),
    phase = ref<
      "idle" | "recording" | "paused" | "saving" | "save-error" | "saved"
    >("idle"),
    elapsed = ref(0),
    lastId = ref(""),
    notice = ref(""),
    loading = ref(true);
  let started = 0,
    accumulated = 0,
    saveTimer: ReturnType<typeof setTimeout> | undefined;
  function persist(next: PublicRecord[]) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      records.value = next;
      notice.value = "";
      return true;
    } catch {
      notice.value = "浏览器暂时无法保存演示数据，请检查存储设置后重试。";
      return false;
    }
  }
  try {
    const raw = localStorage.getItem(storageKey);
    const value = raw ? JSON.parse(raw) : seed();
    if (
      !Array.isArray(value) ||
      !value.every(
        (r) =>
          r &&
          typeof r.id === "string" &&
          typeof r.title === "string" &&
          Number.isFinite(r.createdAt) &&
          Number.isFinite(r.readyAt) &&
          Number.isFinite(r.duration) &&
          [
            "normal",
            "capture-error",
            "save-error",
            "offline",
            "transcript-error",
            "analysis-error",
          ].includes(r.scenario),
      )
    )
      throw new Error("invalid");
    records.value = value;
  } catch {
    records.value = seed();
    notice.value = "旧演示数据无法读取，已恢复示例记录。";
  }
  const loadTimer = setTimeout(() => (loading.value = false), 250);
  const timer = setInterval(() => {
    now.value = Date.now();
    if (phase.value === "recording")
      elapsed.value = accumulated + (now.value - started) / 1000;
  }, 200);
  function start() {
    if (phase.value !== "idle") return;
    if (scenario.value === "capture-error") {
      notice.value =
        "录音暂不可用（演示）：请检查麦克风权限或设备连接，再尝试开始。";
      return;
    }
    notice.value = "";
    accumulated = 0;
    elapsed.value = 0;
    started = Date.now();
    phase.value = "recording";
  }
  function pause() {
    if (phase.value !== "recording") return;
    accumulated += (Date.now() - started) / 1000;
    elapsed.value = accumulated;
    phase.value = "paused";
  }
  function resume() {
    if (phase.value !== "paused") return;
    started = Date.now();
    phase.value = "recording";
  }
  function finish(retry = false) {
    if (
      retry
        ? phase.value !== "save-error"
        : !["recording", "paused"].includes(phase.value)
    )
      return;
    if (phase.value === "recording")
      accumulated += (Date.now() - started) / 1000;
    elapsed.value = accumulated;
    phase.value = "saving";
    notice.value = "";
    saveTimer = setTimeout(() => {
      if (scenario.value === "save-error" && !retry) {
        phase.value = "save-error";
        return;
      }
      const timestamp = Date.now();
      const r: PublicRecord = {
        id: crypto.randomUUID(),
        title:
          "新录音 · " +
          new Date(timestamp).toLocaleString("zh-CN", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          }),
        createdAt: timestamp,
        duration: Math.floor(elapsed.value),
        readyAt: timestamp,
        scenario: scenario.value === "save-error" ? "normal" : scenario.value,
      };
      if (persist([r, ...records.value])) {
        lastId.value = r.id;
        phase.value = "saved";
      } else phase.value = "save-error";
    }, 600);
  }
  function next() {
    if (phase.value !== "saved") return;
    phase.value = "idle";
    elapsed.value = 0;
    notice.value = "";
  }
  function recover() {
    scenario.value = "normal";
    notice.value = "";
    persist(
      records.value.map((r) =>
        ["offline", "transcript-error", "analysis-error"].includes(r.scenario)
          ? {
              ...r,
              scenario: "normal",
              readyAt:
                Date.now() - (r.scenario === "analysis-error" ? 3000 : 0),
            }
          : r,
      ),
    );
  }
  function reset(empty = false) {
    if (saveTimer) clearTimeout(saveTimer);
    if (persist(empty ? [] : seed())) {
      phase.value = "idle";
      elapsed.value = 0;
      lastId.value = "";
      scenario.value = "normal";
    }
  }
  const active = computed(() =>
    ["recording", "paused", "saving", "save-error"].includes(phase.value),
  );
  onUnmounted(() => {
    clearInterval(timer);
    clearTimeout(loadTimer);
    if (saveTimer) clearTimeout(saveTimer);
  });
  return {
    records,
    now,
    scenario,
    phase,
    elapsed,
    lastId,
    notice,
    loading,
    active,
    start,
    pause,
    resume,
    finish,
    next,
    recover,
    reset,
  };
}
export const transcript = [
  {
    time: "00:12",
    speaker: "说话人 1",
    text: "这次先把快速录音和公开结果的流程跑通，登录、用户权限和群推送放到后面。",
  },
  {
    time: "00:45",
    speaker: "说话人 2",
    text: "录完后自动转成文字，再整理讨论重点、结论和行动事项。大家打开链接就能看到。",
  },
  {
    time: "01:18",
    speaker: "说话人 1",
    text: "先检查录音、保存和处理状态。下次再一起确定测试安排，负责人和具体日期这次还没有定。",
  },
];
export const sampleAnalysis = {
  summary:
    "本次讨论明确先完成免登录快速录音与公共结果查看。录音结束后自动转写和分析，结果逐步展示，减少人工操作。",
  points: [
    "本阶段聚焦录音、转写和结果查看的完整流程。",
    "公共页面无需登录，处理进度应清楚可见。",
    "保存成功与AI分析完成是不同状态，需要分别反馈。",
  ],
  decisions: [
    "身份、组织权限与群推送留待后续阶段。",
    "先检查页面流程和状态，再接入真实处理能力。",
  ],
  tasks: [
    {
      text: "核对录音、保存和处理状态的页面反馈",
      owner: "负责人未明确",
      due: "期限未明确",
      evidence: "01:18",
    },
    {
      text: "安排下一次测试范围讨论",
      owner: "负责人未明确",
      due: "期限未明确",
      evidence: "01:18",
    },
  ],
};
