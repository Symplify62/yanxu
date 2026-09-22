import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yanxu.config import Settings
from yanxu.store import Store
from yanxu.identity import initialize, router
from yanxu.identity.__main__ import bootstrap
from yanxu.identity.auth import token_digest

PASSWORD = "independent-test-password!"


@pytest.fixture
def env(tmp_path):
    settings = Settings(data_dir=tmp_path)
    store = Store(settings)
    initialize(store)
    admin = bootstrap(store, "admin", PASSWORD, "管理员")
    app = FastAPI()
    app.state.settings, app.state.store = settings, store
    app.include_router(router)
    client = TestClient(app)
    auth = client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD}).json()
    return client, store, admin, {"Authorization": "Bearer " + auth["accessToken"]}


def create_person(client, headers, name="同事", username=None, role="member", **kwargs):
    value = {"name": name, **kwargs}
    if username:
        value.update(username=username, password=PASSWORD, roleId=role)
    result = client.post("/api/admin/users", json=value, headers=headers)
    assert result.status_code == 200, result.text
    return result.json()


def login_as(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["accessToken"]}


def test_login_hash_storage_expiry_and_logout(env):
    c, store, admin, h = env
    token = h["Authorization"].split()[1]
    me = c.get("/api/auth/me", headers=h)
    assert me.status_code == 200 and me.json()["personId"] == admin["personId"]
    assert me.headers["cache-control"] == "no-store"
    assert set(me.json()) == {"id", "username", "personId", "displayName", "permissions"}
    with store.connect() as db:
        account = dict(db.execute("SELECT * FROM identity_accounts").fetchone())
        sessions = json.dumps([dict(r) for r in db.execute("SELECT * FROM identity_sessions")])
    assert account["password_hash"].startswith("$argon2id$")
    assert token not in sessions and token_digest(token) in sessions
    assert PASSWORD not in str(account)
    with store.connect(True) as db:
        db.execute("UPDATE identity_sessions SET expires_at=?", (time.time() - 1,))
    assert c.get("/api/auth/me", headers=h).status_code == 401
    h = login_as(c, "admin")
    assert c.post("/api/auth/logout", headers=h).status_code == 200
    assert c.get("/api/auth/me", headers=h).status_code == 401
    assert c.post("/api/auth/logout", headers=h).status_code == 200
    denied = c.get("/api/auth/me")
    assert denied.status_code == 401
    assert denied.headers["cache-control"] == "no-store"
    assert denied.headers["www-authenticate"] == "Bearer"
    assert c.get("/api/auth/me", headers={"Authorization": "Bearer anything"}).status_code == 401


def test_login_failures_rate_limit_and_validation_redaction(env):
    c, store, _, _ = env
    for i in range(8):
        response = c.post("/api/auth/login", json={"username": "admin", "password": "wrong-secret"})
        assert response.status_code == 401
        assert response.json()["detail"] == "账号或密码错误"
    response = c.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    assert response.status_code == 429
    # Session restart does not discard attempts, and expired attempts no longer block.
    initialize(Store(store.settings))
    assert c.post("/api/auth/login", json={"username": "admin", "password": PASSWORD}).status_code == 429
    with store.connect(True) as db:
        db.execute("UPDATE identity_login_attempts SET attempted_at=0")
    assert c.post("/api/auth/login", json={"username": "admin", "password": PASSWORD}).status_code == 200
    secret = "s" * 300
    assert secret not in c.post("/api/auth/login", json={"username": "admin", "password": secret}).text


def test_unknown_and_disabled_login_same_error(env):
    c, _, _, h = env
    person = create_person(c, h, username="disabled-user", active=False)
    responses = [c.post("/api/auth/login", json={"username": u, "password": PASSWORD}) for u in ("disabled-user", "nonexistent")]
    assert [r.status_code for r in responses] == [401, 401]
    assert responses[0].json() == responses[1].json()


