# 前端补充入口

当前实施范围优先读[第一阶段：免登录录音与公共结果](../docs/phases/phase-01.md)。v1.3的登录、个人/共享范围、组织角色与发群在本期暂缓，不能据此重新增加本期前置步骤。

继承[项目AGENTS](../AGENTS.md)。真实公共结果入口是后端5189的`public.html`，启动在`src/live/`，复用`src/styles`的A主题和`src/records`公共组件；`phase-one.html`保留独立演示。`prototype.html`和`src/design-lab/`保留完整A方案参考，B/C比较已移除。

| 要改什么 | 读取什么 |
| --- | --- |
| 颜色、字体、间距、图标 | [视觉基础](docs/frontend-guides/01-视觉基础.md) |
| 页面结构、导航、宽度、长表单 | [布局与多端](docs/frontend-guides/02-布局与多端.md) |
| 按钮/表单/表格或录音等业务组件 | [组件与业务模式](docs/frontend-guides/03-组件与业务模式.md) |
| 加载/异常/权限状态、提交/关闭、提示语 | [交互状态与文案](docs/frontend-guides/04-交互状态与文案.md) |
| 页面状态、API、会话、mock或新模块 | [工程实施](docs/frontend-guides/05-工程实施.md) |
| 测试、可访问性、截图或验收 | [验收与维护](docs/frontend-guides/06-验收与维护.md) |

复合任务先读[任务导航](docs/frontend-guides/README.md)对应行；不要求全读六份规范。具体页面位置/动作查DES-10，状态/权限查STATE/ACL，测试用例由这些规格导出。

运行命令和依赖以[package.json](package.json)为准。选定A入口和旧v0.4路由同时存在，修改前确认目标；保留旧路径的历史回归，不把mock成功报告为真实服务成功。

页面精简遵循[根AGENTS的页面简洁原则](../AGENTS.md)：提交前检查重复标题、宣传语和解释段落；详细规则按需读[文案规范](docs/frontend-guides/04-交互状态与文案.md)。
