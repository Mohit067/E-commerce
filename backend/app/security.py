"""Password hashing + JWT helpers (no hard-coded secrets; via Settings)."""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from .config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _encode(payload: dict[str, Any], secret: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    data = {**payload, "iat": now, "exp": now + expires}
    return jwt.encode(data, secret, algorithm=settings.algorithm)


def create_access_token(sub: str, role: str = "customer") -> str:
    return _encode({"sub": sub, "role": role, "type": "access"},
                   settings.secret_key, timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(sub: str) -> str:
    return _encode({"sub": sub, "type": "refresh"},
                   settings.refresh_secret_key, timedelta(days=settings.refresh_token_expire_days))


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def decode_refresh_token(token: str) -> dict[str, Any]:
    data = jwt.decode(token, settings.refresh_secret_key, algorithms=[settings.algorithm])
    if data.get("type") != "refresh":
        raise jwt.InvalidTokenError("not a refresh token")
    return data
