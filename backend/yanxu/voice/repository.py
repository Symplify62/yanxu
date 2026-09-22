import hashlib
import bisect
import json
import math
import time
import uuid
from pathlib import Path
from contextlib import nullcontext
from .engine import MODEL_VERSION


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def initialize(store):
    root = store.settings.data_dir / 'private-voices'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    with store.connect(True) as db:
        db.execute('CREATE TABLE IF NOT EXISTS feature_schema(module TEXT PRIMARY KEY, version INTEGER NOT NULL)')
        version = db.execute("SELECT version FROM feature_schema WHERE module='voice'").fetchone()
        if version and version[0] > 2:
            raise RuntimeError('声音资料版本高于当前程序，请使用新版服务')
        if version and version[0] == 2:
            return
        statements = '''
        CREATE TABLE IF NOT EXISTS feature_schema(module TEXT PRIMARY KEY, version INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS voice_profiles(
          person_id TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0,
          active_id TEXT, candidate_id TEXT, revoked_at REAL);
        CREATE TABLE IF NOT EXISTS voice_enrollments(
          id TEXT PRIMARY KEY, person_id TEXT NOT NULL, creator_id TEXT NOT NULL,
          client_id TEXT NOT NULL, revision INTEGER NOT NULL, name_snapshot TEXT NOT NULL,
          sha256 TEXT NOT NULL, total_bytes INTEGER NOT NULL, status TEXT NOT NULL,
          created_at REAL NOT NULL, completed_at REAL, audio_path TEXT, duration REAL,
          model TEXT, embedding TEXT, quality TEXT, error TEXT,
          consent_at REAL NOT NULL, UNIQUE(creator_id,client_id));
        CREATE TABLE IF NOT EXISTS voice_objects(
          enrollment_id TEXT PRIMARY KEY, bucket TEXT NOT NULL, object_key TEXT NOT NULL,
          status TEXT NOT NULL, next_at REAL NOT NULL DEFAULT 0, error TEXT);
        CREATE TABLE IF NOT EXISTS voice_jobs(
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, target_id TEXT NOT NULL,
          fingerprint TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0,
          owner TEXT, lease_until REAL, error TEXT, created_at REAL NOT NULL,
          UNIQUE(kind,target_id,fingerprint));
        CREATE INDEX IF NOT EXISTS voice_jobs_ready ON voice_jobs(status,next_at,lease_until);
        INSERT INTO feature_schema(module,version) VALUES('voice',2)
          ON CONFLICT(module) DO UPDATE SET version=MAX(version,excluded.version);
        '''
        for statement in statements.split(';'):
            if statement.strip():
                db.execute(statement)


def profile_snapshot(db, roster):
    profiles = []
    for entry in roster:
        person_id = entry.get('personId')
        row = db.execute('''SELECT p.id,p.name,p.active,v.revision,v.active_id,v.revoked_at,
          e.model,e.embedding FROM identity_people p LEFT JOIN voice_profiles v ON v.person_id=p.id
          LEFT JOIN voice_enrollments e ON e.id=v.active_id WHERE p.id=?''', (person_id,)).fetchone()
        if not row:
            continue
        profiles.append({
            'personId': row['id'], 'name': row['name'], 'active': bool(row['active']),
            'revision': row['revision'], 'enrollmentId': row['active_id'],
            'revoked': row['revoked_at'] is not None, 'model': row['model'],
            'embedding': json.loads(row['embedding']) if row['embedding'] and row['active'] and row['revoked_at'] is None else None,
        })
    return profiles


def attribution_payload(db, row, settings):
    transcript = json.loads(row['transcript']) if isinstance(row['transcript'], str) else row['transcript']
    roster = json.loads(row.get('roster_json') or '[]')
    # Original words/times only. A prior attribution must not change cache identity.
    segments = [{k: s[k] for k in ('id', 'start', 'end', 'text') if k in s} for s in transcript.get('segments', [])]
    return {'recordingId': row['id'], 'sha256': row['sha256'], 'duration': row['duration'],
            'segments': segments, 'profiles': profile_snapshot(db, roster),
            'threshold': float(getattr(settings, 'voice_match_threshold', .75)),
            'margin': float(getattr(settings, 'voice_match_margin', .08)),
            'engineCommand': getattr(settings, 'voice_engine_command', ''),
            'model': getattr(settings, 'voice_model_version', MODEL_VERSION), 'pipeline': 'voice-v2-cluster-first'}


