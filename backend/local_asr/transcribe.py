#!/usr/bin/env python3
"""Local ASR with timeline-preserving chunks, resumable artifacts and explicit review status."""
import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time

for key in ('HF_HUB_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY', 'TRANSFORMERS_OFFLINE'):
    os.environ[key] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from artifacts import atomic_json, cached_chunk, export_results, file_hash, fingerprint, make_cues
from engines import Engines, require_models
from media import extract_audio, inspect_media, speech_chunks


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', help='Existing local video/audio path; URLs are not accepted')
    p.add_argument('--output', required=True)
    p.add_argument('--engine', choices=['qwen', 'whisper'], default='qwen')
    p.add_argument('--models', default=str(Path(os.environ.get('LOCAL_ASR_HOME', str(Path.home()/'.local/share/pcim-asr')))/'models'))
    p.add_argument('--glossary', help='UTF-8 JSON list of vocabulary hints; never a full reference transcript')
    p.add_argument('--max-seconds', type=float, default=60)
    p.add_argument('--audio-track', type=int, default=0)
    p.add_argument('--limit-seconds', type=float, help='Explicit diagnostic prefix only; output is marked partial_input')
    p.add_argument('--stop-after', type=int, help='Stop after N new chunks to test/resume a job')
    return p


def run(args):
    started = time.perf_counter()
    if '://' in args.input:
        raise ValueError('Local files only; download through an authorized workflow before transcription')
    source, media = inspect_media(args.input, args.audio_track)
    models = require_models(args.models, args.engine)
    glossary = json.loads(Path(args.glossary).read_text()) if args.glossary else []
    if not isinstance(glossary, list) or any(not isinstance(x, str) or len(x) > 80 for x in glossary) or len(glossary) > 100:
        raise ValueError('Glossary must be at most 100 short strings')
    if args.limit_seconds is not None and args.limit_seconds <= 0:
        raise ValueError('limit-seconds must be positive')
    output = Path(args.output).expanduser().resolve()
    if output == source.parent or output == source or source.is_relative_to(output):
        raise ValueError('Choose a separate output directory that does not contain the input')
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / '.job.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    versions = {name: importlib.metadata.version(name) for name in ('mlx', 'mlx-audio', 'mlx-whisper', 'silero-vad', 'onnxruntime')}
    code = {p.name: file_hash(p) for p in Path(__file__).parent.glob('*.py')}
    config = dict(input_sha256=file_hash(source), media=media, engine=args.engine, models=models, glossary=glossary,
                  max_seconds=args.max_seconds, limit_seconds=args.limit_seconds, versions=versions,
                  python=platform.python_version(), code=code)
    signature = fingerprint(config)
    manifest_path = output/'manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if previous and previous['fingerprint'] != signature:
        raise ValueError('Input/configuration changed; choose a new output directory to preserve prior results')
    if not previous and any(x.name != '.job.lock' for x in output.iterdir()):
        raise ValueError('Output directory is not empty and has no matching job manifest')
    audio = output/'audio.wav'
    if audio.exists() and previous and previous.get('audio_sha256') and file_hash(audio) != previous['audio_sha256']:
        lock.close()
        raise ValueError('Cached audio changed; choose a fresh output directory')
    manifest = dict(config=config, fingerprint=signature, source=str(source), status='running', review_status='unreviewed',
                    partial_input=args.limit_seconds is not None, prior_status=previous.get('status') if previous else None)
    if previous and previous.get('audio_sha256'):
        manifest['audio_sha256'] = previous['audio_sha256']
    atomic_json(manifest_path, manifest)
    completed, resumed, new = [], 0, 0
    try:
        audio = output/'audio.wav'
        if not audio.exists():
            extract_audio(source, audio, args.audio_track)
        samples, spans = speech_chunks(audio, args.max_seconds)
        if args.limit_seconds:
            samples = samples[:round(args.limit_seconds * 16000)]
            spans = [(a, min(b, args.limit_seconds)) for a, b in spans if a < args.limit_seconds]
        manifest['audio_sha256'] = file_hash(audio)
        manifest['audio_seconds'] = len(samples)/16000
        manifest['chunk_count'] = len(spans)
        chunks_dir = output/'chunks'
        chunks_dir.mkdir(exist_ok=True)
        engine = Engines(args.engine, models, glossary)
        prepare_seconds = time.perf_counter() - started
        for i, (start, end) in enumerate(spans):
            path = chunks_dir/f'{i:04}.json'
            key = fingerprint(dict(job=signature, span=[start, end], audio=manifest['audio_sha256']))
            chunk = cached_chunk(path, key)
            was_cached = chunk is not None
            if chunk:
                resumed += 1
            else:
                result = engine.transcribe(samples[round(start*16000):round(end*16000)])
                corrections = []
                cues = make_cues(result['words'], media['audio_offset'] + start, end-start,
                                 corrections=corrections)
                result['alignment_corrections'] = corrections
                if corrections:
                    result['issues'].append(f'{len(corrections)}处末尾词时间戳在20毫秒容差内截至音频边界，原始值已保留')
                if result['text'].strip() and not cues:
                    raise ValueError('Transcription has no valid subtitle alignment')
                chunk = dict(fingerprint=key, status='complete', start=start+media['audio_offset'], end=end+media['audio_offset'], cues=cues, **result)
                atomic_json(path, chunk)
                new += 1
            completed.append(chunk)
            print(json.dumps(dict(chunk=i+1,total=len(spans),cached=was_cached,seconds=end,engine=args.engine)), flush=True)
            if args.stop_after and new >= args.stop_after and len(completed) < len(spans):
                manifest['status'] = 'interrupted'
                break
        else:
            manifest['status'] = 'complete' if completed else 'complete_no_speech'
        manifest.update(resumed_chunks=resumed, new_chunks=new, completed_chunks=len(completed),
                        elapsed_seconds=time.perf_counter()-started, prepare_seconds=prepare_seconds,
                        model_load_seconds=engine.load_seconds,
                        asr_seconds=sum(c['asr_seconds'] for c in completed), align_seconds=sum(c['align_seconds'] for c in completed),
                        peak_mlx_bytes=max((c['peak_mlx_bytes'] for c in completed), default=0))
        export_results(output, completed, manifest)
        atomic_json(manifest_path, manifest)
        print(json.dumps(dict(status=manifest['status'],output=str(output),elapsed_seconds=manifest['elapsed_seconds'],resumed=resumed)),flush=True)
        return manifest
    except BaseException as error:
        manifest.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', error=str(error), completed_chunks=len(completed))
        atomic_json(manifest_path, manifest)
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    try:
        run(parser().parse_args())
    except (ValueError, RuntimeError, FileNotFoundError, BlockingIOError) as error:
        raise SystemExit(str(error))
