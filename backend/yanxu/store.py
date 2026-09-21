import json, sqlite3, time, uuid, secrets
from contextlib import contextmanager
from .config import Settings


class Conflict(Exception):
    pass


class Missing(Exception):
    pass


class Busy(Conflict):
    pass


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS recordings(
              id TEXT PRIMARY KEY, client_id TEXT UNIQUE NOT NULL, upload_token TEXT NOT NULL,
              title TEXT NOT NULL, total_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, extension TEXT NOT NULL,
              created_at REAL NOT NULL, duration REAL DEFAULT 0, state TEXT NOT NULL DEFAULT 'uploading',
              audio_path TEXT, media_type TEXT, transcript TEXT, analysis TEXT, error TEXT,
              interrupted INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS parts(recording_id TEXT NOT NULL, part_no INTEGER NOT NULL,
              size INTEGER NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(recording_id, part_no));
            CREATE TABLE IF NOT EXISTS jobs(recording_id TEXT PRIMARY KEY, stage TEXT NOT NULL DEFAULT 'asr',
              status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
              next_at REAL NOT NULL DEFAULT 0, lease_until REAL, owner TEXT, error TEXT);
            CREATE INDEX IF NOT EXISTS jobs_ready ON jobs(status,next_at,lease_until);
            CREATE TABLE IF NOT EXISTS usage(id INTEGER PRIMARY KEY, recording_id TEXT, created_at REAL, tokens INTEGER);
            CREATE TABLE IF NOT EXISTS cloud_objects(
              recording_id TEXT PRIMARY KEY, bucket TEXT NOT NULL, object_key TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
              next_at REAL NOT NULL DEFAULT 0, error TEXT, verified_at REAL);
            PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self, write=False):
        db = sqlite3.connect(self.settings.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA synchronous=FULL")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM recordings WHERE id=?", (id,)).fetchone()
        if not row:
            raise Missing()
        return dict(row)

    def create(self, value):
        with self.connect(True) as db:
            row = db.execute(
                "SELECT * FROM recordings WHERE client_id=?", (value["client_id"],)
            ).fetchone()
            if row:
                if (
                    row["sha256"] != value["sha256"]
                    or row["total_bytes"] != value["total_bytes"]
                ):
                    raise Conflict("同一录音编号对应的文件已改变")
                return dict(row)
            count = db.execute(
                "SELECT count(*) FROM recordings WHERE state!='complete'"
            ).fetchone()[0]
            if count >= self.settings.max_pending:
                raise Busy("当前待处理任务较多，请稍后重试")
            if self.settings.min_free_bytes:
                import shutil

                reserved = db.execute(
                    "SELECT COALESCE(sum(total_bytes),0) FROM recordings WHERE state='uploading'"
                ).fetchone()[0]
                free = shutil.disk_usage(self.settings.data_dir).free
                if free < self.settings.min_free_bytes + 2 * (
                    reserved + value["total_bytes"]
                ):
                    raise Busy("存储空间不足，请稍后重试；录音请保留在设备上")
            id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO recordings(id,client_id,upload_token,title,total_bytes,sha256,extension,created_at,interrupted) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    id,
                    value["client_id"],
                    secrets.token_urlsafe(32),
                    value["title"],
                    value["total_bytes"],
                    value["sha256"],
                    value["extension"],
                    time.time(),
                    int(value.get("interrupted", False)),
                ),
            )
            row = db.execute("SELECT * FROM recordings WHERE id=?", (id,)).fetchone()
            return dict(row)

    def parts(self, id):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT part_no,size,sha256 FROM parts WHERE recording_id=? ORDER BY part_no",
                    (id,),
                )
            ]

    def add_part(self, id, no, size, digest):
        with self.connect(True) as db:
            old = db.execute(
                "SELECT * FROM parts WHERE recording_id=? AND part_no=?", (id, no)
            ).fetchone()
            if old and (old["sha256"] != digest or old["size"] != size):
                raise Conflict("分片内容冲突")
            db.execute(
                "INSERT OR IGNORE INTO parts VALUES(?,?,?,?)", (id, no, size, digest)
            )

    def seal(self, id, path, media_type, duration):
        with self.connect(True) as db:
            db.execute(
                "UPDATE recordings SET audio_path=?,media_type=?,duration=?,state='queued',error=NULL WHERE id=? AND state='uploading'",
                (str(path), media_type, duration, id),
            )
            db.execute("INSERT OR IGNORE INTO jobs(recording_id) VALUES(?)", (id,))
            if self.settings.storage == "qiniu":
                from .cloud import enqueue

                enqueue(db, self.settings, id)

    def claim(self, stage=None, cloud_ready=False):
        now = time.time()
        owner = str(uuid.uuid4())
        with self.connect(True) as db:
            query = "SELECT * FROM jobs WHERE ((status IN ('pending','retry') AND next_at<=?) OR (status='running' AND lease_until<?))"
            params = [now, now]
            if stage:
                query += " AND stage=?"
                params.append(stage)
            if cloud_ready:
                query += " AND EXISTS (SELECT 1 FROM cloud_objects c WHERE c.recording_id=jobs.recording_id AND c.status='ready' AND c.bucket=?)"
                params.append(self.settings.qiniu_bucket)
            job = db.execute(query + " ORDER BY next_at LIMIT 1", params).fetchone()
            if not job:
                return None
            db.execute(
                "UPDATE jobs SET status='running',attempts=attempts+1,owner=?,lease_until=? WHERE recording_id=?",
                (owner, now + self.settings.lease_seconds, job["recording_id"]),
            )
            db.execute(
                "UPDATE recordings SET state=? WHERE id=?",
                (
                    "transcribing" if job["stage"] == "asr" else "analyzing",
                    job["recording_id"],
                ),
            )
            return dict(
                db.execute(
                    "SELECT * FROM jobs WHERE recording_id=?", (job["recording_id"],)
                ).fetchone()
            )

    def heartbeat(self, id, owner):
        with self.connect(True) as db:
            result = db.execute(
                "UPDATE jobs SET lease_until=? WHERE recording_id=? AND owner=? AND status='running'",
                (time.time() + self.settings.lease_seconds, id, owner),
            )
            return bool(result.rowcount)

    def finish(self, job, result):
        with self.connect(True) as db:
            live = db.execute(
                "SELECT * FROM jobs WHERE recording_id=? AND owner=? AND status='running'",
                (job["recording_id"], job["owner"]),
            ).fetchone()
            if not live:
                return False
            column = "transcript" if job["stage"] == "asr" else "analysis"
            db.execute(
                f"UPDATE recordings SET {column}=?,state=?,error=NULL WHERE id=?",
                (
                    json.dumps(result, ensure_ascii=False),
                    "analyzing" if job["stage"] == "asr" else "complete",
                    job["recording_id"],
                ),
            )
            if job["stage"] == "asr":
                db.execute(
                    "UPDATE jobs SET stage='analysis',status='pending',attempts=0,next_at=0,owner=NULL,lease_until=NULL,error=NULL WHERE recording_id=?",
                    (job["recording_id"],),
                )
            else:
                db.execute(
                    "UPDATE jobs SET status='complete',owner=NULL,lease_until=NULL,error=NULL WHERE recording_id=?",
                    (job["recording_id"],),
                )
            return True

    def fail(self, job, error, retryable=True):
        with self.connect(True) as db:
            live = db.execute(
                "SELECT * FROM jobs WHERE recording_id=? AND owner=? AND status='running'",
                (job["recording_id"], job["owner"]),
            ).fetchone()
            if not live:
                return
            retry = retryable and live["attempts"] < self.settings.max_attempts
            db.execute(
                "UPDATE jobs SET status=?,next_at=?,error=?,owner=NULL,lease_until=NULL WHERE recording_id=?",
                (
                    "retry" if retry else "failed",
                    time.time()
                    + self.settings.retry_seconds * 2 ** (live["attempts"] - 1),
                    error,
                    job["recording_id"],
                ),
            )
            state = (
                ("transcribing" if job["stage"] == "asr" else "analyzing")
                if retry
                else ("transcript-error" if job["stage"] == "asr" else "analysis-error")
            )
            db.execute(
                "UPDATE recordings SET state=?,error=? WHERE id=?",
                (state, error, job["recording_id"]),
            )

    def list(self, q="", limit=30, offset=0, state_filter="all"):
        condition = (
            " AND state='complete'"
            if state_filter == "complete"
            else " AND state!='complete'"
            if state_filter == "processing"
            else ""
        )
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM recordings WHERE audio_path IS NOT NULL AND title LIKE ?"
                + condition
                + " ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",
                ("%" + q + "%", limit, offset),
            ).fetchall()
            count = db.execute(
                "SELECT count(*) FROM recordings WHERE audio_path IS NOT NULL AND title LIKE ?"
                + condition,
                ("%" + q + "%",),
            ).fetchone()[0]
        return [dict(r) for r in rows], count

    def used_today(self):
        with self.connect() as db:
            return db.execute(
                "SELECT COALESCE(sum(tokens),0) FROM usage WHERE created_at>=?",
                (time.time() // 86400 * 86400,),
            ).fetchone()[0]

    def usage(self, id, tokens):
        with self.connect(True) as db:
            db.execute(
                "INSERT INTO usage(recording_id,created_at,tokens) VALUES(?,?,?)",
                (id, time.time(), tokens),
            )


def public_record(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "createdAt": round(row["created_at"] * 1000),
        "duration": row["duration"],
        "status": row["state"],
        "hasAudio": bool(row["audio_path"]),
        "interrupted": bool(row["interrupted"]),
        "error": row["error"],
        "sha256": row["sha256"],
        "transcript": json.loads(row["transcript"]) if row["transcript"] else None,
        "analysis": json.loads(row["analysis"]) if row["analysis"] else None,
    }
