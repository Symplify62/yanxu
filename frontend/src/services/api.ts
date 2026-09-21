import { http } from "./http";
import type {
  AdminData,
  DemoConfig,
  DeviceView,
  Employee,
  Group,
  Meeting,
  RevisionInput,
  Scenario,
  Session,
  Settings,
} from "../domain/types";
export const api = {
  demo: {
    config: () => http<DemoConfig>("/demo/config", { scope: "demo" }),
    settings: (body: { scenario?: Scenario; online?: boolean }) =>
      http<Settings>("/demo/settings", { method: "POST", body, scope: "demo" }),
    reset: () =>
      http<boolean>("/demo/reset", { method: "POST", scope: "demo" }),
  },
  auth: {
    login: (userId: string) =>
      http<Session>("/auth/demo-login", {
        method: "POST",
        body: { userId },
        scope: "demo",
      }),
    me: (scope: "employee" | "admin") => http<Employee>("/session", { scope }),
    logout: (scope: "employee" | "admin") =>
      http<boolean>("/session", { method: "DELETE", scope }),
  },
  device: {
    get: () => http<DeviceView>("/device", { scope: "device" }),
    refresh: () =>
      http<DeviceView>("/device/challenge", {
        method: "POST",
        scope: "device",
      }),
    scan: (challenge: string, userId: string) =>
      http<DeviceView>("/device/scan", {
        method: "POST",
        scope: "device",
        body: { challenge, userId },
      }),
    start: (department: string) =>
      http<DeviceView>("/device/start", {
        method: "POST",
        scope: "device",
        body: { department },
      }),
    action: (action: string) =>
      http<DeviceView>("/device/actions/" + action, {
        method: "POST",
        scope: "device",
      }),
  },
  meetings: {
    list: (q = "") => http<Meeting[]>("/meetings?q=" + encodeURIComponent(q)),
    get: (id: string) => http<Meeting>("/meetings/" + encodeURIComponent(id)),
    transcript: (id: string) =>
      http<Array<{ id: string; time: string; speaker: string; text: string }>>(
        "/meetings/" + encodeURIComponent(id) + "/transcript",
      ),
    revise: (id: string, body: RevisionInput) =>
      http<Meeting>("/meetings/" + id + "/revision", { method: "PATCH", body }),
    share: (id: string, subject: string) =>
      http<Meeting>("/meetings/" + id + "/grants", {
        method: "POST",
        body: { subject },
      }),
    revoke: (id: string, grant: string) =>
      http<Meeting>("/meetings/" + id + "/grants/" + grant, {
        method: "DELETE",
      }),
    people: () => http<{ people: Employee[]; groups: Group[] }>("/people"),
  },
  admin: {
    get: () => http<AdminData>("/admin", { scope: "admin" }),
    toggle: (id: string) =>
      http<AdminData>("/admin/users/" + id + "/toggle", {
        method: "POST",
        scope: "admin",
      }),
    route: (department: string, target: string, expectedVersion: number) =>
      http<AdminData>("/admin/routes", {
        method: "PATCH",
        scope: "admin",
        body: { department, target, expectedVersion },
      }),
    group: (id: string, members: string[], expectedVersion: number) =>
      http<AdminData>("/admin/groups/" + id, {
        method: "PATCH",
        scope: "admin",
        body: { members, expectedVersion },
      }),
    pause: (paused: boolean) =>
      http<AdminData>("/admin/pause", {
        method: "POST",
        scope: "admin",
        body: { paused },
      }),
    recover: (id: string, reason: string) =>
      http<AdminData>("/admin/recover/" + id, {
        method: "POST",
        scope: "admin",
        body: { reason },
      }),
    sync: () =>
      http<AdminData>("/admin/sync", { method: "POST", scope: "admin" }),
  },
};
