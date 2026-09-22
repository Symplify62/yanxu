import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";
const credentials = JSON.parse(
  readFileSync(
    resolve("../.local-data/evidence/identity-voice/credentials.json"),
    "utf8",
  ),
) as { username: string; password: string };
const evidence = resolve("../.local-data/evidence/identity-voice");
const password = "Account-ui-test-" + randomUUID();
async function adminHeaders(request: APIRequestContext) {
  const response = await request.post("/api/auth/login", { data: credentials });
  expect(response.status()).toBe(200);
  return { Authorization: `Bearer ${(await response.json()).accessToken}` };
}
async function person(request: APIRequestContext, roleId = "member") {
  const headers = await adminHeaders(request);
  const username = "web-" + randomUUID().slice(0, 8),
    name = "页面测试" + username.slice(-4);
  const response = await request.post("/api/admin/users", {
    headers,
    data: { name, username, password, roleId },
  });
  expect(response.status()).toBe(200);
  return { person: await response.json(), username, password, headers, name };
}
async function login(page: Page, values = credentials) {
  await page.goto("/account.html");
  await page.getByLabel("账号", { exact: true }).fill(values.username);
  await page.getByLabel("密码", { exact: true }).fill(values.password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(
    page.getByRole("navigation", { name: "工作台导航" }),
  ).toBeVisible();
}
async function check(page: Page, label: string) {
  await page.getByRole("dialog").getByText(label, { exact: true }).click();
  await expect(
    page.getByRole("checkbox", { name: label, exact: true }),
  ).toBeChecked();
}
function wav() {
  const sampleRate = 16000,
    frames = sampleRate * 4;
  const bytes = Buffer.alloc(44 + frames * 2);
  bytes.write("RIFF");
  bytes.writeUInt32LE(bytes.length - 8, 4);
  bytes.write("WAVEfmt ", 8);
  bytes.writeUInt32LE(16, 16);
  bytes.writeUInt16LE(1, 20);
  bytes.writeUInt16LE(1, 22);
  bytes.writeUInt32LE(sampleRate, 24);
  bytes.writeUInt32LE(sampleRate * 2, 28);
  bytes.writeUInt16LE(2, 32);
  bytes.writeUInt16LE(16, 34);
  bytes.write("data", 36);
  bytes.writeUInt32LE(frames * 2, 40);
  for (let i = 0; i < frames; i++)
    bytes.writeInt16LE(
      Math.sin((i / sampleRate) * 440 * Math.PI * 2) * 3000,
      44 + i * 2,
    );
  return bytes;
}

test("真实登录、错误反馈与桌面后台", async ({ page }) => {
  await page.goto("/account.html");
  await expect(
    page.getByRole("navigation", { name: "工作台导航" }),
  ).toHaveCount(0);
  await page.getByLabel("账号", { exact: true }).fill("unknown-ui-user");
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByText("账号或密码错误", { exact: true })).toBeVisible();
  await page.getByLabel("账号", { exact: true }).fill(credentials.username);
  await page.getByLabel("密码", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("link", { name: "用户管理", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "新增用户", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-desktop-users.png"),
    fullPage: true,
  });
});

test("部门、角色、带账号的人员完整管理", async ({ page }) => {
  const suffix = randomUUID().slice(0, 6),
    department = "测试部门" + suffix,
    role = "会议助理" + suffix,
    name = "同事" + suffix;
  await login(page);
  await page.getByRole("link", { name: "部门管理", exact: true }).click();
  await page.getByRole("button", { name: "新增部门", exact: true }).click();
  await page.getByLabel("部门名称", { exact: true }).fill(department);
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect(page.getByRole("heading", { name: department })).toBeVisible();
  await page.getByRole("link", { name: "角色管理", exact: true }).click();
  await page.getByRole("button", { name: "新增角色", exact: true }).click();
  await page.getByLabel("角色名称", { exact: true }).fill(role);
  await check(page, "发起录音");
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect(page.getByText(role, { exact: true })).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-roles.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "用户管理", exact: true }).click();
  await page.getByRole("button", { name: "新增用户", exact: true }).click();
  await page.getByLabel("姓名", { exact: true }).fill(name);
  await page
    .getByRole("combobox", { name: "部门", exact: true })
    .press("Enter");
  await page.getByRole("option", { name: department, exact: true }).click();
  await check(page, "允许账号登录");
  await page.getByLabel("登录账号", { exact: true }).fill("ui-" + suffix);
  await page.getByLabel("用户密码", { exact: true }).fill(password);
  await page
    .getByRole("combobox", { name: "用户角色", exact: true })
    .press("Enter");
  await page.getByRole("option", { name: role, exact: true }).click();
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("搜索用户").fill(name);
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  await expect(
    page.getByRole("cell", { name: department, exact: true }),
  ).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-created-user.png"),
    fullPage: true,
  });
});

