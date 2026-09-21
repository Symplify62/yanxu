# 完整 A 方案原型

已确认采用 A / Element Plus，入口为本地 `/prototype.html`；可切换平板、员工手机、管理后台和组件状态。它使用 MSW 合成数据，供后续完整产品方案参考。

当前真实公共页面位于 `src/live` 与 `src/records`，第一阶段不实施登录、组织权限或群发送。开发入口见[前端说明](../../README.md)，视觉决策见[方案确认](selection.md)。

B/C 比较页、专用组件和依赖已移除。历史比较过程仍可查[当时的验证记录](verification.md)；其中旧文件与截图需从清理前提交读取，恢复方法见[清理记录](../../../docs/repository/cleanup.md)。

A 的组件适配保留在 `src/design-lab/kits/Element*`，共用样式位于 `src/styles/a-theme.css`、`a-layout.css` 与 `records.css`。实现定位与边界见[工程实施](../frontend-guides/05-工程实施.md)。
