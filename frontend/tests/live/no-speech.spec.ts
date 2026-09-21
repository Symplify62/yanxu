import { test, expect } from "@playwright/test";
const records = [
  {
    id: "no-speech-test",
    title: "静音测试记录",
    status: "no-speech",
    interrupted: true,
    duration: 2,
    createdAt: 1789979181503,
    hasAudio: true,
    error: null,
    transcript: { noSpeech: true, text: "", segments: [] },
    analysis: null,
  },
  {
    id: "complete-test",
    title: "正常会议",
    status: "complete",
    duration: 7,
    createdAt: 1789979000000,
    hasAudio: true,
    error: null,
    transcript: { text: "已识别", segments: [] },
    analysis: { summary: "正常摘要", points: [], decisions: [], tasks: [] },
  },
  {
    id: "error-test",
    title: "处理异常记录",
    status: "transcript-error",
    duration: 7,
    createdAt: 1789978900000,
    hasAudio: true,
    error: "转写暂未完成",
    transcript: null,
    analysis: null,
  },
];
test("无语音是已处理结果：筛选、中断提示、跳过AI和原音入口", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.route("**/api/recordings**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/audio")) {
      await route.fulfill({ status: 204 });
      return;
    }
    const id = url.pathname.split("/")[3];
    if (id) {
      await route.fulfill({ json: records.find((r) => r.id === id) });
      return;
    }
    const filter = url.searchParams.get("filter");
    const items = records.filter((r) =>
      filter === "complete"
        ? ["complete", "no-speech"].includes(r.status)
        : filter === "processing"
          ? r.status === "transcript-error"
          : true,
    );
    await route.fulfill({ json: { items, total: items.length } });
  });
  await page.goto("/?app=1");
  await expect(page.locator(".p1-result-row")).toHaveCount(3);
  await expect(page.locator(".p1-status.no-speech")).toHaveText("未检测到语音");
  await expect(page.locator(".p1-status.failed")).toHaveCount(1);
  await page.getByRole("button", { name: "已完成", exact: true }).click();
  await expect(page.locator(".p1-result-row")).toHaveCount(2);
  await page.getByRole("button", { name: /静音测试记录/ }).click();
  await expect(
    page.getByText("未检测到语音", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText("录音已保留，已跳过 AI 分析。")).toBeVisible();
  await expect(page.getByText("录音曾中断，以下为已保留内容。")).toBeVisible();
  await expect(page.locator(".p1-progress, .p1-spin, .p1-error")).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("button", { name: "AI 分析", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator("audio")).toHaveAttribute(
    "src",
    "/api/recordings/no-speech-test/audio",
  );
  await expect(page.getByRole("link", { name: "下载录音" })).toHaveAttribute(
    "href",
    "/api/recordings/no-speech-test/audio?download=true",
  );
  await page.screenshot({
    path: "../.local-data/evidence/no-speech/detail-mobile.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.getByText("录音已保留，已跳过 AI 分析。")).toBeVisible();
  await page.getByRole("button", { name: "返回公共记录" }).click();
  await page
    .getByRole("button", { name: "处理中 / 异常", exact: true })
    .click();
  await expect(page.locator(".p1-result-row")).toHaveCount(1);
  await expect(page.locator(".p1-result-row")).toContainText("处理异常记录");
  await page.locator(".p1-result-row").click();
  await expect(page.getByRole("alert")).toContainText("转写暂未完成");
});
