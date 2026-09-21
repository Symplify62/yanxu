import hashlib, io, json, time, wave
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.store import Store, Conflict, public_record
from yanxu.worker import process_one
from yanxu.deepseek import ProviderError, validate


def wav_bytes():
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x01\x00" * 16000)
    return b.getvalue()


@pytest.fixture
def env(tmp_path):
    settings = Settings(
        data_dir=tmp_path, chunk_size=8192, retry_seconds=0, lease_seconds=2
    )
    app = create_app(settings)
    return TestClient(app), app.state.store, settings


def upload(client, raw=None, client_id="recording-test-0001"):
    raw = raw or wav_bytes()
    body = {
        "client_id": client_id,
        "title": "真实录音测试",
        "total_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "extension": "wav",
    }
    r = client.post("/api/recordings", json=body)
    assert r.status_code == 200
    session = r.json()
    id = session["id"]
    headers = {"X-Upload-Token": session["uploadToken"]}
    for i, start in enumerate(range(0, len(raw), session["chunkSize"])):
        r = client.put(
            f"/api/uploads/{id}/parts/{i}",
            content=raw[start : start + session["chunkSize"]],
            headers=headers,
        )
        assert r.status_code == 200
    return id, headers, body, raw


def test_resumable_idempotent_and_public_audio(env):
    c, s, cfg = env
    id, headers, body, raw = upload(c)
    again = c.post("/api/recordings", json=body).json()
    assert again["id"] == id
    assert c.get(f"/api/uploads/{id}", headers=headers).json()["parts"]
    assert c.post(f"/api/uploads/{id}/complete", headers=headers).status_code == 200
    assert c.post(f"/api/uploads/{id}/complete", headers=headers).status_code == 200
    body = c.get("/api/recordings").json()
    assert body["total"] == 1
    assert (
        "upload_token" not in json.dumps(body)
        and "audio_path" not in json.dumps(body)
        and "client_id" not in json.dumps(body)
    )
    result = c.get(f"/api/recordings/{id}/audio", headers={"Range": "bytes=0-43"})
    assert result.status_code == 206 and result.content == raw[:44]
    assert c.get(f"/api/recordings/{id}/audio?download=true").content == raw
    assert (
        "attachment"
        in c.get(f"/api/recordings/{id}/audio?download=true").headers[
            "content-disposition"
        ]
    )
    assert (
        c.get(
            f"/api/recordings/{id}/audio", headers={"Range": "bytes=999999-"}
        ).status_code
        == 416
    )
    assert Store(cfg).get(id)["state"] == "queued"


def test_upload_protection_and_partial_seal(env):
    c, s, cfg = env
    id, h, body, raw = upload(c)
    assert (
        c.put(f"/api/uploads/{id}/parts/0", content=raw[: cfg.chunk_size]).status_code
        == 403
    )
    assert (
        c.put(
            f"/api/uploads/{id}/parts/0", content=b"x" * cfg.chunk_size, headers=h
        ).status_code
        == 409
    )
    assert (
        c.put(f"/api/uploads/{id}/parts/-1", content=b"x", headers=h).status_code == 422
    )
    assert (
        c.put(
            f"/api/uploads/{id}/parts/1", content=b"x" * (cfg.chunk_size + 1), headers=h
        ).status_code
        == 413
    )
    assert (
        c.post("/api/recordings", json={**body, "sha256": "0" * 64}).status_code == 409
    )
    session = c.post(
        "/api/recordings", json={**body, "client_id": "another-client-id-001"}
    ).json()
    assert (
        c.post(
            f"/api/uploads/{session['id']}/complete",
            headers={"X-Upload-Token": session["uploadToken"]},
        ).status_code
        == 409
    )
    assert c.get("/api/recordings").json()["total"] == 0


def test_corrupt_media_and_whole_digest(env):
    c, s, cfg = env
    id, h, b, raw = upload(c, b"bad audio file" * 400)
    assert c.post(f"/api/uploads/{id}/complete", headers=h).status_code == 422
    assert c.get(f"/api/recordings/{id}/audio").status_code == 404
    id, h, b, raw = upload(c, client_id="digest-test-00001")
    with s.connect(True) as db:
        db.execute("UPDATE recordings SET sha256=? WHERE id=?", ("0" * 64, id))
    assert c.post(f"/api/uploads/{id}/complete", headers=h).status_code == 409


class Analyzer:
    def analyze(self, *args):
        return {"summary": "有效摘要", "points": [], "decisions": [], "tasks": []}


