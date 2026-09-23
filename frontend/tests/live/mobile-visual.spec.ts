import { test, expect } from "@playwright/test";

const record = {
  id: "visual-complete",
  title: "采购与生产计划周会",
  createdAt: 1790092800000,
  duration: 1800,
  status: "complete",
  hasAudio: true,
  transcript: {
    text: "先确认交货日期。",
    segments: [
      {
        id: "s1",
        start: 0,
        end: 3,
        speaker: "说话人 1",
        text: "先确认交货日期，再调整生产计划。",
      },
    ],
  },
  analysis: {
    summary: "本周优先确认采购交期，技术部在周五前提供方案。",
    points: ["采购与生产同步排期"],
    decisions: ["周五前提交方案"],
    tasks: [],
  },
};
for (const width of [320, 390, 768, 1280]) {
  test(`结果详情 ${width}：完成状态紧凑、正文优先、内容标签可用`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 740 });
    await page.route("**/api/recordings**", (route) =>
      route.fulfill({ json: record }),
    );
    await page.goto("/?app=1#/records/visual-complete");
    await expect(page.locator(".p1-complete-status")).toHaveText("已完成");
    await expect(page.locator(".p1-progress")).toHaveCount(0);
    await expect(page.locator(".p1-summary")).toHaveText(
      record.analysis.summary,
    );
    expect((await page.locator(".p1-summary").boundingBox())!.y).toBeLessThan(
      400,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../.local-data/evidence/mobile-visual-system-20260923/web-detail-${width}.png`,
    });
    await page.getByRole("button", { name: "逐字稿", exact: true }).click();
    await expect(page.locator(".p1-transcript")).toContainText(
      "先确认交货日期",
    );
    await page.getByRole("button", { name: "原始录音", exact: true }).click();
    await expect(page.getByRole("link", { name: "下载录音" })).toBeVisible();
  });
}
test("未完成与失败记录仍保留进度及错误反馈", async ({ page }) => {
  for (const status of ["queued", "transcript-error"]) {
    await page.route("**/api/recordings**", (route) =>
      route.fulfill({
        json: {
          ...record,
          status,
          analysis: null,
          transcript: null,
          error: status.includes("error") ? "转写暂未完成" : null,
        },
      }),
    );
    await page.goto("/?app=1#/records/visual-complete");
    await expect(page.locator(".p1-progress")).toBeVisible();
    await expect(page.locator(".p1-complete-status")).toHaveCount(0);
    if (status.includes("error"))
      await expect(page.getByRole("alert")).toContainText("转写暂未完成");
    await page.unroute("**/api/recordings**");
  }
});
