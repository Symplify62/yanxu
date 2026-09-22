"""Cross-module HTTP contracts. Engine doubles prove routing/privacy, not accuracy."""
import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.identity.__main__ import bootstrap
from yanxu.store import Store
from yanxu.voice import process_one as voice_once
from yanxu.worker import process_one
from test_voice_profiles import GoodEngine, enroll, wav_bytes, PASSWORD, login


@pytest.fixture
def env(tmp_path):
    cfg = Settings(data_dir=tmp_path, retry_seconds=0, max_attempts=1)
    app = create_app(cfg)
    s, c = app.state.store, TestClient(app)
    admin = bootstrap(s, 'admin', PASSWORD, '管理员')
    h = login(c, 'admin')
    a = c.post('/api/admin/users', headers=h, json={'name': '真实甲', 'username': 'speaker-a', 'password': PASSWORD, 'roleId': 'organizer'}).json()
    b = c.post('/api/admin/users', headers=h, json={'name': '真实乙', 'username': 'speaker-b', 'password': PASSWORD, 'roleId': 'organizer'}).json()
    return c, s, h, a, b


def body(person):
    audio = wav_bytes()
    return {'client_id': 'managed-test-client-0001', 'title': '测试会议', 'total_bytes': len(audio),
            'sha256': hashlib.sha256(audio).hexdigest(), 'extension': 'wav',
            'participants': [{'personId': person['id']}], 'rosterClientId': 'frozen-roster-1'}, audio


def sealed(c, h, person):
    value, audio = body(person)
    res = c.post('/api/managed/recordings', headers=h, json=value)
    assert res.status_code == 200, res.text
    session = res.json()
    uh = {'X-Upload-Token': session['uploadToken']}
    for n, start in enumerate(range(0, len(audio), session['chunkSize'])):
        assert c.put(f'/api/uploads/{session["id"]}/parts/{n}', headers=uh, content=audio[start:start + session['chunkSize']]).status_code == 200
    assert c.post(f'/api/uploads/{session["id"]}/complete', headers=uh).status_code == 200
    return session['id']


def asr(cfg, row):
    return {'text': '先讨论交付时间。', 'segments': [{'id': 's1', 'start': 0., 'end': 4., 'text': '先讨论交付时间。', 'speaker': None}]}


def test_ownership_roster_idempotency_and_legacy_token_isolation(env):
    c, s, h, a, b = env
    ah, bh = login(c, 'speaker-a'), login(c, 'speaker-b')
    value, _ = body(a)
    assert c.post('/api/managed/recordings', json=value).status_code == 401
    first = c.post('/api/managed/recordings', json=value, headers=ah).json()
    again = c.post('/api/managed/recordings', json=value, headers=ah).json()
    assert first == again
    other = c.post('/api/managed/recordings', json=value, headers=bh).json()
    assert first['id'] != other['id'] and first['uploadToken'] != other['uploadToken']
    assert c.get('/api/managed/recordings/' + first['id'], headers=bh).status_code == 404
    mutated = {**value, 'participants': [{'personId': b['id']}]}
    assert c.post('/api/managed/recordings', json=mutated, headers=ah).status_code == 409
    assert c.post('/api/recordings', json=value).status_code == 422
    old = {k: v for k, v in value.items() if k not in ('participants', 'rosterClientId')}
    old['client_id'] = s.get(first['id'])['client_id']
    assert c.post('/api/recordings', json=old).status_code == 409
    assert c.post('/api/managed/recordings', json={**value, 'client_id': 'different-client-0001', 'participants': [{'personId': 'missing'}]}, headers=ah).status_code == 422


