from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_me_in_production_use_strong_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(user_id: UUID, email_hash: str, expires_delta: Optional[timedelta] = None) -> tuple[str, str, datetime]:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta
    jti = str(uuid4())

    to_encode = {
        "sub": str(user_id),  # Subject: user ID
        "email_hash": email_hash,  # Hashed email, not plain text
        "jti": jti,  # JWT ID for token identification
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, jti, expire


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Token is invalid, expired, or tampered with
        return None


def get_user_id_from_token(token: str) -> Optional[UUID]:
    payload = decode_access_token(token)
    if payload is None:
        return None

    try:
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        return UUID(user_id_str)
    except (ValueError, AttributeError):
        return None


def get_token_expiration(token: str) -> Optional[datetime]:
    payload = decode_access_token(token)
    if payload is None:
        return None

    exp_timestamp = payload.get("exp")
    if exp_timestamp is None:
        return None

    return datetime.utcfromtimestamp(exp_timestamp)


def get_jti_from_token(token: str) -> Optional[str]:
    payload = decode_access_token(token)
    if payload is None:
        return None

    return payload.get("jti")