def test_directory_scope_and_http_crud(env):
    c, _, _, h = env
    dep = c.post("/api/admin/departments", json={"name": "研发"}, headers=h).json()
    member = create_person(c, h, username="member-one", departmentId=dep["id"])
    guest = create_person(c, h, "来宾")
    organizer = create_person(c, h, "组织者", username="organizer", role="organizer")
    member_auth, organizer_auth = login_as(c, "member-one"), login_as(c, "organizer")
    directory = c.get("/api/people", headers=member_auth).json()
    assert [p["id"] for p in directory["items"]] == [member["id"]]
    assert [d["id"] for d in directory["departments"]] == [dep["id"]]
    assert set(directory["items"][0]) == {"id", "name", "detail", "departmentId", "departmentName", "active"}
    assert len(c.get("/api/people", headers=organizer_auth).json()["items"]) == 4
    for resource in ("users", "roles", "departments"):
        assert c.get("/api/admin/" + resource, headers=member_auth).status_code == 403
        assert c.get("/api/admin/" + resource).status_code == 401
        assert c.post("/api/admin/" + resource, json={"name": "Forbidden"}, headers=organizer_auth).status_code == 403
        assert c.delete("/api/admin/" + resource + "/any", headers=organizer_auth).status_code == 403
    changed = c.patch("/api/admin/users/" + guest["id"], json={"name": "来宾改名", "detail": "外部", "departmentId": dep["id"]}, headers=h)
    assert changed.status_code == 200 and changed.json()["name"] == "来宾改名"
    assert changed.json()["username"] is None
    assert c.delete("/api/admin/users/" + guest["id"], headers=h).status_code == 200
    assert guest["id"] not in [p["id"] for p in c.get("/api/admin/users", headers=h).json()["items"]]


def test_password_reset_disable_role_change_take_effect_immediately(env):
    c, _, _, h = env
    role = c.post("/api/admin/roles", json={"name": "测试组织者", "permissions": ["record"]}, headers=h).json()
    person = create_person(c, h, username="tester", role=role["id"])
    session = login_as(c, "tester")
    assert "record" in c.get("/api/auth/me", headers=session).json()["permissions"]
    assert c.patch("/api/admin/roles/" + role["id"], json={"permissions": []}, headers=h).status_code == 200
    assert c.get("/api/auth/me", headers=session).json()["permissions"] == []
    new_password = PASSWORD + "updated"
    assert c.patch("/api/admin/users/" + person["id"], json={"password": new_password}, headers=h).status_code == 200
    assert c.get("/api/auth/me", headers=session).status_code == 401
    assert c.post("/api/auth/login", json={"username": "tester", "password": PASSWORD}).status_code == 401
    auth = c.post("/api/auth/login", json={"username": "tester", "password": new_password}).json()
    session = {"Authorization": "Bearer " + auth["accessToken"]}
    assert c.patch("/api/admin/users/" + person["id"], json={"active": False}, headers=h).status_code == 200
    assert c.get("/api/auth/me", headers=session).status_code == 401


def test_last_admin_and_privilege_escalation_are_blocked(env):
    c, _, admin, h = env
    path = "/api/admin/users/" + admin["personId"]
    for patch in ({"active": False}, {"roleId": "organizer"}):
        assert c.patch(path, json=patch, headers=h).status_code == 409
    assert c.delete(path, headers=h).status_code == 409
    assert c.patch("/api/admin/roles/admin", json={"permissions": []}, headers=h).status_code == 409
    role = c.post("/api/admin/roles", json={"name": "用户维护", "permissions": ["users", "roles"]}, headers=h).json()
    user = create_person(c, h, username="user-manager", role=role["id"])
    limited = login_as(c, "user-manager")
    assert c.patch("/api/admin/users/" + user["id"], json={"roleId": "admin"}, headers=limited).status_code == 403
    assert c.patch(path, json={"password": "take-over-password"}, headers=limited).status_code == 403
    assert c.post("/api/admin/roles", json={"name": "升级", "permissions": ["record"]}, headers=limited).status_code == 403
    assert c.delete(path, headers=limited).status_code == 403
    another = create_person(c, h, username="other-admin", role="admin")
    other_auth = login_as(c, "other-admin")
    assert c.patch(path, json={"active": False}, headers=other_auth).status_code == 200
    assert c.get("/api/auth/me", headers=h).status_code == 401
    assert c.delete("/api/admin/users/" + another["id"], headers=other_auth).status_code == 409


