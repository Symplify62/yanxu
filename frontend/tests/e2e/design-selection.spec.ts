import { test, expect } from "@playwright/test";
test("A方案确认: 历史入口固定A，录音与手机后台联通", async ({ page }) => {
  await page.goto("/prototype.html");
  await expect(page).toHaveURL(/\/prototype.html$/);
  await expect(
    page.getByRole("heading", { name: "言序 · 正式组件原型" }),
  ).toBeVisible();
  await expect(page.getByRole("tablist", { name: "选择设计方向" })).toHaveCount(
    0,
  );
  await expect(page.locator("iframe")).toHaveAttribute(
    "src",
    /variant=element/,
  );
  await expect(page.locator(".lab-footer")).not.toContainText("切换 A/B");
  const f = page.frameLocator("iframe");
  await expect(f.locator(".qr-wrap img")).toBeVisible();
  await page.screenshot({
    path: "evidence/design-lab/selected/tablet.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "模拟扫码登录", exact: true }).click();
  await f.getByRole("button", { name: "确认模拟扫码", exact: true }).click();
  await f.getByRole("button", { name: "开始录音", exact: true }).click();
  await f.getByRole("button", { name: "结束并保存", exact: true }).click();
  await expect(f.getByTestId("tablet-saved")).toBeVisible();
  await page.getByRole("button", { name: "员工手机端", exact: true }).click();
  await f
    .getByRole("button", { name: "模拟企业微信登录", exact: true })
    .click();
  await expect(f.locator(".meeting-item")).toHaveCount(2);
  await page.screenshot({
    path: "evidence/design-lab/selected/phone.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "管理后台", exact: true }).click();
  await f.getByRole("button", { name: "进入演示管理员", exact: true }).click();
  await expect(f.locator(".metrics-strip")).toContainText("03");
  await page.screenshot({
    path: "evidence/design-lab/selected/admin.png",
    fullPage: true,
  });
});
test("A方案确认: 分端直达、方案锁定及历史比较入口", async ({ page }) => {
  const f = page.frameLocator("iframe");
  await page.goto("/prototype.html?surface=employee&variant=shadcn");
  await expect(
    f.getByRole("button", { name: "模拟企业微信登录", exact: true }),
  ).toBeVisible();
  await expect(page.locator("iframe")).toHaveAttribute(
    "src",
    /variant=element/,
  );
  await page.goto("/prototype.html?surface=admin");
  await expect(
    f.getByRole("button", { name: "进入演示管理员", exact: true }),
  ).toBeVisible();
  await page.goto("/prototype.html?surface=components");
  await expect(
    f.getByRole("heading", { name: "组件与交互状态" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "查看历史方案对比" }).click();
  await expect(page.getByRole("tab")).toHaveCount(2);
  await expect(
    page.getByRole("link", { name: "← 打开已确认的 A 原型" }),
  ).toHaveAttribute("href", "/prototype.html");
});
