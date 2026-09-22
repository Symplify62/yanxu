"""Behavioral checks against isolated DB/files; synthetic tone is transport-only."""
import hashlib
import io
import json
import math
import time
import wave

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yanxu.config import Settings
from yanxu.store import Store
from yanxu.identity import initialize as init_identity, router as identity_router
from yanxu.identity.__main__ import bootstrap
from yanxu.voice import initialize, router, process_one, enqueue_attribution, public_transcript, protected_transcript
from yanxu.voice import repository as repo
from yanxu.voice.engine import MODEL_VERSION

PASSWORD = 'test-only-strong-password'


def wav_bytes(seconds=5):
    stream = io.BytesIO()
    import struct
    with wave.open(stream, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b''.join(struct.pack('<h', int(3000 * math.sin(i / 16000 * 2 * math.pi * 200))) for i in range(16000 * seconds)))
    return stream.getvalue()


@pytest.fixture
def env(tmp_path):
    cfg = Settings(data_dir=tmp_path)
    cfg.voice_worker_token = 'voice-only-token-123456789-abcdefghijk'
    cfg.voice_engine_command = ''
    cfg.voice_model_version = MODEL_VERSION
    store = Store(cfg)
    init_identity(store)
    initialize(store)
    admin = bootstrap(store, 'admin', PASSWORD, '管理员')
    app = FastAPI()
    app.state.store, app.state.settings = store, cfg
    app.include_router(identity_router)
    app.include_router(router)
    c = TestClient(app)
    h = login(c, 'admin')
    person = c.post('/api/admin/users', headers=h, json={'name': '甲', 'username': 'person-a', 'password': PASSWORD, 'roleId': 'member'}).json()
    second = c.post('/api/admin/users', headers=h, json={'name': '乙', 'username': 'person-b', 'password': PASSWORD, 'roleId': 'member'}).json()
    return c, store, h, person, second


def login(c, name):
    response = c.post('/api/auth/login', json={'username': name, 'password': PASSWORD})
    assert response.status_code == 200, response.text
    return {'Authorization': 'Bearer ' + response.json()['accessToken']}


def enroll(c, h, person, client_id='test-registration', complete=True):
    audio = wav_bytes()
    value = {'clientId': client_id, 'sha256': hashlib.sha256(audio).hexdigest(), 'totalBytes': len(audio),
             'nameConfirmed': True, 'voiceConfirmed': True, 'cloudConsent': True, 'confirmedName': person['name']}
    response = c.post(f'/api/people/{person["id"]}/voice-enrollments', headers=h, json=value)
    assert response.status_code == 200, response.text
    id = response.json()['id']
    response = c.put(f'/api/voice-enrollments/{id}/audio', headers=h, content=audio)
    assert response.status_code == 200, response.text
    if complete:
        response = c.post(f'/api/voice-enrollments/{id}/complete', headers=h)
        assert response.status_code == 200, response.text
    return id, value


class GoodEngine:
    def run(self, kind, audio, payload):
        if kind == 'enrollment':
            return {'model': MODEL_VERSION, 'embedding': [1.] + [0.] * 255, 'quality': {'testDouble': True}}
        profile = next((p for p in payload['profiles'] if p.get('embedding')), None)
        return {'model': MODEL_VERSION, 'pipeline': 'voice-v2-cluster-first', 'turns': [{'start': 0, 'end': 4, 'speakerId': 'speaker-1',
                'personId': profile['personId'] if profile else None, 'score': .9, 'margin': .2}]}


