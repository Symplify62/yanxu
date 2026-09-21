import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";
test("真实服务：匿名列表、逐字稿、分析、播放、下载与刷新", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const list = await (await request.get("/api/recordings")).json();
  const item = list.items.find(
    (x: any) => x.status === "complete" && x.analysis && x.transcript,
  );
  expect(item).toBeTruthy();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "公共记录" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("演示控制");
  await page.screenshot({
    path: "../.local-data/evidence/web/list-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", {
      name: new RegExp(item.title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")),
    })
    .click();
  await expect(page.locator(".p1-summary")).toHaveText(item.analysis.summary);
  await page.screenshot({
    path: "../.local-data/evidence/web/detail-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "逐字稿", exact: true }).click();
  await expect(page.locator(".p1-transcript")).toHaveCount(
    item.transcript.segments.length,
  );
  await page.getByRole("button", { name: "原始录音", exact: true }).click();
  const audio = page.locator("audio");
  await expect
    .poll(() => audio.evaluate((el: HTMLAudioElement) => el.readyState))
    .toBeGreaterThanOrEqual(1);
  expect(
    await audio.evaluate((el: HTMLAudioElement) => el.duration),
  ).toBeCloseTo(item.duration, 0);
  await audio.evaluate((el: HTMLAudioElement) => el.play());
  await expect
    .poll(() => audio.evaluate((el: HTMLAudioElement) => el.currentTime))
    .toBeGreaterThan(0);
  await audio.evaluate((el: HTMLAudioElement) => el.pause());
  const range = await request.get(`/api/recordings/${item.id}/audio`, {
    headers: { Range: "bytes=0-43" },
  });
  expect(range.status()).toBe(206);
  expect((await range.body()).length).toBe(44);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "下载录音", exact: true }).click();
  const download = await downloadPromise;
  await download.saveAs("../.local-data/evidence/web/downloaded.wav");
  const payload = await (
    await request.get(`/api/recordings/${item.id}/audio?download=true`)
  ).body();
  expect(createHash("sha256").update(payload).digest("hex")).toBe(item.sha256);
  await page.reload();
  await expect(page.locator(".p1-summary")).toHaveText(item.analysis.summary);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../.local-data/evidence/web/detail-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
