import { describe, it, expect, beforeEach } from "vitest";
import { MockDatabase, MockError } from "../src/mocks/database";
import type { Meeting } from "../src/domain/types";
let db: MockDatabase, now: number;
beforeEach(() => {
  db = new MockDatabase();
  now = Date.now();
});
function recorded(owner = "lin", dept = "sales") {
  db.scan(db.device.challenge, owner, now);
  db.start(dept, now);
  db.action("end", now + 2000);
  db.tick(now + 2600);
  return db.meetings.at(-1)!;
}
function finish(m: Meeting) {
  for (let i = 0; i < 5; i++) db.advance(m, now + 10000 + i * 2000);
}
describe("身份、扫码与采集绑定", () => {
  it("自动开户只授基础权限，停用与跨企业拒绝", () => {
    expect(db.login("zhou").user.registered).toBe(true);
    expect(db.employee("zhou").admin).toBe(false);
    expect(() => db.login("left")).toThrow(MockError);
    expect(() => db.login("outside")).toThrow(MockError);
  });
  it("挑战过期和重放拒绝", () => {
    expect(() =>
      db.scan(db.device.challenge, "lin", db.device.expiresAt + 1),
    ).toThrow();
    db.scan(db.device.challenge, "lin", now);
    expect(() => db.scan(db.device.challenge, "chen", now)).toThrow();
  });
  it("未经身份不能开始，归属不可伪造", () => {
    expect(() => db.start("sales")).toThrow();
    db.scan(db.device.challenge, "chen");
    expect(() => db.start("sales")).toThrow();
    expect(db.device.phase).toBe("ready");
  });
  it("保存后员工退出，任务仍绑定原发起人", () => {
    const m = recorded();
    expect(db.device.employee).toBeNull();
    expect(m.owner).toBe("lin");
    expect(m.progress).toBe(0);
    finish(m);
    expect(m.state).toBe("ACCEPTED");
    expect(m.sendCount).toBe(1);
  });
  it("保存失败不伪造退出，恢复保持原归属", () => {
    db.changeScenario("save-failure");
    db.scan(db.device.challenge, "chen");
    db.start("finance");
    db.action("end", now + 1000);
    db.tick(now + 2000);
    expect(db.device.phase).toBe("save-error");
    expect(db.device.employee).toBe("chen");
    db.action("retry-save", now + 2100);
    db.tick(now + 3000);
    expect(db.meetings.at(-1)?.owner).toBe("chen");
    expect(db.device.employee).toBeNull();
  });
  it("暂停不计采集，不因长时强制停止", () => {
    db.scan(db.device.challenge, "lin", now);
    db.start("sales", now);
    db.action("pause", now + 3600000);
    db.action("resume", now + 7200000);
    expect(db.deviceView(now + 18000000).elapsed).toBe(14400);
    expect(db.device.phase).toBe("recording");
  });
  it("新场必须联网，已录断网继续保存和补传", () => {
    db.settings.online = false;
    expect(() => db.scan(db.device.challenge, "lin")).toThrow();
    db.settings.online = true;
    db.scan(db.device.challenge, "lin");
    db.start("sales");
    db.settings.online = false;
    db.action("end", now + 1000);
    db.tick(now + 2000);
    const m = db.meetings.at(-1)!;
    expect(m.state).toBe("WAITING_NETWORK");
    db.settings.online = true;
    finish(m);
    expect(m.state).toBe("ACCEPTED");
  });
  it("连续两场人员隔离，调整部门不获得该部门全部资料", () => {
    const a = recorded("lin", "finance");
    db.action("next");
    const b = recorded("chen", "finance");
    expect(a.owner).toBe("lin");
    expect(b.owner).toBe("chen");
    expect(db.canRead(db.meetings[1]!, db.employee("lin"))).toBe(false);
  });
});
describe("对象访问、只读共享和版本", () => {
  it("系统管理员无默认正文权，无权和未知记录一致拒绝", () => {
    for (const id of ["m1", "nonexistent"])
      expect(() => db.readable(id, db.employee("admin"))).toThrow("记录不可用");
    expect(() => db.readable("m2", db.employee("lin"))).toThrow();
  });
  it("共享后可读不可改，撤销后新请求拒绝", () => {
    db.share("m1", db.employee("lin"), "chen");
    expect(db.readable("m1", db.employee("chen")).id).toBe("m1");
    expect(() => db.owned("m1", db.employee("chen"))).toThrow("查看权限");
    const g = db.meetings[0]!.grants[0]!;
    db.revoke("m1", db.employee("lin"), g.id);
    expect(() => db.readable("m1", db.employee("chen"))).toThrow();
  });
  it("共享不群发，不能重复授权或选择外部/停用人员", () => {
    const m = db.meetings[0]!;
    db.share("m1", db.employee("lin"), "zhou");
    expect(m.sendCount).toBe(1);
    expect(() => db.share("m1", db.employee("lin"), "zhou")).toThrow();
    expect(() => db.share("m1", db.employee("lin"), "outside")).toThrow();
    expect(() => db.share("m1", db.employee("lin"), "left")).toThrow();
  });
  it("发起人不能撤销管理员独立来源", () => {
    db.meetings[0]!.grants.push({
      id: "managed",
      subject: "chen",
      grantedBy: "admin",
      active: true,
    });
    expect(() => db.revoke("m1", db.employee("lin"), "managed")).toThrow();
    expect(db.meetings[0]!.grants[0]!.active).toBe(true);
  });
  it("更正内容和事项不改发送快照或再次发送", () => {
    const m = db.meetings[0]!,
      before = structuredClone(m.publication);
    db.revise("m1", db.employee("lin"), {
      expectedVersion: 1,
      summary: "人工更正",
      tasks: m.tasks.map((t) => ({
        ...t,
        owner: "补充人",
        evidence: "forged",
      })),
      reason: "核对原文",
    });
    expect(m.version).toBe(2);
    expect(m.publication).toEqual(before);
    expect(m.tasks[0]!.evidence).toBe("seg-004");
    expect(m.sendCount).toBe(1);
  });
  it("版本竞争及空原因拒绝，已有内容不覆盖", () => {
    const m = db.meetings[0]!;
    expect(() =>
      db.revise("m1", db.employee("lin"), {
        expectedVersion: 0,
        summary: "bad",
        tasks: m.tasks,
        reason: "x",
      }),
    ).toThrow("版本");
    expect(() =>
      db.revise("m1", db.employee("lin"), {
        expectedVersion: 1,
        summary: "bad",
        tasks: m.tasks,
        reason: "",
      }),
    ).toThrow("原因");
    expect(m.version).toBe(1);
  });
  it("首次冻结后更正不阻止发送，快照依然v1", () => {
    const m = recorded();
    db.advance(m);
    db.advance(m);
    db.advance(m);
    expect(m.publication?.version).toBe(1);
    db.revise(m.id, db.employee("lin"), {
      expectedVersion: 1,
      summary: "后续更正",
      tasks: m.tasks,
      reason: "补充",
    });
    db.advance(m);
    expect(m.state).toBe("ACCEPTED");
    expect(m.publication?.version).toBe(1);
  });
  it("组成员变化撤销组来源，独立授权仍可用", () => {
    db.share("m1", db.employee("lin"), "group:project");
    expect(db.canRead(db.meetings[0]!, db.employee("zhou"))).toBe(true);
    db.setGroup("project", [], 1);
    expect(db.canRead(db.meetings[0]!, db.employee("zhou"))).toBe(false);
    db.share("m1", db.employee("lin"), "zhou");
    expect(db.canRead(db.meetings[0]!, db.employee("zhou"))).toBe(true);
  });
});
describe("自动处理与管理员恢复", () => {
  it("未知负责人不阻断全自动发送，重复推进不重发", () => {
    const m = recorded();
    finish(m);
    expect(m.tasks[1]!.owner).toBe("");
    for (let i = 0; i < 10; i++) db.advance(m);
    expect(m.sendCount).toBe(1);
  });
  it("AI自动重试耗尽由管理员恢复，仅继续失败阶段", () => {
    db.changeScenario("ai-failure");
    const m = recorded();
    finish(m);
    expect(m.state).toBe("FAILED");
    expect(m.attempts).toBe(2);
    db.recover(m.id, "依赖恢复");
    finish(m);
    expect(m.sendCount).toBe(1);
  });
  it("缺群不猜目标，规则改变不重路由已有快照", () => {
    db.changeScenario("missing-route");
    const m = recorded();
    finish(m);
    expect(m.state).toBe("UNCONFIGURED");
    db.setRoute("sales", "项目协作群（模拟）", 1);
    expect(m.target).toBe("");
    db.recover(m.id, "确认新目标");
    finish(m);
    expect(m.publication?.target).toBe("项目协作群（模拟）");
  });
  it("UNKNOWN永不盲重发，人工记录不伪造发送次数", () => {
    db.changeScenario("unknown");
    const m = recorded();
    finish(m);
    expect(m.state).toBe("UNKNOWN");
    for (let i = 0; i < 10; i++) db.advance(m);
    expect(m.sendCount).toBe(0);
    db.recover(m.id, "已核查渠道接收");
    expect(m.resolvedManually).toBe(true);
    expect(m.sendCount).toBe(0);
  });
  it("应急停发保留原件，恢复不重复成功目标", () => {
    const m = recorded();
    db.settings.paused = true;
    finish(m);
    expect(m.state).toBe("PAUSED");
    expect(m.progress).toBe(3);
    db.settings.paused = false;
    finish(m);
    expect(m.sendCount).toBe(1);
  });
  it("账号停用撤会话，不可自动开户复活；保护最后管理员", () => {
    const s = db.login("lin");
    db.toggleUser("lin");
    expect(() => db.auth(s.token)).toThrow();
    expect(() => db.login("lin")).toThrow();
    expect(() => db.toggleUser("admin")).toThrow();
  });
  it("普通员工不能取得管理API资格", () => {
    const s = db.login("lin");
    expect(() => db.auth(s.token, true)).toThrow("管理权限");
  });
  it("配置版本冲突与非法目标拒绝", () => {
    expect(() => db.setRoute("sales", "项目协作群（模拟）", 0)).toThrow("规则");
    expect(() => db.setRoute("sales", "https://evil", 1)).toThrow("允许");
  });
});
