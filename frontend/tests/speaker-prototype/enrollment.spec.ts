import { test, expect, type Page } from "@playwright/test";
const entry = "/speaker-prototype.html";
const evidence = "../.local-data/evidence/speaker-redesign";
async function navAdmin(page: Page, section: string) {
  await page.getByRole("button", { name: "管理后台", exact: true }).click();
  await page
    .getByRole("navigation", { name: "后台模块" })
    .getByRole("button", { name: section, exact: true })
    .click();
}
async function back(page: Page) {
  await page
    .locator(".product-header")
    .getByRole("button", { name: "返回录音", exact: true })
    .click();
}
async function enroll(page: Page, persistent = true) {
  const d = page.getByRole("dialog", { name: "录入声音", exact: true });
  await d.getByRole("button", { name: "开始录入", exact: true }).click();
  await d.getByRole("button", { name: "结束录入", exact: true }).click();
  await expect(
    d.getByRole("button", { name: "确认保存", exact: true }),
  ).toBeDisabled();
  await d.getByRole("button", { name: "播放示例录音", exact: true }).click();
  await expect(
    d.getByRole("button", { name: "暂停示例录音", exact: true }),
  ).toBeVisible();
  await d
    .getByText("本人确认：姓名正确，录音是我的声音", { exact: true })
    .click();
  if (persistent) {
    await expect(
      d.getByRole("button", { name: "确认保存", exact: true }),
    ).toBeDisabled();
    await d
      .getByText("同意保存声音，用于下次会议识别", { exact: true })
      .click();
  }
  await d.getByRole("button", { name: "确认保存", exact: true }).click();
  await expect(d).not.toBeVisible();
}
async function endMeeting(page: Page) {
  await page.getByRole("button", { name: "结束录音", exact: true }).click();
  await page.getByRole("button", { name: "结束并整理", exact: true }).click();
  await expect(page.getByText("整理完成 · 示例结果")).toBeVisible();
}
async function selectOption(page: Page, label: string, option: string) {
  await page
    .locator(".el-select")
    .filter({ has: page.getByRole("combobox", { name: label, exact: true }) })
    .click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

test.beforeEach(async ({ page }) => {
  await page.goto(entry);
});

test("录音首页直接头像选人，确认姓名及授权，生成声纹后开始并持久保留会议", async ({
  page,
}) => {
  await expect(
    page.getByRole("heading", { name: "会议录音", exact: true }),
  ).toBeVisible();
  await expect(page.locator("table")).toHaveCount(0);
  const avatars = page.getByRole("region", { name: "常用参会者" });
  await avatars.getByRole("button", { name: "选择周宁", exact: true }).click();
  await expect(
    avatars.getByRole("button", { name: "取消选择周宁", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .locator(".pending-voices")
    .getByRole("button", { name: "周宁", exact: true })
    .click();
  const d = page.getByRole("dialog", { name: "录入声音", exact: true });
  await d.getByRole("button", { name: "开始录入", exact: true }).click();
  await d.getByRole("button", { name: "结束录入", exact: true }).click();
  await d
    .getByText("本人确认：姓名正确，录音是我的声音", { exact: true })
    .click();
  await d.getByText("同意保存声音，用于下次会议识别", { exact: true }).click();
  await d.getByRole("textbox", { name: "确认姓名", exact: true }).fill("周凝");
  await expect(
    d.getByRole("button", { name: "确认保存", exact: true }),
  ).toBeDisabled();
  await d
    .getByText("本人确认：姓名正确，录音是我的声音", { exact: true })
    .click();
  await page.screenshot({ path: `${evidence}/voice-confirm.png` });
  await d.getByRole("button", { name: "确认保存", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "取消选择周凝", exact: true }),
  ).toContainText("声纹可用");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "取消选择周凝", exact: true }),
  ).toContainText("声纹可用");
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "暂停录音", exact: true }).click();
  await expect(page.getByText("已暂停", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "继续录音", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "管理后台", exact: true }),
  ).toBeDisabled();
  await endMeeting(page);
  await expect(
    page.locator(".transcript-speaker").filter({ hasText: "周凝" }),
  ).toBeVisible();
  await page.screenshot({ path: `${evidence}/transcript.png`, fullPage: true });
  await page.getByRole("button", { name: "下一场会议", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "开始录音", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "会议记录", exact: true }).click();
  await expect(page.locator(".history-item")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".history-item")).toHaveCount(1);
});

