import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

SECRET_KEY = os.environ.get("GATEWAY_SECRET_KEY", "change-me-in-production")
DB_PATH = os.environ.get("GATEWAY_DB_PATH", "data/users.db")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
#  Database
# ============================================================

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create DB directory, tables, and migrate from env vars if first run."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user'
                            CHECK(role IN ('admin', 'user')),
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # Migrate from environment variables on first run
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        _migrate_from_env(conn)

    conn.close()


def _migrate_from_env(conn: sqlite3.Connection):
    """Import users from GATEWAY_USERS / GATEWAY_USERNAME on first boot."""
    users_json = os.environ.get("GATEWAY_USERS")
    users = []
    if users_json:
        users = json.loads(users_json)
    else:
        username = os.environ.get("GATEWAY_USERNAME", "admin")
        password = os.environ.get("GATEWAY_PASSWORD", "admin")
        users = [{"username": username, "password": password}]

    for i, user in enumerate(users):
        role = "admin" if i == 0 else "user"
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (user["username"], pwd_context.hash(user["password"]), role),
        )
    conn.commit()


# ============================================================
#  User CRUD
# ============================================================

def get_all_users() -> list[dict]:
    """Return all users (password excluded)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, role, is_active, created_at, updated_at "
        "FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, role, is_active, created_at, updated_at "
        "FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    """Full record including password hash — for auth use only."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def authenticate(username: str, password: str) -> dict | None:
    """Verify credentials. Returns user info (without password) or None."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND is_active = 1",
        (username,),
    ).fetchone()
    conn.close()
    if row and pwd_context.verify(password, row["password"]):
        return {"id": row["id"], "username": row["username"], "role": row["role"]}
    return None


def create_user(username: str, password: str, role: str = "user") -> dict:
    conn = get_db()
    hashed = pwd_context.hash(password)
    cursor = conn.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        (username, hashed, role),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return get_user_by_id(user_id)


def update_user(user_id: int, **kwargs) -> dict | None:
    """Update one or more editable fields on a user."""
    allowed = {"username", "role", "is_active"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return get_user_by_id(user_id)

    updates["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]

    conn = get_db()
    conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    conn = get_db()
    cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def update_password(user_id: int, new_password: str) -> bool:
    hashed = pwd_context.hash(new_password)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_db()
    cursor = conn.execute(
        "UPDATE users SET password = ?, updated_at = ? WHERE id = ?",
        (hashed, now, user_id),
    )
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def count_admins() -> int:
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    ).fetchone()[0]
    conn.close()
    return count


# ============================================================
#  JWT
# ============================================================

def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
