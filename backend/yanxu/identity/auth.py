"""Password authentication and revocable opaque sessions. No identity is inferred from voice."""
import hashlib
import json
import re
import secrets
import time
from contextlib import contextmanager
from threading import BoundedSemaphore

from fastapi import HTTPException, Request
from pwdlib import PasswordHash

PASSWORDS = PasswordHash.recommended()
# Unknown users still pay the same password verification cost.
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))
WINDOW_SECONDS = 15 * 60
PASSWORD_WORK = BoundedSemaphore(2)


@contextmanager
def password_work():
    # Argon2 intentionally uses memory; bound concurrent operations on small servers.
    if not PASSWORD_WORK.acquire(blocking=False):
        raise HTTPException(429, "账号服务繁忙，请稍后重试", headers={"Retry-After": "1"})
    try:
        yield
    finally:
        PASSWORD_WORK.release()


def hash_password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 256:
        raise HTTPException(422, "密码须为12至256个字符")
    with password_work():
        return PASSWORDS.hash(value)


def normalize_username(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._@-]{3,80}", value.strip()):
        raise HTTPException(422, "账号须为3至80位字母、数字或 . _ @ -")
    return value.strip().lower()


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def enabled(request):
    if not getattr(request.app.state.settings, "identity_enabled", True):
        raise HTTPException(503, "账号服务未启用")


def bearer_token(request):
    header = request.headers.get("authorization", "")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", parts[1]):
        raise HTTPException(401, "请登录", headers={"WWW-Authenticate": "Bearer"})
    return parts[1]


ACCOUNT_SELECT = """SELECT a.id,a.username,a.person_id,a.password_hash,a.role_id,a.active AS account_active,
 p.name,p.active AS person_active,p.deleted_at,r.permissions FROM identity_accounts a
 JOIN identity_people p ON p.id=a.person_id JOIN identity_roles r ON r.id=a.role_id"""


def principal(row):
    return {"id": row["id"], "username": row["username"], "personId": row["person_id"],
            "displayName": row["name"], "permissions": json.loads(row["permissions"])}


def current_account(request: Request):
    enabled(request)
    digest = token_digest(bearer_token(request))
    with request.app.state.store.connect() as db:
        row = db.execute(ACCOUNT_SELECT + """ JOIN identity_sessions s ON s.account_id=a.id
            WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>?
            AND a.active=1 AND p.active=1 AND p.deleted_at IS NULL""", (digest, time.time())).fetchone()
    if row is None:
        raise HTTPException(401, "登录已失效，请重新登录", headers={"WWW-Authenticate": "Bearer"})
    return principal(row)


def require_permission(request: Request, permission):
    account = current_account(request)
    if permission not in account["permissions"]:
        raise HTTPException(403, "没有此操作权限")
    return account


def login(store, username, password, address, hours):
    username = normalize_username(username)
    now = time.time()
    buckets = [("name:" + token_digest(username), 8), ("ip:" + token_digest(address), 30)]
    # Reserve attempts before expensive hashing. The counter survives process restarts.
    with store.connect(True) as db:
        db.execute("DELETE FROM identity_login_attempts WHERE attempted_at<?", (now - WINDOW_SECONDS,))
        for bucket, maximum in buckets:
            count = db.execute("SELECT count(*) FROM identity_login_attempts WHERE bucket=?", (bucket,)).fetchone()[0]
            if count >= maximum:
                raise HTTPException(429, "登录尝试过多，请稍后重试", headers={"Retry-After": str(WINDOW_SECONDS)})
        for bucket, _ in buckets:
            db.execute("INSERT INTO identity_login_attempts VALUES(?,?)", (bucket, now))
        row = db.execute(ACCOUNT_SELECT + " WHERE a.username=?", (username,)).fetchone()
    with password_work():
        valid = PASSWORDS.verify(password, row["password_hash"] if row else DUMMY_HASH)
    if not valid or row is None or not row["account_active"] or not row["person_active"] or row["deleted_at"]:
        raise HTTPException(401, "账号或密码错误")
    token = secrets.token_urlsafe(32)
    expires = now + max(1, min(float(hours), 24 * 30)) * 3600
    # Recheck after hashing: a concurrent reset/disable must not yield a valid session.
    with store.connect(True) as db:
        current = db.execute(ACCOUNT_SELECT + " WHERE a.id=?", (row["id"],)).fetchone()
        if not current or current["password_hash"] != row["password_hash"] or not current["account_active"] or not current["person_active"] or current["deleted_at"]:
            raise HTTPException(401, "账号或密码错误")
        db.execute("DELETE FROM identity_login_attempts WHERE bucket=?", (buckets[0][0],))
        # Successful users behind one office NAT must not exhaust the IP failure budget.
        db.execute("DELETE FROM identity_login_attempts WHERE rowid=(SELECT rowid FROM identity_login_attempts WHERE bucket=? AND attempted_at=? LIMIT 1)", (buckets[1][0], now))
        db.execute("DELETE FROM identity_sessions WHERE expires_at<?", (now,))
        db.execute("INSERT INTO identity_sessions VALUES(?,?,?,?,NULL)", (token_digest(token), row["id"], now, expires))
    return {"accessToken": token, "expiresAt": expires, "account": principal(current)}


def revoke_account_sessions(db, account_id):
    db.execute("UPDATE identity_sessions SET revoked_at=? WHERE account_id=? AND revoked_at IS NULL", (time.time(), account_id))
