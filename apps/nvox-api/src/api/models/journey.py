from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional
from uuid import UUID


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


class AnswerRequest(BaseModel):
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
    success: bool
    answer_saved: bool = Field(..., description="Whether the answer was successfully saved")
    transitioned: bool = Field(..., description="Whether a stage transition occurred")
    current_stage: str = Field(..., description="Current stage after processing the answer")
    previous_stage: Optional[str] = Field(None, description="Previous stage (if transition occurred)")
    questions: List[Dict[str, Any]] = Field(..., description="Questions for current stage")
    transition_reason: Optional[str] = Field(None, description="Reason for transition (if any)")
    message: str


class DeleteUserResponse(BaseModel):
    success: bool
    user_id: UUID
    anonymized: bool = Field(..., description="Whether user data was anonymized")
    message: str


class StageHistoryItem(BaseModel):
    stage_id: str = Field(..., description="ID of the stage")
    stage_name: str = Field(..., description="Human-readable stage name")
    visit_number: int = Field(..., description="Visit number for this stage")
    entered_at: str = Field(..., description="ISO timestamp when stage was entered")
    exited_at: Optional[str] = Field(None, description="ISO timestamp when stage was exited")
    is_current: bool = Field(..., description="Whether this is the current stage")
    questions_answered: int = Field(..., description="Number of questions answered in this stage")


class JourneyHistoryResponse(BaseModel):
    success: bool
    user_id: UUID
    stages: List[StageHistoryItem] = Field(..., description="List of stages visited in chronological order")
    total_stages_visited: int = Field(..., description="Total number of stages visited")
    journey_started_at: str = Field(..., description="ISO timestamp when journey started")
    message: Optional[str] = None


class StageDetailsResponse(BaseModel):
    success: bool
    stage_id: str = Field(..., description="ID of the stage")
    stage_name: str = Field(..., description="Human-readable stage name")
    visit_number: int = Field(..., description="Visit number for this stage")
    questions: List[Dict[str, Any]] = Field(..., description="Questions with answers for this stage")
    entered_at: str = Field(..., description="ISO timestamp when stage was entered")
    exited_at: Optional[str] = Field(None, description="ISO timestamp when stage was exited")
    is_current: bool = Field(..., description="Whether this is the current stage")
    message: Optional[str] = None
