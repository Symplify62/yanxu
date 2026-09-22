import hashlib
import hmac
import json
import os
import tempfile
import time
import uuid
import wave
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ConfigDict, StrictBool
from . import repository as repo
from .engine import MODEL_VERSION

from functools import wraps
from ..identity.routes import PrivateRoute


class VoicePrivateRoute(PrivateRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        @wraps(handler)
        async def guarded(request):
            try:
                response = await handler(request)
            except HTTPException as error:
                response = JSONResponse({'detail': error.detail}, status_code=error.status_code, headers=error.headers)
            response.headers['Cache-Control'] = 'no-store'
            return response
        return guarded


router = APIRouter(route_class=VoicePrivateRoute)
PRIVATE_HEADERS = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
MAX_SAMPLE_BYTES = 16 * 1024 * 1024


def principal(request):
    from ..identity import current_account
    return current_account(request)


def access_person(request, person_id, operation='enroll'):
    actor = principal(request)
    permissions = actor['permissions']
    allowed = actor.get('personId') == person_id or 'voices' in permissions
    if operation == 'enroll':
        allowed = allowed or 'record' in permissions
    if not allowed:
        raise HTTPException(403, '无权访问此声音档案')
    store = request.app.state.store
    with store.connect() as db:
        row = db.execute('SELECT * FROM identity_people WHERE id=? AND active=1', (person_id,)).fetchone()
    if not row:
        raise HTTPException(404, '人员不存在或已停用')
    return store, actor, dict(row)


def enrollment(request, id, write=False):
    actor = principal(request)
    store = request.app.state.store
    with store.connect() as db:
        row = db.execute('SELECT * FROM voice_enrollments WHERE id=?', (id,)).fetchone()
        if not row or (row['creator_id'] != actor['id'] and 'voices' not in actor['permissions'] and row['person_id'] != actor.get('personId')):
            raise HTTPException(404, '登记不存在')
        if write and row['person_id'] != actor.get('personId') and not any(p in actor['permissions'] for p in ('record', 'voices')):
            raise HTTPException(403, '无权修改此声音登记')
        person = db.execute('SELECT active FROM identity_people WHERE id=?', (row['person_id'],)).fetchone()
        profile = db.execute('SELECT * FROM voice_profiles WHERE person_id=?', (row['person_id'],)).fetchone()
    if not person or not person['active'] or profile['revoked_at'] is not None or row['status'] == 'revoked':
        raise HTTPException(409, '人员或声音授权已失效')
    return store, dict(row), dict(profile)


def status(row):
    return {'id': row['id'], 'personId': row['person_id'], 'status': row['status'],
            'version': row['revision'], 'recordedAt': round(row['created_at'] * 1000), 'error': row['error']}


@router.get('/api/voice-profiles')
def list_profiles(request: Request):
    actor = principal(request)
    store = request.app.state.store
    with store.connect() as db:
        rows = db.execute('''SELECT p.id,v.revision,v.active_id,v.candidate_id,v.revoked_at,
          e.status,e.created_at,e.error,c.status AS candidate_status,c.error AS candidate_error
          FROM identity_people p LEFT JOIN voice_profiles v ON v.person_id=p.id
          LEFT JOIN voice_enrollments e ON e.id=v.active_id
          LEFT JOIN voice_enrollments c ON c.id=v.candidate_id WHERE p.active=1 ORDER BY p.name,p.id''').fetchall()
    items = []
    for row in rows:
        if not any(x in actor['permissions'] for x in ('voices', 'record')) and row['id'] != actor.get('personId'):
            continue
        state = 'revoked' if row['revoked_at'] else 'ready' if row['active_id'] else row['candidate_status'] or 'missing'
        items.append({'personId': row['id'], 'status': state, 'version': row['revision'] or 0,
                      'recordedAt': round(row['created_at'] * 1000) if row['created_at'] else None,
                      'error': row['candidate_error'] or row['error'], 'pendingStatus': row['candidate_status']})
    return {'items': items}


class EnrollmentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    clientId: str = Field(min_length=8, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    totalBytes: int = Field(gt=44, le=MAX_SAMPLE_BYTES)
    nameConfirmed: StrictBool
    voiceConfirmed: StrictBool
    cloudConsent: StrictBool
    confirmedName: str | None = Field(default=None, max_length=80)


@router.post('/api/people/{person_id}/voice-enrollments')
def create_enrollment(person_id: str, value: EnrollmentCreate, request: Request):
    store, actor, person = access_person(request, person_id)
    if not all((value.nameConfirmed, value.voiceConfirmed, value.cloudConsent)):
        raise HTTPException(422, '请本人确认姓名、声音和云端保存授权')
    if value.confirmedName is not None and value.confirmedName != person['name']:
        raise HTTPException(409, '姓名已改变，请重新确认')
    with store.connect(True) as db:
        old = db.execute('SELECT * FROM voice_enrollments WHERE creator_id=? AND client_id=?', (actor['id'], value.clientId)).fetchone()
        if old:
            if old['person_id'] != person_id or old['sha256'] != value.sha256 or old['total_bytes'] != value.totalBytes:
                raise HTTPException(409, '登记编号对应内容已改变')
            if old['status'] in ('revoked', 'superseded'):
                raise HTTPException(409, '此登记已失效，请重新确认后登记')
            return status(old)
        db.execute('INSERT OR IGNORE INTO voice_profiles(person_id) VALUES(?)', (person_id,))
        p = db.execute('SELECT * FROM voice_profiles WHERE person_id=?', (person_id,)).fetchone()
        if p['candidate_id']:
            db.execute("UPDATE voice_enrollments SET status='superseded' WHERE id=?", (p['candidate_id'],))
            db.execute("UPDATE voice_jobs SET status='superseded',owner=NULL,lease_until=NULL WHERE kind='enrollment' AND target_id=? AND status!='complete'", (p['candidate_id'],))
        id, now, revision = str(uuid.uuid4()), time.time(), p['revision'] + 1
        db.execute('''INSERT INTO voice_enrollments(id,person_id,creator_id,client_id,revision,name_snapshot,
          sha256,total_bytes,status,created_at,consent_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (id, person_id, actor['id'], value.clientId, revision, person['name'], value.sha256, value.totalBytes, 'uploading', now, now))
        db.execute('UPDATE voice_profiles SET revision=?,candidate_id=?,revoked_at=NULL WHERE person_id=?', (revision, id, person_id))
        row = db.execute('SELECT * FROM voice_enrollments WHERE id=?', (id,)).fetchone()
    return status(row)


@router.put('/api/voice-enrollments/{id}/audio')
async def upload_audio(id: str, request: Request):
    store, row, profile = enrollment(request, id, write=True)
    if profile['candidate_id'] != id or profile['revision'] != row['revision'] or row['status'] != 'uploading':
        raise HTTPException(409, '登记已封存或被新登记替代')
    root = store.settings.data_dir / 'private-voices'
    fd, temporary = tempfile.mkstemp(prefix='.upload-', dir=root)
    written, digest = 0, hashlib.sha256()
    try:
        with os.fdopen(fd, 'wb') as target:
            async for block in request.stream():
                written += len(block)
                if written > row['total_bytes']:
                    raise HTTPException(413, '声音文件超过申报长度')
                target.write(block)
                digest.update(block)
            target.flush()
            os.fsync(target.fileno())
        if written != row['total_bytes'] or digest.hexdigest() != row['sha256']:
            raise HTTPException(422, '声音文件长度或校验值不符')
        try:
            with wave.open(temporary, 'rb') as wav:
                if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() not in (16000, 24000, 44100, 48000):
                    raise ValueError()
                duration = wav.getnframes() / wav.getframerate()
                if not 3 <= duration <= 120:
                    raise ValueError()
                if len(wav.readframes(wav.getnframes())) != wav.getnframes() * 2:
                    raise ValueError()
        except (wave.Error, EOFError, ValueError):
            raise HTTPException(422, '请提供3至120秒的单声道16位PCM WAV声音样本')
        final = root / (id + '.wav')
        with store.connect(True) as db:
            # Uploading may outlive a role change. Check the current session and
            # permission again while the write transaction excludes such changes.
            enrollment(request, id, write=True)
            live = db.execute('SELECT * FROM voice_profiles WHERE person_id=?', (row['person_id'],)).fetchone()
            active = db.execute('SELECT active FROM identity_people WHERE id=?', (row['person_id'],)).fetchone()
            state = db.execute('SELECT status FROM voice_enrollments WHERE id=?', (id,)).fetchone()
            if not active['active'] or live['candidate_id'] != id or live['revision'] != row['revision'] or state['status'] != 'uploading':
                raise HTTPException(409, '登记已改变，请重新检查')
            os.replace(temporary, final)
            db.execute('UPDATE voice_enrollments SET audio_path=?,duration=? WHERE id=?', (str(final), duration, id))
        return {'id': id, 'status': 'uploaded'}
    finally:
        Path(temporary).unlink(missing_ok=True)


@router.post('/api/voice-enrollments/{id}/complete')
def complete_enrollment(id: str, request: Request):
    store, row, profile = enrollment(request, id, write=True)
    if row['status'] in ('queued', 'processing', 'ready'):
        return status(row)
    if profile['candidate_id'] != id or row['status'] != 'uploading' or not row['audio_path']:
        raise HTTPException(409, '请先上传当前声音样本')
    payload = {'enrollmentId': id, 'sha256': row['sha256'], 'revision': row['revision'],
               'engineCommand': getattr(store.settings, 'voice_engine_command', ''),
               'model': getattr(store.settings, 'voice_model_version', MODEL_VERSION), 'pipeline': 'voice-v2-cluster-first'}
    with store.connect(True) as db:
        enrollment(request, id, write=True)
        live = db.execute('SELECT candidate_id,revision FROM voice_profiles WHERE person_id=?', (row['person_id'],)).fetchone()
        if live['candidate_id'] != id or live['revision'] != row['revision']:
            raise HTTPException(409, '登记已改变')
        db.execute("UPDATE voice_enrollments SET status='queued' WHERE id=?", (id,))
        db.execute('INSERT OR IGNORE INTO voice_jobs(id,kind,target_id,fingerprint,payload,created_at) VALUES(?,?,?,?,?,?)',
                   (str(uuid.uuid4()), 'enrollment', id, repo.fingerprint(payload), repo.encode(payload), time.time()))
    return {'id': id, 'status': 'queued'}


@router.get('/api/voice-enrollments/{id}')
def enrollment_status(id: str, request: Request):
    return status(enrollment(request, id)[1])


@router.post('/api/people/{person_id}/voice-profile/revoke')
def revoke(person_id: str, request: Request):
    store, _, _ = access_person(request, person_id, 'revoke')
    with store.connect(True) as db:
        db.execute('INSERT OR IGNORE INTO voice_profiles(person_id) VALUES(?)', (person_id,))
        paths = [r[0] for r in db.execute('SELECT audio_path FROM voice_enrollments WHERE person_id=?', (person_id,)) if r[0]]
        db.execute('UPDATE voice_profiles SET revision=revision+1,active_id=NULL,candidate_id=NULL,revoked_at=? WHERE person_id=?', (time.time(), person_id))
        db.execute("UPDATE voice_enrollments SET status='revoked',embedding=NULL,quality=NULL WHERE person_id=?", (person_id,))
        db.execute("UPDATE voice_jobs SET status='superseded',owner=NULL,lease_until=NULL WHERE kind='enrollment' AND target_id IN (SELECT id FROM voice_enrollments WHERE person_id=?)", (person_id,))
        db.execute("UPDATE voice_objects SET status='deleting',next_at=0 WHERE enrollment_id IN (SELECT id FROM voice_enrollments WHERE person_id=?) AND status!='deleted'", (person_id,))
        # Persisted job snapshots also contain features. Revocation removes those copies.
        for job in db.execute("SELECT id,payload FROM voice_jobs WHERE kind='attribution'").fetchall():
            payload = json.loads(job['payload'])
            changed = False
            for profile in payload.get('profiles', []):
                if profile['personId'] == person_id:
                    profile.update(embedding=None, name='', revoked=True)
                    changed = True
            if changed:
                db.execute('UPDATE voice_jobs SET payload=? WHERE id=?', (repo.encode(payload), job['id']))
    for path in paths:
        Path(path).unlink(missing_ok=True)
    return {'personId': person_id, 'status': 'revoked'}


@router.get('/api/people/{person_id}/voice-profile/audio')
def profile_audio(person_id: str, request: Request):
    store, _, _ = access_person(request, person_id, 'audio')
    with store.connect() as db:
        row = db.execute('''SELECT e.audio_path FROM voice_profiles p JOIN voice_enrollments e ON e.id=p.active_id
          WHERE p.person_id=? AND p.revoked_at IS NULL AND e.status='ready' ''', (person_id,)).fetchone()
    if not row or not row['audio_path'] or not Path(row['audio_path']).is_file():
        raise HTTPException(404, '声音样本不存在')
    return FileResponse(row['audio_path'], media_type='audio/wav', headers=PRIVATE_HEADERS)


def machine(request):
    store = request.app.state.store
    expected = getattr(store.settings, 'voice_worker_token', '')
    parts = request.headers.get('authorization', '').split()
    token = parts[1] if len(parts) == 2 and parts[0].lower() == 'bearer' else ''
    if len(expected) < 32 or not token or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(403, '声音处理凭证无效')
    return store


class Lease(BaseModel):
    owner: str = Field(min_length=1, max_length=100)


class Result(Lease):
    result: dict


class Failure(Lease):
    retryable: bool = True


@router.post('/internal/voice/claim')
def claim_job(request: Request):
    store = machine(request)
    from .storage import cleanup_one
    cleanup_one(store)
    job = repo.claim(store)
    if not job:
        return {'job': None}
    if job['kind'] == 'attribution':
        with store.connect() as db:
            row = dict(db.execute('SELECT * FROM recordings WHERE id=?', (job['target_id'],)).fetchone())
            fresh = repo.attribution_payload(db, row, store.settings)
        if repo.fingerprint(fresh) != job['fingerprint']:
            # Completion path atomically supersedes it and queues a consent-current snapshot.
            repo.finish(store, job, {})
            return {'job': None}
    else:
        with store.connect() as db:
            live = db.execute('''SELECT e.id FROM voice_enrollments e JOIN voice_profiles p ON p.person_id=e.person_id
              JOIN identity_people i ON i.id=e.person_id WHERE e.id=? AND p.candidate_id=e.id
              AND p.revision=e.revision AND p.revoked_at IS NULL AND i.active=1''', (job['target_id'],)).fetchone()
        if not live:
            repo.fail(store, job, '声音授权或人员状态已改变', retryable=False)
            return {'job': None}
    exported = {k: v for k, v in job['payload'].items() if k != 'engineCommand'}
    if 'profiles' in exported:
        exported['profiles'] = [{k: v for k, v in p.items() if k != 'name'} for p in exported['profiles']]
    return {'job': {'id': job['id'], 'kind': job['kind'], 'owner': job['owner'], 'payload': exported,
                    'leaseSeconds': store.settings.lease_seconds, 'audioUrl': f'/internal/voice/{job["id"]}/audio'}}


@router.post('/internal/voice/{id}/heartbeat')
def heartbeat_job(id: str, value: Lease, request: Request):
    if not repo.heartbeat(machine(request), id, value.owner):
        raise HTTPException(409, '任务租约已失效')
    return {'ok': True}


@router.get('/internal/voice/{id}/audio')
def worker_audio(id: str, owner: str, request: Request):
    store = machine(request)
    with store.connect() as db:
        job = repo.owned_job(db, id, owner)
        if not job:
            raise HTTPException(409, '任务租约已失效')
        if job['kind'] == 'enrollment':
            row = db.execute('''SELECT e.audio_path FROM voice_enrollments e JOIN voice_profiles p ON p.person_id=e.person_id
              JOIN identity_people i ON i.id=e.person_id WHERE e.id=? AND p.candidate_id=e.id
              AND p.revision=e.revision AND p.revoked_at IS NULL AND i.active=1''', (job['target_id'],)).fetchone()
        else:
            row = db.execute('SELECT audio_path FROM recordings WHERE id=?', (job['target_id'],)).fetchone()
    if not row or not row['audio_path'] or not Path(row['audio_path']).is_file():
        raise HTTPException(404, '当前任务声音文件不可用')
    return FileResponse(row['audio_path'], headers=PRIVATE_HEADERS)


@router.post('/internal/voice/{id}/complete')
def finish_job(id: str, value: Result, request: Request):
    store = machine(request)
    with store.connect() as db:
        job = repo.owned_job(db, id, value.owner)
    if not job:
        raise HTTPException(409, '任务租约已失效')
    try:
        if job['kind'] == 'enrollment':
            from .storage import archive, PrivateStorageError
            try:
                archive(store, job['target_id'])
            except PrivateStorageError:
                raise HTTPException(503, '私有声音归档暂未完成')
        complete = repo.finish(store, job, value.result)
    except (ValueError, TypeError, KeyError, OverflowError):
        raise HTTPException(422, '声音处理结果无效')
    if not complete:
        raise HTTPException(409, '声音档案或任务租约已改变')
    return {'ok': True}


@router.post('/internal/voice/{id}/fail')
def fail_job(id: str, value: Failure, request: Request):
    store = machine(request)
    with store.connect() as db:
        job = repo.owned_job(db, id, value.owner)
    if not job or not repo.fail(store, job, retryable=value.retryable):
        raise HTTPException(409, '任务租约已失效')
    return {'ok': True}
