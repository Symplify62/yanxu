"""Public Android release metadata. Publication is an offline operator action."""
import json
import re
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="/app")
NAME = re.compile(r"yanxu-[1-9][0-9]*-[a-f0-9]{12}\.apk")


def require(condition):
    if not condition:
        raise ValueError("Invalid release manifest")


def artifacts(request):
    return request.app.state.settings.data_dir.parent / "artifacts"


@router.get("/update.json")
def latest(request: Request):
    folder = artifacts(request)
    origin = request.app.state.settings.public_origin
    package = request.app.state.settings.android_package_name
    path = folder / "android-update.json"
    if not path.is_file():
        return JSONResponse({"available": False}, headers={"Cache-Control": "no-store"})
    try:
        value = json.loads(path.read_text())
        require(isinstance(value["url"], str))
        filename = value["url"].removeprefix(origin + "/app/releases/")
        require(NAME.fullmatch(filename))
        require(value["url"] == origin + "/app/releases/" + filename)
        require(value["packageName"] == package)
        require(type(value["versionCode"]) is int and value["versionCode"] > 0)
        require(isinstance(value["versionName"], str) and 1 <= len(value["versionName"]) <= 40)
        require(type(value["minSdk"]) is int and value["minSdk"] >= 26)
        require(type(value["size"]) is int and 0 < value["size"] <= 100 * 1024 * 1024)
        require(re.fullmatch(r"[a-f0-9]{64}", value["sha256"]))
        require(filename == f"yanxu-{value['versionCode']}-{value['sha256'][:12]}.apk")
        require(not (folder / "releases" / filename).is_symlink())
        require((folder / "releases" / filename).stat().st_size == value["size"])
        require(isinstance(value.get("notes", ""), str) and len(value.get("notes", "")) <= 2000)
        clean = {k: value[k] for k in ("versionCode", "versionName", "minSdk", "packageName", "url", "size", "sha256")}
        clean.update(available=True, notes=value.get("notes", ""))
    except (ValueError, KeyError, TypeError, AssertionError, OSError):
        raise HTTPException(503, "更新信息暂不可用")
    return JSONResponse(clean, headers={"Cache-Control": "no-store"})


@router.get("/releases/{filename}")
def download(filename: str, request: Request):
    if not NAME.fullmatch(filename):
        raise HTTPException(404, "安装包不存在")
    path = artifacts(request) / "releases" / filename
    if not path.is_file() or path.is_symlink():
        raise HTTPException(404, "安装包不存在")
    return FileResponse(path, filename=filename, media_type="application/vnd.android.package-archive",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})
