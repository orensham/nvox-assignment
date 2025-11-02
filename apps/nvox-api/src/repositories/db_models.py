from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class UserDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email_hash: str
    password_hash: str
    journey_stage: str
    journey_started_at: datetime
    created_at: datetime
    updated_at: datetime


class SessionDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    token_jti: str
    expires_at: datetime
    created_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool


class UserJourneyStateDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    current_stage_id: str
    visit_number: int = Field(ge=1)
    journey_started_at: datetime
    last_updated_at: datetime
    created_at: datetime


class UserAnswerDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    stage_id: str
    question_id: str
    answer_value: Any
    visit_number: int = Field(ge=1)
    answered_at: datetime
    version: int = Field(ge=1)
    is_current: bool


class StageTransitionDB(BaseModel):
    """Represents a row from the stage_transitions table."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    from_stage_id: Optional[str] = None
    to_stage_id: str
    from_visit_number: Optional[int] = Field(None, ge=1)
    to_visit_number: int = Field(ge=1)
    transition_reason: Optional[str] = None
    matched_rule_id: Optional[str] = None
    matched_question_id: Optional[str] = None
    matched_answer_value: Optional[Any] = None
    transitioned_at: datetime


class UserJourneyPathDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    stage_id: str
    visit_number: int = Field(ge=1)
    entered_at: datetime
    exited_at: Optional[datetime] = None
    is_current: bool


def record_to_model(record: Any, model_class: type[BaseModel]) -> BaseModel:
    if record is None:
        raise ValueError("Cannot convert None record to model")

    return model_class(**dict(record))


def records_to_models(records: list[Any], model_class: type[BaseModel]) -> list[BaseModel]:
    return [record_to_model(record, model_class) for record in records]


def optional_record_to_model(
    record: Any | None,
    model_class: type[BaseModel]
) -> BaseModel | None:
    if record is None:
        return None

    return record_to_model(record, model_class)
