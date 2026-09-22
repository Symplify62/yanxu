export type Permission =
  "record" | "users" | "roles" | "departments" | "voices";
export interface Account {
  id: string;
  username: string;
  personId: string;
  displayName: string;
  permissions: Permission[];
}
export interface Person {
  id: string;
  name: string;
  detail: string;
  departmentId: string | null;
  departmentName: string | null;
  active: boolean;
  accountId?: string | null;
  username?: string | null;
  roleId?: string | null;
}
export interface Department {
  id: string;
  name: string;
  parentId: string | null;
}
export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  builtin: boolean;
}
export interface VoiceProfile {
  personId: string;
  status: string;
  version: number;
  recordedAt: number | null;
  error?: string | null;
}
export interface Recording {
  speakerStatus?: "none" | "waiting" | "complete" | "failed";
  id: string;
  title: string;
  createdAt: number;
  duration: number;
  status: string;
  error?: string | null;
  participants?: { personId: string; name: string }[];
  transcript?: {
    text: string;
    segments: {
      id?: string;
      start: number;
      end: number;
      text: string;
      speaker: string | null;
    }[];
  } | null;
  analysis?: { summary: string } | null;
}
export const permissionLabels: Record<Permission, string> = {
  record: "发起录音",
  users: "用户管理",
  roles: "角色管理",
  departments: "部门管理",
  voices: "声纹管理",
};
export const voiceLabels: Record<string, string> = {
  missing: "未登记",
  none: "未登记",
  uploading: "等待上传",
  queued: "等待生成",
  pending: "等待生成",
  processing: "生成中",
  ready: "可用",
  active: "可用",
  failed: "需重录",
  error: "需重录",
  revoked: "已撤回",
};
