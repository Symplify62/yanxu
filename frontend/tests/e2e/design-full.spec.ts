import { test, expect, type Page } from "@playwright/test";
async function send(
  page: Page,
  action: string,
  extra: Record<string, string> = {},
) {
  await page.evaluate(
    ({ action, extra }) =>
      window.postMessage(
        { type: "yanxu-design", action, ...extra },
        location.origin,
      ),
    { action, extra },
  );
}
async function surface(page: Page, name: string) {
  await send(page, "navigate", { surface: name });
}
async function snap(page: Page, variant: string, name: string) {
  await page.evaluate(async () => {
    await Promise.all(
      document
        .getAnimations()
        .filter(
          (a) =>
            a.playState === "running" &&
            a.effect?.getTiming().iterations !== Infinity,
        )
        .map((a) => a.finished.catch(() => {})),
    );
  });
  await page.screenshot({
    path: `evidence/design-lab/full/${variant}-${name}.png`,
    fullPage: true,
  });
}
async function pick(page: Page, variant: string, label: string, value: string) {
  if (variant === "element") {
    await page
      .getByRole("combobox", { name: label, exact: true })
      .locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]')
      .click();
    await page.getByRole("option", { name: value, exact: true }).click();
  } else {
    await page.getByRole("combobox", { name: label, exact: true }).click();
    await page.getByRole("option", { name: value, exact: true }).click();
  }
}
async function employee(page: Page) {
  await surface(page, "employee");
  await page
    .getByRole("button", { name: "模拟企业微信登录", exact: true })
    .click();
  await expect(page.locator(".meeting-item").first()).toBeVisible();
}
async function admin(page: Page) {
  await surface(page, "admin");
  await page
    .getByRole("button", { name: "进入演示管理员", exact: true })
    .click();
  await expect(page.locator(".metrics-strip")).toBeVisible();
}
async function record(page: Page) {
  await send(page, "scan");
  await page.getByRole("button", { name: "确认模拟扫码", exact: true }).click();
  await page.getByRole("button", { name: "开始录音", exact: true }).click();
  await page.getByRole("button", { name: "结束并保存", exact: true }).click();
  await expect(page.getByTestId("tablet-saved")).toBeVisible();
}
for (const variant of ["element", "shadcn"]) {
  test(`${variant}完整: 录音跨端查阅、五类资料、校验、更正不重发`, async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    let token = "";
    page.on("request", (r) => {
      if (r.url().includes("/api/v1/meetings"))
        token = r.headers()["x-demo-session"] || token;
    });
    await page.goto(`/design-option.html?variant=${variant}`);
    await expect(page.locator(".qr-wrap img")).toBeVisible();
    await record(page);
    await expect(page.getByTestId("tablet-saved")).toContainText("渠道已接收", {
      timeout: 18000,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await surface(page, "employee");
    await expect(
      page.getByRole("button", { name: "模拟企业微信登录", exact: true }),
    ).toBeVisible();
    await snap(page, variant, "phone-login");
    await page
      .getByRole("button", { name: "模拟企业微信登录", exact: true })
      .click();
    await expect(page.locator(".meeting-item")).toHaveCount(2);
    await snap(page, variant, "phone-list");
    await page.getByRole("textbox", { name: "搜索会议" }).fill("无此标题");
    await expect(
      page.getByText("没有找到相关会议", { exact: true }),
    ).toBeVisible();
    await snap(page, variant, "phone-empty");
    await page.getByRole("textbox", { name: "搜索会议" }).fill("");
    await page.getByRole("button", { name: /新会议 · 自动整理样例/ }).click();
    await expect(page.locator(".summary-content")).toBeVisible();
    await snap(page, variant, "phone-summary");
    for (const [label, file] of [
      ["逐字稿", "transcript"],
      ["事项", "tasks"],
      ["录音", "audio"],
      ["版本", "versions"],
    ]) {
      await page
        .getByRole("navigation", { name: "会议资料类型" })
        .getByRole("button", { name: label, exact: true })
        .click();
      await expect(page.locator(".detail-body h2")).toBeVisible();
      if (label === "逐字稿")
        await expect(page.locator(".transcript-item")).toHaveCount(3);
      await snap(page, variant, "phone-" + file);
    }
    await page
      .getByRole("button", { name: "查看自动发送快照", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toContainText(
      "保存更正不改写此快照",
    );
    await snap(page, variant, "phone-snapshot");
    await page.getByRole("button", { name: "关闭", exact: true }).click();
    await page
      .getByRole("navigation", { name: "会议资料类型" })
      .getByRole("button", { name: "纪要", exact: true })
      .click();
    await page.getByRole("button", { name: "主动更正", exact: true }).click();
    await page
      .getByRole("button", { name: "保存更正，不重发", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("请填写");
    await page
      .getByRole("textbox", { name: "纪要", exact: true })
      .fill("完整对比更正内容");
    await page
      .getByRole("textbox", { name: "负责人1", exact: true })
      .fill("刘工");
    await page
      .getByRole("textbox", { name: "更正原因", exact: true })
      .fill("根据原始发言核对");
    await snap(page, variant, "phone-edit");
    await page
      .getByRole("button", { name: "保存更正，不重发", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(page.locator(".summary-content")).toHaveText(
      "完整对比更正内容",
    );
    await expect(page.locator(".version-line")).toContainText("当前 v2");
    const m = await page.evaluate(
      async (token) =>
        (
          await (
            await fetch("/api/v1/meetings/rec-001", {
              headers: { "X-Demo-Session": token },
            })
          ).json()
        ).data,
      token,
    );
    expect(m.sendCount).toBe(1);
    expect(m.publication.version).toBe(1);
    expect(m.tasks[1].owner).toBe("刘工");
    expect(errors).toEqual([]);
  });
  test(`${variant}完整: 共享只读、撤销、账号拒绝与手机宽度`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/design-option.html?variant=${variant}&surface=employee`);
    await pick(page, variant, "演示员工", "其他企业用户");
    await page
      .getByRole("button", { name: "模拟企业微信登录", exact: true })
      .click();
    await expect(page.getByRole("alert")).toBeVisible();
    await snap(page, variant, "login-error");
    await pick(page, variant, "演示员工", "林同事");
    await page
      .getByRole("button", { name: "模拟企业微信登录", exact: true })
      .click();
    await page.getByRole("button", { name: /报价与交付协调/ }).click();
    await page.getByRole("button", { name: "共享查看权", exact: true }).click();
    await pick(page, variant, "授权对象", "陈同事");
    await page
      .getByRole("button", { name: "添加只读授权", exact: true })
      .click();
    await expect(page.locator(".grant-row")).toContainText("陈同事");
    await snap(page, variant, "phone-share");
    await page.getByRole("button", { name: "关闭", exact: true }).click();
    await page.getByRole("button", { name: "退出", exact: true }).click();
    await pick(page, variant, "演示员工", "陈同事");
    await page
      .getByRole("button", { name: "模拟企业微信登录", exact: true })
      .click();
    await page.getByRole("button", { name: /报价与交付协调/ }).click();
    await expect(page.locator(".detail-heading")).toContainText("只读共享");
    await expect(
      page.getByRole("button", { name: "主动更正", exact: true }),
    ).toHaveCount(0);
    await snap(page, variant, "phone-readonly");
    await page.getByRole("button", { name: "退出", exact: true }).click();
    await page
      .getByRole("button", { name: "模拟企业微信登录", exact: true })
      .click();
    await page.getByRole("button", { name: /报价与交付协调/ }).click();
    await page.getByRole("button", { name: "共享查看权", exact: true }).click();
    await page.getByRole("button", { name: "撤销", exact: true }).click();
    await expect(page.getByText("尚未共享", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "关闭", exact: true }).click();
    await page.getByRole("button", { name: "退出", exact: true }).click();
    await pick(page, variant, "演示员工", "陈同事");
    await page
      .getByRole("button", { name: "模拟企业微信登录", exact: true })
      .click();
    await expect(page.getByRole("button", { name: /财务例会/ })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /报价与交付协调/ }),
    ).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
  test(`${variant}完整: 后台全模块、真实配置表单、异常恢复与审计`, async ({
    page,
  }) => {
    await page.goto(`/design-option.html?variant=${variant}`);
    await expect(page.locator(".qr-wrap img")).toBeVisible();
    await send(page, "scenario", { value: "ai-failure" });
    await record(page);
    await expect(page.getByTestId("tablet-saved")).toContainText("管理员接管", {
      timeout: 18000,
    });
    await surface(page, "admin");
    await expect(
      page.getByRole("button", { name: "进入演示管理员", exact: true }),
    ).toBeVisible();
    await snap(page, variant, "admin-login");
    await page
      .getByRole("button", { name: "进入演示管理员", exact: true })
      .click();
    await expect(page.locator(".metrics-strip")).toBeVisible();
    await snap(page, variant, "admin-overview");
    await expect(page.locator(".admin-main")).not.toContainText("125,000");
    const nav = page.getByRole("navigation", { name: "后台模块" });
    await nav.getByRole("button", { name: "用户与身份", exact: true }).click();
    await page.getByRole("textbox", { name: "搜索员工姓名" }).fill("周同事");
    await page.getByRole("button", { name: "停用", exact: true }).click();
    await page.getByRole("button", { name: "确认变更", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "启用", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "启用", exact: true }).click();
    await page.getByRole("button", { name: "确认变更", exact: true }).click();
    await page.getByRole("textbox", { name: "搜索员工姓名" }).fill("");
    await snap(page, variant, "admin-people");
    await nav.getByRole("button", { name: "组织部门", exact: true }).click();
    await page.getByRole("button", { name: "财务部", exact: true }).click();
    await expect(page.locator(".table-surface")).toContainText("陈同事");
    await expect(page.locator(".table-surface")).not.toContainText("林同事");
    await page
      .getByRole("button", { name: "模拟同步组织", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText("模拟组织同步");
    await snap(page, variant, "admin-organization");
    await nav.getByRole("button", { name: "角色权限", exact: true }).click();
    await snap(page, variant, "admin-roles");
    await page
      .getByRole("button", { name: "查看权限", exact: true })
      .first()
      .click();
    await expect(page.getByRole("dialog")).toContainText("基础员工");
    await snap(page, variant, "admin-role-dialog");
    await page.getByRole("button", { name: "关闭", exact: true }).click();
    await nav.getByRole("button", { name: "业务访问组", exact: true }).click();
    await snap(page, variant, "admin-groups");
    await page
      .getByRole("button", { name: "维护成员", exact: true })
      .first()
      .click();
    const check = page.getByRole("checkbox", { name: "陈同事", exact: true });
    if (variant === "element")
      await page
        .getByRole("dialog")
        .locator("label.el-checkbox")
        .filter({ hasText: "陈同事" })
        .click();
    else await check.check();
    await expect(check).toBeChecked();
    await snap(page, variant, "admin-group-dialog");
    await page
      .getByRole("button", { name: "确认成员变更", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(page.locator(".full-data-table")).toContainText("陈同事");
    await nav
      .getByRole("button", { name: "部门与接收群", exact: true })
      .click();
    await snap(page, variant, "admin-routes");
    await page
      .getByRole("button", { name: "配置接收群", exact: true })
      .first()
      .click();
    await pick(page, variant, "群连接", "项目协作群（模拟）");
    await page.getByRole("button", { name: "取消", exact: true }).click();
    await expect(page.locator(".full-data-table")).not.toContainText(
      "项目协作群（模拟）",
    );
    await page
      .getByRole("button", { name: "配置接收群", exact: true })
      .first()
      .click();
    await pick(page, variant, "群连接", "项目协作群（模拟）");
    await snap(page, variant, "admin-route-dialog");
    await page.getByRole("button", { name: "保存新规则", exact: true }).click();
    await expect(page.locator(".full-data-table")).toContainText(
      "项目协作群（模拟）",
    );
    await page
      .getByRole("button", { name: "应急停止发送", exact: true })
      .click();
    await page.getByRole("button", { name: "确认停发", exact: true }).click();
    await expect(page.getByText("已应急停发", { exact: true })).toBeVisible();
    await page
      .getByRole("button", { name: "恢复自动发送", exact: true })
      .click();
    await page.getByRole("button", { name: "确认恢复", exact: true }).click();
    await nav.getByRole("button", { name: /异常处理/ }).click();
    await expect(
      page.getByRole("button", { name: "重新检查并恢复", exact: true }),
    ).toBeVisible();
    await snap(page, variant, "admin-exceptions");
    await page
      .getByRole("button", { name: "重新检查并恢复", exact: true })
      .click();
    await page
      .getByRole("button", { name: "确认恢复该阶段", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText("请填写处理依据");
    await page
      .getByRole("textbox", { name: "处理依据", exact: true })
      .fill("模拟依赖恢复已确认");
    await snap(page, variant, "admin-recovery-dialog");
    await page
      .getByRole("button", { name: "确认恢复该阶段", exact: true })
      .click();
    await expect(
      page.getByText("没有需要人工接管的异常", { exact: true }),
    ).toBeVisible();
    await nav.getByRole("button", { name: "操作记录", exact: true }).click();
    await expect(page.locator(".full-data-table")).toContainText(
      "变更账号状态",
    );
    await snap(page, variant, "admin-audit");
    await nav.getByRole("button", { name: "设备与存储", exact: true }).click();
    await expect(page.getByText("会议室 A", { exact: true })).toBeVisible();
    await expect(page.locator(".device-overview .grant-row")).toContainText(
      "渠道已接收",
      { timeout: 18000 },
    );
    await snap(page, variant, "admin-devices");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await surface(page, "components");
    await expect(
      page.getByRole("heading", { name: "组件与交互状态" }),
    ).toBeVisible();
    await snap(page, variant, "components");
    await page.getByRole("button", { name: "验证表单", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("请填写姓名");
  });
}
test("完整对比容器: 只显示A/B，切换端不丢数据，切换方案保留所选业务端", async ({
  page,
}) => {
  await page.goto("/design-lab.html");
  await expect(page.getByRole("tab")).toHaveCount(2);
  await page.getByRole("button", { name: "员工手机端", exact: true }).click();
  const f = page.frameLocator("iframe");
  await f
    .getByRole("button", { name: "模拟企业微信登录", exact: true })
    .click();
  await expect(f.locator(".meeting-item")).toBeVisible();
  await f.getByRole("button", { name: /报价与交付协调/ }).click();
  await expect(
    f.getByRole("button", { name: "主动更正", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "管理后台", exact: true }).click();
  await f.getByRole("button", { name: "进入演示管理员", exact: true }).click();
  await expect(f.locator(".metrics-strip")).toBeVisible();
  await page.getByRole("button", { name: "员工手机端", exact: true }).click();
  await expect(f.locator(".meeting-item")).toBeVisible();
  await page.getByRole("tab", { name: "克制 · shadcn/vue" }).click();
  await expect(
    f.getByRole("button", { name: "模拟企业微信登录", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "evidence/design-lab/full/comparison.png",
    fullPage: true,
  });
});
for (const variant of ["element", "shadcn"]) {
  test(`${variant}完整: 后台窄屏与登录失效关闭权限弹窗`, async ({ page }) => {
    let token = "";
    page.on("request", (r) => {
      if (r.url().endsWith("/api/v1/admin"))
        token = r.headers()["x-demo-session"] || token;
    });
    await page.goto(`/design-option.html?variant=${variant}&surface=admin`);
    await page
      .getByRole("button", { name: "进入演示管理员", exact: true })
      .click();
    await expect(page.locator(".metrics-strip")).toBeVisible();
    for (const width of [768, 390]) {
      await page.setViewportSize({ width, height: 960 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await snap(page, variant, "admin-width-" + width);
    }
    await page.setViewportSize({ width: 1280, height: 900 });
    await page
      .getByRole("navigation", { name: "后台模块" })
      .getByRole("button", { name: "角色权限", exact: true })
      .click();
    await page
      .getByRole("button", { name: "查看权限", exact: true })
      .first()
      .click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.evaluate(async (token) => {
      await fetch("/api/v1/session", {
        method: "DELETE",
        headers: { "X-Demo-Session": token },
      });
    }, token);
    await expect(
      page.getByRole("button", { name: "进入演示管理员", exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(
      page.getByRole("navigation", { name: "后台模块" }),
    ).toHaveCount(0);
  });
}
