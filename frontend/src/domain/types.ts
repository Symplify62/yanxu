export type Scope = "employee" | "admin" | "device" | "demo";
export type Scenario =
  | "normal"
  | "offline"
  | "save-failure"
  | "ai-failure"
  | "missing-route"
  | "unknown";
export type JobState =
  | "QUEUED"
  | "WAITING_NETWORK"
  | "ARCHIVED"
  | "TRANSCRIBED"
  | "READY"
  | "ACCEPTED"
  | "RETRYING"
  | "FAILED"
  | "UNCONFIGURED"
  | "UNKNOWN"
  | "PAUSED"
  | "OWNER_DISABLED";
export interface Employee {
  id: string;
  name: string;
  department: string;
  allowedDepartments: string[];
  active: boolean;
  internal: boolean;
  registered: boolean;
  admin: boolean;
}
export interface Department {
  id: string;
  name: string;
}
export interface TaskItem {
  id: string;
  text: string;
  owner: string;
  due: string;
  evidence: string;
}
export interface ContentVersion {
  version: number;
  summary: string;
  tasks: TaskItem[];
  reason: string;
}
export interface Publication {
  version: number;
  summary: string;
  tasks: TaskItem[];
  target: string;
}
export interface Grant {
  id: string;
  subject: string;
  grantedBy: string;
  active: boolean;
}
export interface Meeting {
  id: string;
  title: string;
  owner: string;
  department: string;
  duration: number;
  createdAt: string;
  progress: number;
  state: JobState;
  summary: string;
  tasks: TaskItem[];
  version: number;
  versions: ContentVersion[];
  publication: Publication | null;
  grants: Grant[];
  target: string;
  attempts: number;
  sendCount: number;
  scenario: Scenario;
  nextAt: number;
  resolvedManually: boolean;
}
export type DevicePhase =
  "scan" | "ready" | "recording" | "paused" | "saving" | "save-error" | "saved";
export interface DeviceState {
  phase: DevicePhase;
  employee: string | null;
  department: string;
  challenge: string;
  expiresAt: number;
  consumed: boolean;
  elapsed: number;
  startedAt: number | null;
  saveAt: number | null;
  lastMeeting: string | null;
}
export interface DeviceView extends DeviceState {
  online: boolean;
  employeeName: string | null;
  allowedDepartments: string[];
  target: string | null;
  queue: Array<{ id: string; duration: number; state: JobState }>;
}
export interface Session {
  token: string;
  user: Employee;
}
export interface Settings {
  scenario: Scenario;
  online: boolean;
  paused: boolean;
  aiEnabled: boolean;
  routeVersion: number;
  routes: Record<string, string>;
}
export interface AuditEvent {
  id: string;
  time: string;
  action: string;
  detail: string;
}
export interface Group {
  id: string;
  name: string;
  members: string[];
  version: number;
}
export interface Role {
  id: string;
  name: string;
  protected: boolean;
  permissions: string[];
}
export interface DemoConfig {
  settings: Settings;
  people: Employee[];
  departments: Department[];
}
export interface AdminData {
  settings: Settings;
  people: Employee[];
  departments: Department[];
  groups: Group[];
  roles: Role[];
  jobs: Array<
    Pick<
      Meeting,
      | "id"
      | "department"
      | "duration"
      | "state"
      | "progress"
      | "attempts"
      | "sendCount"
      | "resolvedManually"
    >
  >;
  audit: AuditEvent[];
}
export interface RevisionInput {
  expectedVersion: number;
  summary: string;
  tasks: TaskItem[];
  reason: string;
}
