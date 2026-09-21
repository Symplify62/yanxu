# 言序 · A方案正式组件原型

开发前按任务读取[前端规范导航](docs/frontend-guides/README.md)；局部工作入口见[AGENTS.md](AGENTS.md)。

A方案已于2026-09-21确认，作为后续前端设计基线。当前正式原型使用Vue 3 / TypeScript与Element Plus，覆盖平板、员工手机和管理后台，沿用PRD v1.3 U-11全自动业务基线。接口由MSW提供合成数据。详见[方案确认](docs/design-lab/selection.md)。

## 当前原型入口

- **[打开A方案正式原型](http://127.0.0.1:5178/prototype.html)**（根地址也进入此页）
- [员工手机](http://127.0.0.1:5178/prototype.html?surface=employee) · [管理后台](http://127.0.0.1:5178/prototype.html?surface=admin) · [组件状态](http://127.0.0.1:5178/prototype.html?surface=components)

## 历史对照

- **A/B完整原型对比**：[Element Plus / shadcn/vue](http://127.0.0.1:5178/design-lab.html)（覆盖平板、员工手机、管理后台与组件状态，已选定A，比较页仅保留历史对照；见 [设计说明](docs/design-lab/README.md)）

- 平板交互：[http://127.0.0.1:5178/tablet](http://127.0.0.1:5178/tablet)
- 员工手机：[http://127.0.0.1:5178/employee](http://127.0.0.1:5178/employee)
- 管理后台：[http://127.0.0.1:5178/admin](http://127.0.0.1:5178/admin)
- 组件与状态：[http://127.0.0.1:5178/components](http://127.0.0.1:5178/components)

当前由本任务启动构建后的本地预览服务，仅监听127.0.0.1。服务停止后，在此目录运行：

```sh
npm ci
npm run build
npm run preview
```

开发时使用 `npm run dev`（同一默认端口，先停止预览服务再启动）。依赖版本精确固定，使用package-lock.json；本轮Node为24.14.1。

## 原v0.4迁移记录（历史）

- Vue Router页面路由；Element Plus按钮/表单/表格/弹窗/抽屉/树/状态；Vant手机导航、表单、弹层、选择器、标签及列表。
- 页面只调用src/services，不直接操作模拟数据库；MSW处理实际fetch请求并返回200/401/403/404/409/422等结果。
- 模拟扫码、过期/停用/首次开户、录音状态与本地保存反馈、退出后设备队列、自动处理/发送。
- 手机本人或授权资料、只读共享/撤销、纪要和事项可选更正、版本冲突与旧发送快照保留。
- 管理账号状态、组织同步示例、访问组成员、部门群配置、应急停发、异常恢复、审计与设备元数据。
- 组件展示页直接复用实际组件，可看表单错误、禁用/加载、处理状态及弹窗。

## 演示方式

平板选“模拟手机扫码”→林同事→开始→结束。保存页只有下一场扫码；顶部端切换是评审导航，不属于平板App。切换员工手机端，以林同事模拟登录，可看新会议和种子会议。管理员入口使用专门管理身份，默认无会议正文权限。

“演示控制”可切换断网、保存失败、AI重试耗尽、缺群和发送结果不明。全部变化只在当前标签页的模拟服务内存中；刷新/重置会还原资料并使旧演示登录过期。不同标签页不共享模拟数据库。

## 明确边界

这是可复用前端工程，不是生产系统。二维码不可真实扫描，不接企业微信、麦克风、真实音频、AI或群发送。模拟任务由浏览器请求与时钟推进，不证明关闭浏览器后的服务端持续处理。用户/设备/后台权限只在mock模型验证，真实后端必须独立实现和测试。

平板仍是Web交互预览，不是原生Android安装包，不能验证息屏、长录音或真实持久队列。完整自定义角色委派编辑和详细分片诊断仍待后续实现；当前角色目录为只读预置展示。未知人员和日期保留原文，不自动派单。

员工首次登录、组织同步与外网访问是已确认业务目标，但没有真实企业身份或网络接入证据。模拟请求使用X-Demo-Session，不能沿用为生产认证。非mock模式在入口明确阻断，尚未配置实际服务适配。

## 代码组织

- src/domain：类型、展示语义。
- src/services：HTTP错误与类型化API，未来接真实契约的适配边界。
- src/mocks：合成数据、状态/权限模型、MSW handlers与浏览器启动。
- src/composables：员工/管理会话、请求轮询及卸载保护。
- src/components：状态、错误反馈、设备队列、手机更正和共享。
- src/pages：平板、手机与按职责拆分的管理工作区。
- src/styles：设计变量与布局，组件按需导入。
- tests：Vitest规则/HTTP契约与Playwright浏览器流程。

## 验证

```sh
npm run typecheck
npm test
npm run build
npm run test:e2e
```

E2E使用本机Chrome的隔离测试上下文和模拟数据，需要Chrome可执行文件；playwright.config.ts启动/复用本工程本地预览。30项规则/模拟HTTP检查、6条浏览器流程及开发导航检查结果见[验证记录](docs/verification.md)。截图在evidence/screenshots。

本轮只做本地工程，没有提交、推送或公网发布。旧单文件HTML/PRD/ZIP未修改，仍在外层目录。
