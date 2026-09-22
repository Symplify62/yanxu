# 0.3.0 账号与声音发布验证

2026-09-22用户确认提交、合入并推送release、部署阿里云、最后发布Android更新。源代码与本地实施边界见[实施记录](identity-voice-delivery.md)。

## 已发布版本

2026-09-22后续密码规则更新已发布：最低6个字符，无字符组合要求；发布源为release合并提交`ada8b1ee49a591d8959ebc9f423cc23549df8bb6`（[PR #9](https://github.com/Symplify62/yanxu/pull/9)），当前目录`/opt/yanxu/releases/20260922-password-six`。只更新账号校验和页面，未修改现有密码、数据库结构或Android安装包；发布前备份在`/var/lib/yanxu/backups/password-six-20260922/`。全后端113项、浏览器创建/重置/登录与构建通过；生产验证6位数字/字母/符号通过请求校验仍要求认证、5位返回422，线上页面资源已更新。以下0.3.0大版本发布记录保留当时时点。

- 功能提交 `21a22128fec27e466ea66778b5e33d9a62cbabc6`，通过 [PR #7](https://github.com/Symplify62/yanxu/pull/7) 合入release；实际服务来源为合并提交 `096b0e37701ae3e94041c0ef95635aa088abd004`。
- 公网工作台：<https://yanxu.qjl666.xyz/account.html>；公共记录：<https://yanxu.qjl666.xyz/>。
- ECS current：`/opt/yanxu/releases/20260922-identity-voice`；目录内SOURCE_COMMIT与上述release来源一致。旧`20260921-updates`目录保留。
- API、analysis、cloud及maintenance timer均active。云端仅运行API/分析/存储；Mac保留remote-asr并新增`cn.jiajian.yanxu.remote-voice` LaunchAgent。
- APK为0.3.0/code10，106272字节，SHA256 `083d3de89184a142b0c40c658432426d3bfa66476e37d853c49c1f2b9eb8146b`。与旧0.1.7保持同包名、同签名。
- 更新清单与旧下载入口均已发布并通过公网下载校验；不可变文件为`/app/releases/yanxu-10-083d3de89184.apk`，清单最后原子替换，保留旧code8文件。首次安装/手动升级入口为<https://yanxu.qjl666.xyz/app/yanxu-debug.apk>。

## 迁移、备份与回退

先在旧SQLite一致性副本迁移，然后在停用三个言序服务与maintenance后再次备份、迁移实际库。对recordings、jobs、parts、cloud_objects、usage的原有列逐项比对：7条记录、7项任务、67项分片、7项云对象、5条用量完整保留；旧状态5 complete、2 no-speech，SQLite quick_check通过。功能schema为core=2、identity=1、voice=2。

升级前一致性数据库、配置、Nginx、旧APK/清单、assets、uploads与原有private-voices备份位于服务器`/var/lib/yanxu/backups/identity-voice-20260922/switch/`；预演副本位于同级prepare。目录700、敏感文件600。发布脚本与状态记录受root保护；临时上传的管理员/机器凭据文件和含凭据压缩包已经删除。

备份凭据与ASR、声音凭据分离。`/internal/asr/backup-bundle`包含一致性SQLite和未撤回声音样本。Mac每日下载后实际恢复验证再保存，ECS/Mac均保留30份；原音继续由七牛恢复。超过数据库512MiB/单样本16MiB/总包2GiB时明确失败，不记作备份成功。

实际公网备份为2979840字节、包含2份合成声音；SHA256 `dafbab3b5d21f7eab081eb9c771d6ab67983523889710fa882279f3138884d41`。本机恢复到新目录后，用原管理员登录、两份私有样本回听SHA与上传原件相同。没有仅凭备份下载完成就声明恢复成功。

生产已经开放新写入，后续回退应先停接新写入并保留新版数据库与私有样本，使用已验证的旧快照恢复旧程序，同时单独保留升级后增量；不能只切旧代码或覆盖新库。已安装code10的App不能自动降级，问题修复使用更高版本。

## 公网业务验收

只新增明确标注的合成验收人物甲乙与一条31.591375秒录音，不使用真实同事素材；既有7条公共记录ID及音频SHA保持不变。

1. 真实管理员登录、云人员建立、本人声音/姓名/云同意验证、私有登记与生成通过。甲样本75秒、2400044字节，验证生产Nginx新16MiB声音入口生效。
2. App协议对应的managed创建、分片封存、七牛同步、Mac Qwen、独立声音worker、ECS DeepSeek真实完成。测试记录为`c9f52dff-af73-4dce-a1e1-e5c8e9bef7fb`。
3. 六段逐字稿中甲乙各两段具名，两段跨人保留未识别；公共接口只返回编号且没有人员/档案ID与私有绑定，受控接口返回授权姓名。匿名声音接口401；错误类别机器凭据403。
4. 公共Range206和下载SHA验证通过，真实浏览器音频播放进度推进。浏览器登录后实名与退出后的公共编号截图均已核验，测试浏览器工作空间已关闭。
5. 本机预检全后端106项、前端30项和完整构建通过；真实工作台9项浏览器用例（8真实API、1状态响应模拟）通过。Android本机/云接口、权限与资料隔离检查见实施记录。

声音匹配分数不是概率。以上合成实测证明真实链路、隐私边界和恢复能力；尚未证明真实同事会议准确率、多人重叠、远距离、长会议或各OEM免确认安装。

## Android自行升级验收

专用新AVD `Yanxu_Update_030_API36` / emulator-5562从0.1.7/code8开始；既有5554和5560未操作。关闭自动更新并导入4秒合成录音到隔离本地服务，形成非空音频、元数据和设置基线。随后在App中开启自动更新，完成公网清单检查、下载和系统安装。首次安装来源授权及Play Protect扫描按系统要求确认；扫描显示安全后安装成功，没有绕过系统保护，也没有使用ADB安装新版。

最终实际读取版本0.3.0/code10，installerPackageName和initiatingPackageName均为`cn.jiajian.yanxu`；已安装APK的SHA与公网发布包一致。升级前后128044字节WAV、283字节meta及连接设置文件的SHA全部一致，业务地址保持`http://10.0.2.2:5197`，手动开启后的automatic=true保留。新版界面显示旧录音已上传和应用更新0.3.0。证据保存后，仅关闭本轮新建的5562模拟器，既有设备不变。

本次证明App自动检查/下载、自身发起覆盖安装以及数据保留；这台模拟器首次安装仍需要系统确认，不承诺所有安卓设备均静默安装。

## 证据与恢复入口

本次详细日志、截图、校验和备份均在被忽略的`.local-data/evidence/identity-voice-release/`，不把凭据或私有数据库提交Git：

- `preflight.md`、`apk-verification.json`、`published-apk-verification.json`：构建、签名、发布文件。
- `server-final-snapshot.txt`：真实current、SOURCE_COMMIT、服务状态及备份完成标记。
- `production-smoke-result.json`：公网处理、权限、原音完整性、旧记录与备份恢复。
- `production-private-transcript.png`、`production-public-transcript.png`：真实浏览器对照。
- `android-update/`：独立设备升级基线与终态。

生产首位管理员通过标准输入安全初始化，独立于本地测试库；登录资料只保存在用户本机受保护交付文件。服务器声音原件不进入公开七牛桶。配置与模型权重不随Git发布。
