"""Durable cloud mirror, independent of ASR/analysis. Originals stay on disk."""

import hashlib
import time
from pathlib import Path
from urllib.parse import quote


class CloudError(Exception):
    pass


def enqueue(db, cfg, id):
    row = db.execute("SELECT * FROM recordings WHERE id=?", (id,)).fetchone()
    if not row or not row["audio_path"]:
        raise CloudError("录音尚未封存")
    key = f"recordings/{id}/{row['sha256']}.{row['extension']}"
    db.execute(
        "INSERT OR IGNORE INTO cloud_objects(recording_id,bucket,object_key) VALUES(?,?,?)",
        (id, cfg.qiniu_bucket, key),
    )


class QiniuMirror:
    def __init__(self, cfg):
        from qiniu import Auth, BucketManager, UploadProgressRecorder
        from qiniu.services.storage.uploaders import ResumeUploaderV2

        self.cfg = cfg
        self.auth = Auth(cfg.qiniu_access_key, cfg.qiniu_secret_key)
        self.manager = BucketManager(self.auth, preferred_scheme="https")
        cache = cfg.data_dir / "qiniu-resume"
        cache.mkdir(exist_ok=True)
        self.uploader = ResumeUploaderV2(
            cfg.qiniu_bucket,
            auth=self.auth,
            preferred_scheme="https",
            upload_progress_recorder=UploadProgressRecorder(str(cache)),
        )

    def ensure(self, row, item):
        from qiniu import etag

        path = Path(row["audio_path"])
        with path.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        if path.stat().st_size != row["total_bytes"] or digest != row["sha256"]:
            raise CloudError("本地原音校验失败")
        expected = etag(str(path))
        key = item["object_key"]
        result, info = self.manager.stat(item["bucket"], key)
        if info.status_code == 612:
            # insertOnly avoids replacing an existing object after a lost response.
            token = self.auth.upload_token(
                item["bucket"],
                key,
                3600,
                {
                    "insertOnly": 1,
                    "fsizeLimit": row["total_bytes"],
                },
            )
            result, info = self.uploader.upload(
                key,
                file_path=str(path),
                up_token=token,
                mime_type=row["media_type"],
            )
            if info.status_code not in (200, 614):
                raise CloudError("七牛上传暂未完成")
            result, info = self.manager.stat(item["bucket"], key)
        if info.status_code != 200 or not result:
            raise CloudError("七牛文件校验暂未完成")
        if result.get("hash") != expected or result.get("fsize") != row["total_bytes"]:
            raise CloudError("七牛文件校验不一致")


def sync_one(store, mirror):
    """Called under the cloud-worker process lock; pending rows survive termination."""
    with store.connect() as db:
        row = db.execute(
            "SELECT * FROM cloud_objects WHERE status IN ('pending','retry') AND next_at<=? ORDER BY next_at,recording_id LIMIT 1",
            (time.time(),),
        ).fetchone()
    if not row:
        return False
    item = dict(row)
    try:
        if item["bucket"] != store.settings.qiniu_bucket:
            raise CloudError("任务空间与当前配置不一致")
        mirror.ensure(store.get(item["recording_id"]), item)
    except Exception as exc:
        # SDK exceptions may contain request headers/tokens: never persist str(exc).
        error = str(exc) if isinstance(exc, CloudError) else "七牛连接暂未完成"
        attempt = item["attempts"] + 1
        with store.connect(True) as db:
            db.execute(
                "UPDATE cloud_objects SET status=?,attempts=?,next_at=?,error=? WHERE recording_id=?",
                (
                    "failed" if attempt >= 8 else "retry",
                    attempt,
                    time.time() + min(3600, 10 * 2 ** min(attempt - 1, 9)),
                    error,
                    item["recording_id"],
                ),
            )
    else:
        with store.connect(True) as db:
            db.execute(
                "UPDATE cloud_objects SET status='ready',error=NULL,verified_at=? WHERE recording_id=?",
                (time.time(), item["recording_id"]),
            )
    return True


def delivery_url(store, id, download=False):
    cfg = store.settings
    if not cfg.qiniu_delivery:
        return None
    with store.connect() as db:
        obj = db.execute(
            "SELECT * FROM cloud_objects WHERE recording_id=?", (id,)
        ).fetchone()
    if not obj or obj["status"] != "ready" or obj["bucket"] != cfg.qiniu_bucket:
        return None
    url = cfg.qiniu_domain + "/" + quote(obj["object_key"], safe="/")
    if download:
        url += "?attname=" + quote(id + "." + obj["object_key"].rsplit(".", 1)[-1])
    return url
