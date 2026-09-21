# REF-01｜来源与参考边界

## 1. 业务来源优先级

U-01至U-08来自本次对话用户的明确表述，逐项记录在BASE-01，是首期需求依据。本套所有具体状态/页面/安全和验收方法为作者在这些目标上提出的设计细化，均标为评审稿，不声称已经由用户逐条批准。

来源不能相互偷换：参考项目功能不等于本产品已实现，技术API不等于已获授权，模拟器通过不等于真机可靠，模板样例不等于真实会议数据。

## 2. 历史设备资料

HIST-01：用户上传的《Insta360 Wave API 文档与开发指南》，25页，存放在sources/HIST-01-Wave-API.pdf。第1至2页定义设备HTTP/MQTT接入并说明实时音频暂不支持，第19至21页定义录制文件上传。仅保存作历史参考；本次安卓首版不继承这些接口或鉴权算法，也不因此推断平板需要MQTT、Wave服务或厂家固件。

当前需求由用户后来明确的“安卓平板，可先模拟器开发”覆盖设备路线。此前的Wave开发交接包仍是旧范围资料，不在本包中作为有效需求复制。

## 3. 官方平台资料登记

核查日期：2026-09-20。只登记与本PRD相关的窄范围事实，不对外部网站后续不变作保证；实现具体API前需再次核查并冻结版本。

EXT-01｜Android MediaRecorder overview
https://developer.android.com/media/platform/mediarecorder
支持：系统提供音频采集/保存/播放接口及权限说明。局限：页面保留模拟器不能录音的提示，因此不能根据另一页的开关就宣布所有环境可录音。用于DES-03和验收边界。

EXT-02｜Foreground service types
https://developer.android.com/develop/background-work/services/fgs/service-types
支持：microphone前台服务类型、相应权限与后台启动条件。用于技术设计，不表示前台服务永远不会中断。

EXT-03｜Android Emulator extended controls
https://developer.android.com/studio/run/emulator-extended-controls
支持：可启用Virtual microphone uses host audio input；默认关闭且宿主可能要求权限。与EXT-01的表述差异保留，实际镜像测试决定该环境结果。

EXT-04｜Persistent work / Task scheduling
https://developer.android.com/develop/background-work/background-tasks/persistent
支持：可持久调度后台任务的框架能力。用于上传/恢复建议，不当作持续录音服务或立即执行保证。

EXT-05｜Sharing audio input
https://developer.android.com/media/platform/sharing-audio-input
支持：麦克风输入可能受其他应用争用及系统规则影响。用于“计时不等于已有效收音”的检测与真机验收要求。

EXT-06｜腾讯云：企业微信群机器人获取Webhook
https://www.tencentcloud.com/zh/document/product/1254/78645
支持：以企业微信5.0为例的消息推送/自定义消息推送创建路径和Webhook获取。不能由此认定用户实际组织与目标群已经开通，也不用于凭空填入消息限额或阅读回执。

EXT-07｜OpenAI：Custom instructions with AGENTS.md
https://developers.openai.com/codex/guides/agents-md/
核查时转向官方learn.chatgpt.com对应页面。支持：项目可通过AGENTS.md提供Codex工作规则。不能替代PRD、测试执行或用户生产授权。

EXT-08｜Android Lock task mode
https://developer.android.com/work/dpc/dedicated-devices/lock-task-mode
支持：专用设备锁定涉及管理配置和应用许可。第一版不是必须实现的硬件所有者功能。

EXT-09｜腾讯HiFlow：企业微信群机器人
https://hiflow.tencent.com/document/applications/wwx-robot/
支持：群Webhook可用于单向自动消息推送。本文不把其平台集成功能当作本项目已部署功能。

## 4. 未证实与不采用的外部推断

没有确认具体平板收音效果、任何开源项目当前版本可直接完整采用、指定云AI月价、最终真实群权限或访问地址。本包未运行产品测试，也未读取任何本机源码仓库。

企业微信开发者API入口本轮抓取失败，因此正文不硬编码由该入口推导的限额和详细错误码，留待实现适配时核查。历史对话引用的其他网页不得未经核查当作当前协议。

## 5. 使用引用的方式

独立Markdown引用U-xx、EXT-xx与HIST-01；合订本保留相同编号，来源位置在本章。页面/字段设计为本项目建议，不在厂商文档名下标注。随实现保存依赖版本和许可登记，但不把本包的来源说明当作法律意见。
