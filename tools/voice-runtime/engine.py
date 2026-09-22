#!/usr/bin/env python3
"""Local baseline: official CNCeleb WeSpeaker ONNX, Kaldi fbank, WebRTC VAD.

The model is real. Voice matching is not authentication and the thresholds below
are deliberately labelled uncalibrated. No overlap separation or neural change
point detector is claimed. Input/output JSON stays on local stdin/stdout.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import subprocess
import time

import kaldi_native_fbank as knf
import numpy as np
import onnxruntime as ort
import soundfile as sf
from scipy.signal import resample_poly
import webrtcvad

MODEL_SHA = 'e7584940aeac8d5512d875e58ce6c09ba4ddad65d8128e1dac0d93aadd087ebb'
MODEL_VERSION = 'wespeaker-cnceleb-resnet34-lm:e7584940aeac8d55:kaldi80-v1'


class SampleQualityError(ValueError):
    pass


def unit(value):
    norm = np.linalg.norm(value)
    if not np.isfinite(norm) or norm < 1e-8:
        raise SampleQualityError('empty embedding')
    return value / norm


class Engine:
    def __init__(self, model_path):
        model_path = Path(model_path)
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != MODEL_SHA:
            raise ValueError('Model SHA256 differs from reviewed official weights')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model_path), sess_options=options, providers=['CPUExecutionProvider'])

    def read(self, path):
        try:
            pcm, rate = sf.read(path, dtype='float32', always_2d=True)
        except (sf.LibsndfileError, RuntimeError):
            decoded = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', '16000', 'pipe:1'], capture_output=True, check=True, timeout=3600)
            pcm, rate = np.frombuffer(decoded.stdout, dtype='<f4')[:, None], 16000
        pcm = pcm.mean(axis=1)
        if rate != 16000:
            divisor = math.gcd(rate, 16000)
            pcm = resample_poly(pcm, 16000 // divisor, rate // divisor).astype(np.float32)
        return np.clip(pcm, -1, 1)

    def speech(self, pcm):
        vad = webrtcvad.Vad(2)
        frame = 480
        regions = []
        start = last = None
        for offset in range(0, len(pcm) - frame + 1, frame):
            samples = (pcm[offset:offset + frame] * 32767).astype('<i2').tobytes()
            voiced = vad.is_speech(samples, 16000)
            if voiced:
                if start is None:
                    start = offset
                last = offset + frame
            elif start is not None and offset - last >= 3200:
                if last - start >= 4800:
                    regions.append((start, last))
                start = last = None
        if start is not None and last - start >= 4800:
            regions.append((start, last))
        return regions

    def embedding(self, pcm):
        if len(pcm) < 8000:
            raise SampleQualityError('less than half a second of speech')
        options = knf.FbankOptions()
        options.frame_opts.samp_freq = 16000
        options.frame_opts.dither = 0
        options.frame_opts.frame_length_ms = 25
        options.frame_opts.frame_shift_ms = 10
        options.frame_opts.window_type = 'hamming'
        options.mel_opts.num_bins = 80
        options.mel_opts.debug_mel = False
        computer = knf.OnlineFbank(options)
        computer.accept_waveform(16000, (pcm * 32768).tolist())
        computer.input_finished()
        feats = np.stack([computer.get_frame(i) for i in range(computer.num_frames_ready)]).astype(np.float32)
        feats -= feats.mean(axis=0, keepdims=True)
        result = self.session.run(['embs'], {'feats': feats[None]})[0][0]
        return unit(result)

    def enroll(self, pcm):
        regions = self.speech(pcm)
        active = np.concatenate([pcm[start:end] for start, end in regions]) if regions else np.array([])
        if len(active) < 3 * 16000:
            raise SampleQualityError('less than three seconds of usable speech')
        if np.mean(np.abs(active) > .995) > .03 or np.sqrt(np.mean(active ** 2)) < .003:
            raise SampleQualityError('clipped or too quiet')
        # Multiple windows reduce phonetic sensitivity; reject grossly inconsistent samples.
        windows = [active[i:i + 48000] for i in range(0, len(active), 48000) if len(active[i:i + 48000]) >= 16000]
        vectors = np.stack([self.embedding(window) for window in windows])
        centre = unit(vectors.mean(axis=0))
        minimum = float(min(vectors @ centre))
        if minimum < .45:
            raise SampleQualityError('inconsistent sample; record a single person')
        return {'model': MODEL_VERSION, 'embedding': centre.tolist(), 'quality': {
            'speechSeconds': round(len(active) / 16000, 3), 'durationSeconds': round(len(pcm) / 16000, 3),
            'windowConsistency': round(minimum, 4), 'singleSpeakerVerified': False, 'calibrated': False}}

    def attribute(self, pcm, payload):
        profiles = []
        for profile in payload.get('profiles', []):
            if profile.get('active') and not profile.get('revoked') and profile.get('embedding') and profile.get('model') == MODEL_VERSION:
                embedding = np.asarray(profile['embedding'], dtype=np.float32)
                if embedding.shape == (256,) and np.isfinite(embedding).all():
                    profiles.append((profile['personId'], unit(embedding)))
        threshold = float(payload.get('threshold', .75))
        margin_limit = float(payload.get('margin', .08))
        turns, clusters = [], []
        # First diarize without names. Identifying each 1.5s window independently
        # fragments the same voice and is unsuitable for the LM model's >3s context.
        for start, end in self.speech(pcm):
            if end - start < 12000:
                continue
            offsets = list(range(start, max(start + 1, end - 24000 + 1), 12000))
            if end - offsets[-1] > 24000:
                offsets.append(end - 24000)
            windows = []
            for offset in offsets:
                stop = min(end, offset + 24000)
                vector = self.embedding(pcm[offset:stop])
                scores = sorted([(float(vector @ cluster['vector']), i) for i, cluster in enumerate(clusters)], reverse=True)
                # Do not use the registered attendee count to force clustering.
                if scores and scores[0][0] >= .72 and (len(scores) == 1 or scores[0][0] - scores[1][0] >= .03):
                    index = scores[0][1]
                    cluster = clusters[index]
                    cluster['vector'] = unit(cluster['vector'] * cluster['count'] + vector)
                    cluster['count'] += 1
                    cluster['windows'].append(vector)
                else:
                    index = len(clusters)
                    clusters.append({'vector': vector, 'count': 1, 'windows': [vector], 'audio': []})
                windows.append({'start': offset / 16000, 'end': stop / 16000, 'cluster': index})
            centres = [(item['start'] + item['end']) / 2 for item in windows]
            for i, item in enumerate(windows):
                item['start'] = start / 16000 if i == 0 else (centres[i - 1] + centres[i]) / 2
                item['end'] = end / 16000 if i == len(windows) - 1 else (centres[i] + centres[i + 1]) / 2
                a, b = round(item['start'] * 16000), round(item['end'] * 16000)
                clusters[item['cluster']]['audio'].append((a, b))
                turns.append(item)
        identities = []
        for cluster in clusters:
            # Bounded pooling provides sufficient phonetic context; no duplicated
            # overlapping windows, no ASR text or name hints enter the embedding.
            intervals = cluster['audio']
            samples, total = [], 0
            for a, b in intervals:
                amount = min(b - a, 30 * 16000 - total)
                if amount <= 0:
                    break
                samples.append(pcm[a:a + amount])
                total += amount
            consistency = min(float(v @ cluster['vector']) for v in cluster['windows'])
            person, top, gap = None, -1., -1.
            if total >= 3 * 16000 and consistency >= .60:
                pooled = self.embedding(np.concatenate(samples))
                scores = sorted([(float(pooled @ reference), pid) for pid, reference in profiles], reverse=True)
                top = scores[0][0] if scores else -1.
                gap = top - (scores[1][0] if len(scores) > 1 else 0.)
                if scores and top >= threshold and gap >= margin_limit:
                    person = scores[0][1]
            identities.append({'personId': person, 'score': top, 'margin': gap})
        # Several coherent clusters may independently match one registered person;
        # only such independently accepted matches share that person's stable ID.
        person_ids, anonymous_ids, output = {}, {}, []
        next_id = 1
        for turn in turns:
            index = turn['cluster']
            identity = identities[index]
            person = identity['personId']
            mapping, key = (person_ids, person) if person else (anonymous_ids, index)
            if key not in mapping:
                mapping[key] = f'speaker-{next_id}'
                next_id += 1
            item = {k: turn[k] for k in ('start', 'end')}
            item.update(speakerId=mapping[key], **identity)
            if output and output[-1]['speakerId'] == item['speakerId'] and abs(output[-1]['end'] - item['start']) < .001:
                output[-1]['end'] = item['end']
                output[-1]['score'] = min(output[-1]['score'], item['score'])
                output[-1]['margin'] = min(output[-1]['margin'], item['margin'])
            else:
                output.append(item)
        return {'model': MODEL_VERSION, 'turns': output, 'calibrated': False, 'pipeline': 'voice-v2-cluster-first'}


def main():
    started = time.monotonic()
    try:
        value = json.load(sys.stdin)
        root = Path(__file__).resolve().parents[2]
        path = os.environ.get('YANXU_VOICE_MODEL_PATH', str(root / '.local-data/voice-runtime/models/cnceleb_resnet34_LM.onnx'))
        engine = Engine(path)
        pcm = engine.read(value['audioPath'])
        result = engine.enroll(pcm) if value['kind'] == 'enrollment' else engine.attribute(pcm, value['payload'])
        result['elapsedSeconds'] = round(time.monotonic() - started, 3)
        print(json.dumps(result))
    except SampleQualityError:
        print(json.dumps({'errorCode': 'sample_quality'}))
        sys.exit(2)
    except Exception:
        print(json.dumps({'errorCode': 'engine_failure'}))
        sys.exit(1)


if __name__ == '__main__':
    main()
