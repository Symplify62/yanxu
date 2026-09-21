# 言序前端

Vue 3 / TypeScript / Element Plus，采用暖白与绿色的 A 方案。开发时从 [任务导航](docs/frontend-guides/README.md) 选择相关规范。

## 入口

| 入口 | 用途 | 数据来源 |
| --- | --- | --- |
| 后端 5189 根地址 / `public.html` | 真实公共列表、详情、回听、下载 | 后端 API；本地旧测试库与公网独立 |
| 5178 / `phase-one.html` | 第一阶段录音与结果交互演示 | 浏览器模拟资料，不采音 |
| 5178 / `prototype.html` | 已确认的完整 A 方案，含手机和后台 | MSW 合成资料，后续产品参考 |
| 5178 /tablet、/employee、/admin | 早期组件原型回归 | MSW 合成资料 |

开发服务器根地址进入第一阶段演示；完整 A 原型支持 `surface=tablet/employee/admin/components`。`design-option.html` 是 A 原型内部 iframe 的承载页。B/C 比较页及其组件库已移除，历史可从 Git 找回。

当前真实服务已接入 Android 录音、转写与 AI，详见 [部署记录](../docs/implementation/public-deployment.md)。扫码、组织权限和群发送在第一阶段暂缓。

## 启动与验证

在本目录执行：

```sh
npm ci
npm run dev
```

构建与本地预览使用 `npm run build`、`npm run preview`。默认监听 127.0.0.1:5178，启动前确认端口归属。真实页面还需运行 [后端](../backend/README.md)，配置见 [配置说明](../config/README.md)。模型与运行数据不随 Git 克隆。

`npm test` 验证规则与模拟 HTTP，`npm run test:e2e` 使用 Chrome 验证保留的原型流程，`npm run test:live` 验证本地真实服务。真实服务回归需要已有完成的测试录音。长期回归使用项目 Playwright，新产物位于被忽略的 `.local-data/evidence/`。

## 代码定位

- `src/live`：真实公共 API 请求、路由与页面装配。
- `src/records`：共用列表、详情与状态/类型；演示样例由演示入口传入。
- `src/styles/a-theme.css`、`a-layout.css`、`records.css`：A 主题、完整原型布局和公共记录布局。
- `src/phase-one`：独立第一阶段演示、模拟录音状态与样例。
- `src/design-lab`：保留的完整 A 原型、Element Plus 适配组件；目录名沿用历史，已无 B/C 实现。
- `src/domain`、`src/services`、`src/mocks`：完整原型的类型、请求与合成服务。
- `src/pages`、`src/components`、`src/composables`：早期原型与仍共用的组件/状态。

真实公共入口不加载演示状态或 MSW。完整原型的模拟身份、发送与恢复结果不代替真实后端验收。目录清理与本次验证见 [清理记录](../docs/repository/cleanup.md)。
