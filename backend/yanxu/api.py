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
from .briefing import (
    DEFAULT_TEMPLATE_IDS,
    DEFAULT_TEMPLATES,
    SECTION_OPTIONS,
    generate_briefing,
    validate_section_ids,
    validate_template_payload,
)
from .briefing_ai import generate_ai_briefing
from .deepseek import ProviderError


class RecordingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(pattern=r"^[a-zA-Z0-9-]{16,80}$")
    title: str = Field(default="", max_length=120)
    total_bytes: int = Field(gt=44)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    extension: str = Field(pattern=r"^(wav|m4a|mp3|webm)$")
    interrupted: bool = False


class BriefingContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meetingTime: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=80)
    weather: str = Field(default="", max_length=80)


class BriefingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[str] = Field(min_length=1, max_length=10)
    context: BriefingContextInput = Field(default_factory=BriefingContextInput)
    templateId: str = Field(default="", max_length=120)
    templateName: str = Field(default="", max_length=120)
    templateDescription: str = Field(default="", max_length=300)


class BriefingTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=300)
    sections: list[str] = Field(min_length=1, max_length=10)


class TextRecordingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=200000)
    sourceName: str = Field(default="", max_length=120)
    context: BriefingContextInput = Field(default_factory=BriefingContextInput)


MIMES = {
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "webm": "audio/webm",
}


def text_transcript(value: TextRecordingCreate):
    text = "\n".join(line.strip() for line in value.text.replace("\r", "").splitlines())
    lines = [line for line in text.splitlines() if line]
    if not lines:
        lines = [value.text.strip()]
    segments = []
    for index, line in enumerate(lines[:200], start=1):
        start = (index - 1) * 30
        segments.append(
            {
                "id": f"seg-{index:04}",
                "start": start,
                "end": start + max(2, min(30, len(line) // 5)),
                "speaker": "文本",
                "text": line[:5000],
            }
        )
    context = {
        "meetingTime": value.context.meetingTime.strip(),
        "location": value.context.location.strip(),
        "weather": value.context.weather.strip(),
        "sourceName": value.sourceName.strip(),
    }
    return {
        "text": "\n".join(segment["text"] for segment in segments),
        "segments": segments,
        "context": {key: val for key, val in context.items() if val},
    }


def text_analysis(_transcript):
    return None


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
    from .admin_recordings import router as admin_recordings_router
    app.include_router(identity_router)
    app.include_router(voice_router)
    app.include_router(managed_router)
    app.include_router(admin_recordings_router)
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

    def briefing_record(id):
        r = store.get(id)
        if not r["audio_path"] and not r["transcript"]:
            raise Missing()
        if r["state"] != "complete":
            raise HTTPException(409, "纪要只能基于已完成记录生成")
        return r

    def template_snapshot(value, sections):
        template = {
            "id": value.templateId.strip(),
            "name": value.templateName.strip(),
            "description": value.templateDescription.strip(),
            "sections": sections,
        }
        return template if template["id"] or template["name"] else None

    def generated_briefing(id, sections, value):
        record = briefing_record(id)
        template = template_snapshot(value, sections)
        if cfg.api_key:
            try:
                return generate_ai_briefing(
                    cfg, store, record, sections, value.context.model_dump(), template
                )
            except ProviderError as e:
                if "用量" in str(e):
                    raise HTTPException(429, str(e)) from None
                raise HTTPException(503 if e.retryable else 422, str(e)) from None
        return generate_briefing(record, sections, value.context.model_dump(), template)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "analysisConfigured": bool(cfg.api_key),
            "version": "0.1.0",
        }

    @app.get("/api/briefing/section-options")
    def briefing_options():
        return {"items": SECTION_OPTIONS}

    @app.get("/api/briefing/templates")
    def briefing_templates():
        return {"items": DEFAULT_TEMPLATES + store.list_templates()}

    @app.post("/api/briefing/templates")
    def create_briefing_template(value: BriefingTemplateRequest):
        try:
            clean = validate_template_payload(value.model_dump())
        except ValueError:
            raise HTTPException(422, "纪要模板无效") from None
        return store.save_template(clean)

    @app.put("/api/briefing/templates/{template_id}")
    def update_briefing_template(template_id: str, value: BriefingTemplateRequest):
        if template_id in DEFAULT_TEMPLATE_IDS:
            raise HTTPException(409, "内置模板不能修改")
        try:
            clean = validate_template_payload(value.model_dump())
        except ValueError:
            raise HTTPException(422, "纪要模板无效") from None
        return store.save_template(clean, template_id)

    @app.delete("/api/briefing/templates/{template_id}")
    def delete_briefing_template(template_id: str):
        if template_id in DEFAULT_TEMPLATE_IDS:
            raise HTTPException(409, "内置模板不能删除")
        store.delete_template(template_id)
        return {"ok": True}

    @app.post("/api/text-recordings")
    def create_text_recording(value: TextRecordingCreate):
        transcript = text_transcript(value)
        if not transcript["segments"]:
            raise HTTPException(422, "导入文本不能为空")
        encoded = transcript["text"].encode("utf-8")
        record = store.create_text_record(
            {
                "client_id": "text-" + str(uuid.uuid4()),
                "title": value.title.strip(),
                "total_bytes": len(encoded),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "duration": transcript["segments"][-1]["end"],
                "transcript": transcript,
                "analysis": text_analysis(transcript),
            }
        )
        return public_record(record)

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
        if not r["audio_path"] and not r["transcript"]:
            raise Missing()
        return public_record(r)

    @app.post("/api/recordings/{id}/briefings/preview")
    def preview_briefing(id: str, value: BriefingRequest):
        try:
            sections = validate_section_ids(value.sections)
        except ValueError:
            raise HTTPException(422, "纪要板块无效") from None
        return generated_briefing(id, sections, value)

    @app.post("/api/recordings/{id}/briefings")
    def archive_briefing(id: str, value: BriefingRequest):
        try:
            sections = validate_section_ids(value.sections)
        except ValueError:
            raise HTTPException(422, "纪要板块无效") from None
        generated = generated_briefing(id, sections, value)
        return store.save_briefing(id, generated)

    @app.get("/api/recordings/{id}/briefings")
    def archived_briefings(id: str):
        r = store.get(id)
        if not r["audio_path"] and not r["transcript"]:
            raise Missing()
        return {"items": store.list_briefings(id)}

    @app.get("/api/recordings/{id}/briefings/{briefing_id}")
    def archived_briefing(id: str, briefing_id: str):
        r = store.get(id)
        if not r["audio_path"] and not r["transcript"]:
            raise Missing()
        return store.get_briefing(id, briefing_id)

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
    from .admin_app_versions import router as admin_app_versions_router, overview_router
    app.include_router(admin_app_versions_router)
    app.include_router(overview_router)

    return app