def _queue_attribution_snapshot(db, recording_id, payload, restore_terminal=False):
    digest = fingerprint(payload)
    old = db.execute("SELECT id,status FROM voice_jobs WHERE kind='attribution' AND target_id=? AND fingerprint=?",
                     (recording_id, digest)).fetchone()
    if old and old['status'] in ('complete', 'failed') and not restore_terminal:
        return False
    if not old:
        db.execute('INSERT INTO voice_jobs(id,kind,target_id,fingerprint,payload,created_at) VALUES(?,?,?,?,?,?)',
                   (str(uuid.uuid4()), 'attribution', recording_id, digest, encode(payload), time.time()))
    elif old['status'] in ('superseded', 'complete', 'failed'):
        # A snapshot can become current again (for example after undoing a name
        # change). A historical terminal job is not proof that its transcript is
        # still stored, so recover actual work and invalidate every old lease.
        db.execute("""UPDATE voice_jobs SET payload=?,status='pending',attempts=0,next_at=0,
          owner=NULL,lease_until=NULL,error=NULL,created_at=? WHERE id=?""",
                   (encode(payload), time.time(), old['id']))
    return True


def enqueue_attribution(store, recording_id, db=None):
    """Returns True when attribution now gates the analysis stage; otherwise False."""
    with (nullcontext(db) if db is not None else store.connect(True)) as db:
        row = db.execute('SELECT * FROM recordings WHERE id=?', (recording_id,)).fetchone()
        if not row:
            return False
        row = dict(row)
        if not row.get('owner_account_id') or not row.get('roster_json') or not row.get('transcript'):
            return False
        transcript = json.loads(row['transcript'])
        if transcript.get('noSpeech') or not transcript.get('segments'):
            return False
        payload = attribution_payload(db, row, store.settings)
        if not _queue_attribution_snapshot(db, recording_id, payload):
            return False
        db.execute("UPDATE jobs SET stage='analysis',status='waiting',owner=NULL,lease_until=NULL WHERE recording_id=?", (recording_id,))
        db.execute("UPDATE recordings SET attribution_state='waiting' WHERE id=?", (recording_id,))
        return True


def claim(store):
    now = time.time()
    with store.connect(True) as db:
        row = db.execute("""SELECT * FROM voice_jobs WHERE (status IN ('pending','retry') AND next_at<=?)
            OR (status='running' AND lease_until<=?) ORDER BY created_at,id LIMIT 1""", (now, now)).fetchone()
        if not row:
            return None
        owner = str(uuid.uuid4())
        db.execute("UPDATE voice_jobs SET status='running',owner=?,lease_until=?,attempts=attempts+1 WHERE id=?",
                   (owner, now + store.settings.lease_seconds, row['id']))
        if row['kind'] == 'enrollment':
            db.execute("UPDATE voice_enrollments SET status='processing' WHERE id=? AND status IN ('queued','processing')", (row['target_id'],))
        job = dict(db.execute('SELECT * FROM voice_jobs WHERE id=?', (row['id'],)).fetchone())
        job['payload'] = json.loads(job['payload'])
        return job


def owned_job(db, job_id, owner):
    row = db.execute("SELECT * FROM voice_jobs WHERE id=? AND owner=? AND status='running' AND lease_until>?", (job_id, owner, time.time())).fetchone()
    return dict(row) if row else None


def heartbeat(store, job_id, owner):
    with store.connect(True) as db:
        if not owned_job(db, job_id, owner):
            return False
        db.execute('UPDATE voice_jobs SET lease_until=? WHERE id=?', (time.time() + store.settings.lease_seconds, job_id))
        return True


def _resume_analysis(db, recording_id):
    db.execute("UPDATE jobs SET status='pending',owner=NULL,lease_until=NULL,next_at=0 WHERE recording_id=? AND stage='analysis' AND status='waiting'", (recording_id,))


def normalize_embedding(value):
    # This service's pinned WeSpeaker model emits exactly 256 dimensions.
    if not isinstance(value, list) or len(value) != 256:
        raise ValueError('声音特征维度无效')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
        raise ValueError('声音特征无效')
    norm = math.hypot(*value)
    if not math.isfinite(norm) or norm < 1e-8:
        raise ValueError('声音特征为空')
    return [float(x) / norm for x in value]


