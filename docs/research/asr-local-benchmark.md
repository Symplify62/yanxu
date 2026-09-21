# 本机ASR样本对比（2026-09-21）

## 结论

建议第一阶段以 **Qwen3-ASR-1.7B（本机MLX BF16）＋ForcedAligner-0.6B** 作为默认接入候选，Whisper large-v3 MLX保留对照。三个完整录音样本里Qwen更快，与配套钉钉稿的差异也更少。它仍需Android手机新录音、长录音覆盖与人工核对验证，未宣称生产准确率达标。

官方候选、运行路径与许可见[一手资料研究](asr-primary-sources.md)，本报告只给出实际本机结果。

## 测试条件

- 本机Apple M4 Max，128 GiB统一内存，macOS 27.0。
- 复用现有本地环境；未下载新模型。ASR和对齐进程由macOS sandbox-exec禁止网络访问，没有调用DeepSeek或任何云转写。
- 用户授权来源为`/Users/alec/钉钉 A1/听记导出`。发现169份audio.mp3，159份有非空配套转写。未修改原始素材。
- 相同16kHz/单声道PCM、相同VAD分段（最大60秒）、中文、无领域词表。Qwen与Whisper使用各自支持的解码/时间戳实现；不是同一推理架构。
- 先运行两个30秒诊断前缀，再逐个模型顺序运行完整样本。模型和系统缓存已暖，不是冷启动/高并发压测。
- 表中耗时为runner的准备、模型加载、ASR和对齐总耗时；不包括初次从源文件准备本次公共PCM样本的时间。进程启动外壳耗时另有少量开销。

## 完整录音对比

字符差异率为对配套**钉钉机器转写稿**的编辑距离/参考字符数，不是人工准确率。统一NFKC、小写和字母数字，忽略标点；没有做繁简转换、口语数字归一或人工纠错，所以这些差别也计入。

| 样本 | 音频时长 | Qwen总耗时 | Whisper总耗时 | Qwen参考差异率 | Whisper参考差异率 |
| --- | --- | --- | --- | --- | --- |
| S1 | 7分26秒 | 26.3秒 | 36.8秒 | 9.69% | 27.07% |
| S2 | 8分36秒 | 43.8秒 | 144.7秒 | 12.43% | 27.08% |
| S4 | 2分01秒 | 8.3秒 | 9.1秒 | 26.57% | 42.44% |

三个完整样本共约18分03秒，各运行两种模型，6次均完成。Qwen MLX峰值约7.0–7.1 GiB；Whisper约3.7 GiB，这是MLX分配峰值，不是整机总内存。OS最大RSS和进程峰值占用另存[测量JSON](asr-local-measurements.json)。

## 单独保留的S3诊断

S3是约104分钟源录音的1068.78–1209.87秒节选（2分21秒）。两引擎都执行完成，但共同VAD只选出1.3秒，输出极少。与126字参考稿差异约97.6%/99.2%，不能把这种执行成功当成有效内容覆盖。

为排除输入快速seek影响，重新完整顺序解码源文件再按PCM时间切片，VAD仍仅选出2秒。增益诊断后选出10.2秒，仍不足以确认参考的整段内容。尚未人工声学标注，原因可能涉及低声/远场语音、VAD阈值或参考时间轴，当前证据不能定责。该样本保留在测量JSON，标记diagnostic_only，不从报告中抹去，也不用于模型准确性排名。

随后补测S4完整短会议，以得到第三份完整录音对照；这种样本变更及原因在此显式记录。没有完成104分钟整场转写或长会议可靠性验收。

## 时间戳与说话人边界

Qwen在S1/S2/S4分别产生160/188/36个零时长对齐词，Whisper为13/17/2。工具已保留文本、合并可用字幕并列入复核。可生成时间戳不代表逐字声学边界已经准确，精确跳转需单独抽查。

这两路当前测试没有说话人分离模块。不能让DeepSeek猜姓名，也不应把占位的“说话人1/2”当真。说话人区分可按需求单独验证MOSS/pyannote等方案，见官方研究，不阻塞先实现基础文字转写。

## 可复查证据与复现

原音频/完整转写正文/参考稿/差异计算输出都在本机`.local-data/asr-research-20260921/`，已被Git忽略；只将不含正文的测量数据和结论入项目文档。输入SHA、权重revision及依赖版本在测量JSON与私有manifest中。

- 样本范围与源路径：本机`samples.json`。
- 原始输出：本机`qwen-S1`、`whisper-S1`等目录的`transcript.review.md`、`transcript.raw.json`、SRT/VTT、manifest与review-issues。
- 准备/比较脚本：本机`prepare.py`、`measure.py`；初轮任务记录`run-results.json`，S4后补运行有独立manifest与time日志。
- 运行器：`/Users/alec/.codex/skills/local-video-transcribe/scripts/run.sh`，两路使用`--max-seconds 60`，正式样本不使用limit-seconds。诊断前缀单独目录且partial_input=true。

复现命令形态（输出目录须新建或与原参数完全一致）：

```sh
bash /Users/alec/.codex/skills/local-video-transcribe/scripts/run.sh <本机样本.wav> --engine qwen --max-seconds 60 --output <新目录>
bash /Users/alec/.codex/skills/local-video-transcribe/scripts/run.sh <同一样本.wav> --engine whisper --max-seconds 60 --output <另一个新目录>
```

运行库：MLX 0.32.2、mlx-audio 0.5.4、mlx-whisper 0.4.3、silero-vad 6.2.1、onnxruntime 1.30.0；Qwen与Whisper都使用MLX社区转换权重，不是官方CUDA实现。具体权重revision以JSON为准。

## 下一步

1. 后端接入时先封装Qwen候选为可替换ASR服务；增加语音覆盖异常与结果过短的诊断，不能只凭返回200判定成功。
2. 用Android App的实际录音检查拾音、噪声、锁屏/后台、中断恢复和长时长；A1已有录音不能替代手机真机证据。
3. DeepSeek分析读取真实逐字稿和时间引用。配置已准备在[config说明](../../config/README.md)，未进行真实调用。
4. 如要报告真正识别准确率，先人工标注固定验证集；保持原始输出，不能拿机器稿一致性直接写成准确率。
