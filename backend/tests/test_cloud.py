import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.store import Store
from yanxu.cloud import sync_one, QiniuMirror, CloudError
from test_pipeline import upload


def setup(tmp_path):
    cfg = Settings(
        data_dir=tmp_path,
        storage="qiniu",
        qiniu_access_key="test-ak",
        qiniu_secret_key="test-sk",
        qiniu_bucket="bucket",
        qiniu_domain="https://audio.example.com",
        qiniu_delivery=True,
    )
    app = create_app(cfg)
    c = TestClient(app)
    id, h, _, raw = upload(c)
    assert c.post(f"/api/uploads/{id}/complete", headers=h).status_code == 200
    return c, app.state.store, id, h, raw


def test_cloud_restart_retry_and_public_delivery(tmp_path):
    c, store, id, h, raw = setup(tmp_path)
    assert c.get(f"/api/recordings/{id}/audio").content == raw

    class Offline:
        def ensure(self, *args):
            raise RuntimeError("secret-key-provider-request-must-not-leak")

    sync_one(store, Offline())
    with store.connect(True) as db:
        item = dict(db.execute("SELECT * FROM cloud_objects").fetchone())
        assert item["status"] == "retry" and "secret" not in item["error"]
        db.execute("UPDATE cloud_objects SET next_at=0")
    # Retry sealing does not reset the outbox or duplicate cloud objects.
    c.post(f"/api/uploads/{id}/complete", headers=h)
    assert store.get(id)["state"] == "queued"
    assert Path(store.get(id)["audio_path"]).read_bytes() == raw
    assert sync_one(Store(store.settings), SimpleNamespace(ensure=lambda *a: None))
    assert not sync_one(store, Offline())
    url = c.get(f"/api/recordings/{id}/audio", follow_redirects=False)
    assert url.status_code == 307 and url.headers["location"].startswith(
        "https://audio.example.com/recordings/"
    )
    download = c.get(
        f"/api/recordings/{id}/audio?download=true", follow_redirects=False
    )
    assert "attname=" + id + ".wav" in download.headers["location"]
    assert "test-sk" not in json.dumps(c.get(f"/api/recordings/{id}").json())
    store.settings.qiniu_delivery = False
    assert (
        c.get(f"/api/recordings/{id}/audio", headers={"Range": "bytes=0-43"}).content
        == raw[:44]
    )
    assert c.get(f"/api/recordings/{id}/audio?download=true").content == raw


def test_cloud_provider_integrity_and_idempotency(tmp_path):
    from qiniu import etag

    _, store, id, _, raw = setup(tmp_path)
    row = store.get(id)
    with store.connect() as db:
        item = dict(db.execute("SELECT * FROM cloud_objects").fetchone())
    mirror = QiniuMirror(store.settings)
    # Existing valid object is verified, never uploaded again.
    mirror.manager = SimpleNamespace(
        stat=lambda *a: (
            {"hash": etag(row["audio_path"]), "fsize": len(raw)},
            SimpleNamespace(status_code=200),
        )
    )
    mirror.uploader = SimpleNamespace(
        upload=lambda *a, **kw: pytest.fail("duplicate upload")
    )
    mirror.ensure(row, item)
    mirror.manager = SimpleNamespace(
        stat=lambda *a: (
            {"hash": "wrong", "fsize": len(raw)},
            SimpleNamespace(status_code=200),
        )
    )
    with pytest.raises(CloudError, match="不一致"):
        mirror.ensure(row, item)
    Path(row["audio_path"]).write_bytes(b"corrupt")
    with pytest.raises(CloudError, match="本地"):
        mirror.ensure(row, item)


def test_cloud_retry_exhaustion_and_old_records_not_published(tmp_path):
    c, store, id, _, _ = setup(tmp_path)
    with store.connect(True) as db:
        db.execute("UPDATE cloud_objects SET attempts=7")

    def fail(*args):
        raise CloudError("连接暂未完成")

    sync_one(store, SimpleNamespace(ensure=fail))
    with store.connect() as db:
        assert db.execute("SELECT status FROM cloud_objects").fetchone()[0] == "failed"
    assert c.get(f"/api/recordings/{id}/audio").status_code == 200
    local = Settings(data_dir=tmp_path / "local")
    app = create_app(local)
    lc = TestClient(app)
    old, h, _, _ = upload(lc)
    lc.post(f"/api/uploads/{old}/complete", headers=h)
    local.storage = "qiniu"
    with Store(local).connect() as db:
        assert db.execute("SELECT count(*) FROM cloud_objects").fetchone()[0] == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://audio.example.com",
        "https://user:pass@audio.example.com",
        "https://audio.example.com/path",
        "https://audio.example.com?token=x",
    ],
)
def test_cloud_requires_https_origin(url):
    with pytest.raises(ValueError):
        Settings(qiniu_domain=url)


def test_cloud_rejects_incomplete_configuration():
    with pytest.raises(ValueError):
        Settings(storage="qiniu")
    with pytest.raises(ValueError):
        Settings(qiniu_delivery=True)