test("抽屉按部门点选与临时来宾，未录入降级为编号，下一场不保留来宾", async ({
  page,
}) => {
  await page.getByRole("button", { name: "按部门选人", exact: true }).click();
  const d = page.getByRole("dialog", { name: "选择参会者", exact: true });
  await d.getByRole("button", { name: "设计部", exact: true }).click();
  await expect(d.locator(".person-tile")).toHaveCount(1);
  await d.getByRole("button", { name: "选择周宁", exact: true }).click();
  await d.getByRole("button", { name: "添加临时来宾", exact: false }).click();
  const add = page.getByRole("dialog", { name: "添加临时来宾", exact: true });
  await add.getByRole("textbox", { name: "用户姓名" }).fill("顾远");
  await add.getByRole("button", { name: "添加并选中", exact: true }).click();
  await d.getByRole("button", { name: "完成选择", exact: true }).click();
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "仍然开始", exact: true }).click();
  await endMeeting(page);
  await expect(page.locator(".unknown-tag")).toHaveCount(2);
  await page.getByRole("button", { name: "下一场会议", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "选择顾远", exact: true }),
  ).toHaveCount(0);
});

test("用户新增、编辑、停用和恢复联动头像候选", async ({ page }) => {
  await navAdmin(page, "用户管理");
  await page.getByRole("button", { name: "添加用户", exact: true }).click();
  let d = page.getByRole("dialog", { name: "添加用户", exact: true });
  await d.getByRole("button", { name: "保存用户", exact: true }).click();
  await expect(d.getByRole("alert")).toContainText("姓名");
  await d.getByRole("textbox", { name: "用户姓名" }).fill("赵晴");
  await d.getByRole("textbox", { name: "用户备注" }).fill("项目协同");
  await selectOption(page, "所属部门", "研发部");
  await d.getByRole("button", { name: "保存用户", exact: true }).click();
  await expect(
    page.locator(".el-table__body tr").filter({ hasText: "赵晴" }),
  ).toContainText("研发部");
  await page.getByRole("button", { name: "编辑赵晴", exact: true }).click();
  d = page.getByRole("dialog", { name: "编辑用户", exact: true });
  await d.getByRole("textbox", { name: "用户姓名" }).fill("赵清");
  await d.getByRole("button", { name: "保存用户", exact: true }).click();
  await page.getByRole("button", { name: "停用赵清", exact: true }).click();
  await page.getByRole("button", { name: "确认操作", exact: true }).click();
  await back(page);
  await expect(
    page.getByRole("button", { name: "选择赵清", exact: true }),
  ).toHaveCount(0);
  await navAdmin(page, "用户管理");
  await page.getByRole("button", { name: "启用赵清", exact: true }).click();
  await page.getByRole("button", { name: "确认操作", exact: true }).click();
  await back(page);
  await expect(
    page.getByRole("button", { name: "选择赵清", exact: true }),
  ).toBeVisible();
});

test("角色可创建配置删除；演示权限阻止无权入口", async ({ page }) => {
  await navAdmin(page, "角色管理");
  await page.getByRole("button", { name: "新建角色", exact: true }).click();
  let d = page.getByRole("dialog", { name: "新建角色", exact: true });
  await d.getByRole("textbox", { name: "角色名称" }).fill("声纹维护员");
  await d.getByRole("textbox", { name: "职责说明" }).fill("维护声音档案");
  await d.getByRole("button", { name: "创建角色", exact: true }).click();
  await page
    .locator(".permissions-grid")
    .getByText("声纹管理", { exact: true })
    .click();
  await page.getByRole("button", { name: "保存权限", exact: true }).click();
  await page.reload();
  await expect(page.getByRole("button", { name: /声纹维护员/ })).toBeVisible();
  await page.getByRole("button", { name: /声纹维护员/ }).click();
  await expect(
    page.getByRole("checkbox", { name: "声纹管理", exact: true }),
  ).toBeChecked();
  await page.getByRole("button", { name: "删除角色", exact: true }).click();
  await page.getByRole("button", { name: "确认操作", exact: true }).click();
  await expect(page.getByRole("button", { name: /声纹维护员/ })).toHaveCount(0);
  await page.getByLabel("演示身份", { exact: true }).selectOption("zhou");
  await expect(
    page.getByRole("button", { name: "管理后台", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "开始录音", exact: true }),
  ).toBeDisabled();
  await page.goto(entry + "#/admin/users");
  await expect(
    page.getByRole("heading", { name: "当前身份无此权限" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "添加用户", exact: true }),
  ).toHaveCount(0);
});

