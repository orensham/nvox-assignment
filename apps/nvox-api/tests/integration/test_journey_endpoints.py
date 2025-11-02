import pytest
from httpx import AsyncClient


@pytest.fixture
async def authenticated_user_with_journey(test_client: AsyncClient, sample_email, sample_password):
    response = await test_client.post(
        "/v1/signup",
        json={"email": sample_email, "password": sample_password}
    )
    assert response.status_code == 201
    data = response.json()

    login_response = await test_client.post(
        "/v1/login",
        json={"email": sample_email, "password": sample_password}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()

    return {
        "user_id": data["user_id"],
        "token": token_data["access_token"],
        "email": sample_email
    }


@pytest.mark.asyncio
async def test_signup_initializes_journey(test_client: AsyncClient, sample_email, sample_password):
    response = await test_client.post(
        "/v1/signup",
        json={"email": sample_email, "password": sample_password}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"]
    assert "journey" in data
    assert data["journey"]["current_stage"] == "REFERRAL"
    assert "started_at" in data["journey"]


@pytest.mark.asyncio
async def test_get_current_journey_success(test_client: AsyncClient, authenticated_user_with_journey):
    token = authenticated_user_with_journey["token"]

    response = await test_client.get(
        "/v1/journey/current",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert data["current_stage"] == "REFERRAL"
    assert data["visit_number"] == 1
    assert "questions" in data
    assert len(data["questions"]) > 0


@pytest.mark.asyncio
async def test_get_current_journey_unauthorized(test_client: AsyncClient):
    response = await test_client.get("/v1/journey/current")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_submit_answer_boolean_no_transition(test_client: AsyncClient, authenticated_user_with_journey):
    token = authenticated_user_with_journey["token"]

    response = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": "ref_has_nephrologist_note",
            "answer_value": "yes"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert data["answer_saved"]
    assert not data["transitioned"]
    assert data["current_stage"] == "REFERRAL"


@pytest.mark.asyncio
async def test_submit_answer_with_transition(test_client: AsyncClient, authenticated_user_with_journey):
    token = authenticated_user_with_journey["token"]

    answer_response = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": "ref_karnofsky",
            "answer_value": 80.0
        }
    )
    assert answer_response.status_code == 200
    answer_data = answer_response.json()
    assert answer_data["success"]
    assert answer_data["answer_saved"]
    assert not answer_data["transitioned"]
    assert answer_data["current_stage"] == "REFERRAL"

    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert continue_response.status_code == 200
    data = continue_response.json()
    assert data["success"]
    assert data["transitioned"]
    assert data["previous_stage"] == "REFERRAL"
    assert data["current_stage"] == "WORKUP"
    assert "questions" in data


@pytest.mark.asyncio
async def test_submit_answer_low_score_exit(test_client: AsyncClient):
    response = await test_client.post(
        "/v1/signup",
        json={"email": "exit_test@example.com", "password": "TestPass1"}
    )
    assert response.status_code == 201

    login_response = await test_client.post(
        "/v1/login",
        json={"email": "exit_test@example.com", "password": "TestPass1"}
    )
    token = login_response.json()["access_token"]

    answer_response = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": "ref_karnofsky",
            "answer_value": 30.0
        }
    )
    assert answer_response.status_code == 200
    answer_data = answer_response.json()
    assert answer_data["success"]
    assert answer_data["answer_saved"]
    assert not answer_data["transitioned"]
    assert answer_data["current_stage"] == "REFERRAL"

    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert continue_response.status_code == 200
    data = continue_response.json()
    assert data["success"]
    assert data["transitioned"]
    assert data["current_stage"] == "EXIT"


@pytest.mark.asyncio
async def test_submit_answer_invalid_question(test_client: AsyncClient, authenticated_user_with_journey):
    token = authenticated_user_with_journey["token"]

    response = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": "nonexistent_question",
            "answer_value": 50.0
        }
    )

    assert response.status_code == 422
    data = response.json()
    assert "not found" in data["detail"].lower() or "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_submit_answer_invalid_value(test_client: AsyncClient, authenticated_user_with_journey):
    token = authenticated_user_with_journey["token"]

    response = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_id": "ref_karnofsky",
            "answer_value": 150.0
        }
    )

    assert response.status_code == 422
    data = response.json()

    assert "value" in data["detail"].lower() or "must be" in data["detail"].lower()


@pytest.mark.asyncio
async def test_submit_answer_updates_existing(test_client: AsyncClient, authenticated_user_with_journey):
    token = authenticated_user_with_journey["token"]

    response1 = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 70.0}
    )
    assert response1.status_code == 200

    response2 = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 80.0}
    )
    assert response2.status_code == 200
    data = response2.json()
    assert data["success"]


@pytest.mark.asyncio
async def test_delete_user_anonymizes_data(test_client: AsyncClient, authenticated_user_with_journey):
    token = authenticated_user_with_journey["token"]
    original_email = authenticated_user_with_journey["email"]

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 80.0}
    )

    response = await test_client.delete(
        "/v1/user",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"]
    assert "anonymized" in data["message"].lower()

    login_response = await test_client.post(
        "/v1/login",
        json={"email": original_email, "password": "TestPass1"}
    )
    assert login_response.status_code == 401


@pytest.mark.asyncio
async def test_journey_flow_complete_path(test_client: AsyncClient):
    signup_response = await test_client.post(
        "/v1/signup",
        json={"email": "journey_flow@example.com", "password": "TestPass1"}
    )
    assert signup_response.status_code == 201

    login_response = await test_client.post(
        "/v1/login",
        json={"email": "journey_flow@example.com", "password": "TestPass1"}
    )
    token = login_response.json()["access_token"]

    current_response = await test_client.get(
        "/v1/journey/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert current_response.json()["current_stage"] == "REFERRAL"

    answer_response = await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 80.0}
    )
    assert answer_response.json()["current_stage"] == "REFERRAL"
    assert not answer_response.json()["transitioned"]

    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert continue_response.json()["transitioned"]
    assert continue_response.json()["current_stage"] == "WORKUP"

    current_response = await test_client.get(
        "/v1/journey/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    current_data = current_response.json()
    assert current_data["current_stage"] == "WORKUP"
    assert current_data["visit_number"] == 1
