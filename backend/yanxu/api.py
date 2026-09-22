import hashlib, hmac, math, os, re, uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from .config import Settings
from .store import Store, Conflict, Missing, Busy, public_record
from .media import file_lock, inspect_audio


class RecordingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,80}$")
    title: str = Field(default="", max_length=120)
    total_bytes: int = Field(gt=44)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    extension: str = Field(pattern=r"^(wav|m4a|mp3|webm)$")
    interrupted: bool = False


MIMES = {
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "webm": "audio/webm",
}


def create_app(settings=None):
    cfg = settings or Settings.load()
    store = Store(cfg)
    app = FastAPI(title="言序服务", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    app.state.settings = cfg
    from .remote_tasks import router as worker_router
    app.include_router(worker_router)
    from .identity import router as identity_router
    from .voice import router as voice_router
    from .managed_recordings import router as managed_router
    app.include_router(identity_router)
    app.include_router(voice_router)
    app.include_router(managed_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5178", "http://localhost:5178"],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"],
        allow_headers=["Content-Type", "X-Upload-Token", "Authorization"],
    )

    @app.exception_handler(Busy)
    async def busy(_, e):
        return JSONResponse(
            {"detail": str(e)}, status_code=429, headers={"Retry-After": "30"}
        )

    @app.exception_handler(Conflict)
    async def conflict(_, e):
        return JSONResponse({"detail": str(e)}, status_code=409)

    @app.exception_handler(Missing)
    async def missing(_, e):
        return JSONResponse({"detail": "记录不存在"}, status_code=404)

    def owned(id, token):
        r = store.get(id)
        if not token or not hmac.compare_digest(
            token.encode(), r["upload_token"].encode()
        ):
            raise HTTPException(403, "上传会话无效")
        return r

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "analysisConfigured": bool(cfg.api_key),
            "version": "0.1.0",
        }

    @app.post("/api/recordings")
    def create(value: RecordingCreate):
        if value.total_bytes > cfg.max_bytes:
            raise HTTPException(413, "文件超过本地服务容量配置")
        d = value.model_dump()
        d["title"] = value.title.strip() or "新录音"
        r = store.create(d)
        return {
            "id": r["id"],
            "uploadToken": r["upload_token"],
            "chunkSize": cfg.chunk_size,
            "state": r["state"],
        }

    @app.get("/api/uploads/{id}")
    def upload_status(id: str, x_upload_token: str | None = Header(default=None)):
        r = owned(id, x_upload_token)
        return {
            "id": id,
            "state": r["state"],
            "parts": store.parts(id),
            "chunkSize": cfg.chunk_size,
        }

    @app.put("/api/uploads/{id}/parts/{number}")
    async def put_part(
        id: str,
        number: int,
        request: Request,
        x_upload_token: str | None = Header(default=None),
    ):
        r = owned(id, x_upload_token)
        count = math.ceil(r["total_bytes"] / cfg.chunk_size)
        if number < 0 or number >= count:
            raise HTTPException(422, "分片编号无效")
        expected = min(cfg.chunk_size, r["total_bytes"] - number * cfg.chunk_size)
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > expected:
                raise HTTPException(413, "分片大小不符合清单")
            data.extend(chunk)
        if len(data) != expected:
            raise HTTPException(422, "分片不完整")
        digest = hashlib.sha256(data).hexdigest()
        folder = cfg.data_dir / "uploads" / id
        with file_lock(folder / ".lock"):
            old = next((p for p in store.parts(id) if p["part_no"] == number), None)
            if old:
                if old["sha256"] != digest:
                    raise Conflict("分片内容冲突")
                return {"part": number, "sha256": digest, "duplicate": True}
            if store.get(id)["state"] != "uploading":
                raise Conflict("录音已封存")
            target = folder / f"{number:08d}.part"
            temp = folder / (str(uuid.uuid4()) + ".tmp")
            with temp.open("wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, target)
            store.add_part(id, number, len(data), digest)
        return {"part": number, "sha256": digest, "duplicate": False}

    @app.post("/api/uploads/{id}/complete")
    def complete(id: str, x_upload_token: str | None = Header(default=None)):
        r = owned(id, x_upload_token)
        folder = cfg.data_dir / "uploads" / id
        with file_lock(folder / ".lock"):
            r = store.get(id)
            if r["audio_path"]:
                return public_record(r)
            parts = store.parts(id)
            count = math.ceil(r["total_bytes"] / cfg.chunk_size)
            if [p["part_no"] for p in parts] != list(range(count)):
                raise Conflict("录音分片尚未上传完整")
            assets = cfg.data_dir / "assets"
            assets.mkdir(exist_ok=True)
            final = assets / (id + "." + r["extension"])
            temp = assets / (id + ".assembling")
            digest = hashlib.sha256()
            size = 0
            with temp.open("wb") as out:
                for p in parts:
                    path = folder / f"{p['part_no']:08d}.part"
                    if not path.is_file():
                        raise Conflict("分片文件缺失，需要重新上传")
                    content = path.read_bytes()
                    if hashlib.sha256(content).hexdigest() != p["sha256"]:
                        raise Conflict("分片校验失败")
                    digest.update(content)
                    size += len(content)
                    out.write(content)
                out.flush()
                os.fsync(out.fileno())
            if size != r["total_bytes"] or digest.hexdigest() != r["sha256"]:
                temp.unlink(missing_ok=True)
                raise Conflict("音频整体校验失败")
            try:
                duration = inspect_audio(temp, r["extension"])
            except ValueError as e:
                temp.unlink(missing_ok=True)
                raise HTTPException(422, str(e))
            os.replace(temp, final)
            store.seal(id, final, MIMES[r["extension"]], duration)
            for part in folder.glob("*.part"):
                part.unlink(missing_ok=True)
            return public_record(store.get(id))

    @app.get("/api/recordings")
    def records(q: str = "", limit: int = 30, offset: int = 0, filter: str = "all"):
        if (
            len(q) > 120
            or not 1 <= limit <= 100
            or offset < 0
            or filter not in ["all", "complete", "processing"]
        ):
            raise HTTPException(422, "查询参数无效")
        rows, total = store.list(q, limit, offset, filter)
        return {"items": [public_record(r) for r in rows], "total": total}

    @app.get("/api/recordings/{id}")
    def detail(id: str):
        r = store.get(id)
        if not r["audio_path"]:
            raise Missing()
        return public_record(r)

    @app.get("/api/recordings/{id}/audio")
    @app.head("/api/recordings/{id}/audio")
    def audio(id: str, download: bool = False):
        r = store.get(id)
        from .cloud import delivery_url
        url = delivery_url(store, id, download)
        if url:
            return RedirectResponse(url, status_code=307, headers={"Cache-Control": "no-store"})
        if not r["audio_path"] or not Path(r["audio_path"]).is_file():
            raise Missing()
        return FileResponse(
            r["audio_path"],
            media_type=r["media_type"],
            filename=(id + "." + r["extension"]) if download else None,
            headers={
                "Cache-Control": "private, max-age=0",
                "X-Content-Type-Options": "nosniff",
            },
        )

    if (cfg.frontend_dist / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=cfg.frontend_dist / "assets"),
            name="assets",
        )

    @app.get("/")
    @app.get("/public.html")
    def public_page():
        page = cfg.frontend_dist / "public.html"
        if not page.is_file():
            raise HTTPException(503, "公共页面尚未构建")
        return FileResponse(page, headers={"Cache-Control": "no-cache"})

    @app.get("/account.html")
    def account_page():
        page = cfg.frontend_dist / "account.html"
        if not page.is_file():
            raise HTTPException(503, "账号工作台尚未构建")
        return FileResponse(page, headers={"Cache-Control": "no-store"})

    @app.get("/app/yanxu-debug.apk")
    def apk():
        path = cfg.data_dir.parent / "artifacts/yanxu-debug.apk"
        if not path.is_file():
            raise Missing()
        return FileResponse(
            path,
            media_type="application/vnd.android.package-archive",
            filename="yanxu-debug.apk",
        )

    from .app_updates import router as updates_router
    app.include_router(updates_router)

    return app
