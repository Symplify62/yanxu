import { test, expect, type Locator, type Page } from "@playwright/test";

const entry = "/speaker-prototype.html#/record";
const participants = (page: Page) =>
  page.getByRole("region", { name: "常用参会者" });
const picker = (page: Page) =>
  page.getByRole("dialog", { name: "选择参会者", exact: true });
const currentAll = (page: Page) =>
  participants(page).locator(
    '.el-checkbox[aria-label="全选当前人员"], .el-checkbox[aria-label="取消全选当前人员"]',
  );
const filteredAll = (page: Page) =>
  picker(page).locator(
    '.el-checkbox[aria-label="全选筛选结果"], .el-checkbox[aria-label="取消全选筛选结果"]',
  );
const input = (label: Locator) => label.locator('input[type="checkbox"]');
const chosen = (scope: Locator) =>
  scope.getByRole("button", { name: /^取消选择/ });

async function expectSelected(scope: Locator, names: string[]) {
  await expect(chosen(scope)).toHaveCount(names.length);
  for (const name of names) {
    await expect(
      scope.getByRole("button", { name: `取消选择${name}`, exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
  }
}

test.beforeEach(async ({ page }) => {
  await page.goto(entry);
  await expect(
    page.getByRole("heading", { name: "会议录音", exact: true }),
  ).toBeVisible();
});

test("首页全选当前人员，可取消全选并正确显示部分选择", async ({ page }) => {
  const all = currentAll(page);
  await expectSelected(participants(page), ["林晓", "陈默"]);
  await expect(all).toHaveAttribute("aria-checked", "mixed");

  // Click the visible Element Plus label rather than its hidden native input.
  await all.click();
  await expect(input(all)).toBeChecked();
  await expect(all).toHaveAttribute("aria-label", "取消全选当前人员");
  await expectSelected(participants(page), [
    "林晓",
    "陈默",
    "周宁",
    "许言",
    "王璐",
    "张伟",
  ]);

  await participants(page)
    .getByRole("button", { name: "取消选择周宁", exact: true })
    .click();
  await expect(all).toHaveAttribute("aria-checked", "mixed");
  await expect(all).toHaveAttribute("aria-label", "全选当前人员");
  await all.click();
  await expect(chosen(participants(page))).toHaveCount(6);
  await all.click();
  await expect(chosen(participants(page))).toHaveCount(0);
  await expect(input(all)).not.toBeChecked();
  await expect(all).not.toHaveAttribute("aria-checked", "mixed");
  await expect(
    page.getByRole("button", { name: "开始录音", exact: true }),
  ).toBeDisabled();
});

test("抽屉只全选或取消当前搜索及部门结果，保留筛选外已选人员", async ({
  page,
}) => {
  await page.getByRole("button", { name: /^更多人员/ }).click();
  const dialog = picker(page);
  const all = filteredAll(page);
  await dialog.getByRole("button", { name: "设计部", exact: true }).click();
  await expect(dialog.locator(".person-tile")).toHaveCount(1);
  await all.click();
  await expectSelected(dialog, ["周宁"]);
  await expect(dialog.locator(".picker-footer")).toContainText("已选 3 人");
  await expect(input(all)).toBeChecked();
  await all.click();
  await expect(chosen(dialog)).toHaveCount(0);
  await expect(dialog.locator(".picker-footer")).toContainText("已选 2 人");

  await dialog.getByRole("button", { name: "供应链", exact: true }).click();
  const search = dialog.getByRole("textbox", { name: "搜索参会者" });
  await search.fill("王璐");
  await all.click();
  await expectSelected(dialog, ["王璐"]);
  await search.clear();
  await expect(all).toHaveAttribute("aria-checked", "mixed");
  await expect(
    dialog.getByRole("button", { name: "选择张伟", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  await search.fill("王璐");
  await all.click();

  await dialog.getByRole("button", { name: "全部", exact: true }).click();
  await search.clear();
  await expectSelected(dialog, ["林晓", "陈默"]);
  await dialog.getByRole("button", { name: "完成选择", exact: true }).click();
  await expectSelected(participants(page), ["林晓", "陈默"]);
});

test("搜索没有结果时全选禁用，清空搜索后原有选择保留", async ({ page }) => {
  await page.getByRole("button", { name: /^更多人员/ }).click();
  const dialog = picker(page);
  const search = dialog.getByRole("textbox", { name: "搜索参会者" });
  await search.fill("不存在的测试同事");
  await expect(
    dialog.getByText("没有找到这位同事", { exact: true }),
  ).toBeVisible();
  await expect(input(filteredAll(page))).toBeDisabled();
  await expect(input(filteredAll(page))).not.toBeChecked();
  await expect(dialog.locator(".picker-footer")).toContainText("已选 2 人");
  await search.clear();
  await expect(input(filteredAll(page))).toBeEnabled();
  await expect(filteredAll(page)).toHaveAttribute("aria-checked", "mixed");
  await expectSelected(dialog, ["林晓", "陈默"]);
});

test("无发起会议权限时首页及人员抽屉全选禁用且名单保持不变", async ({
  page,
}) => {
  await page.getByLabel("演示身份", { exact: true }).selectOption("zhou");
  await expect(input(currentAll(page))).toBeDisabled();
  await expectSelected(participants(page), ["林晓", "陈默"]);
  await page.getByRole("button", { name: "按部门选人", exact: true }).click();
  await expect(input(filteredAll(page))).toBeDisabled();
  await expectSelected(picker(page), ["林晓", "陈默"]);
  await picker(page)
    .getByRole("button", { name: "完成选择", exact: true })
    .click();
  await page.getByLabel("演示身份", { exact: true }).selectOption("lin");
  await expect(input(currentAll(page))).toBeEnabled();
  await expectSelected(participants(page), ["林晓", "陈默"]);
});

test("录音及暂停中可批量追加人员，已加入名单不能取消且结果没有重复", async ({
  page,
}) => {
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await expect(input(currentAll(page))).toBeDisabled();
  await page.getByRole("button", { name: /^添加参会者/ }).click();
  const dialog = picker(page);
  await dialog.getByRole("button", { name: "设计部", exact: true }).click();
  await expect(input(filteredAll(page))).toBeEnabled();
  await filteredAll(page).click();
  await expect(input(filteredAll(page))).toBeChecked();
  await expect(input(filteredAll(page))).toBeDisabled();
  await expect(filteredAll(page)).toHaveAttribute("title", /取消|移除/);
  await expect(dialog.locator(".picker-footer")).toContainText("已选 3 人");
  await expect(
    dialog.getByRole("button", { name: "取消选择周宁", exact: true }),
  ).toBeDisabled();
  await dialog.getByRole("button", { name: "完成选择", exact: true }).click();

  await page.getByRole("button", { name: "暂停录音", exact: true }).click();
  await page.getByRole("button", { name: /^添加参会者/ }).click();
  await expect(filteredAll(page)).toHaveAttribute("aria-checked", "mixed");
  await expect(input(filteredAll(page))).toBeEnabled();
  await filteredAll(page).click();
  await expect(input(filteredAll(page))).toBeChecked();
  await expect(input(filteredAll(page))).toBeDisabled();
  await expect(dialog.locator(".picker-footer")).toContainText("已选 6 人");
  await expect(chosen(dialog)).toHaveCount(6);
  for (const person of await chosen(dialog).all())
    await expect(person).toBeDisabled();
  await dialog.getByRole("button", { name: "完成选择", exact: true }).click();
  await expect(chosen(participants(page))).toHaveCount(6);

  // Reopening the picker cannot re-add existing attendees or clear the roster.
  await page.getByRole("button", { name: /^添加参会者/ }).click();
  await expect(input(filteredAll(page))).toBeDisabled();
  await expect(dialog.locator(".picker-footer")).toContainText("已选 6 人");
  await dialog.getByRole("button", { name: "完成选择", exact: true }).click();
  await page.getByRole("button", { name: "结束录音", exact: true }).click();
  await page.getByRole("button", { name: "结束并整理", exact: true }).click();
  await expect(page.getByText("整理完成 · 示例结果")).toBeVisible();
  await expect(page.locator(".result-heading")).toContainText("6 位参会者");
  await expect(page.locator(".transcript-row")).toHaveCount(6);
});

test("首页全选仅作用可见头像，取消后保留第八位已选人员", async ({ page }) => {
  await page.getByRole("button", { name: /^更多人员/ }).click();
  const dialog = picker(page);
  for (const name of ["来宾甲", "来宾乙"]) {
    await dialog.getByRole("button", { name: /添加临时来宾/ }).click();
    const add = page.getByRole("dialog", { name: "添加临时来宾", exact: true });
    await add.getByRole("textbox", { name: "用户姓名" }).fill(name);
    await add.getByRole("button", { name: "添加并选中", exact: true }).click();
  }
  await dialog.getByRole("button", { name: "完成选择", exact: true }).click();
  await expect(participants(page).locator(".person-tile")).toHaveCount(7);
  await expect(
    participants(page).getByRole("button", {
      name: "取消选择来宾乙",
      exact: true,
    }),
  ).toHaveCount(0);
  await currentAll(page).click();
  await expect(chosen(participants(page))).toHaveCount(7);
  await currentAll(page).click();
  await expect(chosen(participants(page))).toHaveCount(0);
  await page.getByRole("button", { name: /^更多人员/ }).click();
  await expectSelected(dialog, ["来宾乙"]);
  await expect(dialog.locator(".picker-footer")).toContainText("已选 1 人");
});
