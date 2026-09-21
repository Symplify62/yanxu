import type { JobState } from "./types";
export const statusLabels: Record<JobState, string> = {
  QUEUED: "等待上传",
  WAITING_NETWORK: "等待网络",
  ARCHIVED: "原录音已归档",
  TRANSCRIBED: "逐字稿已生成",
  READY: "准备自动发送",
  ACCEPTED: "渠道已接收",
  RETRYING: "正在自动重试",
  FAILED: "处理失败，管理员接管",
  UNCONFIGURED: "接收群未配置",
  UNKNOWN: "发送结果待核查",
  PAUSED: "管理员应急停发",
  OWNER_DISABLED: "发起人停用，等待检查",
};
export function duration(seconds: number) {
  const n = Math.max(0, Math.floor(seconds));
  return [Math.floor(n / 3600), Math.floor((n % 3600) / 60), n % 60]
    .map((x) => String(x).padStart(2, "0"))
    .join(":");
}
export function isException(s: JobState) {
  return ["FAILED", "UNCONFIGURED", "UNKNOWN", "OWNER_DISABLED"].includes(s);
}
