"""Dependency-isolated local engine protocol. No model downloads in API processes."""
import json
import shlex
import subprocess

MODEL_VERSION = 'wespeaker-cnceleb-resnet34-lm:e7584940aeac8d55:kaldi80-v1'


class EngineUnavailable(RuntimeError):
    pass


class CommandEngine:
    def __init__(self, settings):
        self.command = getattr(settings, 'voice_engine_command', '')
        self.model = getattr(settings, 'voice_model_version', MODEL_VERSION)

    def run(self, kind, audio_path, payload):
        if not self.command:
            raise EngineUnavailable('声音模型尚未配置')
        request = {'kind': kind, 'audioPath': str(audio_path), 'payload': payload}
        result = subprocess.run(shlex.split(self.command), input=json.dumps(request), text=True,
                                capture_output=True, timeout=3600)
        if result.returncode:
            # Worker logs must not echo model input, tokens, filesystem paths or raw transcripts.
            try:
                code = json.loads(result.stdout).get('errorCode')
            except (ValueError, TypeError):
                code = None
            if code == 'sample_quality':
                raise ValueError('有效独立语音不足，请在安静环境重新录制')
            raise EngineUnavailable('声音模型运行失败，请检查独立运行环境')
        value = json.loads(result.stdout)
        if value.get('model') != self.model:
            raise ValueError('声音模型版本与服务配置不一致')
        return value
