"""Machine-authenticated ASR leases. No anonymous administration routes."""

import hmac
import math
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .cloud import delivery_url
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

router = APIRouter(prefix="/internal/asr")


def authorized(request: Request):
    expected = request.app.state.settings.worker_token
    header = request.headers.get("authorization", "")
    if (
        not expected
        or len(expected) < 32
        or not hmac.compare_digest(header.encode(), ("Bearer " + expected).encode())
    ):
        raise HTTPException(403, "任务访问凭证无效")
    return request.app.state.store


def backup_authorized(request: Request):
    expected = request.app.state.settings.backup_token
    header = request.headers.get("authorization", "")
    if len(expected) < 32 or not hmac.compare_digest(header.encode(), ("Bearer " + expected).encode()):
        raise HTTPException(403, "备份访问凭证无效")
    return request.app.state.store


@router.get("/backup")
def backup(store=Depends(backup_authorized)):
    import os
    import sqlite3
    import tempfile
    from pathlib import Path

    folder = store.settings.data_dir / "backups"
    folder.mkdir(mode=0o700, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="download-", suffix=".sqlite3", dir=folder)
    os.close(fd)
    path = Path(name)
    with store.connect() as source, sqlite3.connect(path) as dest:
        source.backup(dest)
    return FileResponse(
        path,
        filename="yanxu.sqlite3",
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


@router.get("/backup-bundle")
def backup_bundle(store=Depends(backup_authorized)):
    import uuid
    from .private_backup import create_bundle

    folder = store.settings.data_dir / "backups"
    folder.mkdir(mode=0o700, exist_ok=True)
    path = folder / ("download-" + str(uuid.uuid4()) + ".tar")
    try:
        create_bundle(store, path)
    except (OSError, ValueError):
        path.unlink(missing_ok=True)
        raise HTTPException(503, "私有备份尚未完成，请稍后重试")
    return FileResponse(
        path,
        filename="yanxu-private-backup.tar",
        media_type="application/x-tar",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


class Lease(BaseModel):
    owner: str = Field(min_length=1, max_length=80)


def current(store, id, owner):
    with store.connect() as db:
        row = db.execute(
            "SELECT * FROM jobs WHERE recording_id=? AND owner=? AND stage='asr' AND status='running'",
            (id, owner),
        ).fetchone()
    if not row:
        raise HTTPException(409, "任务已被回收或完成")
    return dict(row)


@router.post("/claim")
def claim(store=Depends(authorized)):
    if not store.settings.qiniu_delivery:
        raise HTTPException(503, "云端原音尚未启用")
    job = store.claim(stage="asr", cloud_ready=True)
    if not job:
        return {"job": None}
    row = store.get(job["recording_id"])
    return {
        "job": {
            "id": row["id"],
            "owner": job["owner"],
            "duration": row["duration"],
            "bytes": row["total_bytes"],
            "sha256": row["sha256"],
            "extension": row["extension"],
            "url": delivery_url(store, row["id"]),
            "leaseSeconds": store.settings.lease_seconds,
        }
    }


@router.post("/{id}/heartbeat")
def heartbeat(id: str, lease: Lease, store=Depends(authorized)):
    current(store, id, lease.owner)
    if not store.heartbeat(id, lease.owner):
        raise HTTPException(409, "任务已被回收")
    return {"ok": True}


class Transcript(Lease):
    result: dict


def validate_transcript(result, duration):
    if "noSpeech" in result and type(result["noSpeech"]) is not bool:
        raise ValueError("无语音标识无效")
    if result.get("noSpeech") is True:
        if result.get("text") != "" or result.get("segments") != []:
            raise ValueError("无语音结果包含矛盾内容")
        return {"noSpeech": True, "text": "", "segments": [], "engine": "Qwen3-ASR-1.7B"}
    segments = result.get("segments")
    if not isinstance(segments, list) or not 1 <= len(segments) <= 100000:
        raise ValueError("转写段落缺失或超过容量")
    clean = []
    last = -1
    for index, segment in enumerate(segments):
        start, end = float(segment["start"]), float(segment["end"])
        text = segment["text"]
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or not 0 <= start <= end <= duration + 2
            or start < last
        ):
            raise ValueError("转写时间无效")
        if not isinstance(text, str) or not text.strip() or len(text) > 20000:
            raise ValueError("转写文本无效")
        last = start
        clean.append(
            {
                "id": f"seg-{index + 1:05d}",
                "start": start,
                "end": end,
                "text": text,
                "speaker": None,
            }
        )
    text = "".join(s["text"] for s in clean)
    if len(text) > 4_000_000:
        raise ValueError("转写文本超过容量")
    return {
        "text": text,
        "segments": clean,
        "engine": "Qwen3-ASR-1.7B",
        "warning": "词级时间未经人工核对；未区分说话人",
    }


@router.post("/{id}/complete")
def complete(id: str, value: Transcript, store=Depends(authorized)):
    job = current(store, id, value.owner)
    try:
        result = validate_transcript(value.result, store.get(id)["duration"])
    except (ValueError, KeyError, TypeError, OverflowError):
        raise HTTPException(422, "转写内容或时间信息无效")
    if not store.finish(job, result):
        raise HTTPException(409, "任务已被回收")
    return {"ok": True}


class Failure(Lease):
    retryable: bool = True
    no_speech: bool = False


@router.post("/{id}/fail")
def fail(id: str, value: Failure, store=Depends(authorized)):
    job = current(store, id, value.owner)
    store.fail(
        job,
        "未检测到可转写的清晰语音" if value.no_speech else "转写暂未完成",
        value.retryable,
    )
    return {"ok": True}
