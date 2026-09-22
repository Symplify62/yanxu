import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";

const credentials = JSON.parse(
  readFileSync(
    resolve("../.local-data/evidence/identity-voice/credentials.json"),
    "utf8",
  ),
);

async function login(page: Page, username: string, password: string) {
  await page.goto("/account.html");
  await page.getByLabel("账号", { exact: true }).fill(username);
  await page.getByLabel("密码", { exact: true }).fill(password);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(
    page.getByRole("navigation", { name: "工作台导航" }),
  ).toBeVisible();
}

test("六位无组合要求：创建、重置、登录和留空保留", async ({
  page,
  request,
  baseURL,
}) => {
  // This creates disposable accounts; never run against the production host.
  expect(new URL(baseURL!).hostname).toBe("127.0.0.1");
  const username = "six-" + randomUUID().slice(0, 8);
  const name = "六位密码测试" + username.slice(-4);
  await login(page, credentials.username, credentials.password);
  await page.getByRole("link", { name: "用户管理", exact: true }).click();
  await page.getByRole("button", { name: "新增用户", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("姓名", { exact: true }).fill(name);
  await dialog.getByText("允许账号登录", { exact: true }).click();
  await dialog.getByLabel("登录账号", { exact: true }).fill(username);
  await expect(
    dialog.getByText("密码（至少6位）", { exact: true }),
  ).toBeVisible();
  await dialog.getByLabel("用户密码").fill("12345");
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(
    dialog.getByText("请填写账号和至少6位密码", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: resolve("../.local-data/evidence/password-policy/create-five-rejected.png"),
    fullPage: true,
  });
  await dialog.getByLabel("用户密码").fill("123456");
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  const signed = await request.post("/api/auth/login", {
    data: { username, password: "123456" },
  });
  expect(signed.status()).toBe(200);
  const oldHeaders = {
    Authorization: `Bearer ${(await signed.json()).accessToken}`,
  };
  await page.getByLabel("搜索用户").fill(name);
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  await expect(
    dialog.getByText("重置密码（至少6位，留空保留）", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: resolve("../.local-data/evidence/password-policy/reset-six.png"),
    fullPage: true,
  });
  await dialog.getByLabel("用户密码").fill("abcde");
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(
    dialog.getByText("请填写账号和至少6位密码", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: resolve("../.local-data/evidence/password-policy/reset-five-rejected.png"),
    fullPage: true,
  });
  await dialog.getByLabel("用户密码").fill("abcdef");
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(
    (await request.get("/api/auth/me", { headers: oldHeaders })).status(),
  ).toBe(401);
  expect(
    (
      await request.post("/api/auth/login", {
        data: { username, password: "abcdef" },
      })
    ).status(),
  ).toBe(200);
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  await dialog.getByRole("button", { name: "保存", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.getByRole("button", { name: "退出登录" }).click();
  await login(page, username, "abcdef");
  await page.screenshot({
    path: resolve("../.local-data/evidence/password-policy/login-six.png"),
    fullPage: true,
  });
});
