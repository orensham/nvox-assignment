from fastapi import APIRouter, Depends, status, HTTPException
from api.models.auth import SignupRequest, SignupResponse, LoginRequest, LoginResponse, LogoutResponse, TokenData
from repositories.user_repository import UserRepository
from repositories.session_repository import SessionRepository
from dependencies.repositories import get_user_repository, get_session_repository
from dependencies.auth import get_current_user
from utils.hashing import hash_email, hash_password, verify_password
from utils.jwt import create_access_token, get_jti_from_token, ACCESS_TOKEN_EXPIRE_MINUTES
from uuid import uuid4
from datetime import datetime


router = APIRouter()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
        request: SignupRequest,
        user_repository: UserRepository = Depends(get_user_repository),
) -> SignupResponse:
    email_hash = hash_email(request.email.lower())
    if await user_repository.user_exists_by_email_hash(email_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    password_hash = hash_password(request.password)
    user_id = uuid4()
    journey_started_at = datetime.utcnow()

    await user_repository.create_user(
        user_id=user_id,
        email_hash=email_hash,
        password_hash=password_hash,
        journey_stage="REFERRAL",
        journey_started_at=journey_started_at
    )

    return SignupResponse(
        success=True,
        user_id=user_id,
        email=email_hash,
        message="Account created successfully",
        journey={
                "current_stage": "REFERRAL",
                "started_at": journey_started_at.isoformat()
        })


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
        request: LoginRequest,
        user_repository: UserRepository = Depends(get_user_repository),
        session_repository: SessionRepository = Depends(get_session_repository),
) -> LoginResponse:
    email_hash = hash_email(request.email.lower())
    user = await user_repository.get_user_by_email_hash(email_hash)

    dummy_hash = "$2b$12$dummy.hash.to.prevent.timing.attack.00000000000000000000000000000000000000000000"
    password_hash = user["password_hash"] if user else dummy_hash
    is_valid = verify_password(request.password, password_hash)

    if not is_valid or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token, jti, expires_at = create_access_token(
        user_id=user["id"],
        email_hash=email_hash
    )

    await session_repository.create_session(
        user_id=user["id"],
        token_jti=jti,
        expires_at=expires_at
    )

    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user["id"],
        message="Login successful"
    )


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
        current_user: TokenData = Depends(get_current_user),
        session_repository: SessionRepository = Depends(get_session_repository),
) -> LogoutResponse:
    revoked_count = await session_repository.revoke_all_user_sessions(current_user.user_id)

    if revoked_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active session found"
        )

    return LogoutResponse(
        success=True,
        message="Logged out successfully"
    )
