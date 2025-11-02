from fastapi import APIRouter, Depends, status, HTTPException
from api.models.journey import (
    JourneyStateResponse,
    AnswerRequest,
    AnswerResponse,
    DeleteUserResponse,
    JourneyHistoryResponse,
    StageHistoryItem,
    StageDetailsResponse
)
from repositories.journey_repository import JourneyRepository
from repositories.user_repository import UserRepository
from repositories.graph_repository import GraphRepository
from dependencies.repositories import get_journey_repository, get_user_repository, get_graph_repository
from dependencies.auth import get_current_user
from api.models.auth import TokenData
from journey.routing_engine import get_routing_engine, RoutingEngine
from utils.hashing import hash_email
import json


router = APIRouter()


@router.get("/journey/current", response_model=JourneyStateResponse, status_code=status.HTTP_200_OK)
async def get_current_journey(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> JourneyStateResponse:
    journey_state = await journey_repository.get_user_journey_state(current_user.user_id)

    if not journey_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey state not found. Please contact support."
        )

    engine = get_routing_engine()
    stage_info = engine.get_stage_info(journey_state.current_stage_id)

    if not stage_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid stage: {journey_state.current_stage_id}"
        )

    previous_answers = await journey_repository.get_current_answers(
        current_user.user_id,
        journey_state.current_stage_id,
        journey_state.visit_number
    )

    answers_map = {
        answer.question_id: answer.answer_value
        for answer in previous_answers
    }

    questions_with_answers = []
    for question in stage_info["questions"]:
        question_dict = dict(question)
        if question["id"] in answers_map:
            question_dict["previous_answer"] = answers_map[question["id"]]
        questions_with_answers.append(question_dict)

    return JourneyStateResponse(
        success=True,
        current_stage=journey_state.current_stage_id,
        stage_name=stage_info["name"],
        visit_number=journey_state.visit_number,
        questions=questions_with_answers,
        journey_started_at=journey_state.journey_started_at.isoformat(),
        last_updated_at=journey_state.last_updated_at.isoformat(),
        message="Journey state retrieved successfully"
    )


