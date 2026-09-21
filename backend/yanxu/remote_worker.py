"""Mac ASR client: outbound HTTPS only; no public port on the Mac."""

import fcntl
import hashlib
import json
import logging
import os
import threading
import time
from urllib.parse import urlsplit
import httpx
from .config import Settings
from .worker import transcribe
from .deepseek import ProviderError

logger = logging.getLogger("yanxu.remote_worker")


def backup_database(cfg, client):
    import datetime
    import sqlite3

    folder = cfg.data_dir / "cloud-backups"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    files = sorted(folder.glob("*.sqlite3"))
    if files and time.time() - files[-1].stat().st_mtime < 86400:
        return
    temp = folder / "receiving.tmp"
    size = 0
    with client.stream("GET", "/internal/asr/backup") as response:
        response.raise_for_status()
        with temp.open("wb") as out:
            temp.chmod(0o600)
            for chunk in response.iter_bytes(1024 * 1024):
                size += len(chunk)
                if size > 512 * 1024**2:
                    raise ValueError("Database backup too large")
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
    with sqlite3.connect(f"file:{temp}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Invalid database backup")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.replace(temp, folder / (stamp + ".sqlite3"))
    for old in files[:-29]:
        old.unlink()
    logger.info("Cloud database backup saved on Mac")


def download(client, cfg, job):
    url = urlsplit(job["url"])
    expected = urlsplit(cfg.qiniu_domain)
    if url.scheme != "https" or url.netloc != expected.netloc:
        raise ValueError("Unexpected audio origin")
    folder = cfg.data_dir / "remote-audio"
    folder.mkdir(parents=True, exist_ok=True)
    # IDs and extensions come from the server, but never allow path traversal.
    import uuid

    id = str(uuid.UUID(job["id"]))
    if job["extension"] not in ("wav", "m4a", "mp3", "webm"):
        raise ValueError("Invalid audio format")
    target = folder / (id + "." + job["extension"])
    if target.is_file():
        with target.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() == job["sha256"]:
                return target
    temp = target.with_suffix(".part")
    digest = hashlib.sha256()
    count = 0
    # Separate unauthenticated client: worker bearer never goes to object storage.
    with httpx.stream("GET", job["url"], timeout=120) as response:
        response.raise_for_status()
        with temp.open("wb") as out:
            for chunk in response.iter_bytes(1024 * 1024):
                count += len(chunk)
                if count > job["bytes"] or count > cfg.max_bytes:
                    raise ValueError("Audio too large")
                digest.update(chunk)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
    if count != job["bytes"] or digest.hexdigest() != job["sha256"]:
        temp.unlink(missing_ok=True)
        raise ValueError("Audio checksum mismatch")
    os.replace(temp, target)
    return target


def process_remote(cfg, client, asr=transcribe):
    response = client.post("/internal/asr/claim")
    response.raise_for_status()
    job = response.json()["job"]
    if not job:
        return False
    prefix = "/internal/asr/" + job["id"]
    stop = threading.Event()
    lost = threading.Event()

    def heartbeat():
        while not stop.wait(max(1, job["leaseSeconds"] / 3)):
            try:
                r = client.post(prefix + "/heartbeat", json={"owner": job["owner"]})
                if r.status_code in (403, 409):
                    lost.set()
                    return
            except httpx.HTTPError:
                pass

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    cache = cfg.data_dir / "remote-results" / (job["id"] + ".json")
    try:
        path = download(client, cfg, job)
        if cache.is_file():
            saved = json.loads(cache.read_text())
        else:
            saved = {}
        if saved.get("sha256") == job["sha256"]:
            result = saved["result"]
        else:
            result = asr(
                cfg,
                {"id": job["id"], "audio_path": str(path), "duration": job["duration"]},
            )
            cache.parent.mkdir(exist_ok=True)
            temp = cache.with_suffix(".tmp")
            temp.write_text(
                json.dumps(
                    {"sha256": job["sha256"], "result": result}, ensure_ascii=False
                )
            )
            os.replace(temp, cache)
        if not lost.is_set():
            r = client.post(
                prefix + "/complete", json={"owner": job["owner"], "result": result}
            )
            r.raise_for_status()
            logger.info("transcription submitted %s", job["id"])
    except ProviderError as exc:
        if not lost.is_set():
            client.post(
                prefix + "/fail",
                json={
                    "owner": job["owner"],
                    "retryable": exc.retryable,
                    "no_speech": False,
                },
            )
        logger.warning("ASR incomplete %s", job["id"])
    except Exception:
        # Transient connectivity errors leave lease for reclamation, retaining result cache.
        logger.warning("Remote task interrupted %s; retry after lease", job["id"])
    finally:
        stop.set()
        thread.join(timeout=35)
    return True


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    cfg = Settings.load()
    if not cfg.remote_api or len(cfg.worker_token) < 32 or not cfg.qiniu_domain:
        raise SystemExit("远程API、任务令牌或录音域名尚未配置")
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    with (cfg.data_dir / "remote-worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("已有远程转写进程运行")
        with httpx.Client(
            base_url=cfg.remote_api,
            headers={"Authorization": "Bearer " + cfg.worker_token},
            timeout=30,
        ) as client:
            logger.info("Remote ASR worker ready")
            while True:
                try:
                    try:
                        backup_database(cfg, client)
                    except (httpx.HTTPError, OSError, ValueError):
                        logger.warning("Database backup pending; ASR polling continues")
                    if not process_remote(cfg, client):
                        time.sleep(5)
                except httpx.HTTPError:
                    logger.warning("Cloud API unavailable; waiting")
                    time.sleep(15)


if __name__ == "__main__":
    main()
