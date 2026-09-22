import { test, expect, type Page } from "@playwright/test";

const entry = "/speaker-prototype.html#/record";
const archiveKey = "yanxu-speaker-prototype-v2";
const voiceDialog = (page: Page) =>
  page.getByRole("dialog", { name: "录入声音", exact: true });
const peoplePicker = (page: Page) =>
  page.getByRole("dialog", { name: "选择参会者", exact: true });
const participants = (page: Page) =>
  page.getByRole("region", { name: "常用参会者" });

async function selectedNames(page: Page) {
  const buttons = participants(page).getByRole("button", {
    name: /^取消选择/,
  });
  return Promise.all(
    (await buttons.all()).map((button) => button.getAttribute("aria-label")),
  );
}

async function saveEnrollment(page: Page, persistent = true) {
  const dialog = voiceDialog(page);
  await dialog.getByRole("button", { name: "开始录入", exact: true }).click();
  await dialog.getByRole("button", { name: "结束录入", exact: true }).click();
  const save = dialog.getByRole("button", { name: "确认保存", exact: true });
  await expect(save).toBeDisabled();
  await dialog
    .getByText("本人确认：姓名正确，录音是我的声音", { exact: true })
    .click();
  if (persistent) {
    await expect(save).toBeDisabled();
    await dialog
      .getByText("同意保存声音，用于下次会议识别", { exact: true })
      .click();
  } else {
    await expect(
      dialog.getByText("同意保存声音，用于下次会议识别", { exact: true }),
    ).toHaveCount(0);
  }
  await expect(save).toBeEnabled();
  await save.click();
  await expect(dialog).not.toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.goto(entry);
  await expect(
    page.getByRole("heading", { name: "会议录音", exact: true }),
  ).toBeVisible();
});

test("组织者可直接为未选中的成员录制声纹，录入不改变本场名单", async ({
  page,
}) => {
  await page.getByLabel("演示身份", { exact: true }).selectOption("chen");
  const before = await selectedNames(page);
  const person = participants(page).getByRole("button", {
    name: "选择周宁",
    exact: true,
  });
  await expect(person).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("button button")).toHaveCount(0);
  await participants(page)
    .getByRole("button", { name: "录制周宁的声纹", exact: true })
    .click();
  await expect(voiceDialog(page).locator(".voice-person strong")).toHaveText(
    "周宁",
  );
  await saveEnrollment(page);
  await expect(person).toContainText("声纹可用");
  await expect(person).toHaveAttribute("aria-pressed", "false");
  await expect.poll(() => selectedNames(page)).toEqual(before);
  await page.reload();
  await expect(person).toContainText("声纹可用");
  await expect(person).toHaveAttribute("aria-pressed", "false");
  await expect.poll(() => selectedNames(page)).toEqual(before);
});

