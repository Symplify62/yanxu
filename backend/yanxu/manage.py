"""Local operator actions, intentionally not exposed as public HTTP routes."""

import argparse, json, time
from .config import Settings
from .store import Store, Conflict


def retry_failed(store, id):
    with store.connect(True) as db:
        job = db.execute("SELECT * FROM jobs WHERE recording_id=?", (id,)).fetchone()
        if not job or job["status"] != "failed":
            raise Conflict("只能恢复已失败任务")
        db.execute(
            "UPDATE jobs SET status='pending',attempts=0,next_at=0,owner=NULL,lease_until=NULL,error=NULL WHERE recording_id=?",
            (id,),
        )
        db.execute(
            "UPDATE recordings SET state=?,error=NULL WHERE id=?",
            ("queued" if job["stage"] == "asr" else "analyzing", id),
        )
    return {"id": id, "stage": job["stage"], "status": "pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["retry"])
    parser.add_argument("id")
    args = parser.parse_args()
    print(json.dumps(retry_failed(Store(Settings.load()), args.id)))
