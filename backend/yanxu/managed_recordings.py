"""Authenticated meeting ownership and fixed, server-validated participant rosters."""
import json
import uuid

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from .identity import current_account, require_permission
from .identity.routes import PrivateRoute
from .store import Conflict, public_record
from .voice import protected_transcript

router = APIRouter(prefix="/api/managed/recordings", route_class=PrivateRoute)


class Participant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    personId: str = Field(min_length=1, max_length=80)


class ManagedCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,80}$")
    title: str = Field(default="", max_length=120)
    total_bytes: int = Field(gt=44)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    extension: str = Field(pattern=r"^(wav|m4a|mp3|webm)$")
    interrupted: bool = False
    participants: list[Participant] = Field(default_factory=list, max_length=200)
    rosterClientId: str = Field(min_length=1, max_length=100)


def can_read(account, row):
    return (row["owner_account_id"] == account["id"] or is_administrator(account)
            or any(p["personId"] == account["personId"] for p in json.loads(row["roster_json"] or "[]")))


def is_administrator(account):
    return {"record", "users", "roles", "departments", "voices"}.issubset(account["permissions"])


def projection(store, row):
    value = public_record(row)
    value["transcript"] = protected_transcript(store, row)
    value["participants"] = json.loads(row["roster_json"] or "[]")
    return value


@router.post("")
def create(value: ManagedCreate, request: Request, response: Response):
    account = require_permission(request, "record")
    response.headers["Cache-Control"] = "no-store"
    store = request.app.state.store
    if value.total_bytes > store.settings.max_bytes:
        raise HTTPException(413, "文件超过服务容量配置")
    ids = [p.personId for p in value.participants]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "参会名单不能重复")
    data = value.model_dump(exclude={"participants", "rosterClientId"})
    data["title"] = value.title.strip() or "新录音"
    data["client_id"] = "managed-" + str(uuid.uuid5(uuid.NAMESPACE_URL, account["id"] + "/" + value.client_id))
    with store.connect(True) as db:
        old = db.execute("SELECT * FROM recordings WHERE client_id=?", (data["client_id"],)).fetchone()
        if old:
            roster = json.loads(old["roster_json"] or "[]")
            if [p["personId"] for p in roster] != ids:
                raise Conflict("录音的参会名单已固定")
        else:
            roster = []
            for person_id in ids:
                person = db.execute("SELECT id,name FROM identity_people WHERE id=? AND active=1 AND deleted_at IS NULL", (person_id,)).fetchone()
                if not person:
                    raise HTTPException(422, "参会人已停用或不存在，请同步名单")
                roster.append({"personId": person["id"], "name": person["name"]})
        row = store.create(data, owner=account["id"], roster=roster, roster_client_id=value.rosterClientId, db=db)
    return {"id": row["id"], "uploadToken": row["upload_token"], "chunkSize": store.settings.chunk_size, "state": row["state"]}


@router.get("")
def records(request: Request, response: Response, limit: int = 30, offset: int = 0):
    account = current_account(request)
    response.headers["Cache-Control"] = "no-store"
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(422, "查询参数无效")
    store = request.app.state.store
    condition = "owner_account_id IS NOT NULL AND audio_path IS NOT NULL"
    args = []
    if not is_administrator(account):
        condition += " AND (owner_account_id=? OR EXISTS (SELECT 1 FROM json_each(roster_json) p WHERE json_extract(p.value,'$.personId')=?))"
        args = [account["id"], account["personId"]]
    with store.connect() as db:
        total = db.execute("SELECT count(*) FROM recordings WHERE " + condition, args).fetchone()[0]
        rows = db.execute("SELECT * FROM recordings WHERE " + condition + " ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?", [*args, limit, offset]).fetchall()
    return {"items": [projection(store, dict(row)) for row in rows], "total": total}


@router.get("/{recording_id}")
def detail(recording_id: str, request: Request, response: Response):
    account = current_account(request)
    response.headers["Cache-Control"] = "no-store"
    store = request.app.state.store
    row = store.get(recording_id)
    if not row["owner_account_id"] or not can_read(account, row):
        raise HTTPException(404, "记录不存在")
    return projection(store, row)
