"""Organization directory mutations preserve existing recording/voice references."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager

from fastapi import HTTPException
from .auth import hash_password, normalize_username, revoke_account_sessions
from .schema import PERMISSIONS


@contextmanager
def transaction(store):
    try:
        with store.connect(True) as db:
            yield db
    except sqlite3.IntegrityError:
        raise HTTPException(409, "账号或名称已存在") from None


def get_row(db, table, row_id):
    # Table is a fixed module constant supplied only by internal callers.
    row = db.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "记录不存在")
    return row


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(422, label + "不能为空")
    return value.strip()


def valid_department(db, department_id):
    if department_id is not None:
        get_row(db, "identity_departments", department_id)


def permissions(value, actor):
    if not isinstance(value, list) or set(value) - PERMISSIONS:
        raise HTTPException(422, "无效的权限")
    result = sorted(set(value))
    if set(result) - set(actor["permissions"]):
        raise HTTPException(403, "不能授予自己没有的权限")
    return result


def valid_role(db, role_id, actor):
    row = get_row(db, "identity_roles", role_id)
    permissions(json.loads(row["permissions"]), actor)


USER_SELECT = """SELECT p.*,d.name AS department_name,a.id AS account_id,a.username,a.role_id
 FROM identity_people p LEFT JOIN identity_departments d ON d.id=p.department_id
 LEFT JOIN identity_accounts a ON a.person_id=p.id"""


def person_response(row, account=False):
    value = {"id": row["id"], "name": row["name"], "detail": row["detail"],
             "departmentId": row["department_id"], "departmentName": row["department_name"], "active": bool(row["active"])}
    if account:
        value.update(accountId=row["account_id"], username=row["username"], roleId=row["role_id"])
    return value


def user_response(db, person_id):
    return person_response(db.execute(USER_SELECT + " WHERE p.id=?", (person_id,)).fetchone(), True)


def ensure_admin_remains(db):
    count = db.execute("""SELECT count(*) FROM identity_accounts a JOIN identity_people p ON p.id=a.person_id
      WHERE a.role_id='admin' AND a.active=1 AND p.active=1 AND p.deleted_at IS NULL""").fetchone()[0]
    if count == 0:
        raise HTTPException(409, "必须保留至少一位启用的管理员")


def create_user(store, value, actor):
    now, person_id = time.time(), str(uuid.uuid4())
    password_hash = hash_password(value.password) if value.username else None
    with transaction(store) as db:
        valid_department(db, value.departmentId)
        if value.username:
            valid_role(db, value.roleId, actor)
        db.execute("INSERT INTO identity_people VALUES(?,?,?,?,?,?,?,NULL)",
                   (person_id, value.name.strip(), value.detail.strip(), value.departmentId, int(value.active), now, now))
        if value.username:
            db.execute("INSERT INTO identity_accounts VALUES(?,?,?,?,?,?,?,?)", (
                str(uuid.uuid4()), person_id, normalize_username(value.username), password_hash,
                value.roleId, int(value.active), now, now))
        return user_response(db, person_id)


def patch_user(store, person_id, value, actor):
    changes = value.model_dump(exclude_unset=True)
    # Null only clears the department. Other null values are not accidental resets.
    if any(v is None and k != "departmentId" for k, v in changes.items()):
        raise HTTPException(422, "只有部门可以清空")
    password_hash = hash_password(changes["password"]) if "password" in changes else None
    with transaction(store) as db:
        person = get_row(db, "identity_people", person_id)
        if person["deleted_at"] is not None:
            raise HTTPException(404, "人员已归档")
        account = db.execute("SELECT * FROM identity_accounts WHERE person_id=?", (person_id,)).fetchone()
        if "departmentId" in changes:
            valid_department(db, changes["departmentId"])
        if "roleId" in changes:
            valid_role(db, changes["roleId"], actor)
        # Users managers cannot modify passwords or membership of more privileged accounts.
        if account and set(json.loads(get_row(db, "identity_roles", account["role_id"])["permissions"])) - set(actor["permissions"]):
            raise HTTPException(403, "不能修改权限高于自己的人员")
        wants_account = any(k in changes for k in ("username", "password", "roleId"))
        if account is None and wants_account:
            if not all(k in changes for k in ("username", "password", "roleId")):
                raise HTTPException(422, "创建登录账号需同时提供账号、密码及角色")
            db.execute("INSERT INTO identity_accounts VALUES(?,?,?,?,?,?,?,?)", (
                str(uuid.uuid4()), person_id, normalize_username(changes["username"]), password_hash,
                changes["roleId"], int(changes.get("active", person["active"])), time.time(), time.time()))
        elif account:
            mappings = {"username": "username", "roleId": "role_id", "active": "active"}
            for key, column in mappings.items():
                if key in changes:
                    item = normalize_username(changes[key]) if key == "username" else changes[key]
                    db.execute(f"UPDATE identity_accounts SET {column}=?,updated_at=? WHERE id=?", (item, time.time(), account["id"]))
            if password_hash:
                db.execute("UPDATE identity_accounts SET password_hash=?,updated_at=? WHERE id=?", (password_hash, time.time(), account["id"]))
            if any(key in changes for key in ("password", "username", "active")):
                revoke_account_sessions(db, account["id"])
        for key, column in {"name": "name", "detail": "detail", "departmentId": "department_id", "active": "active"}.items():
            if key in changes:
                item = text(changes[key], "姓名") if key == "name" else changes[key]
                db.execute(f"UPDATE identity_people SET {column}=?,updated_at=? WHERE id=?", (item, time.time(), person_id))
        ensure_admin_remains(db)
        return user_response(db, person_id)


def delete_user(store, person_id, actor):
    with transaction(store) as db:
        get_row(db, "identity_people", person_id)
        account = db.execute("SELECT * FROM identity_accounts WHERE person_id=?", (person_id,)).fetchone()
        if account:
            valid_role(db, account["role_id"], actor)
            db.execute("UPDATE identity_accounts SET active=0,updated_at=? WHERE id=?", (time.time(), account["id"]))
            revoke_account_sessions(db, account["id"])
        db.execute("UPDATE identity_people SET active=0,deleted_at=?,updated_at=? WHERE id=?", (time.time(), time.time(), person_id))
        ensure_admin_remains(db)


def role_response(row):
    return {"id": row["id"], "name": row["name"], "description": row["description"],
            "permissions": json.loads(row["permissions"]), "builtin": bool(row["builtin"])}


def create_role(store, value, actor):
    role_id, now = str(uuid.uuid4()), time.time()
    with transaction(store) as db:
        db.execute("INSERT INTO identity_roles VALUES(?,?,?,?,0,?,?)", (role_id, text(value.name, "角色名称"),
                   value.description, json.dumps(permissions(value.permissions, actor)), now, now))
        return role_response(get_row(db, "identity_roles", role_id))


def patch_role(store, role_id, value, actor):
    changes = value.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(422, "角色字段不可为空")
    with transaction(store) as db:
        old = get_row(db, "identity_roles", role_id)
        permissions(json.loads(old["permissions"]), actor)
        if old["builtin"] and any(k in changes for k in ("name", "permissions")):
            raise HTTPException(409, "内置角色的名称与权限不可修改")
        if "permissions" in changes:
            changes["permissions"] = json.dumps(permissions(changes["permissions"], actor))
        for key, item in changes.items():
            if key == "name":
                item = text(item, "角色名称")
            db.execute(f"UPDATE identity_roles SET {key}=?,updated_at=? WHERE id=?", (item, time.time(), role_id))
        return role_response(get_row(db, "identity_roles", role_id))


def delete_role(store, role_id, actor):
    with transaction(store) as db:
        row = get_row(db, "identity_roles", role_id)
        permissions(json.loads(row["permissions"]), actor)
        if row["builtin"] or db.execute("SELECT 1 FROM identity_accounts WHERE role_id=? LIMIT 1", (role_id,)).fetchone():
            raise HTTPException(409, "内置或已关联账号的角色不能删除")
        db.execute("DELETE FROM identity_roles WHERE id=?", (role_id,))


def department_response(row):
    return {"id": row["id"], "name": row["name"], "parentId": row["parent_id"]}


def validate_parent(db, department_id, parent):
    seen = {department_id}
    while parent is not None:
        if parent in seen:
            raise HTTPException(409, "部门不能形成循环层级")
        seen.add(parent)
        parent = get_row(db, "identity_departments", parent)["parent_id"]


def write_department(store, value, department_id=None):
    changes = value.model_dump(exclude_unset=department_id is not None)
    now = time.time()
    with transaction(store) as db:
        if department_id is None:
            department_id = str(uuid.uuid4())
            validate_parent(db, department_id, value.parentId)
            db.execute("INSERT INTO identity_departments VALUES(?,?,?,?,?)", (department_id, text(value.name, "部门名称"), value.parentId, now, now))
        else:
            get_row(db, "identity_departments", department_id)
            if "parentId" in changes:
                validate_parent(db, department_id, changes["parentId"])
            for key, column in {"name": "name", "parentId": "parent_id"}.items():
                if key in changes:
                    item = text(changes[key], "部门名称") if key == "name" else changes[key]
                    db.execute(f"UPDATE identity_departments SET {column}=?,updated_at=? WHERE id=?", (item, now, department_id))
        return department_response(get_row(db, "identity_departments", department_id))


def delete_department(store, department_id):
    with transaction(store) as db:
        get_row(db, "identity_departments", department_id)
        if db.execute("SELECT 1 FROM identity_departments WHERE parent_id=?", (department_id,)).fetchone() or db.execute("SELECT 1 FROM identity_people WHERE department_id=?", (department_id,)).fetchone():
            raise HTTPException(409, "请先移出部门人员和子部门")
        db.execute("DELETE FROM identity_departments WHERE id=?", (department_id,))
