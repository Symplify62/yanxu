# 言序本地后端

API＋独立worker＋SQLite WAL＋持久音频。公网运行见[部署记录](../docs/implementation/public-deployment.md)：阿里云API/分析/云同步，Mac远程转写。本页以下启动命令默认指本机旧测试环境，数据在`.local-data/server`，不入Git；ASR依赖`~/.local/share/pcim-asr`的MLX环境。

## 启动

在本目录：

```sh
uv sync
uv run uvicorn yanxu.api:create_app --factory --host 127.0.0.1 --port 5189
# 另一个终端，在同目录
uv run python -m yanxu.worker
```

公共页面需先在frontend执行`npm run build`。访问 http://127.0.0.1:5189/ 。API只暴露公共记录和归档音频，不挂载项目目录、配置、ASR日志或原始测试目录。

Android USB联调使用`adb -s <设备ID> reverse tcp:5189 tcp:5189`，App服务地址填`http://127.0.0.1:5189`。若改为局域网联调，显式使用LAN监听地址并在App填Mac地址；当前未开放LAN或公网监听。

## 接口

- POST `/api/recordings`：client_id、title、total_bytes、sha256、extension、interrupted。返回id、uploadToken、chunkSize。
- GET `/api/uploads/{id}`：查询已收分片；PUT `/parts/{number}`提交原始字节；POST `/complete`封存。上述写入会话操作都要求X-Upload-Token，保护单次上传，不是用户登录。
- GET `/api/recordings?q=&filter=all|complete|processing&limit=30&offset=0`：匿名分页查询。
- GET `/api/recordings/{id}`：状态、真实转写、分析、音频就绪和中断标识。无client_id、token、服务器路径。
- GET/HEAD `/api/recordings/{id}/audio`：回听，支持Range；`?download=true`下载原件。
- GET `/api/health`：进程与配置存在性，不证明外部供应商一直可用。

本地导入验收样本可从根目录执行`python3 tools/import_recording.py <本地音频> --title <标题>`，走与App相同的上传协议。不会读取整个素材目录或自动批量调用模型。

## 运行边界

- 文件和队列落盘；worker单实例锁＋数据库租约/heartbeat，失败最多3次退避，永久失败保留原音与已完成阶段。转写期间关闭页面不影响worker。
- 本地ASR进程禁网。语音覆盖异常或无语音报错，不用空摘要假装完成；逐字对齐和说话人分离不是本次已验收能力。
- 词级结束时间允许至多20ms的末尾越界修正，原始时间与修正记录保留；其他异常仍拒绝。遇到同类失败及源码指纹变化后的分段缓存恢复，先读[边界修复记录](../docs/implementation/asr-boundary-recovery.md)。
- DeepSeek结果经JSON/证据ID校验，长文本分段分析后汇总；成功的分段缓存绑定转写、提示词和模型配置。外部超时仍可能造成重复计费，未承诺供应商exactly-once。
- 默认上传块1MiB、单文件2GiB、最多30条未完成记录，AI每日token软额度200000（UTC日界，按字符估算预留输出再核实际用量）。可通过`YANXU_MAX_UPLOAD_BYTES`、`YANXU_DAILY_TOKEN_BUDGET`及数据目录配置调整。它们是技术资源边界，不是已验证的无限长录音能力。
- API与worker启动后读取配置；改key/额度需重启。恢复数据库需同时恢复对应assets目录，不能只备份sqlite文件。当前单机本地实现，不支持多个主机共享SQLite。

## 检查

`uv run pytest -q`执行协议、文件校验、匿名查询、预算、任务阶段/租约恢复测试。`uv run python -m yanxu.check_deepseek`使用很小的合成文本验证真实连接，会发生一次付费API调用。真实样本与UI/设备证据见[实施记录](../docs/implementation/phase-one-live.md)。

依赖修复后，在后端目录用`uv run python -m yanxu.manage retry <记录ID>`恢复失败阶段；该操作只允许已失败任务，不暴露成匿名HTTP接口，也不重新生成已完成记录。

## 七牛云录音存储

启用条件与实测状态见[七牛接入记录](../docs/implementation/qiniu-storage.md)。`config/.env.local` 填七牛 AK/SK、空间、HTTPS 文件域名，设置 `YANXU_STORAGE=qiniu` 后重启 API。独立启动 `uv run python -m yanxu.cloud_worker run`；转写 worker 保持原命令。

- 新录音本地封存与云队列写入为同一事务。云同步失败最多退避重试 8 次，与 ASR/AI 队列分开；进程重启继续未完成任务，本地原音始终保留。
- `uv run python -m yanxu.cloud_worker status` 查看云队列。停止云同步进程后用 `retry <记录ID>` 恢复失败；`enqueue <记录ID>` 是显式发布既有原音，不会自动扫描旧素材或历史记录。
- `QINIU_DELIVERY_ENABLED=true` 仅在 HTTPS 实测完成后启用。已校验云对象的音频接口跳转七牛，未同步完成的仍提供本地回听/下载。运行期间云域名故障时设置 `false` 并重启 API，立即恢复本地分发；没有承诺重定向后的浏览器自动降级。
- `uv run python -m yanxu.check_storage` 使用隔离数据库及约 32 KB 合成 WAV 验证真实上传和云完整性；启用分发时额外检查 HTTPS、Range 206、下载附件及 SHA256。不会调用 ASR/DeepSeek 或发布现有会议。
- SDK 上传、管理请求强制 HTTPS。对象键含录音 ID 和 SHA256，禁止覆盖；上传后核验七牛 ETag 和长度。凭证不返回前端，不打印原始供应商异常。
- 上述保留全部本地原音适用于旧本地测试环境。新公网环境采用云主库、远程转写与7天缓存清理，实际差异、备份和恢复以[公网部署记录](../docs/implementation/public-deployment.md)为准。
