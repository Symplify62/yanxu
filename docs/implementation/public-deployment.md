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

公网部署已运行。服务器2vCPU/2GiB/40GiB/3Mbps，上海Ubuntu22.04；部署前实际可用内存1151MiB、根盘可用34GiB，仅发现frps监听7000/7500/8080及SSH。frps进程2764和原端口保留；未升级实例、重启服务器或改变已有安全组规则。

## 运行与恢复入口

- 公共网页/API：`https://yanxu.qjl666.xyz`，A记录指向现有ECS；匿名查看/下载，无员工登录。`audio.qjl666.xyz`沿用七牛专用空间。
- 部署通过阿里云Workbench终端与文件传输完成。公网SSH握手被关闭，因此没有重置密码或更改SSH配置；仅临时加入的本次部署公钥已精确移除。配置经Workbench传入root专用700目录，安装到`/etc/yanxu.env`（600），传输副本已删除。
- 当前代码目录`/opt/yanxu/releases/20260921-no-speech`，`/opt/yanxu/current`指向它。无语音终态发布及旧记录恢复见[修复记录](no-speech-result.md)。服务用户`yanxu`，数据`/var/lib/yanxu/data`，APK`/var/lib/yanxu/artifacts/yanxu-debug.apk`。API只监听127.0.0.1:5189，Nginx接公网80/443，保留原frps端口。
- 云服务：`yanxu-api.service`、`yanxu-analysis.service`、`yanxu-cloud.service`，均启用开机启动与失败重启；日志走`journalctl -u <服务名>`。`YANXU_WORKER_STAGE=analysis`保证服务器不运行本地ASR。
- Mac服务：`~/Library/LaunchAgents/cn.jiajian.yanxu.remote-asr.plist`，登录后自动运行并失败重启；工作目录`backend`，数据`.local-data/remote-cloud`，日志`.local-data/logs/remote-asr.log`。`launchctl print gui/$(id -u)/cn.jiajian.yanxu.remote-asr`查状态。不要与旧本地worker/旧库混用。
- 机器令牌`YANXU_WORKER_TOKEN`在本机`.env.local`与云端`/etc/yanxu.env`中一致，至少32字符；Mac仅主动发HTTPS请求，不公开本机端口。备份接口同样需要此令牌；公网匿名调用实测403。配置变更后分别重启对应进程。
- 录音目前仍为App→ECS分片接收→七牛同步；尚未改成App直传七牛。同步会占用3Mbps服务器出网，长录音可能排队；Mac只领取七牛已校验的录音。
- 服务器保留7天已验证原音缓存；每日03:30 `yanxu-maintenance.timer`先做SQLite一致性备份，重新核对七牛文件hash/长度后才清理旧缓存。保留30份本机数据库快照；磁盘不足2GiB或无法预留上传/组装空间时拒绝新任务，App保留本地文件重试。
- Mac每日获取一次云数据库快照，存`.local-data/remote-cloud/cloud-backups`（不入Git、600）；Mac离线时跨机副本会延迟。已实际下载快照并验证SQLite quick_check和业务记录存在。云对象与快照联合恢复，不依赖已过期的ECS录音缓存。
- 网站HTTPS证书有效至2026-12-20；服务器Certbot timer负责webroot续期，部署钩子校验并重载Nginx。`certbot renew --dry-run --cert-name yanxu.qjl666.xyz`已实际通过模拟续期。**七牛audio证书仍是此前手动DNS签发，尚未自动续期**，与网站证书分开维护。

## 新鲜验证

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

本次未提交或推送Git。服务器实际发布包由当前工作区明确白名单文件构建；首次目录权限问题已修复，业务服务以非root用户运行。后续发布应生成新版本目录并沿用恢复入口；`deploy/provision.sh`是首次安装脚本，会写HTTP站点配置，不应不加检查地作为日常线上升级脚本直接重跑。