def test_phase_retry_restart_and_stale_worker(env):
    c, s, cfg = env
    id, h, _, _ = upload(c)
    c.post(f"/api/uploads/{id}/complete", headers=h)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = list(pool.map(lambda _: s.claim(), range(2)))
    job = next(j for j in jobs if j)
    assert sum(j is not None for j in jobs) == 1
    with s.connect(True) as db:
        db.execute(
            "UPDATE jobs SET lease_until=? WHERE recording_id=?", (time.time() - 1, id)
        )
    replacement = Store(cfg).claim()
    assert replacement and replacement["owner"] != job["owner"]
    assert not s.finish(job, {"text": "stale", "segments": []})
    transcript = {
        "text": "原文",
        "segments": [{"id": "seg-00001", "start": 0, "end": 1, "text": "原文"}],
    }
    assert s.finish(replacement, transcript)

    class Fail:
        def analyze(self, *args):
            raise ProviderError("临时不可用")

    process_one(s, analyzer=Fail())
    assert json.loads(s.get(id)["transcript"]) == transcript
    process_one(Store(cfg), analyzer=Analyzer())
    assert s.get(id)["state"] == "complete"
    assert s.claim() is None


def test_permanent_failure_does_not_fake_completion(env):
    c, s, cfg = env
    id, h, _, _ = upload(c)
    c.post(f"/api/uploads/{id}/complete", headers=h)

    def fail(*args):
        raise ProviderError("没有清晰语音", False)

    process_one(s, asr=fail)
    assert s.get(id)["state"] == "transcript-error"
    assert s.get(id)["analysis"] is None


def test_analysis_contract_rejects_invented_evidence():
    value = {
        "summary": "摘要",
        "points": [],
        "decisions": [],
        "tasks": [
            {"text": "任务", "owner": None, "due": None, "evidence": ["unknown"]}
        ],
    }
    with pytest.raises(ValueError):
        validate(value, {"seg-1"})
    value["tasks"][0]["evidence"] = ["seg-1"]
    assert validate(value, {"seg-1"})["tasks"][0]["owner"] is None


def test_budget_and_invalid_provider_json_are_not_success(env, tmp_path):
    from yanxu.deepseek import DeepSeek

    c, s, cfg = env
    cfg.api_key = "test-not-a-real-key"
    cfg.daily_token_budget = 1
    with pytest.raises(ProviderError, match="用量"):
        DeepSeek(cfg, s).analyze(
            {"segments": [{"id": "seg-1", "text": "测试内容"}]},
            "test",
            tmp_path / "analysis",
        )
    with pytest.raises(ValueError):
        validate({"summary": "", "points": [], "decisions": [], "tasks": []}, {"seg-1"})


def test_media_extension_must_match(env):
    c, s, cfg = env
    raw = wav_bytes()
    body = {
        "client_id": "wrong-extension-001",
        "total_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "extension": "mp3",
    }
    u = c.post("/api/recordings", json=body).json()
    h = {"X-Upload-Token": u["uploadToken"]}
    for i, pos in enumerate(range(0, len(raw), cfg.chunk_size)):
        assert (
            c.put(
                f"/api/uploads/{u['id']}/parts/{i}",
                content=raw[pos : pos + cfg.chunk_size],
                headers=h,
            ).status_code
            == 200
        )
    assert c.post(f"/api/uploads/{u['id']}/complete", headers=h).status_code == 422


def test_global_search_filter_and_capacity_backpressure(env):
    c, s, cfg = env
    id, h, _, _ = upload(c)
    c.post(f"/api/uploads/{id}/complete", headers=h)
    assert c.get("/api/recordings?q=真实&filter=processing").json()["total"] == 1
    assert c.get("/api/recordings?filter=complete").json()["total"] == 0
    assert c.get("/api/recordings?filter=invalid").status_code == 422
    cfg.max_pending = 1
    raw = wav_bytes()
    r = c.post(
        "/api/recordings",
        json={
            "client_id": "over-capacity-0001",
            "total_bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "extension": "wav",
        },
    )
    assert r.status_code == 429 and r.headers["retry-after"] == "30"


def test_operator_retry_requires_failed_state(env):
    from yanxu.manage import retry_failed

    c, s, cfg = env
    id, h, _, _ = upload(c)
    c.post(f"/api/uploads/{id}/complete", headers=h)
    with pytest.raises(Conflict):
        retry_failed(s, id)
    job = s.claim()
    s.fail(job, "依赖未配置", False)
    assert retry_failed(s, id)["stage"] == "asr"
    assert s.get(id)["state"] == "queued" and s.claim()["attempts"] == 1
