# 开发、测试与生产环境隔离

## 范围与当前事实（2026-09-23）

用户确认建立真机可访问的测试环境、分开测试与生产的配置和更新入口，并在有管理权限的 App 个人设置提供后台入口。`release` 仍是唯一发布来源；新环境不迁移生产账号、录音或声音样本。

当前生产入口为 `https://yanxu.qjl666.xyz`，ECS 只有一台 2 vCPU／2 GiB 实例；Workbench 实测约 1.0 GiB 可用内存、33 GiB 可用磁盘。生产数据在 `/var/lib/yanxu/data`，API 监听本机 5189；Mac 运行生产 ASR 与声音远程 worker。本机 5189 是旧测试服务，5198 是隔离的本机联调服务，二者均不是可供同事长期使用的测试环境。

新版本的非机密配置以 `config/environments/{development,testing,production}.env` 为执行来源。测试入口 `https://test-yanxu.qjl666.xyz`、测试音频域名 `https://audio-test.qjl666.xyz` 和独立七牛空间 `yanxu-test-recordings` 已接通；当前生产服务仍运行旧部署和 `/etc/yanxu.env`，尚未切换到版本化生产配置。

`audio-test.qjl666.xyz` 的 Let's Encrypt 证书已绑定并实测 HTTPS 回听、Range 206 和原件 SHA256，有效期至 2026-12-22。它采用手动 DNS 验证，没有自动续期钩子，须在到期前重新签发、上传和切换。测试应用域名的证书也有效至 2026-12-22；ECS 上已有 `certbot.timer` 和成功续期后重载 Nginx 的 deploy hook，尚未执行续期演练。

## 目标边界

| 项目 | 开发 | 测试 | 生产 |
| --- | --- | --- | --- |
| 入口 | 本机回环 | 独立 HTTPS 域名 | `https://yanxu.qjl666.xyz` |
| Android | 独立包名与标识 | 独立包名、默认测试服务、独立更新清单 | 既有包名、生产服务与更新清单 |
| 数据 | 本地可丢弃 | 独立 SQLite、录音、声音档案和备份 | `/var/lib/yanxu/data` |
| 音频存储 | 本地 | 独立七牛测试空间与域名 | 现有生产七牛空间与域名 |
| 凭证 | 本机私有文件 | 独立服务／worker 凭证 | `/etc/yanxu.env` 等既有生产凭证 |

仓库只保存非机密配置：环境名称、域名、包名、服务端口、目录和存储空间名称。真实 API Key、七牛密钥和 worker token 始终放在忽略文件或服务器 600 权限的环境文件，不进入 Android、Git 或前端资源。测试服务已显式加载 `testing.env` 与 `/etc/yanxu-test.env`；未来生产升级时才显式加载 `production.env` 与生产机密文件。两套身份和资源配置冲突时启动失败。

当前测试密钥文件复用既有 DeepSeek／七牛供应商账号凭证，但测试 worker、备份和声音处理令牌已独立生成。测试资源由固定测试空间和服务端配置隔离；供应商凭证本身尚未做到独立受限，不能把此状态描述为凭证层完全隔离。

## 实施切片与验证

1. **配置合同**：创建版本化开发、测试、生产配置，并让后端、Android 与更新清单从同一环境选择读取。验证生产默认包保持既有身份，测试包有独立应用 ID、服务地址及更新来源；交叉来源、跨环境更新与错误配置失败。
2. **测试服务**：在现有 ECS 上用独立用户、目录、SQLite、systemd 单元、Nginx 站点和 HTTPS 域名运行。先量服务内存，确认剩余容量；不得覆盖 `/opt/yanxu/current`、`/etc/yanxu.env` 或生产数据。独立七牛空间用于测试原音；Mac 测试 ASR／声音 worker 使用独立数据目录、锁文件、凭证及 launchd label。
3. **管理入口**：仅有管理权限的账号在 App 个人设置看见“管理后台”，打开所选环境对应的网页工作台；Native token 不传给浏览器，网页单独登录。
4. **隔离验收**：用合成账号、音频和声音样本在测试环境完成登录、录音、转写、AI、声纹归属、公共编号／授权姓名、更新清单检查。核对生产人员／录音数量、服务和更新清单未变。测试 App 与生产 App 可同时安装，互不读取对方数据。物理麦克风识别准确率需另用真实同事样本验收。

证据放 `.local-data/evidence/staging-environment-20260923/`。每个阶段记录实际服务、版本、端口、数据目录、SHA、健康检查和回退入口；没有真实证据的项目保持待验状态。

## 运行验证（2026-09-23）

- ECS 测试版本位于 `/opt/yanxu-test/releases/20260923-env-separation`，以 `yanxu-test` 用户运行 API／分析／云同步和维护 timer，数据位于 `/var/lib/yanxu-test/data`；公网健康检查正常。重跑修正后的部署脚本也通过。生产三个服务仍为 active，生产健康检查正常，公共记录数仍为 8，生产更新清单仍指向既有包名和 versionCode 11。
- 测试公共记录现有 2 条合成语音。匿名录音已自动完成转写、DeepSeek 分析和七牛原音分发，回听／下载的 SHA256 与本机原件一致。合成声音档案经独立 Mac 测试声音 worker 处理为 `ready`；具名测试录音的公共逐字稿只显示“说话人 1”，受控逐字稿显示“合成声线A”。这些合成样本证明链路，不代表真人会议识别准确率。
- 测试管理员 `yanxu_test_admin` 的密码仅在本机权限 600 的 `.local-data/credentials/staging-admin.txt` 中，服务器初始化临时副本已删除。账号登录、用户管理接口和网页工作台已验证；华为手机同时装有生产包和 `cn.jiajian.yanxu.testing` 测试包。测试 App 可见测试公共记录，登录后个人设置出现“管理后台”并打开测试域名的网页登录页。手机麦克风未在本轮开启；实际手机采音、长会与同事声纹效果仍待专项验收。
- 测试更新清单为 versionCode 16，下载 APK 的哈希与本机测试包一致。测试 Mac ASR／声音 LaunchAgent 使用独立标签、数据目录和 token；云端独立备份已由测试 ASR worker 拉取并校验。

## 部署与回退入口

- 测试服务源包包含 `backend/yanxu`、锁文件、`frontend/dist`、环境配置和 `deploy/testing`，放到 `/opt/yanxu-test/releases/<版本>`。测试密钥放 `/etc/yanxu-test.env`，权限 600；以 root 执行 `deploy/testing/provision.sh <测试版本绝对路径>`，先开放 HTTP ACME challenge。证书就绪后执行 `deploy/testing/activate-https.sh`，再验证公网健康、Web 登录和音频 HTTPS。
- Mac 测试 worker 使用 `.local-data/credentials/staging-worker.env`（600），运行 `python3 tools/install_testing_workers.py` 建立独立的 `cn.jiajian.yanxu.test-remote-*` LaunchAgent；数据位于 `.local-data/staging-worker/`。生产 worker 标签、数据和令牌保持独立。
- 回退测试版本：将 `/opt/yanxu-test/current` 指向上一个已验证测试版本，重启 `yanxu-test-*` 服务；需要暂停测试时仅停止 `yanxu-test-*` 和两个测试 LaunchAgent。生产的 `/opt/yanxu/current`、`yanxu-*` 服务及 `release` APK 清单不参与测试回退。
