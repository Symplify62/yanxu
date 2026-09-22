from functools import wraps
from fastapi import APIRouter, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from . import directory as directory
from .auth import bearer_token, change_password, current_account, enabled, login, require_permission, token_digest
from .models import GuestCreate, Login, PasswordChange, UserCreate, UserPatch, RoleCreate, RolePatch, DepartmentCreate, DepartmentPatch


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        @wraps(handler)
        async def guarded(request):
            try:
                response = await handler(request)
            except RequestValidationError as error:
                # FastAPI's default input field can echo a rejected password or whole request.
                response = JSONResponse({"detail": [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in error.errors()]}, status_code=422)
            except HTTPException as error:
                response = JSONResponse({"detail": error.detail}, status_code=error.status_code, headers=error.headers)
            response.headers["Cache-Control"] = "no-store"
            return response
        return guarded


router = APIRouter(route_class=PrivateRoute)


@router.post("/api/auth/login")
def sign_in(value: Login, request: Request):
    enabled(request)
    # Do not trust attacker-controlled forwarding headers for rate limiting.
    address = request.client.host if request.client else "unknown"
    return login(request.app.state.store, value.username, value.password, address, getattr(request.app.state.settings, "session_hours", 24))


@router.get("/api/auth/me")
def me(request: Request):
    return current_account(request)


@router.post("/api/auth/password")
def update_password(value: PasswordChange, request: Request):
    return change_password(request, value.oldPassword, value.newPassword)


@router.post("/api/auth/logout")
def logout(request: Request):
    enabled(request)
    digest = token_digest(bearer_token(request))
    import time
    with request.app.state.store.connect(True) as db:
        db.execute("UPDATE identity_sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL", (time.time(), digest))
    return {"ok": True}


@router.get("/api/people")
def people(request: Request):
    actor = current_account(request)
    scope_all = bool(set(actor["permissions"]) & {"record", "users", "voices"})
    with request.app.state.store.connect() as db:
        query = directory.USER_SELECT + " WHERE p.active=1 AND p.deleted_at IS NULL"
        args = []
        if not scope_all:
            query += " AND p.id=?"
            args.append(actor["personId"])
        items = [directory.person_response(row) for row in db.execute(query + " ORDER BY p.name,p.id", args)]
        departments = [directory.department_response(row) for row in db.execute("SELECT * FROM identity_departments ORDER BY name,id")]
        if not scope_all:
            allowed = {p["departmentId"] for p in items}
            departments = [d for d in departments if d["id"] in allowed]
    return {"items": items, "departments": departments}


@router.get("/api/admin/users")
def users(request: Request):
    require_permission(request, "users")
    with request.app.state.store.connect() as db:
        return {"items": [directory.person_response(row, True) for row in db.execute(directory.USER_SELECT + " WHERE p.deleted_at IS NULL ORDER BY p.name,p.id")]}


@router.post("/api/admin/users")
def add_user(value: UserCreate, request: Request):
    return directory.create_user(request.app.state.store, value, require_permission(request, "users"))


@router.patch("/api/admin/users/{person_id}")
def edit_user(person_id: str, value: UserPatch, request: Request):
    return directory.patch_user(request.app.state.store, person_id, value, require_permission(request, "users"))


@router.delete("/api/admin/users/{person_id}")
def remove_user(person_id: str, request: Request):
    directory.delete_user(request.app.state.store, person_id, require_permission(request, "users"))
    return {"ok": True}


@router.get("/api/admin/roles")
def roles(request: Request):
    require_permission(request, "roles")
    with request.app.state.store.connect() as db:
        return {"items": [directory.role_response(row) for row in db.execute("SELECT * FROM identity_roles ORDER BY builtin DESC,name")]}


@router.post("/api/admin/roles")
def add_role(value: RoleCreate, request: Request):
    return directory.create_role(request.app.state.store, value, require_permission(request, "roles"))


@router.patch("/api/admin/roles/{role_id}")
def edit_role(role_id: str, value: RolePatch, request: Request):
    return directory.patch_role(request.app.state.store, role_id, value, require_permission(request, "roles"))


@router.delete("/api/admin/roles/{role_id}")
def remove_role(role_id: str, request: Request):
    directory.delete_role(request.app.state.store, role_id, require_permission(request, "roles"))
    return {"ok": True}


@router.get("/api/admin/departments")
def departments(request: Request):
    require_permission(request, "departments")
    with request.app.state.store.connect() as db:
        return {"items": [directory.department_response(row) for row in db.execute("SELECT * FROM identity_departments ORDER BY name,id")]}


@router.post("/api/admin/departments")
def add_department(value: DepartmentCreate, request: Request):
    require_permission(request, "departments")
    return directory.write_department(request.app.state.store, value)


@router.patch("/api/admin/departments/{department_id}")
def edit_department(department_id: str, value: DepartmentPatch, request: Request):
    require_permission(request, "departments")
    return directory.write_department(request.app.state.store, value, department_id)


@router.delete("/api/admin/departments/{department_id}")
def remove_department(department_id: str, request: Request):
    require_permission(request, "departments")
    directory.delete_department(request.app.state.store, department_id)
    return {"ok": True}


@router.post("/api/people")
def add_guest(value: GuestCreate, request: Request):
    actor = require_permission(request, "record")
    if not value.name.strip():
        raise HTTPException(422, "姓名不能为空")
    created = directory.create_user(request.app.state.store, UserCreate(name=value.name, detail=value.detail), actor)
    return {key: created[key] for key in ("id", "name", "detail", "departmentId", "departmentName", "active")}