test("退出撤销会话并切换普通成员，不残留管理员资料", async ({
  page,
  request,
}) => {
  const user = await person(request);
  await login(page);
  await page.getByRole("link", { name: "用户管理", exact: true }).click();
  const oldToken = await page.evaluate(() =>
    sessionStorage.getItem("yanxu-account-session-v1"),
  );
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByRole("heading", { name: "登录工作台" })).toBeVisible();
  await expect
    .poll(async () =>
      (
        await request.get("/api/auth/me", {
          headers: { Authorization: `Bearer ${oldToken}` },
        })
      ).status(),
    )
    .toBe(401);
  await page.getByLabel("账号", { exact: true }).fill(user.username);
  await page.getByLabel("密码", { exact: true }).fill(user.password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("link", { name: "声音档案", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "声音档案", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "用户管理", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByRole("cell", { name: /本地管理员/ })).toHaveCount(0);
  await expect(
    page.getByRole("cell", { name: new RegExp(user.name) }),
  ).toBeVisible();
});

test("服务端停用后清理页面并要求重新登录", async ({ page, request }) => {
  const user = await person(request);
  await login(page, user);
  await page.getByRole("link", { name: "声音档案", exact: true }).click();
  await expect(
    page.getByRole("cell", { name: new RegExp(user.name) }),
  ).toBeVisible();
  const result = await request.patch(`/api/admin/users/${user.person.id}`, {
    headers: user.headers,
    data: { active: false },
  });
  expect(result.status()).toBe(200);
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(page.getByRole("heading", { name: "登录工作台" })).toBeVisible();
  await expect(
    page.getByRole("cell", { name: new RegExp(user.name) }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("yanxu-account-session-v1"),
    ),
  ).toBeNull();
});

test("声音登记需本人三项确认，真实私有上传后可撤回", async ({
  page,
  request,
}) => {
  const user = await person(request);
  await login(page, user);
  await page.getByRole("link", { name: "声音档案", exact: true }).click();
  await page.getByRole("button", { name: "登记", exact: true }).click();
  await page.getByLabel("选择本人声音（WAV）").setInputFiles({
    name: "identity-ui-synthetic.wav",
    mimeType: "audio/wav",
    buffer: wav(),
  });
  const save = page.getByRole("button", { name: "保存声音档案" });
  await expect(save).toBeDisabled();
  await check(page, `本人确认姓名为“${user.name}”`);
  await check(page, "已试听，确认是本人声音");
  await expect(save).toBeDisabled();
  await check(page, "本人同意将此声音保存为云端档案，用于会议发言识别");
  await page.screenshot({
    path: resolve(evidence, "account-private-enrollment.png"),
    fullPage: true,
  });
  await save.click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByText("等待生成", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "撤回", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "撤回", exact: true })
    .click();
  await expect(
    page.getByRole("cell", { name: "已撤回", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: resolve(evidence, "account-voice-revoked.png"),
    fullPage: true,
  });
  const anonymous = await request.get(
    `/api/people/${user.person.id}/voice-profile/audio`,
  );
  expect(anonymous.status()).toBe(401);
});

test("手机与平板布局不撑宽，管理操作可达", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.getByRole("link", { name: "用户管理", exact: true }).click();
  await expect(page.getByRole("button", { name: "新增用户" })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-mobile.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "新增用户" }).click();
  await expect(page.getByLabel("姓名", { exact: true })).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-mobile-dialog.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await page.setViewportSize({ width: 820, height: 1180 });
  await page.getByRole("link", { name: "部门管理", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "部门管理", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".el-tree")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-tablet.png"),
    fullPage: true,
  });
});

