from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from app.core.config import get_settings

settings = get_settings()

JWT_SECRET_KEY: str = (
    getattr(settings,"jwt_secret",None)
    or getattr(settings,"secret_key",None)
    or "legaldrishti-dev-secret-key-change-in-production"
)

JWT_ALGORITHM: str = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.jwt_access_token_expire_minutes or 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

def create_access_token(
        subject: str | int,
        extra_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
  
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])