"""Administrator-controlled APK candidates and atomic update-manifest publication."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .app_updates import NAME, artifacts
from .identity.auth import require_system_admin
from .identity.routes import PrivateRoute
from .media import file_lock, write_json

router = APIRouter(prefix="/api/admin/app-versions", route_class=PrivateRoute)
overview_router = APIRouter(route_class=PrivateRoute)
MAX_APK = 100 * 1024 * 1024
SHA = re.compile(r"[a-f0-9]{64}")


class Switch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    expectedCurrentSha: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


def paths(request):
    root = artifacts(request)
    root.mkdir(parents=True, exist_ok=True)
    (root / "releases").mkdir(exist_ok=True)
    (root / "candidates").mkdir(exist_ok=True, mode=0o700)
    return root, root / "android-update.json", root / "android-release-state.json"


def read_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        raise HTTPException(503, "版本资料暂不可用") from None


def manifest_file(root, value, settings):
    if not isinstance(value, dict):
        raise HTTPException(503, "当前版本清单无效")
    url = value.get("url")
    sha = value.get("sha256")
    code = value.get("versionCode")
    if (not isinstance(url, str) or not isinstance(sha, str) or not SHA.fullmatch(sha)
            or type(code) is not int or code < 1 or value.get("packageName") != settings.android_package_name):
        raise HTTPException(503, "当前版本清单无效")
    name = f"yanxu-{code}-{sha[:12]}.apk"
    if not NAME.fullmatch(name) or url != settings.public_origin + "/app/releases/" + name:
        raise HTTPException(503, "当前版本清单无效")
    path = root / "releases" / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size != value.get("size"):
        raise HTTPException(503, "当前安装包缺失")
    if checksum(path) != sha:
        raise HTTPException(503, "当前安装包校验失败")
    return path


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(path):
    aapt = os.environ.get("YANXU_AAPT_BIN") or shutil.which("aapt")
    apksigner = os.environ.get("YANXU_APKSIGNER_BIN") or shutil.which("apksigner")
    if not aapt or not apksigner:
        raise HTTPException(503, "服务器缺少 APK 校验工具")
    try:
        badge = subprocess.run([aapt, "dump", "badging", str(path)], capture_output=True, text=True,
                               timeout=45, check=True).stdout
        certs = subprocess.run([apksigner, "verify", "--print-certs", str(path)], capture_output=True,
                               text=True, timeout=60, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        raise HTTPException(422, "APK 无法通过包信息或签名校验") from None
    package = re.search(r"package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", badge)
    sdk = re.search(r"sdkVersion:'([0-9]+)'", badge)
    signers = re.findall(r"Signer #[0-9]+ certificate SHA-256 digest: ([a-f0-9]{64})", certs)
    if not package or not sdk or len(signers) != 1:
        raise HTTPException(422, "APK 包信息或签名不符合要求")
    return {"packageName": package[1], "versionCode": int(package[2]),
            "versionName": package[3], "minSdk": int(sdk[1]), "signer": signers[0]}


def state_data(state_path):
    value = read_json(state_path, {"releases": [], "events": []})
    if not isinstance(value, dict) or not isinstance(value.get("releases"), list) or not isinstance(value.get("events"), list):
        raise HTTPException(503, "版本资料暂不可用")
    return value


def current_data(root, manifest_path, settings):
    value = read_json(manifest_path, None)
    if value is not None:
        manifest_file(root, value, settings)
    return value


def public_release(value):
    return {key: value[key] for key in ("sha256", "versionCode", "versionName", "minSdk", "packageName", "size", "notes", "uploadedAt") if key in value}


def response(root, manifest, state, settings):
    current = current_data(root, manifest, settings)
    versions = [public_release(v) for v in state["releases"]]
    if current and not any(v["sha256"] == current["sha256"] for v in versions):
        versions.append(public_release({**current, "uploadedAt": None}))
    versions.sort(key=lambda v: (v["versionCode"], v["sha256"]), reverse=True)
    return {"environment": settings.environment, "packageName": settings.android_package_name,
            "current": public_release(current) if current else None, "versions": versions,
            "events": state["events"][-30:][::-1]}


@overview_router.get("/api/environment")
def environment(request: Request):
    return {"environment": request.app.state.settings.environment}


@overview_router.get("/api/admin/overview")
def overview(request: Request):
    require_system_admin(request)
    root, manifest, state = paths(request)
    with request.app.state.store.connect() as db:
        counts = {
            "recordings": db.execute("SELECT count(*) FROM recordings").fetchone()[0],
            "processing": db.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','running','retry','waiting')").fetchone()[0],
            "failed": db.execute("SELECT count(*) FROM jobs WHERE status='failed'").fetchone()[0],
            "cloudPending": db.execute("SELECT count(*) FROM cloud_objects WHERE status IN ('pending','retry')").fetchone()[0],
            "cloudFailed": db.execute("SELECT count(*) FROM cloud_objects WHERE status='failed'").fetchone()[0],
            "users": db.execute("SELECT count(*) FROM identity_people WHERE deleted_at IS NULL").fetchone()[0],
            "voicePending": db.execute("SELECT count(*) FROM voice_jobs WHERE status IN ('pending','running','retry')").fetchone()[0],
        }
    with file_lock(root / ".app-versions.lock"):
        current = current_data(root, manifest, request.app.state.settings)
    return {"environment": request.app.state.settings.environment, "counts": counts,
            "appVersion": public_release(current) if current else None}


@router.get("")
def list_versions(request: Request):
    require_system_admin(request)
    root, manifest, state = paths(request)
    with file_lock(root / ".app-versions.lock"):
        return response(root, manifest, state_data(state), request.app.state.settings)


@router.put("/candidate")
async def upload_candidate(request: Request, notes: str = ""):
    actor = require_system_admin(request)
    if len(notes) > 2000 or request.headers.get("content-type", "").split(";", 1)[0] != "application/vnd.android.package-archive":
        raise HTTPException(422, "请选择 APK 并填写不超过 2000 字的更新说明")
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > MAX_APK):
        raise HTTPException(413, "APK 不能超过 100 MB")
    root, manifest, state_path = paths(request)
    with tempfile.NamedTemporaryFile(prefix="apk-upload-", suffix=".apk", dir=root, delete=False) as tmp:
        temp = Path(tmp.name)
        count = 0
        try:
            async for chunk in request.stream():
                count += len(chunk)
                if count > MAX_APK:
                    raise HTTPException(413, "APK 不能超过 100 MB")
                tmp.write(chunk)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        if not count:
            raise HTTPException(422, "APK 不能为空")
        meta = inspect(temp)
        settings = request.app.state.settings
        if meta["packageName"] != settings.android_package_name or meta["minSdk"] < 26 or meta["versionCode"] < 1 or not meta["versionName"]:
            raise HTTPException(422, "APK 包名或最低系统版本不匹配")
        if len(meta["versionName"]) > 40:
            raise HTTPException(422, "APK 版本名称过长")
        sha = checksum(temp)
        name = f"yanxu-{meta['versionCode']}-{sha[:12]}.apk"
        with file_lock(root / ".app-versions.lock"):
            current = current_data(root, manifest, settings)
            if current:
                old = inspect(manifest_file(root, current, settings))
                if meta["signer"] != old["signer"]:
                    raise HTTPException(422, "APK 签名与当前版本不同")
                if meta["versionCode"] <= current["versionCode"]:
                    raise HTTPException(422, "新版本号须高于当前发布版本")
            elif settings.environment == "production":
                raise HTTPException(409, "生产环境缺少已发布基线，不能上传首个版本")
            state = state_data(state_path)
            if current and not any(v["sha256"] == current["sha256"] for v in state["releases"]):
                state["releases"].append({**current, "signer": old["signer"], "uploadedAt": None})
            if sum(v.get("size", 0) for v in state["releases"]) + count > 2 * 1024**3:
                raise HTTPException(507, "版本文件已达到 2 GB，请先清理旧候选包")
            if any(v["versionCode"] == meta["versionCode"] and v["sha256"] != sha for v in state["releases"]):
                raise HTTPException(409, "该版本号已有不同安装包")
            target = root / "candidates" / name
            if target.exists():
                if target.is_symlink() or checksum(target) != sha:
                    raise HTTPException(409, "安装包文件冲突")
            else:
                os.replace(temp, target)
                target.chmod(0o640)
            if not any(v["sha256"] == sha for v in state["releases"]):
                state["releases"].append({**meta, "sha256": sha, "size": count, "notes": notes, "uploadedAt": time.time()})
                state["events"].append({"action": "upload", "sha256": sha, "actor": actor["username"], "at": time.time()})
                write_json(state_path, state)
            return response(root, manifest, state, settings)
    finally:
        temp.unlink(missing_ok=True)


def switch_release(request, value, rollback):
    actor = require_system_admin(request)
    root, manifest, state_path = paths(request)
    settings = request.app.state.settings
    with file_lock(root / ".app-versions.lock"):
        current = current_data(root, manifest, settings)
        old_sha = current["sha256"] if current else None
        if old_sha != value.expectedCurrentSha:
            raise HTTPException(409, "当前版本已变化，请刷新后重试")
        state = state_data(state_path)
        target = next((v for v in state["releases"] if v["sha256"] == value.sha256), None)
        if target is None and rollback and current and current["sha256"] == value.sha256:
            raise HTTPException(409, "已经是当前版本")
        if target is None:
            raise HTTPException(404, "候选版本不存在")
        name = f"yanxu-{target['versionCode']}-{value.sha256[:12]}.apk"
        published_path = root / "releases" / name
        path = published_path if published_path.exists() else root / "candidates" / name
        if rollback and path != published_path:
            raise HTTPException(409, "只能回退到已发布版本")
        if path.is_symlink() or not path.is_file() or path.stat().st_size != target["size"] or checksum(path) != value.sha256:
            raise HTTPException(409, "安装包校验失败")
        meta = inspect(path)
        if any(meta[k] != target[k] for k in ("packageName", "versionCode", "versionName", "minSdk", "signer")):
            raise HTTPException(409, "安装包元数据已变化")
        if meta["packageName"] != settings.android_package_name:
            raise HTTPException(409, "环境包名不匹配")
        if current:
            old = inspect(manifest_file(root, current, settings))
            if meta["signer"] != old["signer"]:
                raise HTTPException(409, "安装包签名不匹配")
            if rollback:
                if target["versionCode"] >= current["versionCode"]:
                    raise HTTPException(409, "回退只能选择较早的版本")
            elif target["versionCode"] <= current["versionCode"]:
                raise HTTPException(409, "发布版本号须高于当前版本")
        elif rollback:
            raise HTTPException(409, "尚无可回退版本")
        next_manifest = {k: meta[k] for k in ("packageName", "versionCode", "versionName", "minSdk")}
        if path != published_path:
            os.replace(path, published_path)
            path = published_path
        next_manifest.update(url=settings.public_origin + "/app/releases/" + path.name,
                             size=target["size"], sha256=value.sha256, notes=target.get("notes", ""))
        state["events"].append({"action": "rollback_attempt" if rollback else "publish_attempt", "sha256": value.sha256,
                                "fromSha256": old_sha, "actor": actor["username"], "at": time.time()})
        write_json(state_path, state)
        write_json(manifest, next_manifest)
        state["events"].append({"action": "rollback" if rollback else "publish", "sha256": value.sha256,
                                "fromSha256": old_sha, "actor": actor["username"], "at": time.time()})
        write_json(state_path, state)
        return response(root, manifest, state, settings)


@router.post("/publish")
def publish(value: Switch, request: Request):
    return switch_release(request, value, False)


@router.post("/rollback")
def rollback(value: Switch, request: Request):
    return switch_release(request, value, True)
