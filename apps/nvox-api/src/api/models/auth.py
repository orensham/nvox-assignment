from pydantic import BaseModel, EmailStr, Field, field_validator
from uuid import UUID
from typing import Dict, Any


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=12)

    @field_validator('password')
    def validate_password_strength(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        return v


class SignupResponse(BaseModel):
    success: bool
    user_id: UUID
    email: str
    message: str
    journey: Dict[str, Any]
