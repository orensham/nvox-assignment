from fastapi import APIRouter, Depends, status, HTTPException
from api.models.auth import SignupRequest, SignupResponse
from repositories.user_repository import UserRepository
from dependencies.repositories import get_user_repository
from utils.hashing import hash_email, hash_password
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
