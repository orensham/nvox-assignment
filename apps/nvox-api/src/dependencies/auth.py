from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID
from api.models.auth import TokenData
from utils.jwt import decode_access_token, get_user_id_from_token, get_jti_from_token
from repositories.session_repository import SessionRepository
from dependencies.repositories import get_session_repository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session_repository: SessionRepository = Depends(get_session_repository)
) -> TokenData:
    token = credentials.credentials

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    email_hash = payload.get("email_hash")
    jti = payload.get("jti")

    if not user_id_str or not email_hash or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_active = await session_repository.is_session_active(jti)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenData(user_id=user_id, email_hash=email_hash)


async def get_current_user_id(
    current_user: TokenData = Depends(get_current_user)
) -> UUID:
    return current_user.user_id