test("公共记录入口与具名工作台分开，匿名逐字稿只显示编号", async ({
  page,
  request,
}) => {
  const headers = await adminHeaders(request);
  const response = await request.get("/api/managed/recordings", { headers });
  expect(response.status()).toBe(200);
  const records = (await response.json()).items as {
    id: string;
    title: string;
  }[];
  let record: { id: string; title: string } | undefined;
  let speakers: string[] = [];
  for (const candidate of records) {
    const detail = await request.get(
      `/api/managed/recordings/${candidate.id}`,
      { headers },
    );
    const data = await detail.json();
    if (
      data.transcript?.segments?.some(
        (s: { speaker: string | null }) =>
          s.speaker && !s.speaker.startsWith("说话人"),
      )
    ) {
      record = candidate;
      speakers = data.transcript.segments
        .map((s: { speaker: string | null }) => s.speaker)
        .filter(Boolean);
      break;
    }
  }
  expect(record, "隔离API应先准备带具名逐字稿的受保护录音").toBeTruthy();
  await page.goto("/");
  await page.getByRole("link", { name: "账号工作台", exact: true }).click();
  await expect(page.getByRole("heading", { name: "登录工作台" })).toBeVisible();
  const publicResponse = await request.get(`/api/recordings/${record!.id}`);
  const publicData = await publicResponse.json();
  expect(publicData.participants).toBeUndefined();
  for (const segment of publicData.transcript.segments) {
    expect(segment.personId).toBeUndefined();
    expect(
      segment.speaker === null || /^说话人 \d+$/.test(segment.speaker),
    ).toBeTruthy();
  }
  await page.goto(`/#/records/${record!.id}`);
  await page.getByRole("button", { name: "逐字稿", exact: true }).click();
  await expect(
    page.getByText("说话人 1", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-public-numbered-transcript.png"),
    fullPage: true,
  });
  await login(page);
  await page.getByRole("link", { name: "我的录音", exact: true }).click();
  await page.locator(`[data-record-id="${record!.id}"]`).click();
  await expect(
    page.getByText(speakers[0]!, { exact: true }).first(),
  ).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "account-protected-named-transcript.png"),
    fullPage: true,
  });
});

test("识别人状态响应投影：等待和失败均保留逐字稿", async ({
  page,
  request,
}) => {
  const headers = await adminHeaders(request);
  const listed = await request.get("/api/managed/recordings", { headers });
  const record = (await listed.json()).items.find(
    (row: { transcript?: { segments: unknown[] } }) =>
      row.transcript?.segments.length,
  ) as { id: string; title: string } | undefined;
  if (!record) throw new Error("需要先准备可读逐字稿");
  let state = "waiting";
  // Only this state-rendering check overrides a response field; the seven other cases use real API results.
  await page.route(`**/api/managed/recordings/${record.id}`, async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    await route.fulfill({ response, json: { ...data, speakerStatus: state } });
  });
  await login(page);
  await page.locator(`[data-record-id="${record.id}"]`).click();
  await expect(page.getByText("正在识别发言人", { exact: true })).toBeVisible();
  state = "failed";
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(
    page.getByText("发言人识别未完成，逐字稿已保留", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("正在识别发言人", { exact: true })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("heading", { name: "逐字稿", exact: true }),
  ).toBeVisible();
});

test("用户维护员的声音页仅展示服务端授权档案", async ({ page, request }) => {
  const headers = await adminHeaders(request);
  const role = await request.post("/api/admin/roles", {
    headers,
    data: {
      name: "目录维护" + randomUUID().slice(0, 6),
      permissions: ["users"],
    },
  });
  expect(role.status()).toBe(200);
  const roleId = (await role.json()).id;
  const user = await person(request, roleId);
  await login(page, user);
  await page.getByRole("link", { name: "用户管理", exact: true }).click();
  await expect(page.getByRole("cell", { name: /本地管理员/ })).toBeVisible();
  await page.getByRole("link", { name: "声音档案", exact: true }).click();
  await expect(
    page.getByRole("cell", { name: new RegExp(user.name) }),
  ).toBeVisible();
  await expect(page.getByRole("cell", { name: /本地管理员/ })).toHaveCount(0);
  await page.getByRole("link", { name: "用户管理", exact: true }).click();
  expect(
    (
      await request.patch(`/api/admin/roles/${roleId}`, {
        headers,
        data: { permissions: [] },
      })
    ).status(),
  ).toBe(200);
  await page.getByRole("button", { name: "刷新", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "用户管理", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByRole("cell", { name: /本地管理员/ })).toHaveCount(0);
});
