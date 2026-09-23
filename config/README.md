# 本地服务配置

## 环境配置

版本化的非机密配置位于 [`environments/`](environments/)：`development.env`、`testing.env`、`production.env`。启动后端时显式设置 `YANXU_ENVIRONMENT` 选择一份配置；未设置时继续使用旧本机 `.env.local`，以兼容正在运行的服务。测试和生产的入口、七牛空间、音频域名、Android 包名与更新来源以所选文件为准，跨环境覆盖会导致启动失败。

密钥、服务令牌与密码保存在各环境独立的私有文件，后端可通过 `YANXU_SECRET_FILE` 读取权限 600 的绝对路径文件；systemd 可通过对应的 `EnvironmentFile` 注入。Android 构建用 `-PyanxuEnvironment=development|testing|production` 选择同一组非机密配置，默认生产；测试版以独立包名与生产版共存。实际部署与验收边界见[环境隔离](../docs/implementation/environment-separation.md)。

账号与声音新增配置见[实施与运行说明](../docs/implementation/identity-voice-delivery.md)。初始化管理员通过终端标准输入设置密码，无默认密码；声音worker和数据库备份各用独立凭证。模型安装在独立环境，公用录音七牛空间保持原用途。

用户已指定DeepSeek做转写后的文本分析。填写本机`config/.env.local`中的`DEEPSEEK_API_KEY`即可准备好密钥；这个文件被Git忽略，不放到前端、不提交。供他人克隆的空模板是[.env.example](.env.example)。

后端已读取此配置，并完成小样本与真实转写文本的DeepSeek调用。ASR仍在本机禁网运行；只有后续分析会将转写文本发送到用户指定的DeepSeek。修改配置后需重启API和worker。此前ASR选型测试没有调用云服务。

模型默认`deepseek-flash`，可改为账号支持的其他模型。2026-09-21官方文档当前列出`deepseek-flash`和`deepseek-v4-pro`，接口地址为`https://api.deepseek.com`；没有沿用过时的deepseek-chat名称。[DeepSeek官方首次调用说明](https://api-docs.deepseek.com/zh-cn/)

配置约定：key必填；base_url为服务地址；model是API模型ID；timeout_seconds为后端请求超时上限。未来读取器应在缺key时明确报告未配置，不退回固定样例冒充真实分析；不得把key打印到日志。

## 七牛配置

空模板包含 `YANXU_STORAGE`、`QINIU_ACCESS_KEY`、`QINIU_SECRET_KEY`、`QINIU_BUCKET`、`QINIU_PUBLIC_BASE_URL`、`QINIU_DELIVERY_ENABLED`。本机真实凭证只填 `.env.local`（权限 600），不得用 `VITE_` 前缀或放进 Android 资源。已有 DeepSeek 配置需原样保留。

`YANXU_STORAGE=local` 保持原有本地行为；`qiniu` 为新录音登记云同步任务。`QINIU_DELIVERY_ENABLED=false` 时只做云副本，网页仍从本地接口回听；HTTPS 域名验证成功后再开启云分发。上传任务有独立进程，见[后端说明](../backend/README.md)；当前资源与证书状态见[接入记录](../docs/implementation/qiniu-storage.md)。
