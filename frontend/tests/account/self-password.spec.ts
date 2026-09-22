import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";

const administrator = JSON.parse(
  readFileSync(
    resolve("../.local-data/evidence/identity-voice/credentials.json"),
    "utf8",
  ),
);
const evidence = resolve("../.local-data/evidence/self-password");
async function member(request: APIRequestContext) {
  const signed = await request.post("/api/auth/login", { data: administrator });
  expect(signed.status()).toBe(200);
  const headers = {
    Authorization: `Bearer ${(await signed.json()).accessToken}`,
  };
  const user = {
    username: `self-${randomUUID().slice(0, 8)}`,
    password: "123456",
    name: "个人设置验证",
    roleId: "member",
  };
  const response = await request.post("/api/admin/users", {
    headers,
    data: user,
  });
  expect(response.status()).toBe(200);
  return { ...user, id: (await response.json()).id, headers };
}
async function login(page: Page, username: string, password: string) {
  await page.goto("/account.html");
  await page.getByLabel("账号", { exact: true }).fill(username);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(
    page.getByRole("navigation", { name: "工作台导航" }),
  ).toBeVisible();
}
async function fill(
  page: Page,
  oldPassword: string,
  newPassword: string,
  confirmPassword = newPassword,
) {
  await page.getByLabel("旧密码", { exact: true }).fill(oldPassword);
  await page.getByLabel("新密码", { exact: true }).fill(newPassword);
  await page.getByLabel("确认新密码", { exact: true }).fill(confirmPassword);
}
test.beforeEach(async ({ baseURL }) => {
  expect(new URL(baseURL!).hostname).toBe("127.0.0.1");
});

test("普通用户自助改密：校验旧密码、六位密码及全部会话失效", async ({
  page,
  request,
}) => {
  const user = await member(request);
  const signed = await request.post("/api/auth/login", {
    data: { username: user.username, password: user.password },
  });
  expect(signed.status()).toBe(200);
  const otherSession = {
    Authorization: `Bearer ${(await signed.json()).accessToken}`,
  };
  await login(page, user.username, user.password);
  await expect(
    page.getByRole("link", { name: "用户管理", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "个人设置", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "修改密码", exact: true }),
  ).toBeVisible();
  const oldSession = await page.evaluate(() =>
    sessionStorage.getItem("yanxu-account-session-v1"),
  );
  await fill(page, "wrong6", "abcdef");
  await page.getByRole("button", { name: "修改密码", exact: true }).click();
  await expect(page.getByText("旧密码不正确", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "工作台导航" }),
  ).toBeVisible();
  await expect(page.getByLabel("新密码", { exact: true })).toHaveValue(
    "abcdef",
  );
  await page.screenshot({
    path: resolve(evidence, "wrong-old-password.png"),
    fullPage: true,
  });
  await fill(page, user.password, "12345");
  await page.getByRole("button", { name: "修改密码", exact: true }).click();
  await expect(page.getByText("新密码至少6位", { exact: true })).toBeVisible();
  await fill(page, user.password, "abcdef", "abcdeg");
  await page.getByRole("button", { name: "修改密码", exact: true }).click();
  await expect(
    page.getByText("两次输入的新密码不一致", { exact: true }),
  ).toBeVisible();
  await fill(page, user.password, "abcdef");
  await page.screenshot({
    path: resolve(evidence, "settings-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "修改密码", exact: true }).click();
  await expect(page.getByRole("heading", { name: "登录工作台" })).toBeVisible();
  await expect(page.locator(".el-alert--success")).toHaveText(
    /密码已修改，请重新登录/,
  );
  await expect(page.getByLabel("密码", { exact: true })).toHaveValue("");
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("yanxu-account-session-v1"),
    ),
  ).toBeNull();
  expect(
    (await request.get("/api/auth/me", { headers: otherSession })).status(),
  ).toBe(401);
  expect(
    (
      await request.get("/api/auth/me", {
        headers: { Authorization: `Bearer ${oldSession}` },
      })
    ).status(),
  ).toBe(401);
  expect(
    (
      await request.post("/api/auth/login", {
        data: { username: user.username, password: user.password },
      })
    ).status(),
  ).toBe(401);
  await page.screenshot({
    path: resolve(evidence, "changed-login-success.png"),
    fullPage: true,
  });
  await login(page, user.username, "abcdef");
});

test("手机和平板个人设置可操作，离开页面清理密码输入", async ({
  page,
  request,
}) => {
  const user = await member(request);
  await login(page, user.username, user.password);
  for (const [name, width, height] of [
    ["mobile", 390, 844],
    ["tablet", 820, 1180],
  ] as const) {
    await page.setViewportSize({ width, height });
    await page.getByRole("link", { name: "个人设置", exact: true }).click();
    await fill(page, user.password, "!!!!!!");
    await expect(
      page.getByRole("button", { name: "修改密码", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: resolve(evidence, `settings-${name}.png`),
      fullPage: true,
    });
    await page.getByRole("link", { name: "我的录音", exact: true }).click();
    await page.getByRole("link", { name: "个人设置", exact: true }).click();
    await expect(page.getByLabel("旧密码", { exact: true })).toHaveValue("");
    await expect(page.getByLabel("新密码", { exact: true })).toHaveValue("");
    await expect(page.getByLabel("确认新密码", { exact: true })).toHaveValue(
      "",
    );
  }
});

test("账号被停用后不能提交改密，回到登录且不保留输入", async ({
  page,
  request,
}) => {
  const user = await member(request);
  await login(page, user.username, user.password);
  await page.getByRole("link", { name: "个人设置", exact: true }).click();
  await fill(page, user.password, "abcdef");
  expect(
    (
      await request.patch(`/api/admin/users/${user.id}`, {
        headers: user.headers,
        data: { active: false },
      })
    ).status(),
  ).toBe(200);
  await page.getByRole("button", { name: "修改密码", exact: true }).click();
  await expect(page.getByRole("heading", { name: "登录工作台" })).toBeVisible();
  await expect(page.getByLabel("密码", { exact: true })).toHaveValue("");
  await expect(
    page.getByText("登录已失效，请重新登录", { exact: true }),
  ).toBeVisible();
});
