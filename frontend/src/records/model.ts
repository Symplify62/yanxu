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
