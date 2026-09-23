# 阿里云接口与 Mac 转写部署

2026-09-21 用户确认按“现有阿里云服务器运行网站/API、七牛原音、Mac 转写、DeepSeek 分析”落地，目标是 Android 不依赖 USB 使用。授权部署本项目和必要域名/HTTPS，不购买升级、不覆盖已有业务、不批量发布旧会议、不提交代码。

## 切片与验证合同

1. 检查现有 ECS 业务、内存、磁盘、端口；以独立目录、系统服务和域名配置部署，可单独回退。先完成只读检查再修改远端。
2. 云端数据库为任务权威；Mac 主动 HTTPS 领取 ASR、心跳续租、提交结果。机器令牌保护内部任务接口，不是新增员工登录。只有云对象已验证才可领取；离线不丢任务、过期租约可重新领取、旧执行者不能覆盖新结果。云端 worker 只做 DeepSeek 分析。
3. HTTPS 公网入口 `yanxu.qjl666.xyz`，与现有 audio/www/video/mail 隔离。App 默认地址更新，保留本地录音和失败重试。旧安装不能未经检查就切换仍在上传的录音。
4. 七牛原音校验就绪后才可清理云端本地缓存；SQLite一致性备份与恢复说明。API加资源限制，内部密钥不出公开接口或日志。
5. 本地协议/租约/权限/缓存回退回归；公网 HTTPS 页面、App上传→七牛→Mac ASR→DeepSeek→匿名查看和回听下载；关闭 USB 转发验证真实手机路径。手机麦克风不由自动化擅自开启，可使用合成语音导入验证。

界面只改变服务地址默认值及必要部署信息，不改已确认视觉。记录浏览器/设备证据。源码、自动化、运行、上线分别记录。

## 当前状态

