import pytest
from httpx import AsyncClient


async def progress_to_stage(client: AsyncClient, token: str, target_stage: str, answers: dict):
    for question_id, answer_value in answers.items():
        answer_response = await client.post(
            "/v1/journey/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"question_id": question_id, "answer_value": answer_value}
        )
        assert answer_response.status_code == 200

        continue_response = await client.post(
            "/v1/journey/continue",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert continue_response.status_code == 200

        current_data = continue_response.json()
        if current_data.get("current_stage") == target_stage:
            return continue_response

    current_response = await client.get(
        "/v1/journey/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    current_data = current_response.json()
    assert current_data["current_stage"] == target_stage, \
        f"Expected to reach {target_stage} but at {current_data['current_stage']}"

    return current_response


@pytest.mark.asyncio
async def test_fallback_board_to_workup(test_client: AsyncClient):
    signup_response = await test_client.post(
        "/v1/signup",
        json={"email": "fallback_board@example.com", "password": "TestPass1"}
    )
    assert signup_response.status_code == 201

    login_response = await test_client.post(
        "/v1/login",
        json={"email": "fallback_board@example.com", "password": "TestPass1"}
    )
    token = login_response.json()["access_token"]

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 80.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert continue_response.json()["current_stage"] == "WORKUP"

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "wrk_egfr", "answer_value": 12.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert continue_response.json()["current_stage"] == "MATCH"

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "mtc_pra", "answer_value": 50.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert continue_response.json()["current_stage"] == "DONOR"

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "dnr_clearance", "answer_value": 1.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert continue_response.json()["current_stage"] == "BOARD"

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "brd_needs_more_tests", "answer_value": 1.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )
    data = continue_response.json()
    assert data["transitioned"]
    assert data["previous_stage"] == "BOARD"
    assert data["current_stage"] == "WORKUP"

    current_response = await test_client.get(
        "/v1/journey/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    current_data = current_response.json()
    assert current_data["current_stage"] == "WORKUP"
    assert current_data["visit_number"] == 2


@pytest.mark.asyncio
async def test_fallback_donor_to_match(test_client: AsyncClient):
    signup_response = await test_client.post(
        "/v1/signup",
        json={"email": "fallback_donor@example.com", "password": "TestPass1"}
    )
    assert signup_response.status_code == 201

    login_response = await test_client.post(
        "/v1/login",
        json={"email": "fallback_donor@example.com", "password": "TestPass1"}
    )
    token = login_response.json()["access_token"]

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 80.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "wrk_egfr", "answer_value": 12.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "mtc_pra", "answer_value": 50.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "dnr_clearance", "answer_value": 0.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )

    data = continue_response.json()
    assert data["transitioned"]
    assert data["previous_stage"] == "DONOR"
    assert data["current_stage"] == "MATCH"

    current_response = await test_client.get(
        "/v1/journey/current",
        headers={"Authorization": f"Bearer {token}"}
    )
    current_data = current_response.json()
    assert current_data["current_stage"] == "MATCH"
    assert current_data["visit_number"] == 2


@pytest.mark.asyncio
async def test_board_high_risk_to_exit(test_client: AsyncClient):
    signup_response = await test_client.post(
        "/v1/signup",
        json={"email": "board_exit@example.com", "password": "TestPass1"}
    )
    assert signup_response.status_code == 201

    login_response = await test_client.post(
        "/v1/login",
        json={"email": "board_exit@example.com", "password": "TestPass1"}
    )
    token = login_response.json()["access_token"]

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 80.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "wrk_egfr", "answer_value": 12.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "mtc_pra", "answer_value": 50.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "dnr_clearance", "answer_value": 1.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "brd_risk_score", "answer_value": 8.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )

    data = continue_response.json()
    assert data["transitioned"]
    assert data["previous_stage"] == "BOARD"
    assert data["current_stage"] == "EXIT"


@pytest.mark.asyncio
async def test_match_high_pra_to_board(test_client: AsyncClient):
    signup_response = await test_client.post(
        "/v1/signup",
        json={"email": "high_pra@example.com", "password": "TestPass1"}
    )
    assert signup_response.status_code == 201

    login_response = await test_client.post(
        "/v1/login",
        json={"email": "high_pra@example.com", "password": "TestPass1"}
    )
    token = login_response.json()["access_token"]

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "ref_karnofsky", "answer_value": 80.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "wrk_egfr", "answer_value": 12.0}
    )
    await test_client.post("/v1/journey/continue", headers={"Authorization": f"Bearer {token}"})

    await test_client.post(
        "/v1/journey/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"question_id": "mtc_pra", "answer_value": 85.0}
    )
    continue_response = await test_client.post(
        "/v1/journey/continue",
        headers={"Authorization": f"Bearer {token}"}
    )

    data = continue_response.json()
    assert data["transitioned"]
    assert data["previous_stage"] == "MATCH"
    assert data["current_stage"] == "BOARD"
