import { test, expect, type Page } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";

const credentials = JSON.parse(
  readFileSync(
    resolve("../.local-data/evidence/identity-voice/credentials.json"),
    "utf8",
  ),
);
const evidence = resolve("../.local-data/evidence/admin-production-20261005");
mkdirSync(evidence, { recursive: true });
async function login(page: Page, values = credentials) {
  await page.goto("/account.html");
  await page.getByLabel("账号", { exact: true }).fill(values.username);
  await page.getByLabel("密码", { exact: true }).fill(values.password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("button", { name: "退出登录" })).toBeVisible();
}

test("管理员全局入口、访客上传中记录、搜索与详情", async ({
  page,
  request,
}) => {
  const title = "发布隔离录音-" + randomUUID().slice(0, 8);
  const created = await request.post("/api/recordings", {
    data: {
      client_id: randomUUID(),
      title,
      total_bytes: 128,
      sha256: "a".repeat(64),
      extension: "wav",
    },
  });
  expect(created.status()).toBe(200);
  await login(page);
  await expect(page).toHaveURL(/#\/overview$/);
  await expect(
    page.getByRole("link", { name: "我的录音", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "个人设置", exact: true }),
  ).toHaveCount(0);
  await page.locator("a.overview-card[href='#/all-recordings']").click();
  await page.getByLabel("搜索录音", { exact: true }).fill(title);
  await page.getByRole("button", { name: "搜索", exact: true }).click();
  await expect(page.getByText("共 1 条录音", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("cell", { name: title, exact: true }),
  ).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "local-desktop-list.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "查看", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("录音文件尚未就绪", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("audio")).toHaveCount(0);
  await page.getByRole("button", { name: "返回列表", exact: true }).click();
  await expect(page.getByText("共 1 条录音", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "App 版本", exact: true }).click();
  await expect(page.getByText("安装包校验失败", { exact: true })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("heading", { name: "App 版本", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "local-desktop-versions.png"),
    fullPage: true,
  });
});

test("390px 管理导航和录音详情无需横向滚动", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.goto("/account.html#/all-recordings");
  await expect(page.locator(".admin-record-mobile").first()).toBeVisible();
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "local-mobile-list.png"),
    fullPage: true,
  });
  await page.locator(".admin-record-mobile").first().click();
  await expect(
    page.getByRole("heading", { name: "AI 分析", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator(".el-loading-mask")).toHaveCount(0);
  await page.screenshot({
    path: resolve(evidence, "local-mobile-detail.png"),
    fullPage: true,
  });
});

test("普通成员保留个人区且不能进入全局录音或版本管理", async ({
  page,
  request,
}) => {
  const auth = await request.post("/api/auth/login", { data: credentials });
  const headers = {
    Authorization: `Bearer ${(await auth.json()).accessToken}`,
  };
  const username = "release-" + randomUUID().slice(0, 8),
    password = randomUUID();
  const created = await request.post("/api/admin/users", {
    headers,
    data: {
      name: "发布隔离成员",
      username,
      password,
      roleId: "member",
    },
  });
  expect(created.status()).toBe(200);
  try {
    await login(page, { username, password });
    await expect(
      page.getByRole("link", { name: "我的录音", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "个人设置", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "所有录音", exact: true }),
    ).toHaveCount(0);
    await page.goto("/account.html#/all-recordings");
    await expect(page).toHaveURL(/#\/records$/);
    const token = await page.evaluate(() =>
      sessionStorage.getItem("yanxu-account-session-v1"),
    );
    for (const url of [
      "/api/admin/recordings",
      "/api/admin/overview",
      "/api/admin/app-versions",
    ]) {
      expect(
        (
          await request.get(url, {
            headers: { Authorization: `Bearer ${token}` },
          })
        ).status(),
      ).toBe(403);
      expect((await request.get(url)).status()).toBe(401);
    }
  } finally {
    await request.delete(`/api/admin/users/${(await created.json()).id}`, {
      headers,
    });
  }
});
