# 言序

Android 录音 → 自动上传 → Mac 转写 → DeepSeek 分析 → 公共结果。第一阶段免登录，访问者可回听和下载录音。

- [公共记录](https://yanxu.qjl666.xyz/) · [Android 测试包](https://yanxu.qjl666.xyz/app/yanxu-debug.apk)
- [AI 协作入口](AGENTS.md)：按任务读取规范。
- [当前文档地图](docs/README.md)：阶段范围、业务规则与技术来源。
- [前端与设计规范](frontend/docs/frontend-guides/README.md) · [前端启动](frontend/README.md)
- [后端](backend/README.md) · [Android](android/README.md) · [配置](config/README.md)
- [部署与恢复](docs/implementation/public-deployment.md) · [仓库与分支约定](docs/repository/workflow.md)

阿里云承载页面和 API，七牛存原音，Mac 主动领取转写。手机联网使用无需 USB；Mac 离线时新转写等待。真机拾音与长期可靠性仍需专项验收。本地 5189 保留旧测试库，与公网数据分开。

## 页面与设计参考

当前真实页面源码在 `frontend/src/live`，公共列表与详情在 `frontend/src/records`。视觉采用已确认的 [A 方案](frontend/docs/design-lab/selection.md)。

本地 5178 的 [第一阶段演示](http://127.0.0.1:5178/phase-one.html) 和 [完整 A 原型](http://127.0.0.1:5178/prototype.html) 使用模拟数据，用于交互参考；原型的扫码、权限与群发送不代表当前真实服务已实现。

完整产品方案保留在 [v1.3 文档入口](会议室录音系统_PRD_v1.3/README.md)，本期以 [第一阶段范围](docs/phases/phase-01.md) 为准。历史版本与比较方案的保留和恢复方式见 [仓库清理记录](docs/repository/cleanup.md)。