def apply_attribution(payload, transcript, result):
    """The engine may associate time spans, never replace trusted ASR text."""
    model = result.get('model')
    if not isinstance(model, str) or not model or len(model) > 256:
        raise ValueError('识别模型版本缺失')
    if model != payload.get('model', MODEL_VERSION):
        raise ValueError('识别模型版本不一致')
    if result.get('pipeline') != payload.get('pipeline', 'voice-v2-cluster-first'):
        raise ValueError('声音处理管线版本不一致')
    profiles = {p['personId']: p for p in payload['profiles'] if p['active'] and not p['revoked'] and p['embedding'] and p['model'] == model}
    turns = result.get('turns')
    if not isinstance(turns, list) or len(turns) > 200000:
        raise ValueError('说话人片段无效')
    clean = []
    for turn in turns:
        start, end = float(turn['start']), float(turn['end'])
        speaker = turn.get('speakerId')
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= payload['duration'] + 0.1:
            raise ValueError('说话人时间无效')
        if not isinstance(speaker, str) or not speaker.startswith('speaker-') or not speaker[8:].isdigit() or len(speaker) > 32:
            raise ValueError('说话人编号无效')
        person = turn.get('personId')
        if person:
            score, margin = float(turn.get('score', -1)), float(turn.get('margin', -1))
            if person not in profiles or not math.isfinite(score) or not math.isfinite(margin) or not payload['threshold'] <= score <= 1.000001 or not payload['margin'] <= margin <= 2:
                raise ValueError('声纹匹配不符合本场档案或拒绝阈值')
        clean.append({**turn, 'start': start, 'end': end})
    clean.sort(key=lambda turn: (turn['start'], turn['end']))
    starts = [turn['start'] for turn in clean]
    maximum_ends = []
    latest_end = 0
    for turn in clean:
        latest_end = max(latest_end, turn['end'])
        maximum_ends.append(latest_end)
    output = {k: v for k, v in transcript.items() if k not in ('segments', 'voice')}
    output['segments'] = []
    for segment in payload['segments']:
        s = dict(segment)
        votes = {}
        left = bisect.bisect_right(maximum_ends, s['start'])
        right = bisect.bisect_left(starts, s['end'])
        for turn in clean[left:right]:
            duration = max(0, min(s['end'], turn['end']) - max(s['start'], turn['start']))
            if duration:
                key = (turn['speakerId'], turn.get('personId'))
                votes[key] = votes.get(key, 0) + duration
        s['speaker'] = None
        if votes:
            best = sorted(votes.items(), key=lambda x: -x[1])
            key, seconds = best[0]
            # Mixed speaker sentences are withheld; no arbitrary winner for overlapping speech.
            total = sum(votes.values())
            other_seconds = total - seconds
            mixed = other_seconds > .15 and other_seconds / max(total, 1e-8) > .05
            overlaps = total > (s['end'] - s['start']) + .1
            if not mixed and not overlaps and seconds / max(s['end'] - s['start'], 1e-8) >= .5:
                s['speakerId'] = key[0]
                if key[1]:
                    p = profiles[key[1]]
                    s.update(speaker=p['name'], personId=p['personId'], voiceEnrollmentId=p['enrollmentId'])
        output['segments'].append(s)
    output['warning'] = '词级时间未经人工核对；说话人归属为自动识别结果'
    output['voice'] = {'status': 'complete', 'model': model, 'calibrated': False, 'pipeline': payload['pipeline'],
                       'warning': '声音匹配阈值尚未经过真实会议校准；短句、重叠发言可能未识别'}
    return output