@router.post("/journey/answer", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
async def submit_answer(
    request: AnswerRequest,
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> AnswerResponse:
    journey_state = await journey_repository.get_user_journey_state(current_user.user_id)

    if not journey_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey state not found"
        )

    current_stage_id = journey_state.current_stage_id
    current_visit_number = journey_state.visit_number

    engine = get_routing_engine()

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

    await journey_repository.save_answer(
        user_id=current_user.user_id,
        stage_id=current_stage_id,
        question_id=request.question_id,
        answer_value=request.answer_value,
        visit_number=current_visit_number
    )

    current_questions = engine.get_stage_questions(current_stage_id)

    return AnswerResponse(
        success=True,
        answer_saved=True,
        transitioned=False,
        current_stage=current_stage_id,
        previous_stage=None,
        questions=current_questions,
        transition_reason=None,
        message="Answer saved successfully. Call /journey/continue to proceed."
    )


@router.post("/journey/continue", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
async def continue_journey(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
    graph_repository: GraphRepository = Depends(get_graph_repository),
) -> AnswerResponse:
    journey_state = await journey_repository.get_user_journey_state(current_user.user_id)

    if not journey_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey state not found"
        )

    current_stage_id = journey_state.current_stage_id
    current_visit_number = journey_state.visit_number

    engine = RoutingEngine(graph_repository=graph_repository)

    answers = await journey_repository.get_current_answers(
        current_user.user_id,
        current_stage_id,
        current_visit_number
    )

    answers_dict = {
        answer.question_id: answer.answer_value
        for answer in answers
    }

    visit_history = await journey_repository.get_visit_history(current_user.user_id)

    transition_decision = await engine.evaluate_transition_with_graph(
        current_stage_id,
        answers_dict,
        visit_history
    )

    if transition_decision and transition_decision.should_transition:
        next_stage_id = transition_decision.next_stage

        next_visit_number = await journey_repository.get_stage_visit_count(
            current_user.user_id,
            next_stage_id
        ) + 1

        await journey_repository.perform_stage_transition(
            user_id=current_user.user_id,
            from_stage_id=current_stage_id,
            to_stage_id=next_stage_id,
            from_visit_number=current_visit_number,
            to_visit_number=next_visit_number,
            transition_reason=transition_decision.reason,
            matched_rule_id=str(transition_decision.matched_edge.id) if transition_decision.matched_edge else None,
            matched_question_id=transition_decision.question_id,
            matched_answer_value=transition_decision.answer_value
        )

        next_questions = engine.get_stage_questions(next_stage_id)

        return AnswerResponse(
            success=True,
            answer_saved=True,
            transitioned=True,
            current_stage=next_stage_id,
            previous_stage=current_stage_id,
            questions=next_questions,
            transition_reason=transition_decision.reason,
            message=f"Transitioned from {current_stage_id} to {next_stage_id}"
        )
    else:
        current_questions = engine.get_stage_questions(current_stage_id)

        return AnswerResponse(
            success=True,
            answer_saved=False,
            transitioned=False,
            current_stage=current_stage_id,
            previous_stage=None,
            questions=current_questions,
            transition_reason="No routing rule matched for current answers",
            message="No stage transition available. Continue with current stage."
        )


@router.delete("/user", response_model=DeleteUserResponse, status_code=status.HTTP_200_OK)
async def delete_user(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
    user_repository: UserRepository = Depends(get_user_repository),
) -> DeleteUserResponse:
    anonymized_email = f"anonymized_{current_user.user_id}"
    anonymized_email_hash = hash_email(anonymized_email)

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


@router.get("/journey/history", response_model=JourneyHistoryResponse, status_code=status.HTTP_200_OK)
async def get_journey_history(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> JourneyHistoryResponse:
    journey_state = await journey_repository.get_user_journey_state(current_user.user_id)

    if not journey_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey state not found"
        )

    path_history = await journey_repository.get_path_history(current_user.user_id)

    engine = get_routing_engine()

    stages = []
    for path_entry in path_history:
        stage_id = path_entry.stage_id
        visit_number = path_entry.visit_number

        stage_info = engine.get_stage_info(stage_id)
        stage_name = stage_info["name"] if stage_info else stage_id

        answers = await journey_repository.get_current_answers(current_user.user_id, stage_id, visit_number)
        questions_answered = len(answers)

        stages.append(StageHistoryItem(
            stage_id=stage_id,
            stage_name=stage_name,
            visit_number=visit_number,
            entered_at=path_entry.entered_at.isoformat(),
            exited_at=path_entry.exited_at.isoformat() if path_entry.exited_at else None,
            is_current=path_entry.is_current,
            questions_answered=questions_answered
        ))

    return JourneyHistoryResponse(
        success=True,
        user_id=current_user.user_id,
        stages=stages,
        total_stages_visited=len(stages),
        journey_started_at=journey_state.journey_started_at.isoformat(),
        message="Journey history retrieved successfully"
    )


@router.get("/journey/stage/{stage_id}", response_model=StageDetailsResponse, status_code=status.HTTP_200_OK)
async def get_stage_details(
    stage_id: str,
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> StageDetailsResponse:
    engine = get_routing_engine()

    stage_info = engine.get_stage_info(stage_id)
    if not stage_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stage not found: {stage_id}"
        )

    path_history = await journey_repository.get_path_history(current_user.user_id)
    path_entry = next((p for p in path_history if p.stage_id == stage_id), None)

    if not path_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stage not yet visited: {stage_id}"
        )

    answers = await journey_repository.get_current_answers(
        current_user.user_id,
        stage_id,
        path_entry.visit_number
    )

    answers_map = {
        answer.question_id: answer.answer_value
        for answer in answers
    }

    questions_with_answers = []
    for question in stage_info["questions"]:
        question_dict = dict(question)
        if question["id"] in answers_map:
            question_dict["previous_answer"] = answers_map[question["id"]]
        questions_with_answers.append(question_dict)

    return StageDetailsResponse(
        success=True,
        stage_id=stage_id,
        stage_name=stage_info["name"],
        visit_number=path_entry.visit_number,
        questions=questions_with_answers,
        entered_at=path_entry.entered_at.isoformat(),
        exited_at=path_entry.exited_at.isoformat() if path_entry.exited_at else None,
        is_current=path_entry.is_current,
        message="Stage details retrieved successfully"
    )
