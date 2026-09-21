import { test, expect, type Page } from "@playwright/test";
const variants = ["element", "shadcn", "tdesign"];
async function command(page: Page, action: string) {
  await page.evaluate(
    (action) =>
      window.postMessage({ type: "yanxu-design", action }, location.origin),
    action,
  );
}
async function scan(page: Page) {
  await command(page, "scan");
  await expect(
    page.getByText("模拟企业微信扫码", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "确认模拟扫码", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "开始录音", exact: true }),
  ).toBeVisible();
}
for (const variant of variants) {
  test(`${variant}: 真实组件扫码、暂停、保存退出和自动处理`, async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`/design-option.html?variant=${variant}`);
    await expect(
      page.getByRole("heading", { name: "扫码开始这场会议" }),
    ).toBeVisible();
    await expect(page.locator(".qr-wrap img")).toHaveAttribute(
      "src",
      /^data:image\/png/,
    );
    await command(page, "scan");
    await page.getByRole("button", { name: "取消", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "扫码开始这场会议" }),
    ).toBeVisible();
    await scan(page);
    await page.getByRole("button", { name: "开始录音", exact: true }).click();
    await page.getByRole("button", { name: "暂停录音", exact: true }).click();
    await expect(page.getByText("录音已暂停", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "继续录音", exact: true }).click();
    await page.getByRole("button", { name: "结束并保存", exact: true }).click();
    const saved = page.getByTestId("tablet-saved");
    await expect(saved).toBeVisible();
    await expect(saved.getByRole("button")).toHaveCount(1);
    const device = await page.evaluate(
      async () => (await (await fetch("/api/v1/device")).json()).data,
    );
    expect(device.employee).toBeNull();
    await expect(saved).toContainText("渠道已接收", { timeout: 18000 });
    await page.getByRole("button", { name: "下一场扫码", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "扫码开始这场会议" }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });
  test(`${variant}: 过期码、无效员工拒绝、保存故障恢复`, async ({ page }) => {
    await page.goto(`/design-option.html?variant=${variant}`);
    await expect(
      page.getByRole("heading", { name: "扫码开始这场会议" }),
    ).toBeVisible();
    await command(page, "expire");
    await expect(page.getByText("二维码已过期", { exact: true })).toBeVisible();
    await command(page, "scan");
    await expect(
      page.getByText("模拟企业微信扫码", { exact: true }),
    ).toBeHidden();
    await page.getByRole("button", { name: "刷新二维码", exact: true }).click();
    await expect(page.getByText("二维码已过期", { exact: true })).toHaveCount(
      0,
    );
    await command(page, "scan");
    const select = page.locator(
      variant === "element"
        ? ".scan-dialog-body .el-select__wrapper"
        : variant === "tdesign"
          ? ".scan-dialog-body .t-input"
          : ".scan-dialog-body [role=combobox]",
    );
    await select.click();
    await page.getByText("其他企业用户", { exact: true }).click();
    await page
      .getByRole("button", { name: "确认模拟扫码", exact: true })
      .click();
    await expect(page.getByRole("alert")).toBeVisible();
    await select.click();
    await page.getByText("林同事", { exact: true }).last().click();
    await page
      .getByRole("button", { name: "确认模拟扫码", exact: true })
      .click();
    await page.evaluate(async () => {
      await fetch("/api/v1/demo/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: "save-failure" }),
      });
    });
    await page.getByRole("button", { name: "开始录音", exact: true }).click();
    await page.getByRole("button", { name: "结束并保存", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "录音尚未保存成功" }),
    ).toBeVisible();
    const before = await page.evaluate(
      async () => (await (await fetch("/api/v1/device")).json()).data,
    );
    expect(before.employee).toBe("lin");
    await page
      .getByRole("button", { name: "模拟修复并重试保存", exact: true })
      .click();
    await expect(page.getByTestId("tablet-saved")).toBeVisible();
  });
  test(`${variant}: 平板与窄屏布局`, async ({ page }) => {
    for (const width of [1280, 768, 390]) {
      await page.setViewportSize({ width, height: 960 });
      await page.goto(`/design-option.html?variant=${variant}`);
      await expect(page.locator(".qr-wrap img")).toHaveAttribute(
        "src",
        /^data:image\/png/,
      );
      const dimensions = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width);
      await page.screenshot({
        path: `evidence/design-lab/${variant}-${width}.png`,
        fullPage: true,
      });
    }
  });
}
test("对比容器切换样式、外部模拟入口、重置", async ({ page }) => {
  await page.goto("/design-lab.html");
  for (const name of ["温润 · Element Plus", "克制 · shadcn/vue"]) {
    await page.getByRole("tab", { name }).click();
    await expect(
      page.getByRole("button", { name: "模拟扫码登录" }),
    ).toBeEnabled();
    await page.getByRole("tab", { name }).click();
    await expect(
      page.getByRole("button", { name: "模拟扫码登录" }),
    ).toBeEnabled();
    await page.getByRole("button", { name: "模拟扫码登录" }).click();
    const frame = page.frameLocator("iframe");
    await frame
      .getByRole("button", { name: "确认模拟扫码", exact: true })
      .click();
    await expect(
      frame.getByRole("button", { name: "开始录音", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "重新体验" }).click();
    await expect(
      frame.getByRole("heading", { name: "扫码开始这场会议" }),
    ).toBeVisible();
  }
});