def test_real_http_pipeline_waits_public_number_private_name_and_revocation(env):
    c, s, h, a, b = env
    enroll(c, h, a)
    assert voice_once(s, GoodEngine())
    rid = sealed(c, login(c, 'speaker-a'), a)
    assert process_one(s, asr=asr)
    assert s.claim(stage='analysis') is None
    with s.connect() as db:
        assert db.execute('SELECT status FROM jobs WHERE recording_id=?', (rid,)).fetchone()[0] == 'waiting'
    assert voice_once(s, GoodEngine())
    seen = []
    class Analyzer:
        def analyze(self, transcript, *args):
            seen.append(transcript)
            assert 'personId' not in json.dumps(transcript) and '真实甲' not in json.dumps(transcript, ensure_ascii=False)
            return {'summary': '讨论交付时间', 'actions': [], 'decisions': []}
    assert process_one(s, analyzer=Analyzer()) and seen
    pub = c.get('/api/recordings/' + rid).json()
    private = c.get('/api/managed/recordings/' + rid, headers=login(c, 'speaker-a'))
    assert private.headers['cache-control'] == 'no-store'
    assert pub['transcript']['segments'][0]['speaker'] == '说话人 1'
    assert private.json()['transcript']['segments'][0]['speaker'] == '真实甲'
    assert all(k not in json.dumps(pub) for k in ('personId', 'voiceEnrollmentId', 'embedding', 'roster_json', 'owner_account_id'))
    assert c.get('/api/managed/recordings/' + rid, headers=login(c, 'speaker-b')).status_code == 404
    assert c.get('/api/recordings/' + rid + '/audio').status_code == 200
    assert c.post('/api/people/' + a['id'] + '/voice-profile/revoke', headers=h).status_code == 200
    assert c.get('/api/managed/recordings/' + rid, headers=h).json()['transcript']['segments'][0]['speaker'] == '说话人 1'


def test_voice_failure_unblocks_analysis_without_faking_name(env):
    c, s, h, a, b = env
    rid = sealed(c, h, a)
    assert process_one(s, asr=asr)
    assert voice_once(s)  # No model configured in this fixture.
    assert s.get(rid)['transcript']
    job = s.claim(stage='analysis')
    assert job and job['recording_id'] == rid
    assert c.get('/api/recordings/' + rid).json()['transcript']['voice']['status'] == 'failed'


def test_user_maintenance_permission_does_not_grant_other_meetings(env):
    c, s, h, a, b = env
    rid = sealed(c, h, a)
    role = c.post('/api/admin/roles', headers=h, json={'name': '仅人员维护', 'permissions': ['users']}).json()
    response = c.post('/api/admin/users', headers=h, json={'name': '目录维护员', 'username': 'directory-only', 'password': PASSWORD, 'roleId': role['id']})
    assert response.status_code == 200
    limited = login(c, 'directory-only')
    assert c.get('/api/admin/users', headers=limited).status_code == 200
    assert c.get('/api/managed/recordings/' + rid, headers=limited).status_code == 404
    assert c.get('/api/managed/recordings', headers=limited).json()['items'] == []
    assert c.get('/api/managed/recordings/' + rid, headers=h).status_code == 200


def test_core_migration_preserves_legacy_data_and_newer_version(tmp_path):
    cfg = Settings(data_dir=tmp_path)
    s = Store(cfg)
    value, _ = body({'id': 'unused'})
    legacy = {k: v for k, v in value.items() if k not in ('participants', 'rosterClientId')}
    row = s.create(legacy)
    with sqlite3.connect(cfg.db_path) as db:
        db.execute('PRAGMA user_version=9')
    again = Store(cfg)
    assert again.get(row['id'])['sha256'] == row['sha256']
    with again.connect() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 9


def test_upgrade_v1_database_retains_original_upload_and_is_repeatable(tmp_path):
    cfg = Settings(data_dir=tmp_path)
    with sqlite3.connect(cfg.db_path) as db:
        db.execute('''CREATE TABLE recordings(id TEXT PRIMARY KEY, client_id TEXT UNIQUE NOT NULL, upload_token TEXT NOT NULL,
          title TEXT NOT NULL,total_bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,extension TEXT NOT NULL,
          created_at REAL NOT NULL,duration REAL DEFAULT 0,state TEXT NOT NULL DEFAULT 'uploading',
          audio_path TEXT,media_type TEXT,transcript TEXT,analysis TEXT,error TEXT,interrupted INTEGER NOT NULL DEFAULT 0)''')
        db.execute("INSERT INTO recordings(id,client_id,upload_token,title,total_bytes,sha256,extension,created_at) VALUES('legacy-id','legacy-client-0001','existing-token','旧录音',1000,?,'wav',1)", ('f' * 64,))
        db.execute('PRAGMA user_version=1')
    store = Store(cfg)
    Store(cfg)
    row = store.get('legacy-id')
    assert row['upload_token'] == 'existing-token' and row['title'] == '旧录音'
    assert row['owner_account_id'] is None and row['roster_json'] is None
    with store.connect() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute("SELECT version FROM feature_schema WHERE module='core'").fetchone()[0] == 2
