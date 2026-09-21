import time
from fastapi.testclient import TestClient
from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.cloud import sync_one
from yanxu.worker import process_one
from test_pipeline import upload, Analyzer
from types import SimpleNamespace


def test_remote_auth_ready_gate_lease_reclaim_and_analysis(tmp_path):
    cfg = Settings(
        data_dir=tmp_path,
        storage="qiniu",
        qiniu_access_key="ak",
        qiniu_secret_key="sk",
        qiniu_bucket="bucket",
        qiniu_domain="https://audio.example.com",
        qiniu_delivery=True,
        worker_stage="analysis",
        worker_token="x" * 40,
    )
    app = create_app(cfg)
    c = TestClient(app)
    s = app.state.store
    auth = {"Authorization": "Bearer " + cfg.worker_token}
    assert c.post("/internal/asr/claim").status_code == 403
    id, h, _, _ = upload(c)
    c.post(f"/api/uploads/{id}/complete", headers=h)
    assert c.post("/internal/asr/claim", headers=auth).json()["job"] is None
    assert not process_one(s, analyzer=Analyzer())  # Cloud never executes ASR locally.
    sync_one(s, SimpleNamespace(ensure=lambda *a: None))
    first = c.post("/internal/asr/claim", headers=auth).json()["job"]
    assert first["id"] == id and first["url"].startswith("https://audio.example.com/")
    assert "audio_path" not in first and "upload_token" not in first
    assert c.post("/internal/asr/claim", headers=auth).json()["job"] is None
    assert (
        c.post(
            f"/internal/asr/{id}/heartbeat",
            headers=auth,
            json={"owner": first["owner"]},
        ).status_code
        == 200
    )
    with s.connect(True) as db:
        db.execute("UPDATE jobs SET lease_until=?", (time.time() - 1,))
    second = c.post("/internal/asr/claim", headers=auth).json()["job"]
    result = {"segments": [{"start": 0, "end": 1, "text": "测试录音"}]}
    for action in ("heartbeat", "complete", "fail"):
        body = {"owner": first["owner"], "result": result}
        assert (
            c.post(f"/internal/asr/{id}/{action}", headers=auth, json=body).status_code
            == 409
        )
    assert (
        c.post(
            f"/internal/asr/{id}/complete",
            headers=auth,
            json={"owner": second["owner"], "result": {"segments": []}},
        ).status_code
        == 422
    )
    assert (
        c.post(
            f"/internal/asr/{id}/complete",
            headers=auth,
            json={"owner": second["owner"], "result": result},
        ).status_code
        == 200
    )
    assert c.post("/internal/asr/claim", headers=auth).json()["job"] is None
    assert process_one(s, analyzer=Analyzer())
    assert s.get(id)["state"] == "complete"


def test_internal_routes_disabled_without_machine_token(tmp_path):
    c = TestClient(create_app(Settings(data_dir=tmp_path)))
    assert (
        c.post("/internal/asr/claim", headers={"Authorization": "Bearer "}).status_code
        == 403
    )
