"""Read-only, environment-local recording inventory for system administrators."""
from fastapi import APIRouter, HTTPException, Request

from .identity.auth import require_system_admin
from .identity.routes import PrivateRoute
from .managed_recordings import projection

router = APIRouter(prefix="/api/admin/recordings", route_class=PrivateRoute)
FROM = """FROM recordings r LEFT JOIN identity_accounts a ON a.id=r.owner_account_id
LEFT JOIN identity_people p ON p.id=a.person_id"""
STATUSES = {
    "all": None,
    "processing": ("uploading", "queued", "waiting", "transcribing", "analyzing"),
    "complete": ("complete", "no-speech"),
    "failed": ("transcript-error", "analysis-error"),
}


def summary(row):
    return {
        "id": row["id"], "title": row["title"],
        "createdAt": round(row["created_at"] * 1000), "duration": row["duration"],
        "status": row["state"], "speakerStatus": row["attribution_state"],
        "hasAudio": bool(row["audio_path"]), "interrupted": bool(row["interrupted"]),
        "error": row["error"], "source": "account" if row["owner_account_id"] else "guest",
        "ownerName": row["owner_name"], "ownerUsername": row["owner_username"],
    }


def validate(q, status, source, limit, offset):
    if len(q) > 120 or status not in STATUSES or source not in ("all", "guest", "account") or not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "查询参数无效")


@router.get("")
def list_recordings(request: Request, q: str = "", status: str = "all", source: str = "all",
                    limit: int = 20, offset: int = 0):
    require_system_admin(request)
    validate(q, status, source, limit, offset)
    conditions, args = [], []
    if q.strip():
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append("(r.title LIKE ? ESCAPE '\\' OR p.name LIKE ? ESCAPE '\\' OR a.username LIKE ? ESCAPE '\\')")
        args.extend([f"%{escaped}%"] * 3)
    if source != "all":
        conditions.append("r.owner_account_id IS NULL" if source == "guest" else "r.owner_account_id IS NOT NULL")
    if STATUSES[status]:
        values = STATUSES[status]
        conditions.append("r.state IN (" + ",".join("?" for _ in values) + ")")
        args.extend(values)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with request.app.state.store.connect() as db:
        total = db.execute("SELECT count(*) " + FROM + where, args).fetchone()[0]
        rows = db.execute("SELECT r.*,a.username AS owner_username,p.name AS owner_name " + FROM + where +
                          " ORDER BY r.created_at DESC,r.id DESC LIMIT ? OFFSET ?", [*args, limit, offset]).fetchall()
    return {"items": [summary(row) for row in rows], "total": total}


@router.get("/{recording_id}")
def recording_detail(recording_id: str, request: Request):
    require_system_admin(request)
    with request.app.state.store.connect() as db:
        row = db.execute("SELECT r.*,a.username AS owner_username,p.name AS owner_name " + FROM +
                         " WHERE r.id=?", (recording_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "记录不存在")
    value = projection(request.app.state.store, dict(row))
    return {**value, **{key: summary(row)[key] for key in ("source", "ownerName", "ownerUsername")}}
