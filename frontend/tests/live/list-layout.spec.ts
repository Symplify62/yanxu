import { test, expect } from "@playwright/test";

const records = Array.from({ length: 24 }, (_, i) => ({
  id: `layout-${i}`,
  title: `布局验收记录 ${String(i).padStart(2, "0")}`,
  createdAt: 1789948800000 - i * 60000,
  duration: 120,
  status: i === 0 ? "queued" : "complete",
  hasAudio: false,
  transcript: null,
  analysis: null,
}));

test.beforeEach(async ({ page }) => {
  await page.route("**/api/recordings?**", async (route) => {
    const query = new URL(route.request().url()).searchParams;
    const items = records.filter(
      (r) =>
        r.title.includes(query.get("q") || "") &&
        (query.get("filter") === "complete"
          ? r.status === "complete"
          : query.get("filter") === "processing"
            ? r.status !== "complete"
            : true),
    );
    await route.fulfill({ json: { items, total: items.length } });
  });
});

for (const width of [320, 390, 768, 1280]) {
  test(`嵌入列表 ${width}：无重复标题、工具栏紧凑吸顶、筛选可用`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 740 });
    await page.goto("/?app=1");
    await expect(page.locator(".p1-result-row")).toHaveCount(24);
    await expect(
      page.getByRole("heading", { name: "公共记录", exact: true }),
    ).toHaveCount(0);
    const toolbar = page.locator(".p1-list-toolbar");
    const first = await toolbar.boundingBox();
    expect(first!.y).toBeCloseTo(0, 0);
    expect(first!.height).toBeLessThanOrEqual(width <= 650 ? 108 : 64);
    expect(
      (await page
        .getByRole("button", { name: "全部记录", exact: true })
        .boundingBox())!.height,
    ).toBeGreaterThanOrEqual(44);
    await expect(page.getByRole("status")).toHaveText("24 条");
    await page.screenshot({
      path: `../.local-data/evidence/list-layout/${width}-top.png`,
    });
    const rowTop = (await page.locator(".p1-result-row").first().boundingBox())!
      .y;
    await page.mouse.wheel(0, 700);
    await expect
      .poll(
        async () =>
          (await page.locator(".p1-result-row").first().boundingBox())!.y,
      )
      .toBeLessThan(rowTop - 400);
    expect((await toolbar.boundingBox())!.y).toBeCloseTo(first!.y, 0);
    await page.screenshot({
      path: `../.local-data/evidence/list-layout/${width}-scrolled.png`,
    });
    await page.getByRole("button", { name: "已完成", exact: true }).click();
    await expect(page.locator(".p1-result-row")).toHaveCount(23);
    const search = page.getByRole("textbox", { name: "搜索公共记录" });
    await search.fill("记录 05");
    await expect(page.locator(".p1-result-row")).toHaveCount(1);
    await search.fill("不存在");
    await expect(
      page.getByRole("heading", { name: "没有符合条件的记录" }),
    ).toBeVisible();
    await expect(toolbar).toBeVisible();
    await page.getByRole("button", { name: "清除筛选", exact: true }).click();
    await expect(page.locator(".p1-result-row")).toHaveCount(24);
    await expect(search).toHaveValue("");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}

test("窄WebView放大文字后控件换行，不撑宽页面", async ({ page }) => {
  await page.setViewportSize({ width: 280, height: 640 });
  await page.goto("/?app=1");
  await expect(page.locator(".p1-result-row")).toHaveCount(24);
  await page.addStyleTag({
    content:
      ".p1-results.is-live .p1-filters button { font-size: 20px; line-height: 28px; }",
  });
  await expect(
    page.getByRole("button", { name: "处理中 / 异常", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(
    (await page.locator(".p1-list-toolbar").boundingBox())!.height,
  ).toBeGreaterThan(108);
  await page.screenshot({
    path: "../.local-data/evidence/list-layout/large-type.png",
  });
});

test("独立网页保留页面标题，加载时工具栏不消失", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "公共记录", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".p1-result-row")).toHaveCount(24);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/recordings?**", async (route) => {
    await gate;
    await route.fulfill({ json: { items: [], total: 0 } });
  });
  await page.getByRole("textbox", { name: "搜索公共记录" }).fill("延迟响应");
  await expect(page.locator(".p1-list-toolbar")).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("…");
  release();
  await expect(
    page.getByRole("heading", { name: "没有符合条件的记录" }),
  ).toBeVisible();
});
