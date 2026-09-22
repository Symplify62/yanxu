"""Local administrative bootstrap: no public registration and no default password."""
import argparse
import os
import sys

from fastapi import HTTPException
from . import initialize
from .directory import transaction
from .models import UserCreate
from ..config import Settings
from ..store import Store


def bootstrap(store, username, password, name):
    """Create the first administrator once; reruns must not reset a live password."""
    initialize(store)
    from .auth import hash_password, normalize_username
    import time
    import uuid

    username = normalize_username(username)
    # Validate before taking the SQLite write lock.
    value = UserCreate(name=name, username=username, password=password, roleId="admin")
    password_hash = hash_password(value.password)
    with transaction(store) as db:
        if db.execute("SELECT 1 FROM identity_accounts LIMIT 1").fetchone():
            raise HTTPException(409, "已有登录账号，请通过管理员进行维护；初始化不会覆盖现有密码")
        person_id, account_id, now = str(uuid.uuid4()), str(uuid.uuid4()), time.time()
        db.execute("INSERT INTO identity_people VALUES(?,?,?,NULL,1,?,?,NULL)", (person_id, value.name.strip(), "", now, now))
        db.execute("INSERT INTO identity_accounts VALUES(?,?,?,?,?,1,?,?)", (account_id, person_id, username, password_hash, "admin", now, now))
    return {"id": account_id, "personId": person_id, "username": username}


def main():
    parser = argparse.ArgumentParser(description="初始化言序首位管理员；密码仅从标准输入或环境变量读取")
    parser.add_argument("--username", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else os.environ.get("YANXU_BOOTSTRAP_PASSWORD", "")
    if not password:
        parser.error("请通过 --password-stdin 或 YANXU_BOOTSTRAP_PASSWORD 提供密码")
    try:
        result = bootstrap(Store(Settings.load()), args.username, password, args.name)
    except HTTPException as error:
        print(error.detail, file=sys.stderr)
        return 1
    except ValueError:
        print("初始化参数无效，请检查账号、姓名和密码长度", file=sys.stderr)
        return 1
    print("管理员已初始化：" + result["username"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
