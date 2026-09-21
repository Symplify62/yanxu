# Android 自动更新

用户于 2026-09-21 选择“尽可能自动安装，必要时才确认”。沿用当前包名与签名，升级保留本地录音和连接设置。旧 0.1.5 需先覆盖安装一次更新能力；不靠清空数据或卸载升级。

## 行为与页面

- 默认启用自动更新；启动/回到前台检查，后台由有网络约束的持久任务周期检查。下载就绪且无录音、无上传时，通过系统安装器请求自行更新。
- Android 12+ 请求免确认；系统返回需要确认时，前台提示“确认安装”，后台发更新通知。未允许本应用安装更新时提供系统授权入口，不绕过系统权限。
- 设置增加“应用更新”：当前版本、自动更新开关、简短状态和“检查更新/确认安装/允许安装”操作。正常无新版本不反复弹窗；失败保留当前可用版本。
- 正在录音（含暂停）或上传时延后安装；检查/下载失败可重试。后台安装成功不擅自拉起界面，下次打开显示新版本。

## 分发与安全边界

- 更新源固定为 `https://yanxu.qjl666.xyz/app/update.json`，不跟随用户填写的业务测试服务地址改变。
- 版本清单包含版本号/名称、包名、最低系统版本、下载地址、大小、SHA256、更新说明。APK 使用版本与哈希命名的不可变路径，先上传文件再原子发布清单，保留旧版本。
- 客户端只接受指定 HTTPS 域名和 APK 路径，拒绝跳转到其他来源；限制文件大小，下载完成校验长度/哈希、包名、版本和当前安装签名，再交系统安装器验证安装。拒绝降级及不同签名。
- 仅发布现有测试签名的升级包；密钥不入仓库。正式分发签名迁移需单独设计，不能随意换签名导致现有安装无法覆盖升级。

## 实施与验收合同

使用 verified-code-change 与 ai-verification-guardian 标准；GitNexus 查询 MainActivity/LocalStore/UploadJob/API影响，动态安卓生命周期以源码和设备证据补齐。

验证后端清单/下载边界与版本发布；Java纯逻辑测试校验来源、版本、校验和与安装时机；Android构建检查。专用5560模拟器先保留0.1.5录音/设置基线，再覆盖安装更新能力，发布更高版本并通过App自身更新，核对版本、签名、录音字节与设置。覆盖自动检查/下载、系统确认或免确认结果、无更新、关闭自动更新、异常包拒绝和录音保护；不通过ADB冒充App升级。

涉及原生UI，需要模拟器截图。没有物理手机在线时不宣称已验证华为/OEM免确认能力。发布从release已验证提交进行；服务器沿用现有部署和备份方式。

## 平台依据

Android允许满足条件的自更新请求USER_ACTION_NOT_REQUIRED，但仍要求处理STATUS_PENDING_USER_ACTION；应用需安装来源授权，不能保证所有版本和OEM静默更新。[SessionParams](https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams#setRequireUserAction(int)) · [PackageInstaller状态](https://developer.android.com/reference/android/content/pm/PackageInstaller#STATUS_PENDING_USER_ACTION) · [安装来源授权](https://developer.android.com/reference/android/content/pm/PackageManager#canRequestPackageInstalls())。

## 验证与发布结果

已实现更新客户端、系统安装器会话、前台设置与后台任务、版本清单/不可变下载接口及发布打包工具。自动关闭时取消后台任务；开启立即重新检查；下载中断可恢复。录音、导入及待上传文件保护共用安装门禁。

本地：后端39项通过；Java来源/完整性/身份/降级/忙碌门禁测试通过；Android与独立测试APK构建通过。专用5560模拟器上的Instrumentation已验证真实签名读取、拒绝异签名APK、拒绝版本矛盾、录音/导入保护及中断下载状态恢复；测试APK与测试密钥不随产品发布。

已保留0.1.5的4个本地录音文件哈希与业务地址作为覆盖升级基线。公网发布及0.1.6→0.1.7自更新结果待补充。

后续发布：在release构建递增versionCode的新APK，用 `tools/package_android_update.py --help` 准备分发文件，`--previous-apk` 必须指向当前已发布包以验证同签名和版本递增。先传入清单指定的releases文件并验证SHA256，最后原子替换android-update.json和旧下载入口；既有版本文件保留，不以同versionCode覆盖已发布版本。
