import { test, expect, type Page } from "@playwright/test";
async function controls(page: Page) {
  if (
    (await page
      .getByRole("button", { name: "演示控制", exact: true })
      .getAttribute("aria-expanded")) === "false"
  )
    await page.getByRole("button", { name: "演示控制", exact: true }).click();
}
async function scenario(page: Page, label: string) {
  await controls(page);
  await page
    .getByRole("combobox", { name: "演示场景" })
    .locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]')
    .click();
  await page.getByRole("option", { name: label, exact: true }).click();
}
async function record(page: Page) {
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "结束并保存", exact: true }).click();
  await page.getByRole("button", { name: "查看本次结果", exact: true }).click();
}
async function snap(page: Page, name: string) {
  await page.screenshot({
    path: `evidence/phase-one/${name}.png`,
    fullPage: true,
  });
}
test("阶段一页面: 根入口免登录录音，分步结果、详情链接与刷新保留", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page).toHaveURL(/phase-one.html/);
  await expect(
    page.getByRole("button", { name: "开始录音", exact: true }),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText("扫码");
  await expect(page.getByRole("button", { name: "管理后台" })).toHaveCount(0);
  await snap(page, "record-desktop");
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "暂停录音", exact: true }).click();
  await expect(page.getByText("录音已暂停", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "公共记录", exact: true }).click();
  await page.getByRole("button", { name: "快速录音", exact: true }).click();
  await page.getByRole("button", { name: "继续录音", exact: true }).click();
  await snap(page, "recording");
  await page.getByRole("button", { name: "结束并保存", exact: true }).click();
  await expect(
    page.getByText("正在保存本次录音", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "查看本次结果", exact: true }).click();
  await expect(page).toHaveURL(/#\/records\//);
  await page.getByRole("button", { name: "先看逐字稿", exact: true }).click();
  await expect(page.locator(".p1-transcript")).toHaveCount(3);
  await snap(page, "transcript-processing");
  await expect(page.locator(".p1-detail-aside")).toContainText("已完成");
  await page.getByRole("button", { name: "AI 分析", exact: true }).click();
  await expect(page.locator(".p1-summary")).toBeVisible();
  await snap(page, "detail-desktop");
  await page.getByRole("button", { name: "行动事项", exact: true }).click();
  await expect(page.locator(".p1-task")).toHaveCount(2);
  await snap(page, "tasks");
  await page.getByRole("button", { name: "复制结果链接", exact: true }).click();
  const link = await page
    .getByRole("textbox", { name: "结果链接地址" })
    .inputValue();
  expect(link).toBe(page.url());
  await expect(page.getByRole("dialog")).toContainText("暂不支持跨设备");
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await page.reload();
  await expect(page.locator(".p1-summary")).toBeVisible();
  await page.getByRole("button", { name: "公共记录", exact: true }).click();
  await expect(page.locator(".p1-result-row")).toHaveCount(3);
  await snap(page, "list-desktop");
  expect(errors).toEqual([]);
});
test("阶段一页面: 录音不可用和保存失败不假成功", async ({ page }) => {
  await page.goto("/phase-one.html");
  await scenario(page, "录音不可用");
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("录音暂不可用");
  await snap(page, "capture-error");
  await scenario(page, "保存失败");
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "结束并保存", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "录音尚未保存成功" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "查看本次结果", exact: true }),
  ).toHaveCount(0);
  await snap(page, "save-error");
  await page
    .getByRole("button", { name: "重试保存（演示）", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "查看本次结果", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "开始下一段录音", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "开始录音", exact: true }),
  ).toBeVisible();
});
for (const [label, status, file] of [
  ["上传等待网络", "等待网络", "offline"],
  ["转写失败", "转写未完成", "transcript-error"],
  ["AI 分析失败", "分析未完成", "analysis-error"],
]) {
  test(`阶段一页面: ${label}恢复且不伪造结果`, async ({ page }) => {
    await page.goto("/phase-one.html");
    await scenario(page, label!);
    await record(page);
    await expect(page.locator(".p1-detail-aside")).toContainText(status!);
    await expect(page.locator(".p1-summary")).toHaveCount(0);
    await snap(page, file!);
    if (file === "analysis-error") {
      await page
        .getByRole("button", { name: "先看逐字稿", exact: true })
        .click();
      await expect(page.locator(".p1-transcript")).toHaveCount(3);
    }
    await page
      .getByRole("button", { name: "恢复异常（演示）", exact: true })
      .click();
    await expect(page.locator(".p1-detail-aside")).toContainText("已完成");
    await page.getByRole("button", { name: "AI 分析", exact: true }).click();
    await expect(page.locator(".p1-summary")).toBeVisible();
  });
}
test("阶段一页面: 搜索、筛选、空态、无效链接和手机布局", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/phase-one.html");
  await snap(page, "record-mobile");
  await page.getByRole("button", { name: "公共记录", exact: true }).click();
  await expect(page.locator(".p1-result-row")).toHaveCount(2);
  await snap(page, "list-mobile");
  await page.getByRole("textbox", { name: "搜索公共记录" }).fill("没有这场");
  await expect(
    page.getByRole("heading", { name: "没有符合条件的记录" }),
  ).toBeVisible();
  await snap(page, "no-matches");
  await page.getByRole("button", { name: "清除筛选" }).click();
  await page.getByRole("button", { name: /产品周会/ }).click();
  await expect(page.locator(".p1-summary")).toBeVisible();
  await snap(page, "detail-mobile");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.goto("/phase-one.html#/records/invalid");
  await expect(
    page.getByRole("heading", { name: "这条记录暂时不可用" }),
  ).toBeVisible();
  await snap(page, "unavailable");
  await controls(page);
  await page.getByRole("button", { name: "查看空列表", exact: true }).click();
  await expect(page.getByRole("heading", { name: "暂无记录" })).toBeVisible();
  await snap(page, "empty");
  await page
    .getByRole("button", { name: "开始第一段录音", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "开始录音", exact: true }),
  ).toBeVisible();
});
