"""Adapters load local model directories only. No cloud fallback."""
import time
from pathlib import Path
from artifacts import file_hash, fingerprint


class Engines:
    def __init__(self, name, models, glossary):
        self.name, self.models, self.glossary = name, models, glossary
        self.asr = self.aligner = None
        self.load_seconds = 0

    def _load(self):
        started = time.perf_counter()
        if self.name == 'qwen' and self.asr is None:
            from mlx_audio.stt.utils import load_model
            self.asr = load_model(self.models['qwen']['path'])
            self.aligner = load_model(self.models['aligner']['path'])
        elif self.name == 'whisper' and self.asr is None:
            import mlx.core as mx
            from mlx_whisper.transcribe import ModelHolder
            self.asr = ModelHolder.get_model(self.models['whisper']['path'], mx.float16)
        self.load_seconds += time.perf_counter() - started

    def transcribe(self, samples):
        import mlx.core as mx
        self._load()
        started = time.perf_counter()
        issues, diagnostics = [], {}
        if self.name == 'qwen':
            result = self.asr.generate(samples, language='Chinese', temperature=0, max_tokens=2048,
                                       chunk_duration=120, hotwords=self.glossary)
            text = result.text.strip()
            asr_seconds = time.perf_counter() - started
            if result.generation_tokens >= 2048:
                raise RuntimeError('Token limit reached; retry using a smaller chunk size in a new output directory')
            alignment_start = time.perf_counter()
            aligned = self.aligner.generate(samples, text=text, language='Chinese') if text else []
            words = [dict(text=x.text, start=float(x.start_time), end=float(x.end_time)) for x in aligned]
            diagnostics['generation_tokens'] = result.generation_tokens
            align_seconds = time.perf_counter() - alignment_start
        else:
            import mlx_whisper
            result = mlx_whisper.transcribe(samples, path_or_hf_repo=self.models['whisper']['path'],
                                           language='zh', task='transcribe', temperature=0,
                                           word_timestamps=True, initial_prompt='、'.join(self.glossary),
                                           condition_on_previous_text=False, verbose=None)
            text = result['text'].strip()
            words = [dict(text=w['word'], start=float(w['start']), end=float(w['end']))
                     for s in result['segments'] for w in s.get('words', [])]
            asr_seconds = time.perf_counter() - started
            align_seconds = 0  # Whisper's word timing is included in its transcribe call.
            diagnostics['segments'] = [{k: s[k] for k in ('avg_logprob', 'no_speech_prob', 'compression_ratio') if k in s} for s in result['segments']]
            if any(s.get('compression_ratio', 0) > 2.4 for s in result['segments']):
                issues.append('重复/压缩率异常，需回听')
        if not text:
            issues.append('VAD判断有语音但转写为空，需检查')
        if text and not words:
            raise RuntimeError('Text exists without word alignment; refusing fabricated subtitle timing')
        zero_words = sum(w['start'] == w['end'] for w in words)
        if zero_words:
            issues.append(f'{zero_words}个词零时长，已保留文字并与相邻有效时间合并，需复核')
        peak = mx.get_peak_memory()
        mx.clear_cache()
        return dict(text=text, words=words, asr_seconds=asr_seconds, align_seconds=align_seconds,
                    peak_mlx_bytes=peak, diagnostics=diagnostics, issues=issues)


def require_models(root, engine):
    import json
    root = Path(root).expanduser().resolve()
    manifest = root / 'models.json'
    if not manifest.is_file():
        raise ValueError('Models missing: run setup.py first; offline mode will not download them')
    models = json.loads(manifest.read_text())
    result = {}
    for name in (['qwen', 'aligner'] if engine == 'qwen' else ['whisper']):
        model = models[name]
        path = Path(model['path']).resolve()
        if not path.is_dir() or not (path/'config.json').is_file():
            raise ValueError(f'Missing local model: {name}')
        weight = path / ('weights.npz' if name == 'whisper' else 'model.safetensors')
        if not weight.is_file():
            raise ValueError(f'Missing weights: {name}')
        content_hashes = {p.name: file_hash(p) for p in path.iterdir() if p.is_file() and p.suffix in ('.json', '.txt', '.npz', '.safetensors')}
        result[name] = {**model, 'path': str(path), 'weight_size': weight.stat().st_size, 'content_sha256': fingerprint(content_hashes)}
    return result
