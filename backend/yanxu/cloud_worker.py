"""Cloud sync daemon and local-only operator actions."""

import argparse
import fcntl
import json
import time
from .config import Settings
from .store import Store
from .cloud import QiniuMirror, enqueue, sync_one


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["run", "once", "status", "retry", "enqueue"],
        default="run",
        nargs="?",
    )
    parser.add_argument("id", nargs="?")
    args = parser.parse_args()
    cfg = Settings.load()
    store = Store(cfg)
    if args.action == "status":
        with store.connect() as db:
            rows = db.execute(
                "SELECT recording_id,status,attempts,error,verified_at FROM cloud_objects"
            ).fetchall()
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False))
        return
    if cfg.storage != "qiniu":
        raise SystemExit("尚未启用七牛存储")
    with (cfg.data_dir / "cloud-worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("已有云同步进程运行")
        if args.action in ("retry", "enqueue"):
            if not args.id:
                parser.error("需要指定录音 ID")
            with store.connect(True) as db:
                if args.action == "enqueue":
                    enqueue(db, cfg, args.id)
                else:
                    result = db.execute(
                        "UPDATE cloud_objects SET status='pending',attempts=0,next_at=0,error=NULL WHERE recording_id=? AND status IN ('retry','failed')",
                        (args.id,),
                    )
                    if not result.rowcount:
                        raise SystemExit("没有可恢复的云任务")
            return
        mirror = QiniuMirror(cfg)
        while True:
            worked = sync_one(store, mirror)
            if args.action == "once":
                break
            if not worked:
                time.sleep(2)


if __name__ == "__main__":
    main()
