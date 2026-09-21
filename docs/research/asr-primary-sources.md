# 本地中文多人会议 ASR：一手资料核查

核查日期：2026-09-21。用途：Android App 负责采音和可靠保存，Mac 本机先验证后端转写，DeepSeek 负责取得转写后的文本分析；当前本地开发阶段不引入登录。本文是资料研究和选型建议，不是模型实测报告，也不证明 Android 录音、后端、真实会议转写或发布已经完成。

## 本轮优先对比

优先比较 **Qwen3-ASR-1.7B + Qwen3-ForcedAligner-0.6B** 与 **Whisper large-v3**。理由是中文/方言与术语支持值得评估，同时需要一个可在 Apple Silicon 上运行的独立模型基线；这不是准确率排名。主任务已反馈本机存在这两组 MLX 权重及固定 revision，因此本轮先复用现有资产，不为了研究重新下载。具体运行库、转换来源、revision、耗时和输出以主任务实测记录为准；第三方 MLX 转换不能标成 Qwen/OpenAI 官方运行时。

Whisper **large-v3-turbo** 与 Qwen **0.6B** 是后续降低等待时间和资源占用的候选。Turbo 是独立权重，不能把 large-v3 的本轮结果写成 turbo 的结果。OpenAI 将 turbo 定位为 large-v3 的加速版本；其官方速度表基于 A100 英语测试，不能换算成本机中文会议速度。[OpenAI 模型说明](https://github.com/openai/whisper#available-models-and-languages)

## 候选能力与边界

| 候选 | 中文会议、语言与术语 | 长音频与时间戳 | 说话人能力 | 本轮位置 |
| --- | --- | --- | --- | --- |
| Qwen3-ASR 1.7B / 0.6B | 官方列出 30 种语言和 22 种中文方言/口音；可指定中文或自动识别。新原生 Transformers 模型卡提供 context/hotwords prompt，用于提示人名、项目名和领域词。 | 官方包处理长音频；字/词时间戳由额外的 ForcedAligner 0.6B 产生，对齐模型支持含中文的 11 种语言，单段上限 5 分钟。 | 官方 ASR 返回文本、语言、可选时间戳；未提供原生说话人编号，需另接分离流程。 | 1.7B 为优先候选；0.6B 后续评估资源与质量取舍。 |
| Whisper large-v3 / large-v3-turbo | 多语言，支持中文；`initial_prompt` 可提供专有名词上下文，但不保证识别正确。需要使用转写任务，避免误走翻译。 | 30 秒感受窗口，通过顺序滑窗或分块处理长音频；支持段时间戳，推理实现可提供词时间戳。 | 原始转写输出没有说话人标签；需独立分离与时间线对齐。 | large-v3 为本轮独立基线；turbo 后续测加速。 |
| SenseVoiceSmall + FunASR | Small 权重主要支持普通话、粤语、英语、日语、韩语，也能输出情绪和声音事件标签。不能把这些标签当作会议事实或说话人身份。 | 使用 FSMN-VAD 切短片段；官方也有有界重叠窗口的长录音方案。窗口起止不等于逐字时间戳。 | 官方组合范例使用独立 CAM++、VAD、标点模块生成句级 speaker/start/end；编号来自组合流程。 | 适合作为轻量 CPU/组合流程候选，暂不扩大本轮下载范围。 |

逐项依据：[Qwen 官方模型列表与时间戳说明](https://github.com/QwenLM/Qwen3-ASR#released-models-description-and-download)、[Qwen 原生模型卡的上下文提示与对齐接口](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf)、[Qwen 官方输出结构和长音频代码](https://github.com/QwenLM/Qwen3-ASR/blob/main/qwen_asr/inference/qwen3_asr.py)、[Whisper large-v3 模型卡](https://huggingface.co/openai/whisper-large-v3)、[Whisper turbo 长音频说明](https://huggingface.co/openai/whisper-large-v3-turbo#chunked-long-form)、[Whisper 官方转写参数与输出结构](https://github.com/openai/whisper/blob/main/whisper/transcribe.py)、[SenseVoiceSmall 模型卡](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)、[SenseVoice 官方长音频及分离范例](https://github.com/QwenAudio/SenseVoice#speaker-diarization)。

**FunASR 是工具框架，不是一个能统一比较准确率的模型名称。** 它可组合识别、VAD、标点与说话人模块。必须记清具体 checkpoint 和各组件版本；例如 SenseVoiceSmall、Paraformer、Fun-ASR-Nano 不能互相替代名称。官方选型指南把普通话热词/字级时间戳需求指向 Paraformer，把中文/英日文及方言试验指向 Fun-ASR-Nano，同时要求使用自己的音频比较。[FunASR 官方选型指南](https://github.com/modelscope/FunASR/blob/main/docs/model_selection.md)

## Apple Silicon 运行路径

| 模型 | 已核查的一手运行路径 | 不能提前声称的内容 |
| --- | --- | --- |
| Qwen3-ASR | Qwen 官方提供 `qwen-asr` 的 Transformers/vLLM 路径；2026-06-26 增加 `-hf` 原生权重，模型卡要求 Transformers >= 5.13.0。官方示例主要采用 CUDA。 | 本次未找到 Qwen 对 Apple Silicon MLX/MPS 的明确官方兼容承诺。Mac 上的第三方 MLX 实现须单独记录，并用实际结果验证；不能直接搬用 CUDA/vLLM 或 FlashAttention 的性能结论。 |
| Whisper | Apple 的 MLX 示例项目提供 `mlx-whisper`、本地权重转换和词时间戳；whisper.cpp 项目提供 Metal/Accelerate/Core ML 路径。二者都是各自运行时维护者的一手资料，模型来源仍是 OpenAI。 | MLX 社区转换权重并非 OpenAI 发布的原始权重。量化、解码参数、VAD/切块变化后的速度和错误率需重新测。 |
| SenseVoice/FunASR | 官方 FunASR 选型例子允许 `device="cpu"` 做可移植测试；SenseVoice 还提供 CPU 部署和 GGUF 路径。 | 官方 CPU 可运行不等于已经证明本机 ARM 依赖安装、Metal 加速或长会议实时性。当前未完成这条路径的本机验证。 |

来源：[Qwen 官方运行说明](https://github.com/QwenLM/Qwen3-ASR#quickstart)、[原生 Transformers 模型卡](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf#usage)、[Apple MLX Whisper 使用与转换说明](https://github.com/ml-explore/mlx-examples/tree/main/whisper)、[whisper.cpp Apple Silicon 支持](https://github.com/ggml-org/whisper.cpp#core-ml-support)、[FunASR CPU 选型示例](https://github.com/modelscope/FunASR/blob/main/docs/model_selection.md)、[SenseVoice CPU 部署说明](https://github.com/QwenAudio/SenseVoice#run-on-cpu--edge--llamacpp--gguf-no-gpu-no-python)。

本项目的选择建议：先把已安装的两组权重跑出可复查结果，再决定运行库和后端接口；“模型可以在 Mac 上加载”只完成兼容性的一部分。模型初始化、音频解码、ASR、时间对齐和说话人分离应分别计时，再统计总体等待时间。

## 多人会议需要单独验证什么

说话人分离回答“哪个时间段是同一个声音”，不能回答“这个声音就是某员工”。CAM++ 组合流程的标签只在单份录音内聚类，不是跨会议稳定身份；pyannote Community-1 也提供本地说话人分离及与转写时间戳对齐的输出，可作为独立候选。其模型需要按模型卡准备本地资产，之后支持离线运行；这与言序产品是否需要用户登录是两回事。[FunASR 对匿名标签的说明](https://github.com/modelscope/FunASR/blob/main/docs/model_selection.md)、[pyannote 官方模型卡](https://huggingface.co/pyannote/speaker-diarization-community-1)

本项目应把以下三项分开验收：转写文字是否正确；文字时间是否贴合音频；说话人归属是否正确。多人抢话的声音分离还不同于给时间段分配标签；不能因出现“说话人 1/2”就认定重叠发言已完整识别。DeepSeek 做摘要时保留匿名编号和原文时间引用，不根据语气推定姓名，不把听不清的片段补写成事实。这是本项目建议的处理边界，不是上述模型已经提供的业务保证。

## 可选的下一轮候选

- **Fun-ASR-Nano-2512**：官方当前模型面向中文、英语、日语及中文方言/口音，与其单独的 31 语言 MLT-Nano checkpoint 区分。可在需要更强领域词/方言覆盖时进入后续比较，原生导出本身不自动提供说话人和时间戳。本轮不主张它比 Qwen 或 Whisper 更准。[Fun-ASR 官方仓库](https://github.com/QwenAudio/Fun-ASR)、[Nano 官方模型卡](https://huggingface.co/FunAudioLLM/Fun-ASR-Nano-2512)、[FunASR 对原生导出的边界说明](https://github.com/modelscope/FunASR/blob/main/docs/model_selection.md)
- **MOSS-Transcribe-Diarize 0.9B**：2026-07-09 发布。官方模型卡说明支持中文等 50 多种语言、单次最长 90 分钟录音、热词，以及一次输出转写、时间戳和匿名说话人。能力形态直接贴合多人会议，因此值得作为说话人能力的下一轮对照；当前未核实 Apple Silicon 加速路径和本机实测，不能仅凭参数小就认定更轻、更快或更准。长音频上限是官方能力说明，不是本机资源保证。[OpenMOSS 官方模型卡](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize)、[OpenMOSS 官方运行说明](https://github.com/OpenMOSS/MOSS-Transcribe-Diarize)

## 许可证与商用条件

| 资产 | 核查结果 | 落地时应保留的内容 |
| --- | --- | --- |
| Qwen3-ASR 代码、所查 1.7B/0.6B 官方权重 | Apache-2.0。 | 许可证、版权/NOTICE 等归属信息；分发修改版时标注改动，逐一核查实际采用的对齐模型和转换产物。 |
| Whisper 代码和官方权重 | OpenAI 明确均为 MIT。 | 分发副本或实质部分时保留版权与许可声明；运行库有自己的许可证，另行记录。 |
| SenseVoice 仓库代码 | MIT。 | 不把代码许可套到权重上。 |
| 官方 SenseVoiceSmall 权重 | 模型卡标为自定义 `model-license`，链接 FunASR Model Open Source License Agreement v1.1。当前官方仓库 README 明确说明遵守协议可商用，第 3 节是责任风险说明，微调权重可保持私有。 | 第 2.2 节要求注明出处、作者并保留模型名称；应保存采用权重时的协议和 README 澄清版本。其余行为/终止/修订条款也适用，不能简写为 MIT 或 Apache。 |
| FunASR 工具框架 | 代码 MIT；模型权重另看各自模型卡。 | VAD、CAM++、标点等独立资产逐一保留许可，框架 MIT 不自动覆盖它们。 |
| Fun-ASR-Nano-2512、MOSS-Transcribe-Diarize 官方模型卡 | 当前均标注 Apache-2.0。 | 以实际下载的 checkpoint、revision 和依赖资产为准。 |

来源：[Qwen 代码许可证](https://github.com/QwenLM/Qwen3-ASR/blob/main/LICENSE)、[Qwen 1.7B-hf 模型卡](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf)、[Qwen 0.6B 模型卡](https://huggingface.co/Qwen/Qwen3-ASR-0.6B)、[Whisper 代码/权重许可声明](https://github.com/openai/whisper#license)、[MIT 原文](https://github.com/openai/whisper/blob/main/LICENSE)、[SenseVoice 官方许可说明](https://github.com/QwenAudio/SenseVoice#license)、[SenseVoiceSmall 模型卡](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)、[固定提交的 FunASR 模型协议 v1.1](https://github.com/modelscope/FunASR/blob/58830eca4012644aac0c3218c3ccc7d98f003fda/MODEL_LICENSE)、[FunASR 代码许可证](https://github.com/modelscope/FunASR/blob/main/LICENSE)、[Nano 模型卡](https://huggingface.co/FunAudioLLM/Fun-ASR-Nano-2512)、[MOSS 模型卡](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize)。Apache-2.0 的商用/再分发条件以 [Apache 官方条文](https://www.apache.org/licenses/LICENSE-2.0)为依据：允许商业使用，并要求按条款保留许可证、相关声明与修改说明。

## 本机比较应留下的证据

以下为本项目的建议测试方法，不是本次已经执行的结果：

1. 两个模型使用完全相同的音频，保留输入文件摘要、时长、采样率和声道数；保留原始音频，统一送入模型的工作副本，避免反复有损转码。
2. 首轮先测安静近讲、远场会议、中文夹英文/型号/数字、静音与背景噪声、抢话，并追加长音频首尾与切块边界抽查；短示例通过不能代表整场会议通过。
3. 记录模型来源及 revision、运行库版本、精度/量化、设备、切块和解码参数；区分初次加载与稳态推理，记录峰值内存及失败情况。
4. 用人工校对的小段原文计算中文字符错误率；单列人名、项目名、数字、否定词和行动项错误。时间戳抽查能否准确回听，加入分离后再单列说话人错误。
5. 先保存原始 ASR 输出，再让 DeepSeek 基于文字生成纪要；保留摘要的原文依据。不要用“摘要看起来合理”代替转写准确率，也不要让另一模型的转写充当人工真值。

研究边界：本文件依据模型发布方、框架维护者、Apple MLX 项目与许可证原文；未引用社区测评分数，未下载模型，未处理本地会议数据。官方评测说明“值得试哪些候选”，不能替代言序自己的 Android 实录、Mac 运行证据和真实中文多人会议验收。
