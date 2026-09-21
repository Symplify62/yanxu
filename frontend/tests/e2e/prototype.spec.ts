import { test, expect, type Page } from "@playwright/test";
async function employeeLogin(page: Page) {
  await page.getByRole("link", { name: "员工手机端", exact: true }).click();
  await page
    .getByRole("button", { name: "模拟企业微信登录", exact: true })
    .click();
  await expect(page).toHaveURL(/\/employee$/);
  await expect(page.locator(".meeting-list-item").first()).toBeVisible();
}
async function record(page: Page) {
  await page.getByRole("button", { name: "模拟手机扫码", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "模拟企业微信扫码" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "确认模拟扫码", exact: true }).click();
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "结束并保存", exact: true }).click();
  await expect(page.getByTestId("tablet-saved")).toBeVisible();
}
async function adminLogin(page: Page) {
  await page.getByRole("link", { name: "管理后台", exact: true }).click();
  await page
    .getByRole("button", { name: "进入演示管理员", exact: true })
    .click();
  await expect(page).toHaveURL(/\/admin\/overview/);
}
async function setScenario(page: Page, value: string) {
  await page.evaluate(async (value) => {
    await fetch("/api/v1/demo/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: value }),
    });
  }, value);
}
test.beforeEach(async ({ page }) => {
  await page.goto("/tablet");
  await expect(
    page.getByRole("button", { name: "模拟手机扫码", exact: true }),
  ).toBeVisible();
});
test("正式组件完成扫码、自动退出、独立队列、手机更正不重发", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await record(page);
  const saved = page.getByTestId("tablet-saved");
  await expect(saved.getByRole("button")).toHaveCount(1);
  await expect(saved.getByRole("button")).toHaveText("下一场扫码");
  await expect(saved).not.toContainText("在手机查看");
  await expect(saved).toContainText("渠道已接收", { timeout: 18000 });
  await employeeLogin(page);
  await page.getByRole("button", { name: /新会议 · 自动整理样例/ }).click();
  await page.getByRole("button", { name: "主动更正", exact: true }).click();
  const popup = page.locator(".mobile-edit-popup:visible");
  await expect(popup).toBeVisible();
  await popup.locator('textarea[name="summary"]').fill("正式组件更正内容");
  await popup.locator('input[name="task-owner-1"]').fill("刘工");
  await popup.locator('input[name="reason"]').fill("合成原文核对");
  await popup.getByRole("button", { name: "保存更正，不重发" }).click();
  await expect(popup).toBeHidden();
  await expect(page.locator(".meeting-summary")).toContainText(
    "正式组件更正内容",
  );
  await expect(page.locator(".version-tags")).toContainText("当前 v2");
  await expect(page.locator(".version-tags")).toContainText("群快照 v1");
  const state = await page.evaluate(async () => {
    const r = await fetch("/api/v1/meetings", {
      headers: {
        "X-Demo-Session": sessionStorage.getItem("yanxu-employee") || "",
      },
    });
    return (await r.json()).data.find((m: any) => m.id === "rec-001");
  });
  expect(state.sendCount).toBe(1);
  expect(state.tasks[1].owner).toBe("刘工");
  expect(state.publication.tasks[1].owner).toBe("");
  expect(errors).toEqual([]);
});
test("扫码过期可刷新，保存故障不假退出", async ({ page }) => {
  await page.getByRole("button", { name: "模拟过期", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "模拟手机扫码", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "刷新二维码", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "模拟手机扫码", exact: true }),
  ).toBeEnabled();
  await setScenario(page, "save-failure");
  await page.getByRole("button", { name: "模拟手机扫码", exact: true }).click();
  await page.getByRole("button", { name: "确认模拟扫码", exact: true }).click();
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "结束并保存", exact: true }).click();
  await expect(page.getByText("本地保存失败", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "下一场扫码" })).toHaveCount(0);
  await page.getByRole("button", { name: "模拟修复并重试保存" }).click();
  await expect(page.getByTestId("tablet-saved")).toBeVisible();
});
test("手机共享、换人只读、撤销后旧链接拒绝", async ({ page }) => {
  await employeeLogin(page);
  await page.getByRole("button", { name: /报价与交付协调/ }).click();
  await page.getByRole("button", { name: "共享查看权", exact: true }).click();
  await page
    .locator(".mobile-edit-popup:visible")
    .getByRole("button", { name: "添加只读授权" })
    .click();
  await expect(
    page
      .locator(".mobile-edit-popup:visible")
      .getByRole("button", { name: "撤销", exact: true }),
  ).toBeVisible();
  const result = await page.evaluate(async () => {
    const owner = sessionStorage.getItem("yanxu-employee")!;
    const l = await fetch("/api/v1/auth/demo-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: "chen" }),
    });
    const viewer = (await l.json()).data.token;
    const r = await fetch("/api/v1/meetings/m1", {
      headers: { "X-Demo-Session": viewer },
    });
    const d = (await r.json()).data;
    const denied = await fetch("/api/v1/meetings/m1/revision", {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-Demo-Session": viewer },
      body: JSON.stringify({
        expectedVersion: 1,
        summary: "bad",
        tasks: [],
        reason: "bad",
      }),
    });
    const revoke = await fetch("/api/v1/meetings/m1/grants/" + d.grants[0].id, {
      method: "DELETE",
      headers: { "X-Demo-Session": owner },
    });
    const read = await fetch("/api/v1/meetings/m1", {
      headers: { "X-Demo-Session": viewer },
    });
    return {
      readBefore: r.status,
      edit: denied.status,
      revoke: revoke.status,
      readAfter: read.status,
    };
  });
  expect(result).toEqual({
    readBefore: 200,
    edit: 403,
    revoke: 200,
    readAfter: 404,
  });
  await expect(
    page
      .locator(".mobile-edit-popup:visible")
      .getByText("尚未共享", { exact: true }),
  ).toBeVisible();
});
test("AI自动重试失败后管理员接管，恢复继续自动发送", async ({ page }) => {
  await setScenario(page, "ai-failure");
  await record(page);
  await expect(page.getByTestId("tablet-saved")).toContainText(
    "处理失败，管理员接管",
    { timeout: 18000 },
  );
  await adminLogin(page);
  await page.getByRole("menuitem", { name: "异常处理", exact: true }).click();
  await page.getByRole("button", { name: "重新检查并恢复" }).click();
  await page.getByRole("button", { name: "确认恢复该阶段" }).click();
  await expect(page.getByText("请填写处理依据", { exact: true })).toBeVisible();
  await page.getByRole("textbox", { name: "处理依据" }).fill("模拟依赖恢复");
  await page.getByRole("button", { name: "确认恢复该阶段" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByText("没有需要人工接管的异常", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("menuitem", { name: "自动处理概览", exact: true })
    .click();
  await expect(
    page.locator(".el-table__row").filter({ hasText: "rec-001" }),
  ).toContainText("渠道已接收", { timeout: 15000 });
});
test("后台路由和访问组使用正式表单，取消无变更", async ({ page }) => {
  await adminLogin(page);
  await page
    .getByRole("menuitem", { name: "部门与接收群", exact: true })
    .click();
  await page
    .locator(".el-table__row")
    .filter({ hasText: "销售部" })
    .getByRole("button", { name: "配置接收群" })
    .click();
  await expect(
    page.getByRole("dialog", { name: "配置部门接收群" }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "取消", exact: true })
    .click();
  await expect(
    page.locator(".el-table__row").filter({ hasText: "销售部" }),
  ).toContainText("销售管理群（模拟）");
  await page.getByRole("menuitem", { name: "业务访问组", exact: true }).click();
  await page.getByRole("button", { name: "维护成员" }).click();
  await expect(
    page.getByRole("dialog", { name: "维护业务组成员" }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "确认成员变更" })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("menuitem", { name: "角色权限", exact: true }).click();
  await page.getByRole("button", { name: "查看权限" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
});
test("手机宽度、组件状态和权限错误页面", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await employeeLogin(page);
  await page.getByRole("button", { name: /报价与交付协调/ }).click();
  await expect(page.locator(".van-tabs")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 2,
    ),
  ).toBe(true);
  await page.getByRole("link", { name: "组件与状态", exact: true }).click();
  await page.getByRole("button", { name: "验证表单", exact: true }).click();
  await expect(page.getByText("请填写名称", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "查看确认弹窗", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "操作范围确认" }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "知道了" })
    .click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 2,
    ),
  ).toBe(true);
});
