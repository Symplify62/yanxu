# 七牛云录音存储接入

2026-09-21 用户确认补齐阿里云域名、七牛云专用空间与 HTTPS，后端继续本机运行。独立空间 `yanxu-recordings`（华东－浙江、公开读取），使用 `audio.qjl666.xyz`；不改已有 www/video/mail，不部署公网后端，不提交代码。

## 实施与验证合同

- 新录音封存事务同时登记云存储任务；独立持久队列处理七牛上传，失败重试不阻断转写/AI，不删除本地原音。已有本地历史录音不自动批量发布。
- 服务端使用七牛官方 SDK、限定对象上传凭证、固定对象键和内容校验；凭证只存 Git 忽略的本机配置，异常只记录分类，不记录供应商请求/令牌。
- 云端对象验证成功且 HTTPS 文件域名配置完成后，匿名音频接口可跳转七牛回听；未就绪仍返回本地原音，下载保持附件语义。
- 单独的云同步状态与分析状态互不覆盖；本地运维命令查看/恢复云任务，不新增公开管理接口。
- 验证：旧上传/AI回归；失败重试、重启恢复、重复上传、云校验失败、云端读取/Range/下载及本地降级；新建小型合成音频实测云存储与 SHA256；不发布用户旧素材目录。
- 可见 UI 变更：不涉及。既有页面音频路径做实际浏览器回归。
- GitNexus已刷新，Store影响涉及API、worker、manage和测试；跨语言字段与框架路由覆盖由源码及接口测试补证。

## 云端配置与运行证据

- Ego Lite 实际创建并回读 `yanxu-recordings`。密钥页要求身份验证，用户本人完成后，凭证直接保存 `config/.env.local`（600、Git 忽略），未输出原值，没有更换/停用既有密钥。
- 阿里云新增 `audio` CNAME → `audio-qjl666-xyz-idvs1vd.qiniudns.com`；公共 DNS 回读一致。新增 `_acme-challenge.audio` TXT 用于证书验证，未改变旧记录。
- Let’s Encrypt 已签发并上传证书 `yanxu-audio-20261220`，有效至 **2026-12-20 12:08:15（UTC+8）**。七牛国内 CDN 域名状态成功，绑定专用空间、强制 HTTPS、HTTP/2、TLS1.2/1.3、Range 回源开启。
- 阿里云“我的ICP备案信息”中已核实 `qjl666.xyz` 有网站备案 `浙ICP备2025203545号-1`，现网站名称“一个用于学习的简单网站”。本次仅核对，没有变更主体、网站用途或提交言序 App 备案。现域名备案不替代言序后续公网应用上线验收。
- 七牛默认的 Kodo CDN 回源协议界面显示 HTTP，存储源站模式没有协议切换项；已验证的是客户端到 CDN 的 HTTPS，以及服务端 SDK 上传/管理 API 的 HTTPS，不宣称 CDN 内部回源全程 HTTPS。
- 流量告警“言序录音流量提醒”已启用，仅关联 audio 域名；5 分钟数据点流量高于 1 GB 时通知账号现有接收人（尾号5592）。控制台说明告警平均延迟15分钟、最长30分钟；这是提醒，不是硬性费用上限。没有为了测试发送通知或制造高流量。
- 本机 API 5189 已重启读取 `YANXU_STORAGE=qiniu`、`QINIU_DELIVERY_ENABLED=true`，独立云 worker 已启动，日志 `.local-data/logs/cloud-worker.log`。旧 ASR worker 保持运行。新录音封存自动入云队列，历史记录不自动扫描；因此主库云队列刚启用时为空是预期。
- 合成音频 32,044 字节，经真实上传→SDK云端长度/ETag核对→HTTPS GET/HEAD→Range206→附件下载，SHA256 一致。使用隔离的 `.local-data/cloud-smoke` 数据库，没有把用户历史会议发布到七牛。结果保存在 `.local-data/cloud-smoke/verification.json`。
- 后端 18 项测试通过；原本地页面真实服务 E2E 1 项通过；新云端页面 E2E 1 项通过，实际 Chrome 播放时间推进、读取 CDN、下载文件 SHA256 一致；移动截图 `.local-data/evidence/cloud-browser/audio-mobile.png` 已检查。可见 UI 代码变更不涉及。
- 浏览器回归入口：先在 backend 运行 `uv run python -m yanxu.check_storage`，再在 frontend 执行 `npx playwright test -c playwright.cloud.config.ts`。测试启动隔离 API 5190 并自动收尾，不影响主服务5189。
- 可提交的合成数据验证摘要见[云存储结果](../../backend/evidence/cloud-result-metadata.json)，不包含凭证或用户会议内容。文档导航检查与 diff 空白检查通过；未提交、推送或部署公网应用。

## 证书续期与回退

本次证书采用 Certbot 手动 DNS 验证，**尚未设置自动续期**。应在到期前（建议提前30天）重新签发并上传七牛，替换 audio 域名的绑定；不需要更改 CNAME。不能把“HTTPS已验证”理解为续期也已经自动化。

本机证书和账户位于 `.local-data/certbot`，私钥不得提交。重新签发流程：Certbot `certonly --manual --preferred-challenges dns --key-type rsa -d audio.qjl666.xyz`，沿用此目录下 config/work/logs；按新挑战更新 `_acme-challenge.audio` TXT，验证签发后到七牛证书管理上传并替换。当前 TXT 是已完成挑战，后续续期需要新值。自动续期需要另行配置受限 DNS 凭证及证书部署钩子，不能复用浏览器登录态假设可长期自动续签。

最初创建的0元 TrustAsia订单停留在补全信息，未提交虚构公司/联系人资料，也没有付费购买证书；实际使用的是上述 Let’s Encrypt 证书。

云分发故障：把 `QINIU_DELIVERY_ENABLED=false` 并重启 API，恢复本地原音播放/下载。若要停止新增云任务，另设 `YANXU_STORAGE=local` 并重启 API、停止云 worker；已有云文件不会被删除。此时仍需保留数据库与本地 assets，Kodo 副本不等于数据库灾备。

## 官方依据

- [七牛 Python SDK](https://developer.qiniu.com/kodo/sdk/python)
- [CDN HTTPS 配置](https://developer.qiniu.com/fusion/4952/https-configuration)
- [国内 CDN 域名备案要求](https://developer.qiniu.com/fusion/3880/the-domain-name-configuration-faq)
