"""Local-only media decoding; preserve source timestamps across silence."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import numpy as np
import wave
from artifacts import plan_chunks


def media_env():
    env = os.environ.copy()
    # This machine's ffmpeg 8.1 was linked against x265 ABI 215. Do not change global links.
    library = os.environ.get('LOCAL_ASR_DYLD_LIBRARY_PATH', '/opt/homebrew/Cellar/x265/4.1/lib')
    if Path(library, 'libx265.215.dylib').is_file():
        env['DYLD_LIBRARY_PATH'] = library + (':' + env['DYLD_LIBRARY_PATH'] if env.get('DYLD_LIBRARY_PATH') else '')
    return env


def binary(name):
    result = os.environ.get('LOCAL_ASR_' + name.upper()) or shutil.which(name)
    if not result:
        raise ValueError(f'{name} is missing')
    return result


def run_media(args, timeout=600):
    return subprocess.run(args, env=media_env(), check=True, text=True, capture_output=True, timeout=timeout)


def inspect_media(source, audio_track=0):
    source = Path(source).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError('A local media file is required')
    probe = json.loads(run_media([binary('ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(source)]).stdout)
    tracks = [s for s in probe['streams'] if s['codec_type'] == 'audio']
    if not 0 <= audio_track < len(tracks):
        raise ValueError('No selected audio track in input')
    video = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    audio = tracks[audio_track]
    origin = float((video or audio).get('start_time', probe['format'].get('start_time', 0)))
    offset = float(audio.get('start_time', origin)) - origin
    if offset < -.001:
        raise ValueError('Audio starts before video; explicitly normalize this source before transcription')
    return source, dict(duration=float(probe['format']['duration']), audio_offset=max(0, offset), audio_track=audio_track, audio_stream=audio['index'], source_audio_rate=audio.get('sample_rate'), source_channels=audio.get('channels'))


def extract_audio(source, output, track):
    target = Path(output)
    tmp = target.with_name('audio.partial.wav')
    run_media([binary('ffmpeg'), '-v', 'error', '-nostdin', '-y', '-i', str(source), '-map', f'0:a:{track}', '-vn', '-af', 'asetpts=PTS-STARTPTS,aresample=16000:async=1:first_pts=0', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(tmp)])
    tmp.replace(target)


def speech_chunks(audio, max_seconds):
    from silero_vad import load_silero_vad, get_speech_timestamps
    with wave.open(str(audio), 'rb') as wav:
        rate = wav.getframerate()
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError('Expected 16-bit mono WAV')
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768
    if rate != 16000 or samples.ndim != 1:
        raise ValueError('Expected mono 16kHz PCM')
    vad = load_silero_vad(onnx=True)
    speech = get_speech_timestamps(samples, vad, sampling_rate=rate, return_seconds=True,
                                  max_speech_duration_s=max_seconds - 1,
                                  min_silence_duration_ms=350, speech_pad_ms=0)
    duration = len(samples) / rate
    return samples, plan_chunks([(x['start'], min(x['end'], duration)) for x in speech], duration, max_seconds)