def test_consent_auth_scope_and_private_audio(env):
    c, s, h, person, second = env
    endpoint = f'/api/people/{person["id"]}/voice-enrollments'
    audio = wav_bytes()
    value = {'clientId': 'consent-test', 'sha256': hashlib.sha256(audio).hexdigest(), 'totalBytes': len(audio),
             'nameConfirmed': True, 'voiceConfirmed': True, 'cloudConsent': False}
    assert c.post(endpoint, json=value).status_code == 401
    assert c.post(endpoint, headers=h, json=value).status_code == 422
    value['cloudConsent'] = 'yes'
    assert c.post(endpoint, headers=h, json=value).status_code == 422
    value['cloudConsent'] = True
    stranger = login(c, 'person-b')
    assert c.post(endpoint, headers=stranger, json=value).status_code == 403
    own = login(c, 'person-a')
    id, _ = enroll(c, own, person)
    assert c.get(f'/api/voice-enrollments/{id}', headers=stranger).status_code == 404
    assert process_one(s, GoodEngine())
    url = f'/api/people/{person["id"]}/voice-profile/audio'
    assert c.get(url).status_code == 401
    assert c.get(url, headers=stranger).status_code == 403
    result = c.get(url, headers=own)
    assert result.status_code == 200 and result.content == audio
    assert result.headers['cache-control'] == 'no-store'
    listed = c.get('/api/voice-profiles', headers=own).json()
    assert len(listed['items']) == 1 and listed['items'][0]['status'] == 'ready'
    assert 'embedding' not in json.dumps(listed) and 'audio_path' not in json.dumps(listed)
    assert not list(s.settings.data_dir.glob('recordings/*'))


def test_payload_hash_format_idempotency_and_no_false_ready(env):
    c, s, h, person, _ = env
    id, value = enroll(c, h, person, complete=False)
    assert c.post(f'/api/people/{person["id"]}/voice-enrollments', headers=h, json=value).json()['id'] == id
    altered = dict(value, sha256='0' * 64)
    assert c.post(f'/api/people/{person["id"]}/voice-enrollments', headers=h, json=altered).status_code == 409
    assert c.put(f'/api/voice-enrollments/{id}/audio', headers=h, content=b'invalid').status_code == 422
    c.post(f'/api/voice-enrollments/{id}/complete', headers=h)
    assert process_one(s)  # No command configured: failure/retry, never ready.
    assert c.get(f'/api/voice-enrollments/{id}', headers=h).json()['status'] == 'queued'
    with s.connect(True) as db:
        db.execute('UPDATE voice_jobs SET attempts=3,next_at=0')
    assert process_one(s)
    assert c.get(f'/api/voice-enrollments/{id}', headers=h).json()['status'] == 'failed'


def test_rerecord_failure_preserves_old_and_revoke_stops_stale_results(env):
    c, s, h, person, _ = env
    original, _ = enroll(c, h, person)
    process_one(s, GoodEngine())
    second, _ = enroll(c, h, person, 'second-registration')
    job = repo.claim(s)
    with s.connect() as db:
        assert db.execute('SELECT active_id FROM voice_profiles').fetchone()[0] == original
    repo.fail(s, job, retryable=False)
    assert next(p for p in c.get('/api/voice-profiles', headers=h).json()['items'] if p['personId'] == person['id'])['status'] == 'ready'
    third, _ = enroll(c, h, person, 'third-registration')
    job = repo.claim(s)
    assert c.post(f'/api/people/{person["id"]}/voice-profile/revoke', headers=h).status_code == 200
    assert not repo.finish(s, job, GoodEngine().run('enrollment', None, None))
    with s.connect() as db:
        assert db.execute('SELECT active_id FROM voice_profiles').fetchone()[0] is None
        assert all(r[0] is None for r in db.execute('SELECT embedding FROM voice_enrollments'))
    assert not list((s.settings.data_dir / 'private-voices').glob('*.wav'))
    assert c.get(f'/api/people/{person["id"]}/voice-profile/audio', headers=h).status_code == 404


def test_newer_candidate_supersedes_old_worker_and_wrong_model(env):
    c, s, h, person, _ = env
    first, _ = enroll(c, h, person)
    old = repo.claim(s)
    second, _ = enroll(c, h, person, 'newer-registration')
    assert not repo.finish(s, old, GoodEngine().run('enrollment', None, None))
    new = repo.claim(s)
    with pytest.raises(ValueError):
        repo.finish(s, new, {'model': 'different-model', 'embedding': [1.] * 256})
    assert repo.finish(s, new, GoodEngine().run('enrollment', None, None))
    with s.connect() as db:
        assert db.execute('SELECT active_id FROM voice_profiles').fetchone()[0] == second