def test_departments_prevent_cycles_or_dangling_references(env):
    c, _, _, h = env
    parent = c.post("/api/admin/departments", json={"name": "总部"}, headers=h).json()
    child = c.post("/api/admin/departments", json={"name": "子部门", "parentId": parent["id"]}, headers=h).json()
    assert c.patch("/api/admin/departments/" + parent["id"], json={"parentId": child["id"]}, headers=h).status_code == 409
    assert c.delete("/api/admin/departments/" + parent["id"], headers=h).status_code == 409
    person = create_person(c, h, departmentId=child["id"])
    assert c.delete("/api/admin/departments/" + child["id"], headers=h).status_code == 409
    assert c.patch("/api/admin/users/" + person["id"], json={"departmentId": None}, headers=h).status_code == 200
    assert c.delete("/api/admin/departments/" + child["id"], headers=h).status_code == 200
    assert c.delete("/api/admin/departments/" + parent["id"], headers=h).status_code == 200
    assert c.post("/api/admin/users", json={"name": "错误", "departmentId": "missing"}, headers=h).status_code == 404


def test_roles_duplicates_soft_delete_and_unknown_fields(env):
    c, store, _, h = env
    role = c.post("/api/admin/roles", json={"name": "角色一", "permissions": []}, headers=h).json()
    person = create_person(c, h, username="first-user", role=role["id"])
    assert c.delete("/api/admin/roles/" + role["id"], headers=h).status_code == 409
    assert c.post("/api/admin/users", json={"name": "同名账号", "username": "FIRST-USER", "password": PASSWORD, "roleId": "member"}, headers=h).status_code == 409
    secret = "short-secret"
    error = c.post("/api/admin/users", json={"name": "A", "password": secret}, headers=h)
    assert error.status_code == 422 and secret not in error.text
    assert c.post("/api/admin/users", json={"name": "A", "permissions": ["users"]}, headers=h).status_code == 422
    assert c.patch("/api/admin/users/" + person["id"], json={"name": "  "}, headers=h).status_code == 422
    assert c.delete("/api/admin/users/" + person["id"], headers=h).status_code == 200
    with store.connect() as db:
        assert db.execute("SELECT deleted_at FROM identity_people WHERE id=?", (person["id"],)).fetchone()[0]
    # Even archived accounts keep role references, preserving history.
    assert c.delete("/api/admin/roles/" + role["id"], headers=h).status_code == 409
    empty = c.post("/api/admin/roles", json={"name": "空角色", "permissions": []}, headers=h).json()
    assert c.delete("/api/admin/roles/" + empty["id"], headers=h).status_code == 200


def test_migration_is_atomic_idempotent_and_does_not_change_core_version(env):
    _, store, admin, _ = env
    with store.connect(True) as db:
        db.execute("PRAGMA user_version=42")
    initialize(store)
    with store.connect() as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 42
        assert db.execute("SELECT version FROM feature_schema WHERE module='identity'").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM identity_people").fetchone()[0] == 1
    with pytest.raises(Exception):
        bootstrap(store, "other", PASSWORD, "另一位")
    assert admin["username"] == "admin"