test("部门树新增、编辑、删除空部门，非空部门删除被拦截", async ({ page }) => {
  await navAdmin(page, "部门管理");
  await page.getByRole("button", { name: "新增部门", exact: true }).click();
  let d = page.getByRole("dialog", { name: "新增部门", exact: true });
  await d.getByRole("textbox", { name: "部门名称" }).fill("海外事业部");
  await d.getByRole("button", { name: "保存部门", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "海外事业部", exact: true }),
  ).toBeVisible();
  await page
    .locator(".department-heading")
    .getByRole("button", { name: "编辑", exact: true })
    .click();
  d = page.getByRole("dialog", { name: "编辑部门", exact: true });
  await d.getByRole("textbox", { name: "部门名称" }).fill("国际事业部");
  await d.getByRole("button", { name: "保存部门", exact: true }).click();
  await page
    .locator(".department-heading")
    .getByRole("button", { name: "删除", exact: true })
    .click();
  await page.getByRole("button", { name: "确认操作", exact: true }).click();
  await expect(page.getByText("国际事业部", { exact: true })).toHaveCount(0);
  await page
    .locator(".department-tree")
    .getByText("研发部", { exact: true })
    .click();
  await page
    .locator(".department-heading")
    .getByRole("button", { name: "删除", exact: true })
    .click();
  await page.getByRole("button", { name: "确认操作", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("成员和子部门");
});

test("声纹状态：未录入→生成→可用→需重录→撤回，不影响用户", async ({ page }) => {
  await navAdmin(page, "声纹管理");
  await page
    .getByRole("button", { name: "为周宁登记声纹", exact: true })
    .click();
  await enroll(page);
  const row = page.locator(".el-table__body tr").filter({ hasText: "周宁" });
  await expect(row).toContainText("生成中");
  await expect(row).toContainText("可用");
  await page
    .getByRole("button", { name: "查看周宁的声纹", exact: true })
    .click();
  await page.getByRole("button", { name: "标记需重录", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "声音档案", exact: true }),
  ).toContainText("需重录");
  await page.getByRole("button", { name: "撤回声纹", exact: true }).click();
  await page.getByRole("button", { name: "确认撤回", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "声音档案", exact: true }),
  ).toContainText("已撤回");
  await expect(
    page.getByRole("button", { name: "播放示例录音", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await page.reload();
  await expect(
    page.locator(".el-table__body tr").filter({ hasText: "周宁" }),
  ).toContainText("已撤回");
  await back(page);
  await expect(
    page.getByRole("button", { name: "选择周宁", exact: true }),
  ).toBeVisible();
});

test("配置持久保存并与录音页一致，记住名单不包含临时来宾", async ({ page }) => {
  await page.getByRole("button", { name: "打开设置", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "个人与设备设置" }),
  ).toBeVisible();
  await selectOption(page, "麦克风", "会议麦克风（示例）");
  await page
    .locator(".el-switch")
    .filter({
      has: page.getByRole("switch", { name: "记住本场成员", exact: true }),
    })
    .click();
  await page.reload();
  await expect(
    page.getByRole("switch", { name: "记住本场成员", exact: true }),
  ).toBeChecked();
  await page
    .getByRole("navigation", { name: "主导航" })
    .getByRole("button", { name: "录音", exact: true })
    .click();
  await expect(page.locator(".canvas-foot")).toContainText(
    "会议麦克风（示例）",
  );
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await endMeeting(page);
  await page.getByRole("button", { name: "下一场会议", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "取消选择林晓", exact: true }),
  ).toBeVisible();
});

for (const width of [390, 768, 1280])
  test(`录音与四模块后台布局 ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.screenshot({
      path: `${evidence}/record-${width}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.getByRole("button", { name: "按部门选人", exact: true }).click();
    await expect(
      page.getByRole("dialog", { name: "选择参会者", exact: true }),
    ).toBeVisible();
    await expect
      .poll(() =>
        page.locator(".people-drawer").evaluate((el) => {
          const rect = el.getBoundingClientRect();
          return (
            getComputedStyle(el).transform === "none" &&
            rect.left >= 0 &&
            rect.right <= window.innerWidth + 1
          );
        }),
      )
      .toBeTruthy();
    await page.screenshot({
      path: `${evidence}/picker-${width}.png`,
      animations: "disabled",
    });
    await page.getByRole("button", { name: "完成选择", exact: true }).click();
    await page.getByRole("button", { name: "打开设置", exact: true }).click();
    await page.screenshot({
      path: `${evidence}/settings-${width}.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "管理后台", exact: true }).click();
    for (const [section, key] of [
      ["用户管理", "users"],
      ["角色管理", "roles"],
      ["部门管理", "departments"],
      ["声纹管理", "voices"],
    ]) {
      await page
        .getByRole("navigation", { name: "后台模块" })
        .getByRole("button", { name: section, exact: true })
        .click();
      await expect(
        page.getByRole("heading", { name: section, exact: true }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBeTruthy();
      await page.screenshot({
        path: `${evidence}/${key}-${width}.png`,
        fullPage: true,
      });
    }
  });
