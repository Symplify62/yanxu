"""Daily SQLite snapshot and verified cloud-backed cache pruning (cloud host only)."""

import datetime
import json
import sqlite3
import time
from pathlib import Path
from .config import Settings
from .store import Store
from .cloud import QiniuMirror
from .private_backup import create_bundle, validate_bundle


def run(cfg, days=7):
    store = Store(cfg)
    backups = cfg.data_dir / "backups"
    backups.mkdir(mode=0o700, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    private_backup = create_bundle(store, backups / (stamp + ".tar"))
    private_evidence = validate_bundle(private_backup)
    backup = backups / (stamp + ".sqlite3")
    with store.connect() as source, sqlite3.connect(backup) as dest:
        source.backup(dest)
    backup.chmod(0o600)
    deleted = 0
    if cfg.worker_stage == "analysis" and cfg.qiniu_delivery:
        mirror = QiniuMirror(cfg)
        with store.connect() as db:
            rows = db.execute(
                "SELECT r.id FROM recordings r JOIN cloud_objects c ON c.recording_id=r.id WHERE c.status='ready' AND c.bucket=? AND c.verified_at<?",
                (cfg.qiniu_bucket, time.time() - days * 86400),
            ).fetchall()
        for row in rows:
            record = store.get(row["id"])
            path = Path(record["audio_path"])
            if not path.is_file() or not path.resolve().is_relative_to(
                (cfg.data_dir / "assets").resolve()
            ):
                continue
            with store.connect() as db:
                item = dict(
                    db.execute(
                        "SELECT * FROM cloud_objects WHERE recording_id=?", (row["id"],)
                    ).fetchone()
                )
            # Recheck actual remote hash and size before removing any local cache.
            mirror.ensure(record, item)
            # Voice workers consume server audio after ASR. A long Mac outage must
            # not let the seven-day cache policy remove that pending input.
            with store.connect(True) as db:
                current = db.execute("SELECT * FROM recordings WHERE id=?", (row["id"],)).fetchone()
                voice_pending = db.execute("SELECT 1 FROM voice_jobs WHERE kind='attribution' AND target_id=? AND status IN ('pending','retry','running')", (row["id"],)).fetchone()
                if current["owner_account_id"] and (current["state"] not in ('complete', 'no-speech') or current['attribution_state'] == 'waiting' or voice_pending):
                    continue
                path.unlink(missing_ok=True)
                deleted += 1
    # Keep 30 daily local snapshots. Backup must also be copied off-host by operator.
    for old in sorted(backups.glob("*.sqlite3"))[:-30]:
        old.unlink()
    private_snapshots = sorted(p for p in backups.glob("*.tar") if not p.name.startswith("download-"))
    for old in private_snapshots[:-30]:
        old.unlink()
    return {"backup": backup.name, "privateBackup": private_backup.name,
            "privateSamples": private_evidence["samples"], "prunedAudioFiles": deleted}


if __name__ == "__main__":
    print(json.dumps(run(Settings.load())))