def test_bootstrap_cli_uses_stdin_without_printing_password(tmp_path):
    env = {**os.environ, "YANXU_DATA_DIR": str(tmp_path), "YANXU_STORAGE": "local", "QINIU_DELIVERY_ENABLED": "false"}
    result = subprocess.run([sys.executable, "-m", "yanxu.identity", "--username", "initial-admin", "--name", "管理员", "--password-stdin"], input=PASSWORD + "\n", text=True, capture_output=True, env=env, cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == 0, result.stderr
    assert PASSWORD not in result.stdout + result.stderr
    repeat = subprocess.run([sys.executable, "-m", "yanxu.identity", "--username", "initial-admin", "--name", "管理员", "--password-stdin"], input=PASSWORD + "\n", text=True, capture_output=True, env=env, cwd=Path(__file__).resolve().parents[1])
    assert repeat.returncode == 1 and PASSWORD not in repeat.stderr


def test_failed_migration_rolls_back_without_partial_tables(tmp_path, monkeypatch):
    from yanxu.identity import schema
    import sqlite3
    baseline = Store(Settings(data_dir=tmp_path / "baseline"))
    with baseline.connect() as db:
        core_version = db.execute("PRAGMA user_version").fetchone()[0]
    settings = Settings(data_dir=tmp_path / "failed-migration")
    real_roles = schema.BUILTIN_ROLES
    monkeypatch.setattr(schema, "BUILTIN_ROLES", (real_roles[0], real_roles[0]))
    with pytest.raises(sqlite3.IntegrityError):
        Store(settings)
    with sqlite3.connect(settings.db_path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'identity_%'").fetchall() == []
        assert db.execute("PRAGMA user_version").fetchone()[0] == core_version
    monkeypatch.setattr(schema, "BUILTIN_ROLES", real_roles)
    store = Store(settings)
    initialize(store)
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM identity_people").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM identity_roles").fetchone()[0] == 3



def test_reopen_keeps_sessions_accounts_and_data(env):
    c, store, admin, h = env
    person = create_person(c, h, username="persistent")
    reopened = Store(store.settings)
    initialize(reopened)
    c.app.state.store = reopened
    assert c.get("/api/auth/me", headers=h).json()["id"] == admin["id"]
    assert person["id"] in [p["id"] for p in c.get("/api/people", headers=h).json()["items"]]
    assert login_as(c, "persistent")


def test_extra_credentials_not_echoed_and_invalid_user_patch_is_atomic(env):
    c, store, _, h = env
    person = create_person(c, h, "原姓名")
    bad = c.patch("/api/admin/users/" + person["id"], json={"name": "新姓名", "password": PASSWORD}, headers=h)
    assert bad.status_code == 422 and PASSWORD not in bad.text
    with store.connect() as db:
        assert db.execute("SELECT name FROM identity_people WHERE id=?", (person["id"],)).fetchone()[0] == "原姓名"
    result = c.patch("/api/admin/users/" + person["id"], json={"username": "new-login", "password": PASSWORD, "roleId": "member"}, headers=h)
    assert result.status_code == 200
    assert login_as(c, "new-login")
    assert c.patch("/api/admin/users/" + person["id"], json={"active": None}, headers=h).status_code == 422


def test_expensive_password_work_is_bounded(env):
    from yanxu.identity.auth import PASSWORD_WORK
    c, _, _, _ = env
    assert PASSWORD_WORK.acquire(False)
    assert PASSWORD_WORK.acquire(False)
    try:
        response = c.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
        assert response.status_code == 429 and response.headers["retry-after"] == "1"
    finally:
        PASSWORD_WORK.release()
        PASSWORD_WORK.release()
    assert login_as(c, "admin")


def test_successful_logins_do_not_exhaust_shared_office_ip_budget(env):
    c, _, _, _ = env
    for _ in range(32):
        assert login_as(c, "admin")


def test_organizer_adds_people_without_granting_accounts(env):
    c, store, _, h = env
    create_person(c, h, username="meeting-organizer", role="organizer")
    create_person(c, h, username="regular-member", role="member")
    organizer = login_as(c, "meeting-organizer")
    member = login_as(c, "regular-member")
    for _ in range(2):
        response = c.post("/api/people", json={"name": "同名来宾", "detail": "本次参会"}, headers=organizer)
        assert response.status_code == 200
        data = response.json()
        assert set(data) == {"id", "name", "detail", "departmentId", "departmentName", "active"}
        with store.connect() as db:
            assert db.execute("SELECT 1 FROM identity_accounts WHERE person_id=?", (data["id"],)).fetchone() is None
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM identity_people WHERE name='同名来宾'").fetchone()[0] == 2
    assert c.post("/api/people", json={"name": "不能添加"}, headers=member).status_code == 403
    assert c.post("/api/people", json={"name": "不能添加"}).status_code == 401
    for extra in ({"username":"takeover", "password": PASSWORD, "roleId":"admin"}, {"active": False}, {"departmentId":"forbidden"}):
        response = c.post("/api/people", json={"name": "恶意字段", **extra}, headers=organizer)
        assert response.status_code == 422 and PASSWORD not in response.text
    assert c.get("/api/admin/users", headers=organizer).status_code == 403
