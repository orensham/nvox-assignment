import pytest
from uuid import uuid4
from repositories.journey_repository import JourneyRepository
from nvox_common.db.nvox_db_client import NvoxDBClient


@pytest.fixture
def journey_repository(db_pool) -> JourneyRepository:
    db_client = NvoxDBClient(db_pool)
    return JourneyRepository(db_client)


@pytest.fixture
async def test_user_id(journey_repository, db_pool):
    user_id = uuid4()

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email_hash, password_hash)
            VALUES ($1, $2, $3)
            """,
            user_id, "test_email_hash", "test_password_hash"
        )

    await journey_repository.create_journey_state(
        user_id=user_id,
        stage_id="REFERRAL",
        visit_number=1
    )
    await journey_repository.enter_stage(
        user_id=user_id,
        stage_id="REFERRAL",
        visit_number=1
    )
    return user_id


@pytest.mark.asyncio
async def test_create_journey_state(journey_repository, db_pool):
    user_id = uuid4()

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, email_hash, password_hash)
            VALUES ($1, $2, $3)
            """,
            user_id, "test_email_hash", "test_password_hash"
        )

    await journey_repository.create_journey_state(
        user_id=user_id,
        stage_id="REFERRAL",
        visit_number=1
    )

    state = await journey_repository.get_user_journey_state(user_id)
    assert state is not None
    assert state["user_id"] == user_id
    assert state["current_stage_id"] == "REFERRAL"
    assert state["visit_number"] == 1


@pytest.mark.asyncio
async def test_update_journey_stage(test_user_id, journey_repository):
    await journey_repository.update_journey_stage(
        user_id=test_user_id,
        new_stage_id="WORKUP",
        new_visit_number=1
    )

    state = await journey_repository.get_user_journey_state(test_user_id)
    assert state["current_stage_id"] == "WORKUP"
    assert state["visit_number"] == 1


@pytest.mark.asyncio
async def test_save_answer(test_user_id, journey_repository):
    await journey_repository.save_answer(
        user_id=test_user_id,
        stage_id="REFERRAL",
        question_id="ref_karnofsky",
        answer_value=80.0,
        visit_number=1
    )

    answer = await journey_repository.get_answer(test_user_id, "ref_karnofsky")
    assert answer is not None
    assert answer["question_id"] == "ref_karnofsky"
    assert answer["answer_value"] == "80.0"
    assert answer["is_current"]


@pytest.mark.asyncio
async def test_save_answer_versioning(test_user_id, journey_repository):
    await journey_repository.save_answer(
        user_id=test_user_id,
        stage_id="REFERRAL",
        question_id="ref_karnofsky",
        answer_value=60.0,
        visit_number=1
    )

    await journey_repository.save_answer(
        user_id=test_user_id,
        stage_id="REFERRAL",
        question_id="ref_karnofsky",
        answer_value=80.0,
        visit_number=1
    )

    current = await journey_repository.get_answer(test_user_id, "ref_karnofsky")
    assert current["answer_value"] == "80.0"
    assert current["version"] == 2
    assert current["is_current"]

    history = await journey_repository.get_answer_history(test_user_id, "ref_karnofsky")
    assert len(history) == 2
    assert history[0]["version"] == 2
    assert history[1]["version"] == 1


@pytest.mark.asyncio
async def test_get_current_answers(test_user_id, journey_repository):
    await journey_repository.save_answer(
        user_id=test_user_id,
        stage_id="REFERRAL",
        question_id="ref_karnofsky",
        answer_value=80.0,
        visit_number=1
    )
    await journey_repository.save_answer(
        user_id=test_user_id,
        stage_id="REFERRAL",
        question_id="ref_eligible",
        answer_value=True,
        visit_number=1
    )

    answers = await journey_repository.get_current_answers(test_user_id)
    assert len(answers) == 2


@pytest.mark.asyncio
async def test_record_transition(test_user_id, journey_repository):
    await journey_repository.record_transition(
        user_id=test_user_id,
        from_stage_id="REFERRAL",
        to_stage_id="WORKUP",
        from_visit_number=1,
        to_visit_number=1,
        transition_reason="Karnofsky score 80",
        matched_rule_id="REFERRAL_ref_karnofsky_40.0-100.0",
        matched_question_id="ref_karnofsky",
        matched_answer_value=80.0
    )

    history = await journey_repository.get_transition_history(test_user_id)
    assert len(history) == 1
    assert history[0]["from_stage_id"] == "REFERRAL"
    assert history[0]["to_stage_id"] == "WORKUP"
    assert history[0]["matched_rule_id"] == "REFERRAL_ref_karnofsky_40.0-100.0"


@pytest.mark.asyncio
async def test_enter_stage(test_user_id, journey_repository):
    await journey_repository.enter_stage(
        user_id=test_user_id,
        stage_id="WORKUP",
        visit_number=1
    )

    path_entry = await journey_repository.get_current_path_entry(test_user_id)
    assert path_entry is not None
    assert path_entry["stage_id"] == "WORKUP"
    assert path_entry["visit_number"] == 1
    assert path_entry["is_current"]
    assert path_entry["exited_at"] is None


@pytest.mark.asyncio
async def test_get_stage_visit_count(test_user_id, journey_repository):
    count = await journey_repository.get_stage_visit_count(test_user_id, "REFERRAL")
    assert count == 1

    await journey_repository.enter_stage(test_user_id, "WORKUP", 1)
    count = await journey_repository.get_stage_visit_count(test_user_id, "WORKUP")
    assert count == 1

    await journey_repository.enter_stage(test_user_id, "REFERRAL", 2)
    count = await journey_repository.get_stage_visit_count(test_user_id, "REFERRAL")
    assert count == 2


@pytest.mark.asyncio
async def test_get_path_history(test_user_id, journey_repository):
    await journey_repository.enter_stage(test_user_id, "WORKUP", 1)

    await journey_repository.enter_stage(test_user_id, "EXIT", 1)

    history = await journey_repository.get_path_history(test_user_id)
    assert len(history) >= 2  # At least WORKUP and EXIT