test("更多人员录入目标正确，取消和保存都保留部门、搜索和未选中状态", async ({
  page,
}) => {
  const before = await selectedNames(page);
  await page.getByRole("button", { name: /^更多人员/ }).click();
  const picker = peoplePicker(page);
  await picker.getByRole("button", { name: "设计部", exact: true }).click();
  const search = picker.getByRole("textbox", { name: "搜索参会者" });
  await search.fill("周宁");
  await picker
    .getByRole("button", { name: "录制周宁的声纹", exact: true })
    .click();
  await expect(voiceDialog(page).locator(".voice-person strong")).toHaveText(
    "周宁",
  );
  await voiceDialog(page)
    .getByRole("button", { name: "取消", exact: true })
    .click();
  await expect(picker).toBeVisible();
  await expect(search).toHaveValue("周宁");
  await expect(
    picker.getByRole("button", { name: "设计部", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await picker
    .getByRole("button", { name: "录制周宁的声纹", exact: true })
    .click();
  await saveEnrollment(page);
  await expect(picker).toBeVisible();
  await expect(search).toHaveValue("周宁");
  await expect(
    picker.getByRole("button", { name: "设计部", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    picker.getByRole("button", { name: "选择周宁", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  await expect(
    picker.getByRole("button", { name: "重录周宁的声纹", exact: true }),
  ).toBeEnabled();
  await picker.getByRole("button", { name: "完成选择", exact: true }).click();
  await expect.poll(() => selectedNames(page)).toEqual(before);
});

test("已有声音也提供重录入口，放弃新录音保留原姓名、档案和名单", async ({
  page,
}) => {
  const before = await selectedNames(page);
  const savedArchive = await page.evaluate(
    (key) => localStorage.getItem(key),
    archiveKey,
  );
  await participants(page)
    .getByRole("button", { name: "重录林晓的声纹", exact: true })
    .click();
  const dialog = voiceDialog(page);
  await dialog.getByRole("button", { name: "开始录入", exact: true }).click();
  await dialog.getByRole("button", { name: "结束录入", exact: true }).click();
  await dialog.getByRole("textbox", { name: "确认姓名" }).fill("未保存的姓名");
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await page
    .getByRole("dialog", { name: "放弃这次录入？", exact: true })
    .getByRole("button", { name: "放弃录入", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  await expect(
    participants(page).getByRole("button", {
      name: "取消选择林晓",
      exact: true,
    }),
  ).toContainText("声纹可用");
  await expect(
    participants(page).getByRole("button", {
      name: "重录林晓的声纹",
      exact: true,
    }),
  ).toBeEnabled();
  expect(
    await page.evaluate((key) => localStorage.getItem(key), archiveKey),
  ).toBe(savedArchive);
  await expect.poll(() => selectedNames(page)).toEqual(before);
  await page.reload();
  await expect(
    participants(page).getByRole("button", {
      name: "取消选择林晓",
      exact: true,
    }),
  ).toContainText("声纹可用");
});

test("临时来宾即使取消参会选择也能录制声纹，无需长期保存授权", async ({
  page,
}) => {
  const before = await selectedNames(page);
  await page.getByRole("button", { name: /^更多人员/ }).click();
  const picker = peoplePicker(page);
  await picker.getByRole("button", { name: /添加临时来宾/ }).click();
  const add = page.getByRole("dialog", { name: "添加临时来宾", exact: true });
  await add.getByRole("textbox", { name: "用户姓名" }).fill("顾远");
  await add.getByRole("button", { name: "添加并选中", exact: true }).click();
  await picker
    .getByRole("button", { name: "取消选择顾远", exact: true })
    .click();
  await picker
    .getByRole("button", { name: "录制顾远的声纹", exact: true })
    .click();
  await expect(voiceDialog(page).locator(".voice-person strong")).toHaveText(
    "顾远",
  );
  await expect(voiceDialog(page).locator(".scope-tag")).toHaveText("仅本场");
  await saveEnrollment(page, false);
  await expect(
    picker.getByRole("button", { name: "重录顾远的声纹", exact: true }),
  ).toBeEnabled();
  await expect(
    picker.getByRole("button", { name: "选择顾远", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  await picker.getByRole("button", { name: "完成选择", exact: true }).click();
  await expect.poll(() => selectedNames(page)).toEqual(before);
});

test("普通成员仅能录本人声音，录音和暂停时所有可见入口保留但禁用", async ({
  page,
}) => {
  await page.getByLabel("演示身份", { exact: true }).selectOption("zhou");
  const own = participants(page).getByRole("button", {
    name: "录制周宁的声纹",
    exact: true,
  });
  await expect(own).toBeEnabled();
  await expect(
    participants(page).getByRole("button", {
      name: "录制许言的声纹",
      exact: true,
    }),
  ).toBeDisabled();
  await expect(
    participants(page).getByRole("button", {
      name: "重录林晓的声纹",
      exact: true,
    }),
  ).toBeDisabled();
  await own.click();
  await expect(voiceDialog(page).locator(".voice-person strong")).toHaveText(
    "周宁",
  );
  await voiceDialog(page)
    .getByRole("button", { name: "取消", exact: true })
    .click();
  await page.getByLabel("演示身份", { exact: true }).selectOption("lin");
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  for (const name of ["林晓", "陈默"]) {
    const button = participants(page).getByRole("button", {
      name: `重录${name}的声纹`,
      exact: true,
    });
    await expect(button).toBeVisible();
    await expect(button).toBeDisabled();
    await expect(button).toHaveAttribute("title", /结束本场会议/);
  }
  await page.getByRole("button", { name: /^添加参会者/ }).click();
  const picker = peoplePicker(page);
  const entries = picker.getByRole("button", {
    name: /^(录制|重录).+的声纹$/,
  });
  await expect(entries).toHaveCount(6);
  for (const button of await entries.all()) {
    await expect(button).toBeVisible();
    await expect(button).toBeDisabled();
    await expect(button).toHaveAttribute("title", /结束本场会议/);
  }
  await picker.getByRole("button", { name: "完成选择", exact: true }).click();
  await page.getByRole("button", { name: "暂停录音", exact: true }).click();
  await expect(
    participants(page).getByRole("button", {
      name: "重录林晓的声纹",
      exact: true,
    }),
  ).toBeDisabled();
  await expect(voiceDialog(page)).not.toBeVisible();
});
