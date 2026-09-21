"""Timeline and immutable per-chunk artifacts; no model dependencies."""
import hashlib
import json
import math
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def cached_chunk(path, expected):
    try:
        value = json.loads(Path(path).read_text())
        if value.get('fingerprint') == expected and value.get('status') == 'complete':
            return value
    except (OSError, ValueError):
        pass
    return None


def plan_chunks(speech, duration, max_seconds=60):
    if not math.isfinite(duration) or duration <= 0 or not 1 <= max_seconds <= 120:
        raise ValueError('Invalid duration or chunk bound')
    padded = []
    for start, end in speech:
        if not 0 <= start < end <= duration + .01:
            raise ValueError('Invalid speech range')
        a, b = max(0, start - .2), min(duration, end + .2)
        if padded and a <= padded[-1][1]:
            padded[-1] = (padded[-1][0], max(b, padded[-1][1]))
        else:
            padded.append((a, b))
    chunks = []
    for a, b in padded:
        if chunks and a - chunks[-1][1] <= 3 and b - chunks[-1][0] <= max_seconds:
            chunks[-1] = (chunks[-1][0], b)
            continue
        while b - a > max_seconds:
            chunks.append((a, a + max_seconds))
            a += max_seconds
        if b > a:
            chunks.append((a, b))
    return chunks


def join_text(parts):
    result = ''
    for text in parts:
        text = text.strip()
        if result and text and result[-1].isascii() and text[0].isascii() and result[-1].isalnum() and text[0].isalnum():
            result += ' '
        result += text
    return result


# Bounded tolerance for small end overshoots; raw word timings stay immutable.
END_BOUNDARY_TOLERANCE_SECONDS = .020


def make_cues(words, offset, duration, corrections=None):
    result, group = [], []
    last_start = -1

    def flush():
        anchors = [w for w in group if w['end'] > w['start']]
        if not anchors:
            raise ValueError('Text has no positive-duration alignment')
        result.append(dict(start=offset + anchors[0]['start'], end=offset + anchors[-1]['end'],
                           text=join_text([x['text'] for x in group])))

    for index, word in enumerate(words):
        a, b = float(word['start']), float(word['end'])
        if not all(math.isfinite(t) for t in (a, b)) or not 0 <= a <= b <= duration + END_BOUNDARY_TOLERANCE_SECONDS + 1e-9 or a >= duration or a < last_start:
            raise ValueError('Invalid or unordered word alignment')
        if b > duration:
            if corrections is not None:
                corrections.append(dict(word_index=index, original_start=a, original_end=b,
                                        corrected_end=duration, reason='end_boundary_tolerance'))
            b = duration
        last_start = a
        if not word['text'].strip():
            continue
        if group and b > a and any(w['end'] > w['start'] for w in group) and (b - group[0]['start'] > 5 or len(join_text([x['text'] for x in group])) >= 26):
            flush()
            group = []
        group.append(dict(text=word['text'], start=a, end=min(b, duration)))
    if group:
        flush()
    if words and not result:
        raise ValueError('No usable aligned text')
    return result


def timestamp(seconds, separator=','):
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02}{separator}{ms:03}'


def write_subtitles(directory, cues):
    srt, vtt = [], ['WEBVTT\n']
    for i, cue in enumerate(cues, 1):
        srt.append(f"{i}\n{timestamp(cue['start'])} --> {timestamp(cue['end'])}\n{cue['text']}\n")
        vtt.append(f"{timestamp(cue['start'], '.')} --> {timestamp(cue['end'], '.')}\n{cue['text']}\n")
    Path(directory, 'subtitles.srt').write_text('\n'.join(srt))
    Path(directory, 'subtitles.vtt').write_text('\n'.join(vtt))


def export_results(directory, chunks, manifest):
    directory = Path(directory)
    cues = [cue for chunk in chunks for cue in chunk['cues']]
    issues = [dict(chunk=i, issue=issue) for i, chunk in enumerate(chunks) for issue in chunk.get('issues', [])]
    atomic_json(directory / 'transcript.raw.json', dict(manifest=manifest, chunks=chunks, cues=cues))
    atomic_json(directory / 'review-issues.json', issues)
    write_subtitles(directory, cues)
    lines = ['# 本地转写审核稿', '', '以下为模型原始识别；未核对片段不能直接作为题目答案依据。', '']
    for i, chunk in enumerate(chunks):
        lines += [f"## {timestamp(chunk['start'], '.')}–{timestamp(chunk['end'], '.')} · 片段{i + 1}", '', chunk['text'], '']
        lines += [f'- 需复核：{issue}' for issue in chunk.get('issues', [])]
    if not chunks:
        lines += ['没有检测到可转写语音；未生成文本。']
    Path(directory, 'transcript.review.md').write_text('\n'.join(lines) + '\n')
