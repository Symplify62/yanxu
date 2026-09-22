"""Private backup is transport/recovery evidence, not speaker-accuracy evidence."""
import hashlib
import io
import json
import os
import sqlite3
import tarfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.identity.__main__ import bootstrap
from yanxu.maintenance import run
from yanxu.remote_worker import backup_database
from test_voice_profiles import PASSWORD, GoodEngine, enroll, login, wav_bytes


@pytest.fixture
def env(tmp_path):
    cfg = Settings(data_dir=tmp_path / 'server', worker_token='a'*40,
                   backup_token='b'*40, voice_worker_token='c'*40)
    app = create_app(cfg)
    client = TestClient(app)
    bootstrap(app.state.store, 'admin', PASSWORD, '测试管理员')
    headers = login(client, 'admin')
    person = client.post('/api/admin/users', headers=headers, json={'name': '测试人员'}).json()
    enrollment_id, _ = enroll(client, headers, person)
    return cfg, client, app.state.store, headers, person, enrollment_id


def test_bundle_requires_separate_token_and_restores_referenced_audio(env, tmp_path):
    from yanxu.private_backup import restore_bundle
    from yanxu.voice import process_one
    cfg, client, store, _, person, enrollment_id = env
    assert process_one(store, GoodEngine())
    for token in ('', cfg.worker_token, cfg.voice_worker_token):
        response = client.get('/internal/asr/backup-bundle', headers={'Authorization': 'Bearer '+token})
        assert response.status_code == 403
    response = client.get('/internal/asr/backup-bundle', headers={'Authorization': 'Bearer '+cfg.backup_token})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    bundle = tmp_path / 'received.tar'
    bundle.write_bytes(response.content)
    target = tmp_path / 'recovery'
    evidence = restore_bundle(bundle, target)
    assert evidence['samples'] == 1
    audio = target / 'private-voices' / (enrollment_id+'.wav')
    assert audio.read_bytes() == wav_bytes()
    assert audio.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(target/'yanxu.sqlite3') as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT audio_path FROM voice_enrollments WHERE id=?', (enrollment_id,)).fetchone()[0] == str(audio)
    recovered = TestClient(create_app(Settings(data_dir=target)))
    headers = login(recovered, 'admin')
    response = recovered.get(f'/api/people/{person["id"]}/voice-profile/audio', headers=headers)
    assert response.status_code == 200 and response.content == wav_bytes()
    assert not list((cfg.data_dir/'backups').glob('download-*'))
    assert client.get('/internal/asr/backup', headers={'Authorization': 'Bearer '+cfg.backup_token}).content.startswith(b'SQLite format 3')


def test_revoked_and_unreferenced_files_never_enter_bundle(env, tmp_path):
    from yanxu.private_backup import create_bundle, restore_bundle
    cfg, client, store, headers, person, _ = env
    assert client.post(f'/api/people/{person["id"]}/voice-profile/revoke', headers=headers).status_code == 200
    (cfg.data_dir/'private-voices'/'unreferenced.wav').write_bytes(wav_bytes())
    bundle = create_bundle(store, tmp_path/'private.tar')
    assert restore_bundle(bundle, tmp_path/'recovery')['samples'] == 0
    with tarfile.open(bundle) as archive:
        assert not any(member.name.endswith('.wav') for member in archive)


@pytest.mark.parametrize('mode', ['missing', 'changed', 'outside', 'symlink'])
def test_inconsistent_source_fails_without_successful_bundle(env, tmp_path, mode):
    from yanxu.private_backup import create_bundle
    cfg, _, store, _, _, enrollment_id = env
    original = cfg.data_dir/'private-voices'/(enrollment_id+'.wav')
    if mode == 'missing':
        original.unlink()
    elif mode == 'changed':
        original.write_bytes(b'changed')
    else:
        external = tmp_path/'external.wav'
        external.write_bytes(wav_bytes())
        if mode == 'symlink':
            original.unlink()
            original.symlink_to(external)
        else:
            with store.connect(True) as db:
                db.execute('UPDATE voice_enrollments SET audio_path=? WHERE id=?', (str(external), enrollment_id))
    target = tmp_path/'must-not-exist.tar'
    with pytest.raises((ValueError, OSError)):
        create_bundle(store, target)
    assert not target.exists()


def malicious_bundle(path, entries):
    with tarfile.open(path, 'w') as archive:
        for name, data in entries:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))


