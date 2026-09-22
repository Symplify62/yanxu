# 本地声纹运行环境

使用真实 WeSpeaker CNCeleb ResNet34-LM ONNX 模型进行声音特征提取、声音聚类和登记姓名匹配。API服务不加载机器学习依赖；通过本目录 `run.sh` 与独立Python进程交换本地JSON。此目录不使用或修改既有Qwen/`pcim-asr`环境。机器学习推理过程无网络调用。

## 安装与运行

在仓库根目录执行 `tools/voice-runtime/install.sh`。需要已安装uv及Python3.12（uv可获取对应解释器）；锁定依赖见 `requirements.txt`。WAV输入可直接读取；MP3/M4A/WebM等libsndfile不支持的容器使用本机ffmpeg解码。

环境和权重写入 `.local-data/voice-runtime/`，都不入Git。首次安装仅从公开供应商获取运行库和公开模型，不读取或上传已有会议/人员资料。模型下载校验失败时停止；不会接受替换权重。

服务和声音worker配置：

```dotenv
YANXU_VOICE_ENGINE_COMMAND='/absolute/path/to/yanxu/tools/voice-runtime/run.sh'
YANXU_VOICE_MODEL_VERSION=wespeaker-cnceleb-resnet34-lm:e7584940aeac8d55:kaldi80-v1
YANXU_VOICE_MATCH_THRESHOLD=0.75
YANXU_VOICE_MATCH_MARGIN=0.08
```

配置文件中的command若路径含空格，应让参数值包含shell式引号，例如 `YANXU_VOICE_ENGINE_COMMAND="'/Users/alec/My Project/tools/voice-runtime/run.sh'"`。执行使用shlex拆分参数而非shell执行。

在 `backend/` 下：

- 同机worker：`uv run python -m yanxu.voice.worker`；`--once`只领取并处理一次。
- 独立Mac worker：配置服务HTTPS地址 `YANXU_REMOTE_API` 和**独立的** `YANXU_VOICE_WORKER_TOKEN`，执行 `uv run python -m yanxu.voice.remote_worker`。本机联调允许loopback HTTP（Settings也须允许该联调地址），云端必须HTTPS。
- API和Mac两端的模型版本必须一致；ASR token、备份token与声音token不混用。
- 两种worker共用租约队列；不要为同一工作负载同时启动过多模型进程。旧owner、过期租约和声音/授权快照改变的结果不提交。

公开模型版本固定为：

- 官方仓库：[wenet-e2e/wespeaker](https://github.com/wenet-e2e/wespeaker)。
- 官方模型：[Wespeaker/wespeaker-cnceleb-resnet34-LM](https://huggingface.co/Wespeaker/wespeaker-cnceleb-resnet34-LM)。
- 文件：`cnceleb_resnet34_LM.onnx`，约26.5MB。
- SHA256：`e7584940aeac8d5512d875e58ce6c09ba4ddad65d8128e1dac0d93aadd087ebb`。
- 模型卡许可证为 Apache-2.0。WeSpeaker项目许可证副本见 `LICENSE-WeSpeaker.txt`；Kaldi fbank设置参考官方 [ONNX推理示例](https://github.com/wenet-e2e/wespeaker/blob/master/wespeaker/bin/infer_onnx.py)。独立环境第三方包各自按其许可证分发。

## 算法与结果边界

16kHz单声道 → WebRTC VAD → 80维Kaldi fbank（25ms/10ms、Hamming、无dither、均值归一化）→ 256维ONNX声音向量。

登记要求3至120秒PCM WAV，至少3秒有效语音，检查过低音量/明显削波/窗口一致性。`ready`表示可供匹配的特征已生成，**不证明音频只能属于一名真人、不证明本人身份、不用于登录认证**；本人姓名/声音/云端同意必须在登记前明确确认。

会议先对1.5秒滑窗、0.75秒步长做跨整场声音聚类，随后汇集同一簇最多30秒音频提取向量并比较登记档案；少于3秒或不一致的簇保留未知。对可识别簇，要求原始余弦相似度>=0.75且比第二候选至少高0.08。分数不是概率，全部阈值均未经过同事实录校准。不会因本场选了N人就强制把所有语音分配给N人。

管线版本 `voice-v2-cluster-first` 与模型/姓名/声纹版本/授权revision一起进入任务指纹。模型向量预处理版本改变必须重新登记；仅聚类算法改变可保留兼容向量，但要改管线版本并重新做归属。

这是本地可运行基线，不是成熟的多人重叠分离模型：重叠说话、短句、远距离、相似音色、跨设备/重采样差异可能误分或保持未知；没有可靠的重叠检测器，不承诺自动发现所有重叠。转写的一句话跨两个说话人时，服务器保留未知而不强行选一人；原ASR文本与时间不被引擎改写。

## 已运行的模型烟测

2026-09-22，在本机独立环境使用macOS离线TTS制作A/B登记及**不同文本**查询、未登记C查询，真实模型生成256维向量。它仅证明运行/拒绝/链路能力，不能估计真人会议准确率。

首次逐短窗直接认人受A样本重采样差异影响漏绑；对比发现1.5秒窗A余弦为0.653–0.758、整段0.788。改为先聚类再汇集后，在同一31.59秒A→B→A→B音频上，A为0.7861、B为0.9047，阈值未下调，同一人两次发言编号一致；跨人ASR段落仍未知。

证据在 `.local-data/evidence/identity-voice/voice-model/`。可重复步骤：用不同系统声音生成登记和不同文本查询，统一转换PCM16 WAV，先调用登记再将向量用于查询；报告原始分数与未知，不把合成样本当业务验收。真实同事实录、长会议、重叠和跨设备仍待专项验收。

## 私有存储与撤回

默认登记文件位于服务数据目录 `private-voices/`（目录0700、上传文件0600），不会进入公开recordings/云录音队列。特征与版本在服务私有数据库中保存；任何公开逐字稿都只输出编号。部署在阿里云后，这一私有目录就是云端档案来源；它必须加入受保护备份，而不是公开静态目录。

可选 `YANXU_VOICE_PRIVATE_BUCKET` 必须是与公共录音不同的七牛私有空间。每次上传先核验bucketInfo.private==1，之后核验ETag与长度；失败不转用公共空间。私有样本回听始终经过本服务授权接口，不签发永久公开链接。当前适配保留私有磁盘原件并做七牛镜像，未配置私有空间时不会调用七牛；未进行真实七牛私有桶验收。

撤回会移除有效档案、删掉登记向量与任务快照中的对应特征、删除本机样本、拒绝旧任务结果，已具名段落在授权接口也退回编号。七牛对象删除写入持久队列，声音worker继续重试；历史备份需按部署保留策略到期清除。撤回不改变原先已公开会议原音的访问规则。
