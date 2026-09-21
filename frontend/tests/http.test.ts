import { describe, it, expect, beforeAll, beforeEach, afterAll } from "vitest";
import { setupServer } from "msw/node";
import { handlers, resetDatabase } from "../src/mocks/handlers";
const server = setupServer(...handlers),
  base = "http://localhost/api/v1";
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(resetDatabase);
afterAll(() => server.close());
async function request(
  path: string,
  method = "GET",
  body?: unknown,
  token = "",
) {
  return fetch(base + path, {
    method,
    headers: { "Content-Type": "application/json", "X-Demo-Session": token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
async function login(id: string) {
  const r = await request("/auth/demo-login", "POST", { userId: id });
  return (await r.json()).data.token as string;
}
describe("模拟HTTP契约", () => {
  it("匿名列表401，不返回内容", async () => {
    const r = await request("/meetings");
    expect(r.status).toBe(401);
    expect(await r.json()).toMatchObject({
      error: { code: "SESSION_EXPIRED" },
    });
  });
  it("管理资格与正文读取分离", async () => {
    const token = await login("admin");
    expect((await request("/admin", "GET", undefined, token)).status).toBe(200);
    const r = await request("/meetings/m1", "GET", undefined, token);
    expect(r.status).toBe(404);
  });
  it("只读共享和更正拒绝通过接口执行", async () => {
    const a = await login("lin"),
      b = await login("chen");
    expect(
      (await request("/meetings/m1/grants", "POST", { subject: "chen" }, a))
        .status,
    ).toBe(200);
    expect((await request("/meetings/m1", "GET", undefined, b)).status).toBe(
      200,
    );
    expect(
      (
        await request(
          "/meetings/m1/revision",
          "PATCH",
          { expectedVersion: 1, summary: "x", tasks: [], reason: "x" },
          b,
        )
      ).status,
    ).toBe(403);
  });
  it("普通员工不能维护用户或群配置", async () => {
    const a = await login("lin");
    expect((await request("/admin", "GET", undefined, a)).status).toBe(403);
    expect(
      (
        await request(
          "/admin/routes",
          "PATCH",
          { department: "sales", target: "", expectedVersion: 1 },
          a,
        )
      ).status,
    ).toBe(403);
  });
  it("版本冲突返回409而非覆盖", async () => {
    const a = await login("lin");
    const r = await request(
      "/meetings/m1/revision",
      "PATCH",
      { expectedVersion: 0, summary: "x", tasks: [], reason: "x" },
      a,
    );
    expect(r.status).toBe(409);
    expect((await r.json()).error.code).toBe("VERSION_CONFLICT");
  });
  it("状态错误有明确冲突，过期扫码不绑定", async () => {
    await request("/device/actions/expire", "POST");
    const r = await request("/device", "GET");
    const d = (await r.json()).data;
    expect(
      (
        await request("/device/scan", "POST", {
          challenge: d.challenge,
          userId: "lin",
        })
      ).status,
    ).toBe(409);
  });
});
