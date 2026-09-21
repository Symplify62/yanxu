import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.deepseek import ProviderError
from yanxu.store import Store
from yanxu.worker import process_one, transcribe
from yanxu.remote_worker import process_remote
from test_pipeline import upload

NO_SPEECH = {"noSpeech": True, "text": "", "segments": []}


def setup_record(tmp_path, **kwargs):
    cfg = Settings(data_dir=tmp_path, worker_token="t" * 40, **kwargs)
    app = create_app(cfg)
    client = TestClient(app)
    rid, headers, _, audio = upload(client)
    assert client.post(f"/api/uploads/{rid}/complete", headers=headers).status_code == 200
    return cfg, client, app.state.store, rid, audio


def assert_terminal(client, store, rid, audio):
    value = client.get(f"/api/recordings/{rid}").json()
    assert value["status"] == "no-speech"
    assert value["error"] is None and value["analysis"] is None
    assert value["transcript"]["noSpeech"] is True
    assert value["transcript"]["text"] == "" and value["transcript"]["segments"] == []
    assert client.get('/api/recordings?filter=complete').json()['total'] == 1
    assert client.get('/api/recordings?filter=processing').json()['total'] == 0
    assert client.get(f'/api/recordings/{rid}/audio?download=true').content == audio
    assert store.claim() is None
    with store.connect() as db:
        job = db.execute('SELECT * FROM jobs WHERE recording_id=?', (rid,)).fetchone()
        assert job['status'] == 'complete' and job['stage'] == 'asr'
        assert job['owner'] is None and job['error'] is None


def test_local_no_speech_is_terminal_skips_analysis_and_releases_capacity(tmp_path):
    cfg, client, store, rid, audio = setup_record(tmp_path, max_pending=1)
    class ForbiddenAnalyzer:
        def analyze(self, *args):
            pytest.fail('No-speech recordings must never call DeepSeek')
    assert process_one(store, asr=lambda *_: NO_SPEECH, analyzer=ForbiddenAnalyzer())
    assert not process_one(store, analyzer=ForbiddenAnalyzer())
    assert_terminal(client, store, rid, audio)
    upload(client, client_id='another-test-recording')
    assert Store(cfg).get(rid)['state'] == 'no-speech'


def test_remote_no_speech_requires_explicit_valid_result_and_current_owner(tmp_path):
    cfg, client, store, rid, audio = setup_record(tmp_path)
    job = store.claim()
    auth = {'Authorization': 'Bearer ' + cfg.worker_token}
    endpoint = f'/internal/asr/{rid}/complete'
    assert client.post(endpoint, json={'owner': job['owner'], 'result': NO_SPEECH}).status_code == 403
    assert client.post(endpoint, headers=auth, json={'owner': 'stale', 'result': NO_SPEECH}).status_code == 409
    for result in [
        {'segments': []},
        {'noSpeech': 'true', 'text': '', 'segments': []},
        {**NO_SPEECH, 'text': 'contradictory speech'},
        {**NO_SPEECH, 'segments': [{'start': 0, 'end': 1, 'text': 'speech'}]},
    ]:
        assert client.post(endpoint, headers=auth, json={'owner': job['owner'], 'result': result}).status_code == 422
    response = client.post(endpoint, headers=auth, json={'owner': job['owner'], 'result': NO_SPEECH})
    assert response.status_code == 200
    assert_terminal(client, store, rid, audio)
    assert client.post(endpoint, headers=auth, json={'owner': job['owner'], 'result': NO_SPEECH}).status_code == 409


@pytest.mark.parametrize('status,chunks,cues,expected', [
    ('complete_no_speech', [], [], 'no-speech'),
    ('complete', [], [], 'error'),
    ('failed', [], [], 'error'),
    ('complete_no_speech', [{'start': 0, 'end': 1, 'text': 'speech'}], [], 'error'),
])
def test_asr_adapter_distinguishes_no_speech_from_invalid_outputs(tmp_path, monkeypatch, status, chunks, cues, expected):
    cfg = Settings(data_dir=tmp_path)
    output = tmp_path / 'asr' / 'test'
    output.mkdir(parents=True)
    (output / 'manifest.json').write_text(json.dumps({'status': status}))
    (output / 'transcript.raw.json').write_text(json.dumps({'chunks': chunks, 'cues': cues}))
    monkeypatch.setattr('yanxu.worker.subprocess.run', lambda *a, **k: SimpleNamespace(returncode=0))
    row = {'id': 'test', 'audio_path': 'unused.wav', 'duration': 7}
    if expected == 'no-speech':
        assert transcribe(cfg, row)['noSpeech'] is True
    else:
        with pytest.raises(ProviderError):
            transcribe(cfg, row)


def test_remote_permanent_error_is_not_misreported_as_no_speech(tmp_path, monkeypatch):
    cfg, client, store, rid, _ = setup_record(tmp_path, storage='qiniu', qiniu_access_key='ak', qiniu_secret_key='sk', qiniu_delivery=True, qiniu_domain='https://audio.example.com', qiniu_bucket='test')
    with store.connect(True) as db:
        db.execute("UPDATE cloud_objects SET status='ready' WHERE recording_id=?", (rid,))
    client.headers['Authorization'] = 'Bearer ' + cfg.worker_token
    monkeypatch.setattr('yanxu.remote_worker.download', lambda *args: tmp_path / 'unused.wav')
    def invalid_alignment(*args):
        raise ProviderError('转写时间信息缺失', False)
    assert process_remote(cfg, client, asr=invalid_alignment)
    row = store.get(rid)
    assert row['state'] == 'transcript-error'
    assert row['error'] == '转写暂未完成'


def test_remote_worker_submits_no_speech_as_completion(tmp_path, monkeypatch):
    cfg, client, store, rid, _ = setup_record(tmp_path, storage='qiniu', qiniu_access_key='ak', qiniu_secret_key='sk', qiniu_delivery=True, qiniu_domain='https://audio.example.com', qiniu_bucket='test')
    with store.connect(True) as db:
        db.execute("UPDATE cloud_objects SET status='ready' WHERE recording_id=?", (rid,))
    client.headers['Authorization'] = 'Bearer ' + cfg.worker_token
    monkeypatch.setattr('yanxu.remote_worker.download', lambda *args: tmp_path / 'unused.wav')
    assert process_remote(cfg, client, asr=lambda *_: NO_SPEECH)
    assert store.get(rid)['state'] == 'no-speech'
    assert not process_remote(cfg, client, asr=lambda *_: pytest.fail('Must not reprocess terminal result'))
    assert store.used_today() == 0
