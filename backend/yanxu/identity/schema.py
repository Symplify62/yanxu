"""Identity migrations are isolated from the recording schema and its user_version."""
import json
import time

PERMISSIONS = frozenset({"record", "users", "roles", "departments", "voices"})
BUILTIN_ROLES = (
    ("admin", "管理员", "管理全部人员、权限和声音档案", sorted(PERMISSIONS)),
    ("organizer", "会议组织者", "发起录音并协助参会者登记声音", ["record"]),
    ("member", "成员", "查看和维护本人的声音档案", []),
)


def initialize(store):
    with store.connect(True) as db:
        db.execute("CREATE TABLE IF NOT EXISTS feature_schema(module TEXT PRIMARY KEY, version INTEGER NOT NULL)")
        version = db.execute("SELECT version FROM feature_schema WHERE module='identity'").fetchone()
        if version and version[0] > 1:
            raise RuntimeError("身份数据库版本较新，请使用兼容的服务版本")
        if version:
            return
        statements = (
            """CREATE TABLE identity_departments(id TEXT PRIMARY KEY, name TEXT NOT NULL,
               parent_id TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL)""",
            """CREATE TABLE identity_roles(id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
               description TEXT NOT NULL, permissions TEXT NOT NULL, builtin INTEGER NOT NULL DEFAULT 0,
               created_at REAL NOT NULL, updated_at REAL NOT NULL)""",
            """CREATE TABLE identity_people(id TEXT PRIMARY KEY, name TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
               department_id TEXT, active INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL,
               updated_at REAL NOT NULL, deleted_at REAL)""",
            """CREATE TABLE identity_accounts(id TEXT PRIMARY KEY, person_id TEXT NOT NULL UNIQUE,
               username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role_id TEXT NOT NULL,
               active INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL, updated_at REAL NOT NULL)""",
            """CREATE TABLE identity_sessions(token_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL,
               created_at REAL NOT NULL, expires_at REAL NOT NULL, revoked_at REAL)""",
            "CREATE INDEX identity_session_account ON identity_sessions(account_id)",
            """CREATE TABLE identity_login_attempts(bucket TEXT NOT NULL, attempted_at REAL NOT NULL)""",
            "CREATE INDEX identity_attempt_bucket ON identity_login_attempts(bucket,attempted_at)",
        )
        for statement in statements:
            db.execute(statement)
        now = time.time()
        for role_id, name, description, permissions in BUILTIN_ROLES:
            db.execute("INSERT INTO identity_roles VALUES(?,?,?,?,1,?,?)", (role_id, name, description, json.dumps(permissions), now, now))
        db.execute("INSERT INTO feature_schema VALUES('identity',1)")