def test_restore_rejects_traversal_symlink_extra_and_tampered_files(env, tmp_path):
    from yanxu.private_backup import create_bundle, restore_bundle
    good = create_bundle(env[2], tmp_path/'good.tar')
    with tarfile.open(good) as archive:
        entries = [(m.name, archive.extractfile(m).read()) for m in archive]
    for index, bad in enumerate([
        entries + [('../escape', b'x')],
        entries + [('private-voices/unexpected.wav', b'x')],
        [(name, data+b'x' if name.endswith('.wav') else data) for name, data in entries],
        entries + [entries[-1]],
    ]):
        path = tmp_path/f'bad-{index}.tar'
        malicious_bundle(path, bad)
        with pytest.raises(ValueError):
            restore_bundle(path, tmp_path/f'restore-{index}')
        assert not (tmp_path/f'restore-{index}').exists()
    path = tmp_path/'symlink.tar'
    with tarfile.open(path, 'w') as archive:
        member = tarfile.TarInfo('manifest.json')
        member.type = tarfile.SYMTYPE
        member.linkname = '../escape'
        archive.addfile(member)
    with pytest.raises(ValueError):
        restore_bundle(path, tmp_path/'restore-symlink')
    assert not (tmp_path/'escape').exists()


def test_maintenance_keeps_sqlite_compatibility_and_private_bundle(env):
    cfg, _, _, _, _, _ = env
    result = run(cfg)
    assert (cfg.data_dir/'backups'/result['backup']).exists()
    assert (cfg.data_dir/'backups'/result['privateBackup']).exists()
    assert result['privateSamples'] == 1


def test_remote_backup_validates_before_publish_and_retains_thirty(env, tmp_path):
    from yanxu.private_backup import create_bundle
    cfg, client, store, _, _, _ = env
    local = Settings(data_dir=tmp_path/'mac', backup_token=cfg.backup_token)
    bundle = create_bundle(store, tmp_path/'source.tar').read_bytes()
    calls = []
    def response(request):
        calls.append(request)
        return httpx.Response(200, content=bundle)
    with httpx.Client(base_url='https://testserver', transport=httpx.MockTransport(response)) as remote:
        assert backup_database(local, remote)['samples'] == 1
        assert len(calls) == 1
        assert calls[0].url.path == '/internal/asr/backup-bundle'
        assert calls[0].headers['Authorization'] == 'Bearer '+cfg.backup_token
        assert backup_database(local, remote) is None
    folder = local.data_dir/'cloud-backups'
    assert len(list(folder.glob('*.tar'))) == 1
    for n in range(35):
        path = folder/f'200001{n:02d}T000000Z.tar'
        path.write_bytes(bundle)
        os.utime(path, (1, 1))
    for path in folder.glob('*.tar'):
        os.utime(path, (1, 1))
    with httpx.Client(base_url='https://testserver', transport=httpx.MockTransport(response)) as remote:
        backup_database(local, remote)
    assert len(list(folder.glob('*.tar'))) == 30


def test_invalid_remote_backup_not_published_and_can_retry(env, tmp_path):
    cfg = Settings(data_dir=tmp_path/'mac', backup_token='b'*40)
    with httpx.Client(base_url='https://testserver', transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b'broken'))) as remote:
        with pytest.raises(ValueError):
            backup_database(cfg, remote)
    folder = cfg.data_dir/'cloud-backups'
    assert not list(folder.glob('*.tar'))
    assert not list(folder.glob('receiving*'))


def test_backup_failure_does_not_prevent_asr_polling(tmp_path, monkeypatch):
    from yanxu import remote_worker
    cfg = Settings(data_dir=tmp_path/'mac', backup_token='b'*40, worker_token='a'*40,
                   remote_api='https://testserver', qiniu_domain='https://audio.example.com')
    monkeypatch.setattr(Settings, 'load', lambda: cfg)
    called = []
    def failed_backup(*args):
        called.append('backup')
        raise ValueError('corrupted backup')
    class StopTest(Exception):
        pass
    def process(*args):
        called.append('asr')
        raise StopTest()
    monkeypatch.setattr(remote_worker, 'backup_database', failed_backup)
    monkeypatch.setattr(remote_worker, 'process_remote', process)
    with pytest.raises(StopTest):
        remote_worker.main()
    assert called == ['backup', 'asr']


def test_size_limit_and_existing_restore_destination_are_enforced(env, tmp_path, monkeypatch):
    from yanxu import private_backup
    good = private_backup.create_bundle(env[2], tmp_path/'good.tar')
    existing = tmp_path/'existing'
    existing.mkdir()
    (existing/'preserve').write_text('existing data')
    with pytest.raises(ValueError):
        private_backup.restore_bundle(good, existing)
    assert (existing/'preserve').read_text() == 'existing data'
    monkeypatch.setattr(private_backup, 'MAX_BUNDLE_BYTES', 100)
    with pytest.raises(ValueError):
        private_backup.restore_bundle(good, tmp_path/'oversized')
    assert not (tmp_path/'oversized').exists()


def test_bundle_endpoint_fails_closed_when_referenced_sample_missing(env):
    cfg, client, _, _, _, enrollment_id = env
    (cfg.data_dir/'private-voices'/(enrollment_id+'.wav')).unlink()
    response = client.get('/internal/asr/backup-bundle', headers={'Authorization': 'Bearer '+cfg.backup_token})
    assert response.status_code == 503
    assert not list((cfg.data_dir/'backups').glob('download-*'))
