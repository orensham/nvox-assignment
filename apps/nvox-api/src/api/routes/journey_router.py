"""
Journey Router

API endpoints for journey tracking and management:
- GET /v1/journey/current - Get current journey state
- POST /v1/journey/answer - Submit answer and advance journey
- DELETE /v1/user - Anonymize user data
"""

from fastapi import APIRouter, Depends, status, HTTPException
from api.models.journey import (
    JourneyStateResponse,
    AnswerRequest,
    AnswerResponse,
    DeleteUserResponse
)
from repositories.journey_repository import JourneyRepository
from repositories.user_repository import UserRepository
from dependencies.repositories import get_journey_repository, get_user_repository
from dependencies.auth import get_current_user
from api.models.auth import TokenData
from journey.routing_engine import get_routing_engine
from utils.hashing import hash_email
import json


router = APIRouter()


@router.get("/journey/current", response_model=JourneyStateResponse, status_code=status.HTTP_200_OK)
async def get_current_journey(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> JourneyStateResponse:
    """
    Get the current journey state for the authenticated user.

    Returns:
        - Current stage information
        - Questions for the current stage
        - Journey metadata (started_at, visit_number, etc.)
    """
    # Get journey state from database
    journey_state = await journey_repository.get_user_journey_state(current_user.user_id)

    if not journey_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey state not found. Please contact support."
        )

    # Get routing engine and stage info
    engine = get_routing_engine()
    stage_info = engine.get_stage_info(journey_state["current_stage_id"])

    if not stage_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid stage: {journey_state['current_stage_id']}"
        )

    return JourneyStateResponse(
        success=True,
        current_stage=journey_state["current_stage_id"],
        stage_name=stage_info["name"],
        visit_number=journey_state["visit_number"],
        questions=stage_info["questions"],
        journey_started_at=journey_state["journey_started_at"].isoformat(),
        last_updated_at=journey_state["last_updated_at"].isoformat(),
        message="Journey state retrieved successfully"
    )


@router.post("/journey/answer", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
async def submit_answer(
    request: AnswerRequest,
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> AnswerResponse:
    """
    Submit an answer to a question in the current stage.

    Process:
    1. Validate answer against question constraints
    2. Save answer to database
    3. Evaluate routing rules to determine if stage transition should occur
    4. If transition: update state, record transition, enter new stage
    5. Return current state and next questions
    """
    # Get current journey state
    journey_state = await journey_repository.get_user_journey_state(current_user.user_id)

    if not journey_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey state not found"
        )

    current_stage_id = journey_state["current_stage_id"]
    current_visit_number = journey_state["visit_number"]

    # Get routing engine
    engine = get_routing_engine()

    # Validate the answer
    is_valid, error_message = engine.validate_answer(
        current_stage_id,
        request.question_id,
        request.answer_value
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_message
        )

    # Save the answer
    await journey_repository.save_answer(
        user_id=current_user.user_id,
        stage_id=current_stage_id,
        question_id=request.question_id,
        answer_value=request.answer_value,
        visit_number=current_visit_number
    )

    # Determine if we should transition to a new stage
    transition_decision = engine.should_transition(
        current_stage_id,
        request.question_id,
        request.answer_value
    )

    if transition_decision.should_transition:
        # Stage transition required
        next_stage_id = transition_decision.next_stage

        # Calculate visit number for next stage
        next_visit_number = await journey_repository.get_stage_visit_count(
            current_user.user_id,
            next_stage_id
        ) + 1

        # Record the transition
        await journey_repository.record_transition(
            user_id=current_user.user_id,
            from_stage_id=current_stage_id,
            to_stage_id=next_stage_id,
            from_visit_number=current_visit_number,
            to_visit_number=next_visit_number,
            transition_reason=transition_decision.reason,
            matched_rule_id=transition_decision.matched_rule.get_rule_id() if transition_decision.matched_rule else None,
            matched_question_id=request.question_id,
            matched_answer_value=request.answer_value
        )

        # Update journey state
        await journey_repository.update_journey_stage(
            user_id=current_user.user_id,
            new_stage_id=next_stage_id,
            new_visit_number=next_visit_number
        )

        # Enter the new stage in journey path
        await journey_repository.enter_stage(
            user_id=current_user.user_id,
            stage_id=next_stage_id,
            visit_number=next_visit_number
        )

        # Get questions for the new stage
        next_questions = engine.get_stage_questions(next_stage_id)

        return AnswerResponse(
            success=True,
            answer_saved=True,
            transitioned=True,
            current_stage=next_stage_id,
            previous_stage=current_stage_id,
            next_questions=next_questions,
            transition_reason=transition_decision.reason,
            message=f"Transitioned from {current_stage_id} to {next_stage_id}"
        )
    else:
        # No transition - stay in current stage
        current_questions = engine.get_stage_questions(current_stage_id)

        return AnswerResponse(
            success=True,
            answer_saved=True,
            transitioned=False,
            current_stage=current_stage_id,
            previous_stage=None,
            next_questions=current_questions,
            transition_reason=None,
            message="Answer saved successfully. Continue with current stage."
        )


@router.delete("/user", response_model=DeleteUserResponse, status_code=status.HTTP_200_OK)
async def delete_user(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> DeleteUserResponse:
    """
    Anonymize user data while preserving audit trail.

    Process:
    1. Replace email_hash with UUID-based hash
    2. Replace password_hash with 'ANONYMIZED'
    3. Keep all journey data intact (answers, transitions, paths)
    4. User can no longer log in but data remains for analytics
    """
    # Create anonymized email hash from user_id
    anonymized_email = f"anonymized_{current_user.user_id}"
    anonymized_email_hash = hash_email(anonymized_email)

    # Anonymize user data
    await journey_repository.anonymize_user_data(
        user_id=current_user.user_id,
        anonymized_email_hash=anonymized_email_hash
    )

    return DeleteUserResponse(
        success=True,
        user_id=current_user.user_id,
        anonymized=True,
        message="User data has been anonymized. You will be logged out."
    )
