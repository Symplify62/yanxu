# 当前文档地图

仅在需要确认业务/技术范围或不知道权威来源时读取本页。已定位前端工作可直接进入[前端任务导航](../frontend/docs/frontend-guides/README.md)。

当前正在收敛[第一阶段：免登录录音与公网公共结果](phases/phase-01.md)。本期范围与验收以此为先，以下v1.3是完整产品方案的按需来源。

## 来源边界

| 问题 | 权威来源 |
| --- | --- |
| 当前第一阶段做什么 | [阶段范围与验收](phases/phase-01.md)，已覆盖本期旧登录/权限/发群前置规则 |
| 当前采用哪套外观/组件 | [A方案确认](../frontend/docs/design-lab/selection.md)；通用前端规范在前端任务导航 |
| 某页有哪些区域、动作和权限结果 | [DES-10页面级规格](../会议室录音系统_PRD_v1.3/docs/design/DES-10-页面级设计与交互规格.md)对应页面；先搜页名/业务组件名 |
| 常规流程、人机分工、待决事项 | [BASE-01](../会议室录音系统_PRD_v1.3/docs/rules/BASE-01-需求基线与待决事项.md) |
| 状态、保存/上传/处理/发送区别 | [STATE-01](../会议室录音系统_PRD_v1.3/docs/rules/STATE-01-业务对象与状态规则.md) |
| 身份、角色、对象范围、撤权 | [ACL-01](../会议室录音系统_PRD_v1.3/docs/rules/ACL-01-角色权限与数据访问.md) |
| 数据保留、设备可靠性、容量等非功能要求 | [NFR-01](../会议室录音系统_PRD_v1.3/docs/rules/NFR-01-非功能要求与数据生命周期.md) |
| 实际实现/依赖/脚本 | 源码、[package.json](../frontend/package.json)与新鲜运行证据；文档声明不替代验证 |

遇到来源差异：先确认这是已批准变更、历史建议还是实现缺口；记录差异并修正正确来源，不用原型的现状自行降低业务或权限要求。

## 已确认的接入方向

Android App采音、Mac本地开发与转写、DeepSeek分析、匿名回听/下载。ASR选型读[官方资料研究](research/asr-primary-sources.md)和[本机测试结论](research/asr-local-benchmark.md)，密钥准备读[后端配置](../config/README.md)。

## 本地运行入口

[后端运行与接口](../backend/README.md) · [Android测试App](../android/README.md) · [公网部署与恢复](implementation/public-deployment.md) · [早期本地接入证据](implementation/phase-one-live.md)。公网入口为 https://yanxu.qjl666.xyz/ ，本地5189保留旧测试库。

接入七牛存储、阿里云文件域名、证书与云同步时，读[七牛接入记录](implementation/qiniu-storage.md)和[后端配置](../config/README.md)。文件域名可访问不等于公共应用已部署。

## 按业务进入

- 平板录音：[PRD-01](../会议室录音系统_PRD_v1.3/docs/product/PRD-01-平板录音端.md)；实际采集/设备实现再读[安卓设计](../会议室录音系统_PRD_v1.3/docs/design/DES-03-安卓端技术设计要求.md)。
- 上传、音频归档：[PRD-02](../会议室录音系统_PRD_v1.3/docs/product/PRD-02-上传与音频归档.md)。
- 转写、纪要、事项：[PRD-03](../会议室录音系统_PRD_v1.3/docs/product/PRD-03-转写纪要与行动事项.md)。
- 资料查阅、更正、版本：[PRD-04](../会议室录音系统_PRD_v1.3/docs/product/PRD-04-会议记录与人工修订.md)。
- 自动分发、失败/未知结果：[PRD-05](../会议室录音系统_PRD_v1.3/docs/product/PRD-05-分发与审核.md)，文件名含历史“审核”，以正文全自动基线为准。
- 设备配置：[PRD-06](../会议室录音系统_PRD_v1.3/docs/product/PRD-06-设备配置与管理.md)。
- 用户、组织、角色：[PRD-07](../会议室录音系统_PRD_v1.3/docs/product/PRD-07-用户组织与权限管理.md)与ACL。
- 新接口/后端工作：从[技术阅读地图](../会议室录音系统_PRD_v1.3/docs/design/DES-00-实施设计总览与阅读地图.md)选契约、异步任务、数据一致性或认证专题；这些设计不代表服务已实现。
- 里程碑/真实接入/发布准备：[实施工作包](../会议室录音系统_PRD_v1.3/docs/delivery/DEL-01-里程碑与开发工作包.md)、[决策清单](../会议室录音系统_PRD_v1.3/docs/delivery/DEC-01-决策与实施准备清单.md)、[发布检查](../会议室录音系统_PRD_v1.3/docs/delivery/DEL-02-部署运维与上线检查.md)。只展开当前任务需要的部分。

## 历史与证据

当前真实实现归档范围与提交验证见[第一阶段归档提交](implementation/phase-one-commit.md)。

旧PRD v1.0–v1.2、根目录旧HTML和B/C比较实现已从当前分支移除，历史查询与外部ZIP归档见[仓库清理记录](repository/cleanup.md)。v1.3仍保留有效产品规划与设计规则，本期以第一阶段范围优先。

前端既有验证见[原型验证记录](../frontend/docs/design-lab/verification.md)。测试结果、截图是具体时点证据；选A并不等于所有业务、可访问性或设备要求已验收。
