import json
import os
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

SECRET_KEY = os.environ.get("GATEWAY_SECRET_KEY", "change-me-in-production")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _load_users() -> list[dict]:
    """Load users from GATEWAY_USERS JSON env var, or create single user from GATEWAY_USERNAME/PASSWORD."""
    users_json = os.environ.get("GATEWAY_USERS")
    if users_json:
        return json.loads(users_json)

    username = os.environ.get("GATEWAY_USERNAME", "admin")
    password = os.environ.get("GATEWAY_PASSWORD")
    if password:
        return [{"username": username, "password": pwd_context.hash(password)}]

    return [{"username": "admin", "password": pwd_context.hash("admin")}]


# Cache users on first load
_users: list[dict] | None = None


def get_users() -> list[dict]:
    global _users
    if _users is None:
        _users = _load_users()
    return _users


def authenticate(username: str, password: str) -> bool:
    for user in get_users():
        if user["username"] == username:
            return pwd_context.verify(password, user["password"])
    return False


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
