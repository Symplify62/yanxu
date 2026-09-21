# 言序项目

> 当前第一阶段已调整为[免登录录音、自动转写/AI分析与公网公共结果](docs/phases/phase-01.md)；第一阶段页面已实现，真实录音/AI/公网尚未接入。

- [AI协作入口](AGENTS.md)：按任务渐进式读取规范。
- [当前文档地图](docs/README.md)：业务/权限/技术来源。
- [前端任务与设计规范](frontend/docs/frontend-guides/README.md)：A方案视觉、布局、组件、交互、工程与验收。
- [仓库与启动约定](docs/repository/workflow.md)。

# 当前可运行前端：A方案正式组件原型

- [打开本地原型](http://127.0.0.1:5178/phase-one.html)
- [组件与状态展示](http://127.0.0.1:5178/prototype.html?surface=components)
- [工程说明与启动方法](frontend/README.md)
- [技术选择](frontend/docs/technical-choice.md)与[原型验证记录](frontend/docs/design-lab/verification.md)

**2026-09-21已确认A方案**，详见[设计决策](frontend/docs/design-lab/selection.md)。Vue 3＋TypeScript；Element Plus平板、手机及后台Web原型；MSW模拟接口。当前仍是前端原型，真实企业微信、音频、AI、群发送与原生Android未接入。原v0.3 HTML和下列资料继续保留为历史对照。

---

# 文档基线与旧HTML原型

文档基线：**v1.3 已确认全自动业务基线＋页面级规格**；可点击原型：**v0.3**。

- [打开新版原型](会议录音系统_可点击原型_v0.3.html)：员工模拟扫码、开始、结束，本地保存后自动退出，设备自动整理并模拟发群。手机看本人/授权资料，主动更正/共享是可选操作。
- [文档入口](会议室录音系统_PRD_v1.3/README.md)
- [已确认业务基线](会议室录音系统_PRD_v1.3/docs/rules/BASE-01-需求基线与待决事项.md)
- [21页55组件的页面级规格](会议室录音系统_PRD_v1.3/docs/design/DES-10-页面级设计与交互规格.md)
- [页面与测试对应](会议室录音系统_PRD_v1.3/docs/acceptance/UI-01-页面与组件测试对应.md)
- [本轮交付与验证](会议室录音系统_PRD_v1.3/evidence/自动化基线交付验证_v1.3.md)

正常无人工核对/确认发送，无本场禁发；企业微信身份、首次自动开户、默认部门、外网手机查阅、长期档案与无业务时长上限已确认。实际服务接入与产品实现尚未完成。

旧v1.0/v1.1/v1.2与旧HTML全部保留，仅作历史资料，不沿用其中已被替代的普通审核/匿名录音设计。原Word/PDF仅历史版本。
