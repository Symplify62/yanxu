"""One small synthetic WAV -> real Kodo -> optional HTTPS read/Range/download check.

Uses an isolated local database, never enumerates or publishes existing recordings.
"""

import hashlib
import io
import json
import wave
from dataclasses import replace
import httpx
from fastapi.testclient import TestClient
from .api import create_app
from .config import Settings
from .cloud import QiniuMirror, sync_one, delivery_url


def main():
    cfg = Settings.load()
    if cfg.storage != "qiniu":
        raise SystemExit("需要先配置并启用七牛存储")
    cfg = replace(cfg, data_dir=cfg.data_dir.parent / "cloud-smoke")
    app = create_app(cfg)
    client = TestClient(app)
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x01\x00" * 16000)
    data = stream.getvalue()
    digest = hashlib.sha256(data).hexdigest()
    # Stable source identity makes repeated probes safe and idempotent.
    session = client.post(
        "/api/recordings",
        json={
            "client_id": "qiniu-synthetic-check-v1",
            "title": "云存储合成测试",
            "total_bytes": len(data),
            "sha256": digest,
            "extension": "wav",
        },
    ).json()
    id = session["id"]
    headers = {"X-Upload-Token": session["uploadToken"]}
    assert (
        client.put(
            f"/api/uploads/{id}/parts/0", content=data, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(f"/api/uploads/{id}/complete", headers=headers).status_code == 200
    )
    mirror = QiniuMirror(cfg)
    store = app.state.store
    with store.connect(True) as db:
        db.execute(
            "UPDATE cloud_objects SET status='pending',attempts=0,next_at=0 WHERE recording_id=?",
            (id,),
        )
    sync_one(store, mirror)
    with store.connect() as db:
        obj = dict(
            db.execute(
                "SELECT * FROM cloud_objects WHERE recording_id=?", (id,)
            ).fetchone()
        )
    report = {
        "id": id,
        "bytes": len(data),
        "sha256": digest,
        "cloudStatus": obj["status"],
        "error": obj["error"],
    }
    if obj["status"] != "ready":
        print(json.dumps(report, ensure_ascii=False))
        raise SystemExit(1)
    if cfg.qiniu_delivery:
        with httpx.Client(timeout=30) as http:
            url = delivery_url(store, id)
            body = http.get(url)
            body.raise_for_status()
            assert hashlib.sha256(body.content).hexdigest() == digest
            head = http.head(url)
            assert head.status_code == 200
            part = http.get(url, headers={"Range": "bytes=0-43"})
            assert part.status_code == 206 and part.content == data[:44]
            download = http.get(delivery_url(store, id, True))
            assert download.status_code == 200 and download.content == data
            assert "attachment" in download.headers.get("content-disposition", "")
            report.update(https=True, range206=True, download=True, url=url)
    path = cfg.data_dir / "verification.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