def recording(s, person):
    with s.connect(True) as db:
        columns = {r[1] for r in db.execute('PRAGMA table_info(recordings)')}
        for column in ('roster_json', 'owner_account_id', 'attribution_state'):
            if column not in columns:
                db.execute(f'ALTER TABLE recordings ADD COLUMN {column} TEXT')
    audio = s.settings.data_dir / 'test-meeting.wav'
    audio.write_bytes(wav_bytes())
    record = s.create({'client_id': 'voice-test-meeting', 'title': '会议', 'sha256': hashlib.sha256(audio.read_bytes()).hexdigest(),
                      'total_bytes': audio.stat().st_size, 'extension': 'wav'})
    transcript = {'text': '讨论工作', 'segments': [{'id': 'seg1', 'start': 0, 'end': 4, 'text': '讨论工作', 'speaker': None}]}
    with s.connect(True) as db:
        db.execute('UPDATE recordings SET owner_account_id=?,roster_json=?,transcript=?,duration=5,audio_path=? WHERE id=?',
                   ('organizer', json.dumps([{'personId': person['id'], 'name': person['name']}]), json.dumps(transcript), str(audio), record['id']))
        db.execute("INSERT OR REPLACE INTO jobs(recording_id,stage,status) VALUES(?,'analysis','pending')", (record['id'],))
    return record['id']


def test_attribution_waits_then_public_number_private_name_revoke(env):
    c, s, h, person, _ = env
    enroll(c, h, person)
    process_one(s, GoodEngine())
    id = recording(s, person)
    with s.connect(True) as db:
        assert enqueue_attribution(s, id, db=db)
    with s.connect() as db:
        assert db.execute('SELECT status FROM jobs').fetchone()[0] == 'waiting'
    assert process_one(s, GoodEngine())
    row = s.get(id)
    public = public_transcript(row['transcript'])
    assert public['segments'][0]['speaker'] == '说话人 1'
    assert person['name'] not in json.dumps(public, ensure_ascii=False)
    assert 'personId' not in json.dumps(public)
    private = protected_transcript(s, row)
    assert private['segments'][0]['speaker'] == person['name']
    with s.connect() as db:
        assert db.execute('SELECT status FROM jobs').fetchone()[0] == 'pending'
    c.post(f'/api/people/{person["id"]}/voice-profile/revoke', headers=h)
    assert protected_transcript(s, row)['segments'][0]['speaker'] == '说话人 1'


def test_attribution_revoke_during_work_requeues_and_failure_releases_analysis(env):
    c, s, h, person, _ = env
    enroll(c, h, person)
    process_one(s, GoodEngine())
    id = recording(s, person)
    enqueue_attribution(s, id)
    job = repo.claim(s)
    result = GoodEngine().run('attribution', None, job['payload'])
    c.post(f'/api/people/{person["id"]}/voice-profile/revoke', headers=h)
    assert not repo.finish(s, job, result)
    fresh = repo.claim(s)
    assert fresh['payload']['profiles'][0]['embedding'] is None
    assert repo.fail(s, fresh, retryable=False)
    assert json.loads(s.get(id)['transcript'])['segments'][0]['speaker'] is None
    with s.connect() as db:
        assert db.execute('SELECT status FROM jobs').fetchone()[0] == 'pending'


def test_machine_token_lease_and_model_validation(env):
    c, s, h, person, _ = env
    enroll(c, h, person)
    assert c.post('/internal/voice/claim', headers=h).status_code == 403
    assert c.post('/internal/voice/claim', headers={'Authorization': 'Bearer asr-token'}).status_code == 403
    machine = {'Authorization': 'Bearer ' + s.settings.voice_worker_token}
    first = c.post('/internal/voice/claim', headers=machine).json()['job']
    audio = c.get(first['audioUrl'], params={'owner': first['owner']}, headers=machine)
    assert audio.status_code == 200 and audio.content == wav_bytes()
    with s.connect(True) as db:
        db.execute('UPDATE voice_jobs SET lease_until=?', (time.time() - 1,))
    assert c.post(f'/internal/voice/{first["id"]}/heartbeat', json={'owner': first['owner']}, headers=machine).status_code == 409
    second = c.post('/internal/voice/claim', headers=machine).json()['job']
    result = GoodEngine().run('enrollment', None, None)
    assert c.post(f'/internal/voice/{first["id"]}/complete', headers=machine, json={'owner': first['owner'], 'result': result}).status_code == 409
    assert c.post(f'/internal/voice/{second["id"]}/complete', headers=machine, json={'owner': second['owner'], 'result': result}).status_code == 200


