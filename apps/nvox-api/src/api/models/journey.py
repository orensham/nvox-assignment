"""
Journey API Models

Pydantic models for journey-related API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional
from uuid import UUID


# ==============================================================================
# GET /v1/journey/current
# ==============================================================================

class JourneyStateResponse(BaseModel):
    """Response model for GET /v1/journey/current"""
    success: bool
    current_stage: str = Field(..., description="ID of the current stage")
    stage_name: str = Field(..., description="Human-readable stage name")
    visit_number: int = Field(..., description="Number of times user has visited this stage")
    questions: List[Dict[str, Any]] = Field(..., description="Questions for this stage")
    journey_started_at: str = Field(..., description="ISO timestamp when journey started")
    last_updated_at: str = Field(..., description="ISO timestamp of last update")
    message: Optional[str] = None


# ==============================================================================
# POST /v1/journey/answer
# ==============================================================================

class AnswerRequest(BaseModel):
    """Request model for POST /v1/journey/answer"""
    question_id: str = Field(..., description="ID of the question being answered")
    answer_value: Any = Field(..., description="The answer value (type depends on question)")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "question_id": "ref_karnofsky",
                    "answer_value": 75
                }
            ]
        }


class AnswerResponse(BaseModel):
    """Response model for POST /v1/journey/answer"""
    success: bool
    answer_saved: bool = Field(..., description="Whether the answer was successfully saved")
    transitioned: bool = Field(..., description="Whether a stage transition occurred")
    current_stage: str = Field(..., description="Current stage after processing the answer")
    previous_stage: Optional[str] = Field(None, description="Previous stage (if transition occurred)")
    next_questions: List[Dict[str, Any]] = Field(..., description="Questions for current stage")
    transition_reason: Optional[str] = Field(None, description="Reason for transition (if any)")
    message: str


# ==============================================================================
# DELETE /v1/user
# ==============================================================================

class DeleteUserResponse(BaseModel):
    """Response model for DELETE /v1/user"""
    success: bool
    user_id: UUID
    anonymized: bool = Field(..., description="Whether user data was anonymized")
    message: str
