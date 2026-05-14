from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, role: str, extra: Optional[dict] = None) -> str:
    expire = _now_utc() + timedelta(minutes=settings.access_token_ttl_min)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": _now_utc(),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = _now_utc() + timedelta(days=settings.refresh_token_ttl_days)
    payload = {"sub": subject, "type": "refresh", "exp": expire, "iat": _now_utc()}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    secrets_to_try = [settings.jwt_secret]
    if settings.jwt_secret_previous:
        secrets_to_try.append(settings.jwt_secret_previous)
    for secret in secrets_to_try:
        try:
            return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
        except JWTError:
            continue
    return None
