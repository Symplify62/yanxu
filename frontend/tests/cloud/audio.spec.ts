import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

test("真实七牛：页面原音、HTTPS跳转、Range和下载校验", async ({
  page,
  request,
}) => {
  const list = await (await request.get("/api/recordings")).json();
  const item = list.items.find((x: any) => x.title === "云存储合成测试");
  expect(item).toBeTruthy();
  const redirect = await request.get(`/api/recordings/${item.id}/audio`, {
    maxRedirects: 0,
  });
  expect(redirect.status()).toBe(307);
  const remote = redirect.headers().location;
  expect(remote).toMatch(/^https:\/\/audio\.qjl666\.xyz\/recordings\//);
  const responses: string[] = [];
  page.on("response", (r) => {
    if (r.url().startsWith(remote)) responses.push(r.url());
  });
  await page.goto(`/#/records/${item.id}`);
  await page.getByRole("button", { name: "原始录音", exact: true }).click();
  const audio = page.locator("audio");
  await expect
    .poll(() => audio.evaluate((el: HTMLAudioElement) => el.readyState))
    .toBeGreaterThanOrEqual(1);
  expect(
    await audio.evaluate((el: HTMLAudioElement) => el.duration),
  ).toBeCloseTo(1, 1);
  await audio.evaluate((el: HTMLAudioElement) => el.play());
  await expect
    .poll(() => audio.evaluate((el: HTMLAudioElement) => el.currentTime))
    .toBeGreaterThan(0);
  expect(responses.length).toBeGreaterThan(0);
  const range = await request.get(`/api/recordings/${item.id}/audio`, {
    headers: { Range: "bytes=0-43" },
  });
  expect(range.status()).toBe(206);
  expect((await range.body()).length).toBe(44);
  const downloadEvent = page.waitForEvent("download");
  await page.getByRole("link", { name: "下载录音", exact: true }).click();
  const download = await downloadEvent;
  const path = "../.local-data/evidence/cloud-browser/download.wav";
  await download.saveAs(path);
  expect(
    createHash("sha256")
      .update(await readFile(path))
      .digest("hex"),
  ).toBe(item.sha256);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../.local-data/evidence/cloud-browser/audio-mobile.png",
    fullPage: true,
  });
});