def test_low_confidence_unknown_and_mixed_segments_not_forced_to_name():
    profile = {'personId': 'p', 'name': '私有姓名', 'active': True, 'revoked': False, 'model': MODEL_VERSION,
               'embedding': [1.] * 256, 'enrollmentId': 'e'}
    segment = {'id': 's', 'start': 0, 'end': 4, 'text': '讨论工作'}
    payload = {'model': MODEL_VERSION, 'pipeline': 'voice-v2-cluster-first', 'duration': 4, 'profiles': [profile], 'threshold': .75, 'margin': .08, 'segments': [segment]}
    result = {'model': MODEL_VERSION, 'pipeline': 'voice-v2-cluster-first', 'turns': [{'start': 0, 'end': 4, 'speakerId': 'speaker-1', 'personId': 'p', 'score': .5, 'margin': .1}]}
    with pytest.raises(ValueError):
        repo.apply_attribution(payload, {'segments': [segment]}, result)
    result['turns'] = [{'start': 0, 'end': 2, 'speakerId': 'speaker-1', 'personId': 'p', 'score': .9, 'margin': .2},
                       {'start': 2, 'end': 4, 'speakerId': 'speaker-2', 'personId': None}]
    assert repo.apply_attribution(payload, {}, result)['segments'][0]['speaker'] is None


def test_remote_worker_download_checks_hash_and_dedicated_protocol(env):
    from yanxu.voice.remote_worker import process_remote_once
    c, s, h, person, _ = env
    s.settings.remote_api = 'http://127.0.0.1:5197'
    id, _ = enroll(c, h, person)
    assert process_remote_once(s.settings, client=c, engine=GoodEngine())
    assert c.get(f'/api/voice-enrollments/{id}', headers=h).json()['status'] == 'ready'
    assert not list((s.settings.data_dir / 'private-voices' / 'worker-cache').glob('job-*'))
    assert not process_remote_once(s.settings, client=c, engine=GoodEngine())


def test_revoke_scrubs_persisted_attribution_features_and_blocks_worker_audio(env):
    c, s, h, person, _ = env
    enroll(c, h, person)
    process_one(s, GoodEngine())
    id = recording(s, person)
    enqueue_attribution(s, id)
    c.post(f'/api/people/{person["id"]}/voice-profile/revoke', headers=h)
    with s.connect() as db:
        snapshot = json.loads(db.execute("SELECT payload FROM voice_jobs WHERE kind='attribution'").fetchone()[0])
        assert snapshot['profiles'][0]['embedding'] is None
        assert snapshot['profiles'][0]['name'] == ''
    machine = {'Authorization': 'Bearer ' + s.settings.voice_worker_token}
    assert c.post('/internal/voice/claim', headers=machine).json()['job'] is None  # stale snapshot replaced
    fresh = c.post('/internal/voice/claim', headers=machine).json()['job']
    assert fresh['payload']['profiles'][0]['embedding'] is None
    assert 'name' not in fresh['payload']['profiles'][0]


def test_person_disabled_before_machine_claim_never_exports_voice_sample(env):
    c, s, h, person, _ = env
    id, _ = enroll(c, h, person)
    with s.connect(True) as db:
        db.execute('UPDATE identity_people SET active=0 WHERE id=?', (person['id'],))
    assert c.get(f'/api/people/{person["id"]}/voice-profile/audio', headers=h).status_code == 404
    machine = {'Authorization': 'Bearer ' + s.settings.voice_worker_token}
    assert c.post('/internal/voice/claim', headers=machine).json()['job'] is None
    with s.connect() as db:
        assert db.execute('SELECT embedding FROM voice_enrollments WHERE id=?', (id,)).fetchone()[0] is None


def test_future_schema_refused_without_resetting_other_modules(env):
    _, s, _, _, _ = env
    with s.connect(True) as db:
        db.execute("UPDATE feature_schema SET version=999 WHERE module='voice'")
    with pytest.raises(RuntimeError):
        initialize(s)
    with s.connect() as db:
        assert db.execute("SELECT version FROM feature_schema WHERE module='voice'").fetchone()[0] == 999
        assert db.execute("SELECT count(*) FROM identity_people").fetchone()[0] == 3


