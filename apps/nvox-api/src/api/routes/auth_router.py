from fastapi import APIRouter, Depends, status
from nvox_common.db.nvox_db_client import NvoxDBClient
from dependencies.db import get_db_client
from api.models.auth import SignupRequest, SignupResponse
from uuid import uuid4
from datetime import datetime
import hashlib


router = APIRouter()


def hash_email(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
        request: SignupRequest,
        db_client: NvoxDBClient = Depends(get_db_client),
) -> SignupResponse:
    email_hash = hash_email(request.email.lower())

    return SignupResponse(
        success=True,
        user_id=uuid4(),
        email=email_hash,
        message="Account created successfully",
        journey={
                "current_stage": "REFERRAL",
                "started_at": datetime.utcnow().isoformat()
        })