2026-09-23已从 `release` 提交 `f6d4964` 发布生产服务与版本化生产配置，运行与回退证据见[本页生产配置发布](#2026-09-23-生产配置发布)。2026-09-22账号、私有声音与说话人归属发布记录见[0.3.0发布验证](identity-voice-release.md)。下方首次上线验证小节保留历史时点。

公网部署已运行。服务器2vCPU/2GiB/40GiB/3Mbps，上海Ubuntu22.04；部署前实际可用内存1151MiB、根盘可用34GiB，仅发现frps监听7000/7500/8080及SSH。frps进程2764和原端口保留；未升级实例、重启服务器或改变已有安全组规则。

## 运行与恢复入口

- 公共网页/API：`https://yanxu.qjl666.xyz`，A记录指向现有ECS；公共页匿名查看/下载；账号工作台和新App支持组织者账号密码登录。`audio.qjl666.xyz`沿用七牛专用空间。
- 部署通过阿里云Workbench终端与文件传输完成。公网SSH握手被关闭，因此没有重置密码或更改SSH配置；仅临时加入的本次部署公钥已精确移除。配置经Workbench传入root专用700目录，安装到`/etc/yanxu.env`（600），传输副本已删除。
- 当前代码目录`/opt/yanxu/releases/20260923-production-config-f6d4964`，`/opt/yanxu/current`指向它；旧目录`/opt/yanxu/releases/20260922-self-password`保留回退。生产服务显式选择`YANXU_ENVIRONMENT=production`，非机密值来自`config/environments/production.env`，原`/etc/yanxu.env`（600）继续提供密钥。服务用户`yanxu`，数据`/var/lib/yanxu/data`，APK`/var/lib/yanxu/artifacts/yanxu-debug.apk`。API只监听127.0.0.1:5189，Nginx接公网80/443，保留原frps端口。无语音终态与旧记录恢复见[修复记录](no-speech-result.md)，App分发见[自动更新](android-updates.md)。
- 云服务：`yanxu-api.service`、`yanxu-analysis.service`、`yanxu-cloud.service`，均启用开机启动与失败重启；日志走`journalctl -u <服务名>`。`YANXU_WORKER_STAGE=analysis`保证服务器不运行本地ASR。
- Mac服务：`~/Library/LaunchAgents/cn.jiajian.yanxu.remote-asr.plist`，登录后自动运行并失败重启；工作目录`backend`，数据`.local-data/remote-cloud`，日志`.local-data/logs/remote-asr.log`。`launchctl print gui/$(id -u)/cn.jiajian.yanxu.remote-asr`查状态。不要与旧本地worker/旧库混用。
- 机器令牌`YANXU_WORKER_TOKEN`在本机`.env.local`与云端`/etc/yanxu.env`中一致，至少32字符；Mac仅主动发HTTPS请求，不公开本机端口。备份改用独立`YANXU_BACKUP_TOKEN`，声音任务用独立`YANXU_VOICE_WORKER_TOKEN`；ASR凭据不能下载身份/声音备份。配置变更后分别重启对应进程。
- 录音目前仍为App→ECS分片接收→七牛同步；尚未改成App直传七牛。同步会占用3Mbps服务器出网，长录音可能排队；Mac只领取七牛已校验的录音。
- 服务器保留7天已验证原音缓存；每日03:30 `yanxu-maintenance.timer`先做SQLite一致性备份，重新核对七牛文件hash/长度后才清理旧缓存。保留30份本机数据库快照；磁盘不足2GiB或无法预留上传/组装空间时拒绝新任务，App保留本地文件重试。
- Mac每日获取一次一致性数据库和未撤回私有声音的备份包，存`.local-data/remote-cloud/cloud-backups`（不入Git、600）；Mac离线时跨机副本会延迟。已实际下载新版包、验证SQLite与文件SHA，恢复后登录并回听私有样本。云对象与快照联合恢复，不依赖已过期的ECS录音缓存。
- 网站HTTPS证书有效至2026-12-20；服务器Certbot timer负责webroot续期，部署钩子校验并重载Nginx。`certbot renew --dry-run --cert-name yanxu.qjl666.xyz`已实际通过模拟续期。**七牛audio证书仍是此前手动DNS签发，尚未自动续期**，与网站证书分开维护。

## 2026-09-23 生产配置发布

- 发布包仅含`release`提交`f6d4964`的Web、后端和`production.env`，SHA256为`c690ea37042a1c3c79684e56b675c9fbb663b807543e93bb55b7e8d1e018987e`。后端139项测试、前端构建通过；在在线一致性数据库副本上启动新版本，配置身份、`quick_check`、8条旧录音和2个账号通过，新旧schema一致。
- 停止本项目三个生产服务及maintenance timer后，将全部生产数据逐文件复制并核对一致；备份位置为`/var/lib/yanxu/backups/production-config-20260923/switch/`，包含数据、原配置、旧current目标和现有APK。备份库`quick_check=ok`，切换前有8条录音和2个账号。仅给原配置增加`YANXU_ENVIRONMENT=production`选择器，密钥和七牛空间不变；切换后生产三个进程实际从新版本目录运行并带该环境标识。
- 线上API、账号工作台和Android 0.3.5旧App仍可访问；原有8条录音的ID、状态、SHA及原音Range 206逐项复核。生产管理员登录和受保护的用户／角色／声音接口通过，匿名管理接口仍返回401。私有备份接口重新下载2,979,840字节并通过数据库与两份声音文件校验。测试环境三个服务仍active。
- 新增1条明确标注的7.19秒合成验收录音`289bd63f-54d9-4bd8-83dd-a25dfba50953`：上传→七牛→Mac Qwen→DeepSeek→公共完成，回听、下载SHA256及Range 206通过；因此生产公共记录现为9条，原有8条未改。生产Android更新清单继续发布既有包名与0.3.1／versionCode 11，本轮不发布0.3.6 APK，也未开启手机麦克风。
- 证据和截图保存在忽略目录`.local-data/evidence/production-config-release-20260923/`。真实同事声纹准确率、长会、OEM后台与持续运行仍需专项验收。

回退此发布时先停`yanxu-api`、`yanxu-analysis`、`yanxu-cloud`和maintenance timer，保留切换后新增数据，再将`/opt/yanxu/current`指回旧目录、用`switch/yanxu.env.before`恢复`/etc/yanxu.env`并启动服务。新旧schema一致，优先保留当前数据库以免丢失切换后的录音；只有数据库损坏时才使用`switch/data`恢复，并先单独保存故障副本及新增记录。

## 首次上线验证（2026-09-21，历史）

- 后端22项测试通过：新增机器鉴权、仅领取云端就绪原音、ASR/分析分工、租约过期重领、旧owner写入拒绝、备份受保护、磁盘预留和缓存删除门禁。GitNexus对Store.claim存在动态接收者缺口，已按源码调用者和接口测试补证。
- 27.049938秒合成语音经公网真实上传→七牛→Mac Qwen→ECS DeepSeek→公共结果完成，转写6段；真实公网Chrome E2E通过列表、逐字稿、摘要、播放时间推进、Range206、下载SHA256、刷新与移动布局。
- Android测试版0.1.4已安装到ANA-AN00。用户本人解锁后，由App系统文件选择器导入同一合成音频；USB `adb reverse`已移除，手机经公网完成上传并显示转写/AI完成。USB仅用于安装、放置测试素材及界面自动化，没有承担App网络转发。
- 真机发现原下载限制会拦截七牛重定向，现仅额外放行`https://audio.qjl666.xyz/recordings/<id>/<hash>.<audio>`，其他协议、端口、用户信息、非音频路径仍拒绝；纯Java边界测试通过，原音播放进度实际推进，手机Downloads中的865676字节下载文件SHA256与原音一致。
- 三个言序云服务实际重启后，两条测试记录与完整分析仍存在；网站下载APK与本机已安装0.1.4包校验一致。没有以构建成功替代真机或公网验证。
- 公网测试记录仅含两条合成语音（CLI验收与手机验收），未迁移旧本地会议或原素材目录。证据摘要见[公网结果](../../backend/evidence/public-result-metadata.json)，截图存`.local-data/evidence/public`及`.local-data/deploy/phone-*.png`。
- 仍未覆盖：物理麦克风拾音、来电/锁屏/OEM后台、长时录音、压力测试与持续运行观察；Mac睡眠/关机会暂停新转写，但不影响已完成记录查看及云端接收排队。

## 回退

保留原Mac本地服务、原App测试包；新公网服务使用独立目录/服务名。替换前备份对应配置，回退只停用本项目服务与域名配置，不停止其他服务。云数据库/对象数据不因代码回退删除。

数据库恢复时停止三个言序云服务，保留当前数据库及WAL/SHM为故障副本，再把完整SQLite快照恢复到相同数据路径后启动；七牛原音不随之删除。先在隔离目录做quick_check、记录数和对象抽样核对，再切主服务。快照间隔为1天，未承诺零数据丢失；手机保留原音，可用于补回尚未同步或备份的录音。

首次上线时未提交或推送Git，服务器发布包由当时工作区的白名单文件构建；首次目录权限问题已修复，业务服务以非root用户运行。后续发布应生成新版本目录并沿用恢复入口；`deploy/provision.sh`是首次安装脚本，会写HTTP站点配置，不应不加检查地作为日常线上升级脚本直接重跑。
