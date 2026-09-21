# 言序 A/B 完整原型对比（2026-09-21）

**已确认采用A方案**，见[确认记录](selection.md)。当前正式入口：http://127.0.0.1:5178/prototype.html 。

历史对比入口：http://127.0.0.1:5178/design-lab.html

A使用Element Plus 2.14.6，暖白、柔和绿色、较柔和的圆角；B使用shadcn/vue官方组件源码，黑白、细边框与更轻的列表布局。

当前design-lab只展示A和B，C退出本次评审。上方可切换平板录音端、员工手机端、管理后台、组件与状态。同一方案切端保留模拟会议和已登录身份；切换A/B重新初始化该方案模拟数据。两方案使用相同服务与种子数据，便于比较相同功能。

| 页面与流程 | A | B | 行为范围 |
| --- | --- | --- | --- |
| 平板扫码/归属/录音/暂停/保存/下一场 | Element Plus | shadcn/vue | 原自动流程；过期、保存故障与队列反馈 |
| 员工登录、列表、搜索、本人/共享筛选 | Element Plus响应式布局 | shadcn/vue响应式布局 | API身份与内容授权 |
| 会议纪要/逐字稿/事项/录音/版本 | 同主题业务布局 | 同主题业务布局 | 各自就绪、无音频样本明确禁播、下载独立权限 |
| 主动更正、共享/撤销、发送快照 | Element弹窗、输入、选择 | shadcn弹窗、输入、选择 | 原稿与快照保留，更正不重复发群 |
| 管理登录与运行概览 | Element控件、暖绿侧栏 | shadcn控件、黑白侧栏 | 只显示任务元数据，不自动开放会议正文 |
| 用户与身份、组织部门 | Element表格与确认弹窗 | shadcn表格与确认弹窗 | 搜索、启停、保护管理员、模拟组织同步 |
| 角色权限、业务访问组 | 真实表格、弹窗、复选框 | 真实表格、弹窗、复选框 | 预置角色只读；组成员可编辑 |
| 部门接收群、应急停发 | 真实表单与确认弹窗 | 真实表单与确认弹窗 | 配置版本检查、取消不保存 |
| 异常恢复、操作记录、设备 | 同API、同操作 | 同API、同操作 | 处理依据必填、只恢复失败阶段、元数据审计 |
| 组件与状态 | 实际组件样例 | 实际组件样例 | 输入、校验、禁用、加载、状态、弹窗 |

相对于当前v0.4功能完整对比，不代表全部PRD能力已经实现。自定义角色委派、真实录音/回放、企业微信、AI调用与真实群发送仍保持此前边界。A手机样板使用响应式Element控件，以便与B作同范围组件比较；旧主原型手机端的Vant实现保持原样。

新增shadcn组件来源为同一官方new-york-v4 registry的input、textarea、checkbox、table；取用原件和MIT许可证保留。本次屏幕证据位于evidence/design-lab/full。

## 来源与复用

shadcn源码来自官方 https://www.shadcn-vue.com/r/styles/new-york-v4/ 注册表，原始JSON保存在evidence/design-lab/registry-*.json，MIT许可证保存在src/design-lab/ui/LICENSE。使用button/dialog/select/input/textarea/checkbox/table，适配导入路径和项目格式化；业务包装在kits目录。

Element Plus主题参考：https://element-plus.org/en-US/guide/theming.html 。shadcn组件源码分发方式：https://www.shadcn-vue.com/docs/introduction 。

## 架构与验证

独立HTML入口与iframe隔离样式。full/下按员工端、后台、登录、账户状态和共享组件接口划分；复用原型services/api与MSW。业务mock不变化，主原型路由不变化。

用户可在外部演示控制中选择正常、断网、保存失败、AI失败、缺群、未知发送结果场景。后台无需接收录音正文即可处理异常。手机原音播放与下载显示真实边界，不伪造可用能力。

验证合同、结果和已修复问题见verification.md；全量端到端、类型/构建、模型/HTTP结果与截图位于evidence/design-lab/full。