def finish(store, job, result):
    with store.connect(True) as db:
        live = owned_job(db, job['id'], job['owner'])
        if not live:
            return False
        payload = json.loads(live['payload'])
        if job['kind'] == 'enrollment':
            e = db.execute('SELECT * FROM voice_enrollments WHERE id=?', (job['target_id'],)).fetchone()
            p = db.execute('SELECT * FROM voice_profiles WHERE person_id=?', (e['person_id'],)).fetchone()
            person = db.execute('SELECT active FROM identity_people WHERE id=?', (e['person_id'],)).fetchone()
            if not person or not person['active'] or p['revision'] != e['revision'] or p['candidate_id'] != e['id'] or p['revoked_at'] is not None:
                db.execute("UPDATE voice_jobs SET status='superseded',owner=NULL,lease_until=NULL WHERE id=?", (job['id'],))
                db.execute("UPDATE voice_enrollments SET status='superseded' WHERE id=? AND status!='revoked'", (e['id'],))
                return False
            embedding = normalize_embedding(result.get('embedding'))
            model = result.get('model')
            if not isinstance(model, str) or not model or len(model) > 256:
                raise ValueError('声音模型版本缺失')
            if model != payload.get('model', MODEL_VERSION):
                raise ValueError('登记模型版本不一致')
            quality = result.get('quality') or {}
            db.execute("UPDATE voice_enrollments SET status='ready',model=?,embedding=?,quality=?,completed_at=?,error=NULL WHERE id=?",
                       (model, encode(embedding), encode(quality), time.time(), e['id']))
            db.execute('UPDATE voice_profiles SET active_id=?,candidate_id=NULL WHERE person_id=?', (e['id'], e['person_id']))
        else:
            row = dict(db.execute('SELECT * FROM recordings WHERE id=?', (job['target_id'],)).fetchone())
            fresh = attribution_payload(db, row, store.settings)
            if fingerprint(fresh) != live['fingerprint']:
                # Recompute against current consent/profile/roster; stale identities never commit.
                db.execute("UPDATE voice_jobs SET status='superseded',owner=NULL,lease_until=NULL WHERE id=?", (job['id'],))
                _queue_attribution_snapshot(db, row['id'], fresh, restore_terminal=True)
                return False
            transcript = apply_attribution(payload, json.loads(row['transcript']), result)
            db.execute('UPDATE recordings SET transcript=? WHERE id=?', (encode(transcript), row['id']))
            db.execute("UPDATE recordings SET attribution_state='complete' WHERE id=?", (row['id'],))
            _resume_analysis(db, row['id'])
        db.execute("UPDATE voice_jobs SET status='complete',owner=NULL,lease_until=NULL,error=NULL WHERE id=?", (job['id'],))
        return True


def fail(store, job, error='声音处理暂未完成', retryable=True):
    with store.connect(True) as db:
        live = owned_job(db, job['id'], job['owner'])
        if not live:
            return False
        retry = retryable and live['attempts'] < store.settings.max_attempts
        db.execute('UPDATE voice_jobs SET status=?,next_at=?,owner=NULL,lease_until=NULL,error=? WHERE id=?',
                   ('retry' if retry else 'failed', time.time() + store.settings.retry_seconds * 2 ** (live['attempts'] - 1), error, job['id']))
        if job['kind'] == 'enrollment':
            db.execute("UPDATE voice_enrollments SET status=?,error=? WHERE id=? AND status NOT IN ('revoked','superseded')", ('queued' if retry else 'failed', error, job['target_id']))
        elif not retry:
            row = db.execute('SELECT transcript FROM recordings WHERE id=?', (job['target_id'],)).fetchone()
            transcript = json.loads(row['transcript'])
            transcript['voice'] = {'status': 'failed', 'warning': error}
            db.execute('UPDATE recordings SET transcript=? WHERE id=?', (encode(transcript), job['target_id']))
            db.execute("UPDATE recordings SET attribution_state='failed' WHERE id=?", (job['target_id'],))
            _resume_analysis(db, job['target_id'])
        return True


def public_transcript(transcript):
    if not transcript:
        return None
    if isinstance(transcript, str):
        transcript = json.loads(transcript)
    result = {k: transcript[k] for k in ('text', 'noSpeech', 'engine', 'warning') if k in transcript}
    mapping = {}
    result['segments'] = []
    for segment in transcript.get('segments', []):
        item = {k: segment[k] for k in ('id', 'start', 'end', 'text') if k in segment}
        sid = segment.get('speakerId')
        if sid:
            if sid not in mapping:
                mapping[sid] = len(mapping) + 1
            item.update(speaker=f'说话人 {mapping[sid]}', speakerId=f'speaker-{mapping[sid]}')
        else:
            item['speaker'] = None
        result['segments'].append(item)
    if transcript.get('voice'):
        result['voice'] = {k: transcript['voice'][k] for k in ('status', 'calibrated', 'warning') if k in transcript['voice']}
    return result


def protected_transcript(store, row):
    original = json.loads(row['transcript']) if isinstance(row.get('transcript'), str) else row.get('transcript')
    result = public_transcript(original)
    if not result:
        return result
    with store.connect() as db:
        for raw, item in zip(original.get('segments', []), result['segments']):
            person_id = raw.get('personId')
            if not person_id:
                continue
            profile = db.execute('''SELECT p.name,p.active,v.revoked_at,e.status FROM identity_people p
              JOIN voice_profiles v ON v.person_id=p.id JOIN voice_enrollments e ON e.id=?
              WHERE p.id=? AND e.person_id=p.id''', (raw.get('voiceEnrollmentId'), person_id)).fetchone()
            if profile and profile['active'] and profile['revoked_at'] is None and profile['status'] == 'ready':
                item.update(speaker=profile['name'], personId=person_id)
    return result
