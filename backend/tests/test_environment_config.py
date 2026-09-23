import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from yanxu.api import create_app
from yanxu.config import Settings


def test_versioned_profiles_keep_public_identity_and_storage_separate(monkeypatch, tmp_path):
    details = []
    for name in ("testing", "production"):
        monkeypatch.setenv("YANXU_ENVIRONMENT", name)
        monkeypatch.setenv("YANXU_DATA_DIR", str(tmp_path / name))
        monkeypatch.setenv("QINIU_ACCESS_KEY", "isolated-fixture-ak")
        monkeypatch.setenv("QINIU_SECRET_KEY", "isolated-fixture-sk")
        cfg = Settings.load()
        details.append((cfg.public_origin, cfg.android_package_name, cfg.qiniu_bucket, cfg.data_dir))
    assert details[0] == (
        "https://test-yanxu.qjl666.xyz",
        "cn.jiajian.yanxu.testing",
        "yanxu-test-recordings",
        tmp_path / "testing",
    )
    assert details[1] == (
        "https://yanxu.qjl666.xyz",
        "cn.jiajian.yanxu",
        "yanxu-recordings",
        tmp_path / "production",
    )


def test_test_profile_rejects_production_bucket_and_origin(monkeypatch, tmp_path):
    monkeypatch.setenv("YANXU_ENVIRONMENT", "testing")
    monkeypatch.setenv("YANXU_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QINIU_ACCESS_KEY", "isolated-fixture-ak")
    monkeypatch.setenv("QINIU_SECRET_KEY", "isolated-fixture-sk")
    monkeypatch.setenv("QINIU_BUCKET", "yanxu-recordings")
    with pytest.raises(ValueError, match="QINIU_BUCKET"):
        Settings.load()
    monkeypatch.delenv("QINIU_BUCKET")
    monkeypatch.setenv("YANXU_PUBLIC_ORIGIN", "https://yanxu.qjl666.xyz")
    with pytest.raises(ValueError, match="YANXU_PUBLIC_ORIGIN"):
        Settings.load()
    monkeypatch.delenv("YANXU_PUBLIC_ORIGIN")
    monkeypatch.setenv("YANXU_REMOTE_API", "https://yanxu.qjl666.xyz")
    with pytest.raises(ValueError, match="YANXU_REMOTE_API"):
        Settings.load()
    monkeypatch.delenv("YANXU_REMOTE_API")
    monkeypatch.setenv("YANXU_DATA_DIR", "/var/lib/yanxu/data")
    with pytest.raises(ValueError, match="生产目录"):
        Settings.load()


def test_test_update_manifest_cannot_announce_production_package(tmp_path):
    cfg = Settings(
        data_dir=tmp_path / "data",
        environment="testing",
        public_origin="https://test-yanxu.qjl666.xyz",
        android_package_name="cn.jiajian.yanxu.testing",
    )
    client = TestClient(create_app(cfg))
    folder = tmp_path / "artifacts" / "releases"
    folder.mkdir(parents=True)
    audio = b"synthetic-apk-fixture"
    sha = hashlib.sha256(audio).hexdigest()
    filename = f"yanxu-16-{sha[:12]}.apk"
    (folder / filename).write_bytes(audio)
    manifest = dict(
        available=True,
        versionCode=16,
        versionName="0.3.6-test",
        minSdk=26,
        packageName="cn.jiajian.yanxu.testing",
        url=f"https://test-yanxu.qjl666.xyz/app/releases/{filename}",
        size=len(audio),
        sha256=sha,
    )
    path = folder.parent / "android-update.json"
    path.write_text(json.dumps(manifest))
    assert client.get("/app/update.json").json()["packageName"] == manifest["packageName"]
    for changed in (
        {"packageName": "cn.jiajian.yanxu"},
        {"url": f"https://yanxu.qjl666.xyz/app/releases/{filename}"},
    ):
        path.write_text(json.dumps({**manifest, **changed}))
        assert client.get("/app/update.json").status_code == 503