def test_private_bucket_must_be_different_and_verified_before_upload(env):
    from yanxu.voice.storage import PrivateQiniu, PrivateStorageError
    from types import SimpleNamespace
    _, s, _, _, _ = env
    s.settings.qiniu_bucket = 'public-recordings'
    s.settings.voice_private_bucket = 'public-recordings'
    with pytest.raises(PrivateStorageError):
        PrivateQiniu(s.settings)
    s.settings.voice_private_bucket = 'private-voices'
    s.settings.qiniu_access_key = 'fake-test-access'
    s.settings.qiniu_secret_key = 'fake-test-secret'
    class Manager:
        def __init__(self, private):
            self.private = private
        def bucket_info(self, bucket):
            return {'private': self.private}, SimpleNamespace(status_code=200)
        def stat(self, *args):
            raise AssertionError('must not inspect or upload objects in a public bucket')
    for value in (0, None, '1'):
        with pytest.raises(PrivateStorageError):
            PrivateQiniu(s.settings, manager=Manager(value)).ensure('/unused.wav', 'key')
    PrivateQiniu(s.settings, manager=Manager(1)).check_private()


def test_private_errors_and_metadata_are_not_cacheable(env):
    c, s, h, person, _ = env
    for response in (
        c.get('/api/voice-profiles'),
        c.get('/api/voice-profiles', headers=h),
        c.post('/internal/voice/claim'),
        c.post(f'/api/people/{person["id"]}/voice-enrollments', headers=h, json={'unknown':'invalid'}),
    ):
        assert response.headers['cache-control'] == 'no-store'
    s.settings.voice_worker_token = 'short'
    assert c.post('/internal/voice/claim', headers={'Authorization':'Bearer short'}).status_code == 403


def test_segment_containing_short_other_speaker_is_not_majority_named():
    segment = {'id':'s','start':0,'end':10,'text':'甲的长句和乙的短句'}
    profile = {'personId':'p','name':'甲','active':True,'revoked':False,'model':MODEL_VERSION,
               'embedding':[1.]*256,'enrollmentId':'e'}
    payload = {'model':MODEL_VERSION,'pipeline':'voice-v2-cluster-first','duration':10,
               'profiles':[profile],'threshold':.75,'margin':.08,'segments':[segment]}
    result = {'model':MODEL_VERSION,'pipeline':'voice-v2-cluster-first','turns':[
        {'start':0,'end':8.8,'speakerId':'speaker-1','personId':'p','score':.9,'margin':.2},
        {'start':8.8,'end':10,'speakerId':'speaker-2','personId':None}]}
    output=repo.apply_attribution(payload,{},result)['segments'][0]
    assert output['speaker'] is None and 'personId' not in output


@pytest.mark.parametrize('restored_status', ['superseded', 'complete', 'failed'])
@pytest.mark.parametrize('mutation', [{'name': '新姓名'}, {'active': False}], ids=['rename', 'deactivate'])
def test_restored_attribution_snapshot_is_requeued_not_left_waiting(env, restored_status, mutation):
    c, s, h, person, _ = env
    enroll(c, h, person)
    process_one(s, GoodEngine())
    record_id = recording(s, person)
    assert enqueue_attribution(s, record_id)
    first = repo.claim(s)
    assert c.patch(f'/api/admin/users/{person["id"]}', headers=h, json=mutation).status_code == 200
    assert not repo.finish(s, first, GoodEngine().run('attribution', None, first['payload']))
    second = repo.claim(s)
    assert second and second['id'] != first['id']
    # Historical terminal jobs must not be mistaken for a stored transcript of
    # that fingerprint. The current transcript may belong to a later snapshot.
    with s.connect(True) as db:
        db.execute('UPDATE voice_jobs SET status=? WHERE id=?', (restored_status, first['id']))
    assert c.patch(f'/api/admin/users/{person["id"]}', headers=h, json={'name': person['name'], 'active': True}).status_code == 200
    assert not repo.finish(s, second, GoodEngine().run('attribution', None, second['payload']))
    restored = repo.claim(s)
    assert restored is not None and restored['fingerprint'] == first['fingerprint']
    assert restored['attempts'] == 1
    with s.connect() as db:
        assert db.execute('SELECT status FROM jobs WHERE recording_id=?', (record_id,)).fetchone()[0] == 'waiting'
    assert repo.finish(s, restored, GoodEngine().run('attribution', None, restored['payload']))
    with s.connect() as db:
        assert db.execute('SELECT status FROM jobs WHERE recording_id=?', (record_id,)).fetchone()[0] == 'pending'
    assert protected_transcript(s, s.get(record_id))['segments'][0]['speaker'] == person['name']


