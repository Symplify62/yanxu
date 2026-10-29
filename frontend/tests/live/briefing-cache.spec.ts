import { test, expect } from "@playwright/test";

test("preview generates all sections once and displays selected sections", async ({
  page,
  request,
}) => {
  const response = await request.get(
    "/api/recordings?filter=complete&limit=30",
  );
  const data = await response.json();
  const record = data.items.find((item: { id: string }) => item.id);
  expect(record).toBeTruthy();
  let calls = 0;
  await page.route("**/briefings/preview", async (route) => {
    calls++;
    const body = route.request().postDataJSON();
    expect(body.sections).toHaveLength(10);
    await route.fulfill({
      json: {
        engine: "ai-briefing-v1:test",
        sections: body.sections.map((id: string) => ({
          id,
          title: `Section ${id}`,
          lines: [`Content ${id}`],
          evidence: [],
        })),
      },
    });
  });
  await page.goto(`/public.html#/records/${record.id}`);
  await expect(
    page
      .getByRole("navigation", { name: "结果内容" })
      .getByRole("button", { name: "AI 分析", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "个性化纪要", exact: true }).click();
  await expect(page.locator(".p1-briefing-template-summary")).toHaveCount(0);
  await page.getByRole("button", { name: "预览纪要", exact: true }).click();
  await expect(
    page.getByText("Content summary", { exact: true }),
  ).toBeVisible();
  const option = page
    .locator(".p1-briefing-option")
    .filter({ hasText: "风险与阻塞" });
  const wasSelected = (await option.getAttribute("aria-pressed")) === "true";
  const previousPreview = await page
    .locator(".p1-briefing-section")
    .allTextContents();
  await option.click();
  await expect(page.locator(".p1-briefing-section")).toHaveText(
    previousPreview,
  );
  await expect(page.getByText("尚未生成纪要", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "预览纪要", exact: true }).click();
  if (wasSelected)
    await expect(page.getByText("Content risks", { exact: true })).toHaveCount(
      0,
    );
  else
    await expect(
      page.getByText("Content risks", { exact: true }),
    ).toBeVisible();
  expect(calls).toBe(1);
  const order = page.locator(".p1-briefing-order .section-order-row");
  const firstId = await order.first().getAttribute("data-section-id");
  const contentBeforeDrag = await page
    .locator(".p1-briefing-section")
    .allTextContents();
  await order.last().scrollIntoViewIfNeeded();
  const handle = await order.first().getByRole("button").boundingBox();
  const destination = await order.last().boundingBox();
  await page.mouse.move(
    handle!.x + handle!.width / 2,
    handle!.y + handle!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(
    destination!.x + destination!.width / 2,
    destination!.y + destination!.height / 2,
    { steps: 10 },
  );
  await expect(page.locator(".section-order-floating")).toBeVisible();
  await page.screenshot({ path: "../.local-data/evidence/section-order-dragging.png" });
  await page.mouse.up();
  await expect(page.locator(".section-order-floating")).toHaveCount(0);
  await expect(order.last()).toHaveAttribute("data-section-id", firstId!);
  await expect(page.locator(".p1-briefing-section")).toHaveText(
    contentBeforeDrag,
  );
  await page.getByRole("button", { name: "预览纪要", exact: true }).click();
  await expect(page.locator(".p1-briefing-section").last()).toContainText(
    `Content ${firstId}`,
  );
  expect(calls).toBe(1);
  await page.screenshot({
    path: "../.local-data/evidence/briefing-cache.png",
    fullPage: true,
  });
  await page.goto("/public.html#/templates");
  await expect(
    page.locator(".p1-template-list .p1-briefing-template-tags").first(),
  ).toBeVisible();
  await page
    .locator(".p1-template-card-actions")
    .first()
    .getByRole("button", { name: "套用", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "恢复模板组合", exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".p1-template-section-picker button").first(),
  ).toContainText("1. 基础信息");
  const templateOrder = page.locator(".p1-template-order .section-order-row");
  const templateFirst = await templateOrder
    .first()
    .getAttribute("data-section-id");
  const templateHandle = templateOrder.first().getByRole("button");
  await templateOrder.last().scrollIntoViewIfNeeded();
  const from = await templateHandle.boundingBox();
  const to = await templateOrder.last().boundingBox();
  await page.mouse.move(from!.x + from!.width / 2, from!.y + from!.height / 2);
  await page.mouse.down();
  await page.mouse.move(to!.x + to!.width / 2, to!.y + to!.height / 2, {
    steps: 10,
  });
  await page.mouse.up();
  await expect(templateOrder.last()).toHaveAttribute(
    "data-section-id",
    templateFirst!,
  );
  await page.screenshot({
    path: "../.local-data/evidence/template-summary.png",
    fullPage: true,
  });
});
