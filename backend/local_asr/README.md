# 本机ASR适配

从本机已验证的local-video-transcribe技能复制其运行脚本（2026-09-21），作为项目内可复现适配；原文件未修改。模型和独立Python环境继续使用`~/.local/share/pcim-asr`，具体revision记录在该处models/models.json；模型不进入Git。

run.sh通过macOS sandbox-exec禁止ASR网络访问，不做云端回退。此本地适配依赖Apple Silicon/MLX，尚不是通用Linux生产部署包。
