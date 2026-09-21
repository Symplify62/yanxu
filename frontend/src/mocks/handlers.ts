import { http, HttpResponse, delay } from "msw";
import { MockDatabase, MockError } from "./database";
import type { RevisionInput, Scenario } from "../domain/types";
import { transcript } from "./fixtures";
export let db = new MockDatabase();
export function resetDatabase() {
  db = new MockDatabase();
}
const base = "*/api/v1";
const token = (request: Request) => request.headers.get("X-Demo-Session");
const body = async (request: Request) =>
  (await request.json()) as Record<string, any>;
const safe =
  (
    fn: (
      request: Request,
      params: Record<string, any>,
    ) => unknown | Promise<unknown>,
  ) =>
  async ({
    request,
    params,
  }: {
    request: Request;
    params: Record<string, any>;
  }) => {
    await delay(70);
    try {
      db.tick();
      const result = await fn(request, params);
      return HttpResponse.json({ data: result ?? null });
    } catch (error) {
      if (error instanceof MockError)
        return HttpResponse.json(
          { error: { code: error.code, message: error.message } },
          { status: error.status },
        );
      return HttpResponse.json(
        { error: { code: "MOCK_ERROR", message: "模拟服务发生异常" } },
        { status: 500 },
      );
    }
  };
export const handlers = [
  http.get(
    base + "/demo/config",
    safe(() => ({
      settings: db.settings,
      people: db.people,
      departments: db.departments,
    })),
  ),
  http.post(
    base + "/demo/settings",
    safe(async (req) => {
      const b = await body(req);
      if (b.scenario) db.changeScenario(b.scenario as Scenario);
      if (typeof b.online === "boolean") db.settings.online = b.online;
      return db.settings;
    }),
  ),
  http.post(
    base + "/demo/reset",
    safe(() => {
      resetDatabase();
      return true;
    }),
  ),
  http.post(
    base + "/auth/demo-login",
    safe(async (req) => db.login((await body(req)).userId)),
  ),
  http.get(
    base + "/session",
    safe((req) => db.auth(token(req))),
  ),
  http.delete(
    base + "/session",
    safe((req) => {
      const t = token(req);
      if (t) db.sessions.delete(t);
      return true;
    }),
  ),
  http.get(
    base + "/device",
    safe(() => db.deviceView()),
  ),
  http.post(
    base + "/device/challenge",
    safe(() => {
      db.refreshChallenge();
      return db.deviceView();
    }),
  ),
  http.post(
    base + "/device/scan",
    safe(async (req) => {
      const b = await body(req);
      db.scan(b.challenge, b.userId);
      return db.deviceView();
    }),
  ),
  http.post(
    base + "/device/start",
    safe(async (req) => {
      db.start((await body(req)).department);
      return db.deviceView();
    }),
  ),
  http.post(
    base + "/device/actions/:action",
    safe((_req, p) => {
      db.action(String(p.action));
      return db.deviceView();
    }),
  ),
  http.get(
    base + "/people",
    safe((req) => {
      db.auth(token(req));
      return {
        people: db.people.filter((u) => u.active && u.internal && !u.admin),
        groups: db.groups,
      };
    }),
  ),
  http.get(
    base + "/meetings",
    safe((req) => {
      const u = db.auth(token(req));
      const q = new URL(req.url).searchParams.get("q")?.toLowerCase() ?? "";
      return db.meetings
        .filter((m) => db.canRead(m, u) && m.title.toLowerCase().includes(q))
        .reverse();
    }),
  ),
  http.get(
    base + "/meetings/:id",
    safe((req, p) => db.readable(String(p.id), db.auth(token(req)))),
  ),
  http.get(
    base + "/meetings/:id/transcript",
    safe((req, p) => {
      const m = db.readable(String(p.id), db.auth(token(req)));
      if (m.progress < 2)
        throw new MockError(409, "NOT_GENERATED", "逐字稿尚未生成");
      return transcript;
    }),
  ),
  http.patch(
    base + "/meetings/:id/revision",
    safe(async (req, p) =>
      db.revise(
        String(p.id),
        db.auth(token(req)),
        (await body(req)) as unknown as RevisionInput,
      ),
    ),
  ),
  http.post(
    base + "/meetings/:id/grants",
    safe(async (req, p) =>
      db.share(String(p.id), db.auth(token(req)), (await body(req)).subject),
    ),
  ),
  http.delete(
    base + "/meetings/:id/grants/:grant",
    safe((req, p) =>
      db.revoke(String(p.id), db.auth(token(req)), String(p.grant)),
    ),
  ),
  http.get(
    base + "/admin",
    safe((req) => {
      db.auth(token(req), true);
      return db.adminData();
    }),
  ),
  http.post(
    base + "/admin/users/:id/toggle",
    safe((req, p) => {
      db.auth(token(req), true);
      db.toggleUser(String(p.id));
      return db.adminData();
    }),
  ),
  http.patch(
    base + "/admin/routes",
    safe(async (req) => {
      db.auth(token(req), true);
      const b = await body(req);
      db.setRoute(b.department, b.target, b.expectedVersion);
      return db.adminData();
    }),
  ),
  http.patch(
    base + "/admin/groups/:id",
    safe(async (req, p) => {
      db.auth(token(req), true);
      const b = await body(req);
      db.setGroup(String(p.id), b.members, b.expectedVersion);
      return db.adminData();
    }),
  ),
  http.post(
    base + "/admin/pause",
    safe(async (req) => {
      db.auth(token(req), true);
      db.settings.paused = !!(await body(req)).paused;
      db.log("全局发送开关", db.settings.paused ? "应急停发" : "恢复自动发送");
      return db.adminData();
    }),
  ),
  http.post(
    base + "/admin/recover/:id",
    safe(async (req, p) => {
      db.auth(token(req), true);
      db.recover(String(p.id), (await body(req)).reason);
      return db.adminData();
    }),
  ),
  http.post(
    base + "/admin/sync",
    safe((req) => {
      db.auth(token(req), true);
      db.log("模拟组织同步", "未访问企业微信；不改历史归属或自动扩大数据权限");
      return db.adminData();
    }),
  ),
];
