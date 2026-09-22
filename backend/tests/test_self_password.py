"""Self-service password changes use the real HTTP/router/database boundary."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import time

import pytest
from fastapi.testclient import TestClient

from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.identity import auth
from yanxu.identity.__main__ import bootstrap

PASSWORD = "initial-user-password"
NEW_PASSWORD = "123456"
PATH = "/api/auth/password"


def login(client, username, password=PASSWORD):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["accessToken"]}


def body(old=PASSWORD, new=NEW_PASSWORD):
    return {"oldPassword": old, "newPassword": new, "confirmPassword": new}


@pytest.fixture
def env(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    store, client = app.state.store, TestClient(app)
    bootstrap(store, "admin", PASSWORD, "管理员")
    admin = login(client, "admin")
    people = []
    for username in ("member-one", "member-two"):
        response = client.post("/api/admin/users", headers=admin, json={
            "name": username, "username": username, "password": PASSWORD, "roleId": "member",
        })
        assert response.status_code == 200, response.text
        people.append(response.json())
    return client, store, admin, people, login(client, "member-one")


def stored_hash(store, account_id):
    with store.connect() as db:
        return db.execute("SELECT password_hash FROM identity_accounts WHERE id=?", (account_id,)).fetchone()[0]


def test_member_changes_own_password_and_revokes_every_session_only_for_self(env):
    client, store, admin, people, session = env
    another_session = login(client, "member-one")
    other_user = login(client, "member-two")
    before = [stored_hash(store, p["accountId"]) for p in people]
    assert client.get("/api/auth/me", headers=session).json()["permissions"] == []
    assert client.get("/api/admin/users", headers=session).status_code == 403

    response = client.post(PATH, headers=session, json=body())
    assert response.status_code == 200 and response.json() == {"ok": True}
    assert response.headers["cache-control"] == "no-store"
    for previous in (session, another_session):
        assert client.get("/api/auth/me", headers=previous).status_code == 401
        assert client.post(PATH, headers=previous, json=body()).status_code == 401
    for retained in (admin, other_user):
        assert client.get("/api/auth/me", headers=retained).status_code == 200
    assert client.post("/api/auth/login", json={"username": "member-one", "password": PASSWORD}).status_code == 401
    assert login(client, "member-one", NEW_PASSWORD)
    assert login(client, "member-two")
    after = [stored_hash(store, p["accountId"]) for p in people]
    assert after[0] != before[0] and after[0].startswith("$argon2id$")
    assert after[1] == before[1]
    assert PASSWORD not in after[0] and NEW_PASSWORD not in after[0]
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM identity_login_attempts WHERE bucket LIKE 'password:%'").fetchone()[0] == 0


def test_wrong_old_password_is_a_recoverable_error_without_any_account_change(env):
    client, store, _, people, session = env
    before = stored_hash(store, people[0]["accountId"])
    response = client.post(PATH, headers=session, json=body(old="wrong-old-secret"))
    assert response.status_code == 400 and response.json() == {"detail": "旧密码不正确"}
    assert response.headers["cache-control"] == "no-store"
    assert "wrong-old-secret" not in response.text and NEW_PASSWORD not in response.text
    assert client.get("/api/auth/me", headers=session).status_code == 200
    assert stored_hash(store, people[0]["accountId"]) == before
    assert login(client, "member-one")
    assert client.post(PATH, headers=session, json=body()).status_code == 200


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}], ids=["anonymous", "invalid-token"])
def test_authentication_is_required(env, headers):
    client, store, _, people, _ = env
    before = stored_hash(store, people[0]["accountId"])
    response = client.post(PATH, headers=headers, json=body())
    assert response.status_code == 401 and response.headers["www-authenticate"] == "Bearer"
    assert stored_hash(store, people[0]["accountId"]) == before


@pytest.mark.parametrize("changes", [
    {"newPassword": "12345", "confirmPassword": "12345"},
    {"newPassword": "x" * 257, "confirmPassword": "x" * 257},
    {"oldPassword": "x" * 257},
    {"oldPassword": ""},
    {"confirmPassword": "mismatch-secret"},
    {"userId": "another-account"},
], ids=["short", "long", "long-old", "empty-old", "confirmation", "cannot-target-another-account"])
def test_invalid_input_does_not_echo_passwords_or_consume_attempts(env, changes):
    client, store, _, people, session = env
    before = stored_hash(store, people[0]["accountId"])
    request_body = {**body(), **changes}
    response = client.post(PATH, headers=session, json=request_body)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    for value in request_body.values():
        if value:
            assert value not in response.text
    assert client.get("/api/auth/me", headers=session).status_code == 200
    assert stored_hash(store, people[0]["accountId"]) == before
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM identity_login_attempts WHERE bucket LIKE 'password:%'").fetchone()[0] == 0


@pytest.mark.parametrize("password", ["abcdef", "!@#$%^", "a" * 256, PASSWORD],
                         ids=["letters-only", "symbols-only", "maximum", "same-as-old"])
def test_existing_length_rule_and_no_added_password_composition_rule(env, password):
    client, _, _, _, session = env
    assert client.post(PATH, headers=session, json=body(new=password)).status_code == 200
    assert client.get("/api/auth/me", headers=session).status_code == 401
    assert login(client, "member-one", password)


def test_old_password_attempt_limit_survives_new_sessions_restart_and_is_account_scoped(env):
    client, store, _, _, session = env
    second = login(client, "member-one")
    for attempt in range(8):
        response = client.post(PATH, headers=(session, second)[attempt % 2], json=body(old="wrong-secret"))
        assert response.status_code == 400
    # Normal login does not clear this independent password-change bucket.
    fresh = login(client, "member-one")
    reopened = TestClient(create_app(store.settings))
    response = reopened.post(PATH, headers=fresh, json=body())
    assert response.status_code == 429 and response.headers["retry-after"] == "900"
    assert reopened.get("/api/auth/me", headers=fresh).status_code == 200
    other = login(reopened, "member-two")
    assert reopened.post(PATH, headers=other, json=body()).status_code == 200
    with store.connect(True) as db:
        db.execute("UPDATE identity_login_attempts SET attempted_at=? WHERE bucket LIKE 'password:%'", (time.time() - 901,))
    assert reopened.post(PATH, headers=fresh, json=body()).status_code == 200


@pytest.mark.parametrize("action", ["logout", "reset", "disable", "expire", "hash-changed"],
                         ids=["concurrent-logout", "concurrent-admin-reset", "concurrent-disable", "expired-during-verification", "changed-password-without-revocation"])
def test_concurrent_invalidations_cannot_be_overwritten_after_password_verification(env, monkeypatch, action):
    client, store, admin, people, session = env
    account_id = people[0]["accountId"]
    before = stored_hash(store, account_id)
    started, release = Event(), Event()
    original_verify = auth.PASSWORDS.verify

    def held_verify(password, encoded):
        result = original_verify(password, encoded)
        started.set()
        assert release.wait(10), "concurrent action did not finish"
        return result

    monkeypatch.setattr(auth.PASSWORDS, "verify", held_verify)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, PATH, headers=session, json=body())
        try:
            assert started.wait(10), "password verification did not begin"
            if action == "logout":
                assert client.post("/api/auth/logout", headers=session).status_code == 200
            elif action in ("reset", "disable"):
                patch = {"password": "654321"} if action == "reset" else {"active": False}
                assert client.patch("/api/admin/users/" + people[0]["id"], headers=admin, json=patch).status_code == 200
            elif action == "expire":
                with store.connect(True) as db:
                    db.execute("UPDATE identity_sessions SET expires_at=? WHERE account_id=?", (time.time() - 1, account_id))
            else:
                replacement = auth.hash_password("654321")
                with store.connect(True) as db:
                    db.execute("UPDATE identity_accounts SET password_hash=? WHERE id=?", (replacement, account_id))
            concurrent_hash = stored_hash(store, account_id)
        finally:
            release.set()
        response = pending.result(timeout=10)
    assert response.status_code == 401
    assert stored_hash(store, account_id) == concurrent_hash
    if action in ("reset", "hash-changed"):
        assert concurrent_hash != before and original_verify("654321", concurrent_hash)
    else:
        assert concurrent_hash == before
    assert not original_verify(NEW_PASSWORD, concurrent_hash)


def test_two_simultaneous_password_changes_have_exactly_one_winner(env, monkeypatch):
    client, store, _, people, session = env
    second_session = login(client, "member-one")
    both_verified = Barrier(2)
    original_verify = auth.PASSWORDS.verify

    def held_verify(password, encoded):
        result = original_verify(password, encoded)
        both_verified.wait(timeout=10)
        return result

    monkeypatch.setattr(auth.PASSWORDS, "verify", held_verify)
    candidates = ("111111", "222222")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, PATH, headers=h, json=body(new=p))
                   for h, p in zip((session, second_session), candidates)]
        responses = [future.result(timeout=15) for future in futures]
    assert sorted(response.status_code for response in responses) == [200, 401]
    encoded = stored_hash(store, people[0]["accountId"])
    for candidate, response in zip(candidates, responses):
        assert original_verify(candidate, encoded) == (response.status_code == 200)
    for old_session in (session, second_session):
        assert client.get("/api/auth/me", headers=old_session).status_code == 401


def test_failed_commit_rolls_back_password_and_session_changes_together(env, monkeypatch):
    client, store, _, people, session = env
    before = stored_hash(store, people[0]["accountId"])
    original_revoke = auth.revoke_account_sessions

    def failed_revoke(db, account_id):
        original_revoke(db, account_id)
        raise RuntimeError("injected write failure")

    monkeypatch.setattr(auth, "revoke_account_sessions", failed_revoke)
    with pytest.raises(RuntimeError, match="injected write failure"):
        client.post(PATH, headers=session, json=body())
    assert stored_hash(store, people[0]["accountId"]) == before
    assert client.get("/api/auth/me", headers=session).status_code == 200
    assert login(client, "member-one")


def test_self_service_uses_existing_password_work_concurrency_bound(env):
    client, store, _, people, session = env
    before = stored_hash(store, people[0]["accountId"])
    assert auth.PASSWORD_WORK.acquire(False)
    assert auth.PASSWORD_WORK.acquire(False)
    try:
        response = client.post(PATH, headers=session, json=body())
        assert response.status_code == 429 and response.headers["retry-after"] == "1"
    finally:
        auth.PASSWORD_WORK.release()
        auth.PASSWORD_WORK.release()
    assert stored_hash(store, people[0]["accountId"]) == before
    assert client.get("/api/auth/me", headers=session).status_code == 200
    assert client.post(PATH, headers=session, json=body()).status_code == 200