def test_enqueue_reactivates_a_superseded_attribution_snapshot(env):
    c, s, h, person, _ = env
    enroll(c, h, person)
    process_one(s, GoodEngine())
    record_id = recording(s, person)
    assert enqueue_attribution(s, record_id)
    stale = repo.claim(s)
    with s.connect(True) as db:
        db.execute("UPDATE voice_jobs SET status='superseded' WHERE id=?", (stale['id'],))
    assert enqueue_attribution(s, record_id)
    current = repo.claim(s)
    assert current is not None and current['owner'] != stale['owner']
    assert not repo.finish(s, stale, GoodEngine().run('attribution', None, stale['payload']))


@pytest.mark.parametrize('size', [32, 255, 257, 2048])
def test_fixed_model_rejects_incompatible_embedding_dimensions(env, size):
    c, s, h, person, _ = env
    enrollment_id, _ = enroll(c, h, person)
    machine = {'Authorization': 'Bearer ' + s.settings.voice_worker_token}
    job = c.post('/internal/voice/claim', headers=machine).json()['job']
    result = {'model': MODEL_VERSION, 'embedding': [1.] * size}
    response = c.post(f'/internal/voice/{job["id"]}/complete', headers=machine,
                      json={'owner': job['owner'], 'result': result})
    assert response.status_code == 422
    assert c.get(f'/api/voice-enrollments/{enrollment_id}', headers=h).json()['status'] != 'ready'
    result['embedding'] = [1.] * 256
    assert c.post(f'/internal/voice/{job["id"]}/complete', headers=machine,
                  json={'owner': job['owner'], 'result': result}).status_code == 200


@pytest.mark.parametrize('value', [0., float('nan'), float('inf'), 1e308])
def test_fixed_model_rejects_unusable_embedding_values(value):
    with pytest.raises(ValueError):
        repo.normalize_embedding([value] * 256)


def test_enrollment_writes_recheck_current_permissions_after_role_change(env):
    c, s, h, person, _ = env
    role = c.post('/api/admin/roles', headers=h,
                  json={'name': '临时协助登记', 'permissions': ['record']}).json()
    organizer = c.post('/api/admin/users', headers=h, json={
        'name': '组织者', 'username': 'organizer', 'password': PASSWORD, 'roleId': role['id']}).json()
    organizer_headers = login(c, 'organizer')
    other_id, _ = enroll(c, organizer_headers, person, 'other-person-enrollment', complete=False)
    own_id, _ = enroll(c, organizer_headers, organizer, 'own-person-enrollment', complete=False)
    assert c.patch(f'/api/admin/roles/{role["id"]}', headers=h, json={'permissions': []}).status_code == 200
    assert c.get('/api/auth/me', headers=organizer_headers).json()['permissions'] == []
    for endpoint, method, kwargs in (
        (f'/api/voice-enrollments/{other_id}/audio', c.put, {'content': wav_bytes()}),
        (f'/api/voice-enrollments/{other_id}/complete', c.post, {}),
    ):
        assert method(endpoint, headers=organizer_headers, **kwargs).status_code == 403
    # The same session retains read access to its submitted registration and
    # the ordinary member's ability to manage their own voice.
    assert c.get(f'/api/voice-enrollments/{other_id}', headers=organizer_headers).status_code == 200
    assert c.post(f'/api/voice-enrollments/{own_id}/complete', headers=organizer_headers).status_code == 200
    assert c.post(f'/api/voice-enrollments/{other_id}/complete', headers=h).status_code == 200
