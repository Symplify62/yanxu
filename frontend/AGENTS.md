# 前端补充入口

继承[项目AGENTS](../AGENTS.md)。当前正式入口是`prototype.html`，A方案实现位于`src/design-lab/`；目录名保留历史原因，不表示它仍是待选方案。

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
