import sqlite3
import time
from pathlib import Path
from types import SimpleNamespace
from fastapi.testclient import TestClient
from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.cloud import sync_one
from yanxu.maintenance import run
from test_pipeline import upload


def test_backup_private_and_cache_only_after_remote_verification(tmp_path, monkeypatch):
    cfg = Settings(
        data_dir=tmp_path,
        storage="qiniu",
        qiniu_access_key="ak",
        qiniu_secret_key="sk",
        qiniu_bucket="b",
        qiniu_domain="https://audio.example.com",
        qiniu_delivery=True,
        worker_stage="analysis",
        worker_token="x" * 40,
    )
    app = create_app(cfg)
    c = TestClient(app)
    s = app.state.store
    id, h, _, _ = upload(c)
    c.post(f"/api/uploads/{id}/complete", headers=h)
    path = Path(s.get(id)["audio_path"])
    assert c.get("/internal/asr/backup").status_code == 403
    b = c.get(
        "/internal/asr/backup", headers={"Authorization": "Bearer " + cfg.worker_token}
    )
    assert b.status_code == 200 and b.content.startswith(b"SQLite format 3")
    assert not list((tmp_path / "backups").glob("download-*"))
    mirror = SimpleNamespace(ensure=lambda *args: None)
    monkeypatch.setattr("yanxu.maintenance.QiniuMirror", lambda cfg: mirror)
    assert run(cfg)["prunedAudioFiles"] == 0 and path.exists()
    sync_one(s, mirror)
    with s.connect(True) as db:
        db.execute("UPDATE cloud_objects SET verified_at=?", (time.time() - 8 * 86400,))
    assert run(cfg)["prunedAudioFiles"] == 1 and not path.exists()
    assert (
        c.get(f"/api/recordings/{id}/audio", follow_redirects=False).status_code == 307
    )
    backup = next((tmp_path / "backups").glob("*.sqlite3"))
    with sqlite3.connect(backup) as db:
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_disk_reservation_rejects_before_upload(tmp_path, monkeypatch):
    cfg = Settings(data_dir=tmp_path, min_free_bytes=1000)
    app = create_app(cfg)
    c = TestClient(app)
    monkeypatch.setattr("shutil.disk_usage", lambda p: SimpleNamespace(free=1500))
    r = c.post(
        "/api/recordings",
        json={
            "client_id": "disk-full-test-0001",
            "total_bytes": 32044,
            "sha256": "0" * 64,
            "extension": "wav",
        },
    )
    assert r.status_code == 429
