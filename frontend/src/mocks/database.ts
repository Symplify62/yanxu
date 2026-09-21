/** In-memory mock API model only. Not production authentication or storage. */
import type {
  Employee,
  DeviceState,
  DeviceView,
  Meeting,
  Settings,
  Session,
  RevisionInput,
  Group,
  Role,
  AuditEvent,
  Scenario,
} from "../domain/types";
import { people, departments, meeting, sampleSummary, tasks } from "./fixtures";
export class MockError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
const reject = (status: number, code: string, message: string): never => {
  throw new MockError(status, code, message);
};
export class MockDatabase {
  people = people();
  departments = departments;
  meetings: Meeting[] = [
    meeting("m1", "lin", "sales"),
    meeting("m2", "chen", "finance"),
  ];
  settings: Settings = {
    scenario: "normal",
    online: true,
    paused: false,
    aiEnabled: true,
    routeVersion: 1,
    routes: { sales: "销售管理群（模拟）", finance: "财务管理群（模拟）" },
  };
  sessions = new Map<string, string>();
  audit: AuditEvent[] = [];
  groups: Group[] = [
    { id: "project", name: "销售协作组", members: ["zhou"], version: 1 },
  ];
  roles: Role[] = [
    {
      id: "employee",
      name: "基础员工",
      protected: true,
      permissions: ["本人会议", "接受明确授权"],
    },
    {
      id: "viewer",
      name: "会议查看者",
      protected: false,
      permissions: ["纪要/逐字稿/事项", "在线回听"],
    },
    {
      id: "administrator",
      name: "系统管理员",
      protected: true,
      permissions: ["组织与账号", "设备与接收群", "异常处理"],
    },
  ];
  device: DeviceState = {
    phase: "scan",
    employee: null,
    department: "sales",
    challenge: crypto.randomUUID(),
    expiresAt: Date.now() + 120000,
    consumed: false,
    elapsed: 0,
    startedAt: null,
    saveAt: null,
    lastMeeting: null,
  };
  log(action: string, detail: string) {
    this.audit.unshift({
      id: crypto.randomUUID(),
      time: new Date().toISOString(),
      action,
      detail,
    });
  }
  employee(id: string): Employee {
    return (
      this.people.find((x) => x.id === id) ??
      reject(401, "IDENTITY_INVALID", "身份不可用")
    );
  }
  validateIdentity(id: string) {
    const u = this.employee(id);
    if (!u.active || !u.internal)
      reject(403, "IDENTITY_DENIED", "账号已停用或不属于本企业");
    if (!u.registered) {
      u.registered = true;
      this.log("首次身份自动开户", u.name + " · 基础权限");
    }
    return u;
  }
  login(id: string): Session {
    const u = this.validateIdentity(id),
      token = crypto.randomUUID();
    this.sessions.set(token, u.id);
    this.log("模拟企业微信登录", u.name);
    return { token, user: structuredClone(u) };
  }
  auth(token: string | null, admin = false) {
    const id = token ? this.sessions.get(token) : null;
    if (!id) reject(401, "SESSION_EXPIRED", "登录已过期，请重新登录");
    const u = this.employee(id!);
    if (!u.active || !u.internal) {
      this.sessions.delete(token!);
      reject(401, "SESSION_EXPIRED", "当前账号不可用");
    }
    if (admin && !u.admin) reject(403, "ADMIN_REQUIRED", "没有管理权限");
    return u;
  }
  canRead(m: Meeting, u: Employee) {
    return (
      u.active &&
      u.internal &&
      (m.owner === u.id ||
        m.grants.some(
          (g) =>
            g.active &&
            (g.subject === u.id ||
              (g.subject.startsWith("group:") &&
                this.groups
                  .find((x) => x.id === g.subject.slice(6))
                  ?.members.includes(u.id))),
        ))
    );
  }
  readable(id: string, u: Employee) {
    const m = this.meetings.find((x) => x.id === id);
    if (!m || !this.canRead(m, u))
      reject(404, "RESOURCE_UNAVAILABLE", "记录不可用或没有查看权限");
    return m!;
  }
  owned(id: string, u: Employee) {
    const m = this.readable(id, u);
    if (m.owner !== u.id) reject(403, "READ_ONLY", "你只有查看权限");
    return m;
  }
  changeScenario(scenario: Scenario) {
    if (
      ![
        "normal",
        "offline",
        "save-failure",
        "ai-failure",
        "missing-route",
        "unknown",
      ].includes(scenario)
    )
      reject(422, "INVALID_SCENARIO", "无效场景");
    this.settings.scenario = scenario;
    this.settings.online = scenario !== "offline";
  }
  refreshChallenge() {
    if (!["scan", "saved", "ready"].includes(this.device.phase))
      reject(409, "RECORDING_ACTIVE", "请先结束本场录音");
    this.device = {
      ...this.device,
      phase: "scan",
      employee: null,
      challenge: crypto.randomUUID(),
      expiresAt: Date.now() + 120000,
      consumed: false,
      elapsed: 0,
      startedAt: null,
    };
  }
  scan(challenge: string, id: string, now = Date.now()) {
    if (!this.settings.online) reject(503, "OFFLINE", "新场扫码需要网络");
    if (
      challenge !== this.device.challenge ||
      this.device.consumed ||
      now >= this.device.expiresAt ||
      this.device.phase !== "scan"
    )
      reject(409, "CHALLENGE_EXPIRED", "二维码已失效，请刷新后重新扫码");
    const u = this.validateIdentity(id);
    if (u.admin) reject(403, "EMPLOYEE_REQUIRED", "请选择员工演示身份");
    this.device.employee = u.id;
    this.device.department = u.department;
    this.device.phase = "ready";
    this.device.consumed = true;
    this.log("本场扫码", u.name);
  }
  start(department: string, now = Date.now()) {
    if (this.device.phase !== "ready" || !this.device.employee)
      reject(409, "NOT_READY", "请先扫码登录本场");
    const u = this.validateIdentity(this.device.employee!);
    if (!u.allowedDepartments.includes(department))
      reject(403, "DEPARTMENT_FORBIDDEN", "归属不在授权范围");
    this.device.department = department;
    this.device.phase = "recording";
    this.device.elapsed = 0;
    this.device.startedAt = now;
    this.log("开始录音模拟", u.name + " · " + department);
  }
  action(action: string, now = Date.now()) {
    const d = this.device;
    if (action === "pause" && d.phase === "recording") {
      d.elapsed += Math.max(0, Math.floor((now - d.startedAt!) / 1000));
      d.startedAt = null;
      d.phase = "paused";
      return;
    }
    if (action === "resume" && d.phase === "paused") {
      d.startedAt = now;
      d.phase = "recording";
      return;
    }
    if (action === "end" && ["recording", "paused"].includes(d.phase)) {
      if (d.startedAt)
        d.elapsed += Math.max(0, Math.floor((now - d.startedAt) / 1000));
      d.startedAt = null;
      d.phase = "saving";
      d.saveAt = now + 500;
      return;
    }
    if (action === "retry-save" && d.phase === "save-error") {
      this.settings.scenario = "normal";
      d.phase = "saving";
      d.saveAt = now + 500;
      return;
    }
    if (action === "next" && ["saved", "ready", "scan"].includes(d.phase)) {
      this.refreshChallenge();
      return;
    }
    if (action === "expire" && d.phase === "scan") {
      d.expiresAt = now - 1;
      return;
    }
    reject(409, "INVALID_STATE", "当前状态不允许该操作");
  }
  deviceView(now = Date.now()): DeviceView {
    this.tick(now);
    const d = this.device,
      u = d.employee ? this.employee(d.employee) : null;
    return {
      ...structuredClone(d),
      elapsed:
        d.elapsed +
        (d.startedAt ? Math.max(0, Math.floor((now - d.startedAt) / 1000)) : 0),
      employeeName: u?.name ?? null,
      allowedDepartments: u?.allowedDepartments ?? [],
      online: this.settings.online,
      target: this.settings.routes[d.department] ?? null,
      queue: this.meetings
        .filter((m) => m.id.startsWith("rec"))
        .map((m) => ({ id: m.id, duration: m.duration, state: m.state })),
    };
  }
  tick(now = Date.now()) {
    const d = this.device;
    if (d.phase === "saving" && d.saveAt !== null && now >= d.saveAt) {
      if (this.settings.scenario === "save-failure") {
        d.phase = "save-error";
        d.saveAt = null;
        return;
      }
      const id =
        "rec-" +
        (this.meetings.filter((x) => x.id.startsWith("rec")).length + 1)
          .toString()
          .padStart(3, "0");
      const m = meeting(id, d.employee!, d.department);
      Object.assign(m, {
        title: "新会议 · 自动整理样例",
        duration: d.elapsed,
        createdAt: new Date(now).toISOString(),
        progress: 0,
        state: this.settings.online ? "QUEUED" : "WAITING_NETWORK",
        versions: [],
        publication: null,
        sendCount: 0,
        scenario: this.settings.scenario,
        target:
          this.settings.scenario === "missing-route"
            ? ""
            : this.settings.routes[d.department] || "",
        nextAt: now + 1200,
      });
      this.meetings.push(m);
      d.employee = null;
      d.phase = "saved";
      d.saveAt = null;
      d.lastMeeting = id;
      this.log("保存成功，员工已退出", id + " · 设备任务继续");
    }
    for (const m of this.meetings) {
      if (m.id.startsWith("rec") && m.nextAt <= now) this.advance(m, now);
    }
  }
  advance(m: Meeting, now = Date.now()) {
    if (
      m.state === "ACCEPTED" ||
      ["FAILED", "UNKNOWN", "UNCONFIGURED", "OWNER_DISABLED"].includes(m.state)
    )
      return;
    m.nextAt = now + 1400;
    if (m.progress === 0) {
      if (!this.settings.online) {
        m.state = "WAITING_NETWORK";
        return;
      }
      m.progress = 1;
      m.state = "ARCHIVED";
      return;
    }
    if (m.progress < 3 && !this.settings.aiEnabled) {
      m.state = "FAILED";
      this.log("管理员告警", m.id + " · AI未配置");
      return;
    }
    if (m.progress < 3 && m.scenario === "ai-failure") {
      m.attempts++;
      m.state = m.attempts >= 2 ? "FAILED" : "RETRYING";
      if (m.state === "FAILED")
        this.log("管理员告警", m.id + " · 自动重试耗尽");
      return;
    }
    if (m.progress === 1) {
      m.progress = 2;
      m.state = "TRANSCRIBED";
      return;
    }
    if (m.progress === 2) {
      m.progress = 3;
      m.state = "READY";
      m.summary = sampleSummary;
      m.tasks = tasks();
      m.versions = [
        {
          version: 1,
          summary: m.summary,
          tasks: structuredClone(m.tasks),
          reason: "AI 原始版本",
        },
      ];
      m.publication = {
        version: 1,
        summary: m.summary,
        tasks: structuredClone(m.tasks),
        target: m.target,
      };
      return;
    }
    if (this.settings.paused) {
      m.state = "PAUSED";
      return;
    }
    if (!this.employee(m.owner).active) {
      m.state = "OWNER_DISABLED";
      return;
    }
    if (!m.target) {
      m.state = "UNCONFIGURED";
      this.log("管理员告警", m.id + " · 接收群未配置");
      return;
    }
    if (m.scenario === "unknown") {
      m.state = "UNKNOWN";
      this.log("管理员告警", m.id + " · 发送结果不明，不盲重发");
      return;
    }
    m.progress = 4;
    m.state = "ACCEPTED";
    m.sendCount++;
    this.log(
      "自动发送模拟",
      m.id + " · " + m.target + " · v" + m.publication!.version,
    );
  }
  revise(id: string, u: Employee, input: RevisionInput) {
    const m = this.owned(id, u);
    if (m.progress < 3) reject(409, "NOT_GENERATED", "内容尚未生成");
    if (input.expectedVersion !== m.version)
      reject(409, "VERSION_CONFLICT", "版本已变化，请保留内容并重新载入");
    if (
      !input.summary?.trim() ||
      !input.reason?.trim() ||
      !Array.isArray(input.tasks) ||
      input.tasks.length !== m.tasks.length ||
      input.tasks.some(
        (t) => !t.text?.trim() || !m.tasks.some((old) => old.id === t.id),
      )
    )
      reject(422, "INVALID_INPUT", "请填写纪要、事项说明和更正原因");
    m.version++;
    m.summary = input.summary.trim();
    m.tasks = input.tasks.map((t) => ({
      ...t,
      evidence: m.tasks.find((old) => old.id === t.id)!.evidence,
    }));
    m.versions.push({
      version: m.version,
      summary: m.summary,
      tasks: structuredClone(m.tasks),
      reason: input.reason,
    });
    this.log("主动更正，不重发", id + " v" + m.version);
    return m;
  }
  share(id: string, u: Employee, subject: string) {
    const m = this.owned(id, u);
    const group = subject.startsWith("group:")
      ? this.groups.find((g) => g.id === subject.slice(6))
      : null;
    const target = this.people.find((p) => p.id === subject);
    if (
      !group &&
      (!target ||
        !target.active ||
        !target.internal ||
        target.admin ||
        target.id === u.id)
    )
      reject(422, "INVALID_SUBJECT", "请选择有效公司员工或业务组");
    if (m.grants.some((g) => g.active && g.subject === subject))
      reject(409, "DUPLICATE_GRANT", "已有该查看授权");
    m.grants.push({
      id: crypto.randomUUID(),
      subject,
      grantedBy: u.id,
      active: true,
    });
    this.log("添加只读共享", id + " · " + subject);
    return m;
  }
  revoke(id: string, u: Employee, grantId: string) {
    const m = this.owned(id, u),
      g = m.grants.find((g) => g.id === grantId);
    if (!g || g.grantedBy !== u.id)
      reject(403, "GRANT_FORBIDDEN", "不能撤销其他来源授权");
    g!.active = false;
    this.log("撤销本人共享", id);
    return m;
  }
  adminData() {
    return structuredClone({
      settings: this.settings,
      people: this.people.filter((u) => u.internal),
      departments: this.departments,
      groups: this.groups,
      roles: this.roles,
      jobs: this.meetings.map((m) => ({
        id: m.id,
        department: m.department,
        duration: m.duration,
        state: m.state,
        progress: m.progress,
        attempts: m.attempts,
        sendCount: m.sendCount,
        resolvedManually: m.resolvedManually,
      })),
      audit: this.audit,
    });
  }
  toggleUser(id: string) {
    const u = this.employee(id);
    if (u.admin) reject(409, "PROTECTED_ADMIN", "最后恢复管理员受到保护");
    u.active = !u.active;
    if (!u.active)
      for (const [token, uid] of this.sessions)
        if (uid === id) this.sessions.delete(token);
    this.log("变更账号状态", u.name + " " + (u.active ? "启用" : "停用"));
  }
  setRoute(department: string, target: string, expectedVersion: number) {
    if (expectedVersion !== this.settings.routeVersion)
      reject(409, "VERSION_CONFLICT", "规则已变化，请重新载入");
    if (
      !this.departments.some((d) => d.id === department) ||
      ![
        "",
        "销售管理群（模拟）",
        "财务管理群（模拟）",
        "项目协作群（模拟）",
      ].includes(target)
    )
      reject(422, "INVALID_TARGET", "请选择允许的模拟连接");
    this.settings.routes[department] = target;
    this.settings.routeVersion++;
    this.log("新会议路由配置", department + " → " + target);
  }
  setGroup(id: string, members: string[], version: number) {
    const g = this.groups.find((g) => g.id === id);
    if (!g || g.version !== version)
      reject(409, "VERSION_CONFLICT", "访问组已变化");
    if (
      !Array.isArray(members) ||
      members.some(
        (id) =>
          !this.people.some(
            (u) => u.id === id && u.active && u.internal && !u.admin,
          ),
      )
    )
      reject(422, "INVALID_MEMBERS", "成员必须是有效公司员工");
    g!.members = [...new Set(members)];
    g!.version++;
    this.log("维护访问组", g!.name);
  }
  recover(id: string, reason: string) {
    const m = this.meetings.find((m) => m.id === id);
    if (!reason?.trim()) reject(422, "REASON_REQUIRED", "请填写处理依据");
    if (
      !m ||
      !["FAILED", "UNCONFIGURED", "UNKNOWN", "OWNER_DISABLED"].includes(m.state)
    )
      reject(409, "INVALID_STATE", "任务状态已变化");
    if (m!.state === "UNKNOWN") {
      m!.state = "ACCEPTED";
      m!.progress = 4;
      m!.resolvedManually = true;
      this.log("人工记录渠道已接收", id + " · " + reason);
      return;
    }
    if (!this.employee(m!.owner).active)
      reject(409, "OWNER_DISABLED", "发起人仍停用，请先处理资格");
    m!.scenario = "normal";
    m!.target = this.settings.routes[m!.department] || "";
    if (m!.publication) m!.publication.target = m!.target;
    m!.state =
      m!.progress >= 3
        ? "READY"
        : m!.progress === 2
          ? "TRANSCRIBED"
          : "ARCHIVED";
    m!.nextAt = Date.now();
    this.log("管理员恢复失败阶段", id + " · " + reason);
  }
}
