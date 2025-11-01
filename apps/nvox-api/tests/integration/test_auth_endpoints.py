import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSignupEndpoint:
    async def test_signup_success(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "newuser@example.com",
            "password": "SecurePass1"
        }

        response = await test_client.post("/v1/signup", json=payload)

        assert response.status_code == 201
        data = response.json()

        assert data["success"] is True
        assert "user_id" in data
        assert "email" in data
        assert data["message"] == "Account created successfully"

        assert "journey" in data
        assert data["journey"]["current_stage"] == "REFERRAL"
        assert "started_at" in data["journey"]

        assert data["email"] != "newuser@example.com"
        assert len(data["email"]) == 64

    async def test_signup_duplicate_email_fails(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "duplicate@example.com",
            "password": "SecurePass1"
        }

        response1 = await test_client.post("/v1/signup", json=payload)
        assert response1.status_code == 201

        response2 = await test_client.post("/v1/signup", json=payload)
        assert response2.status_code == 409

        data = response2.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

    async def test_signup_case_insensitive_email(self, test_client: AsyncClient, clean_db):
        payload1 = {
            "email": "Test@Example.com",
            "password": "SecurePass1"
        }
        payload2 = {
            "email": "test@example.com",
            "password": "SecurePass2"
        }

        response1 = await test_client.post("/v1/signup", json=payload1)
        assert response1.status_code == 201

        response2 = await test_client.post("/v1/signup", json=payload2)
        assert response2.status_code == 409

    async def test_signup_invalid_password_too_long(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "test@example.com",
            "password": "ThisPasswordIsTooLong123"
        }

        response = await test_client.post("/v1/signup", json=payload)
        assert response.status_code == 422

    async def test_signup_invalid_password_too_short(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "test@example.com",
            "password": "short"
        }

        response = await test_client.post("/v1/signup", json=payload)
        assert response.status_code == 422

    async def test_signup_invalid_email_format(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "not-an-email",
            "password": "SecurePass1"
        }

        response = await test_client.post("/v1/signup", json=payload)
        assert response.status_code == 422

    async def test_signup_missing_email(self, test_client: AsyncClient, clean_db):
        payload = {
            "password": "SecurePass1"
        }

        response = await test_client.post("/v1/signup", json=payload)
        assert response.status_code == 422

    async def test_signup_missing_password(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "test@example.com"
        }

        response = await test_client.post("/v1/signup", json=payload)
        assert response.status_code == 422

    async def test_signup_empty_payload(self, test_client: AsyncClient, clean_db):
        response = await test_client.post("/v1/signup", json={})
        assert response.status_code == 422

    async def test_signup_multiple_users(self, test_client: AsyncClient, clean_db):
        users = [
            {"email": "user1@example.com", "password": "Pass1word"},
            {"email": "user2@example.com", "password": "Pass2word"},
            {"email": "user3@example.com", "password": "Pass3word"},
        ]

        for user in users:
            response = await test_client.post("/v1/signup", json=user)
            assert response.status_code == 201

            data = response.json()
            assert data["success"] is True

    async def test_signup_password_not_returned(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "secure@example.com",
            "password": "SecurePass1"
        }

        response = await test_client.post("/v1/signup", json=payload)
        data = response.json()

        assert "password" not in data
        assert "password_hash" not in data

    async def test_signup_returns_hashed_email(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "hash@example.com",
            "password": "SecurePass1"
        }

        response = await test_client.post("/v1/signup", json=payload)
        data = response.json()

        assert data["email"] != "hash@example.com"
        assert len(data["email"]) == 64
        assert data["email"].isalnum()

    async def test_signup_sets_default_journey_stage(self, test_client: AsyncClient, clean_db):
        payload = {
            "email": "journey@example.com",
            "password": "SecurePass1"
        }

        response = await test_client.post("/v1/signup", json=payload)
        data = response.json()

        assert data["journey"]["current_stage"] == "REFERRAL"

    async def test_signup_generates_unique_user_ids(self, test_client: AsyncClient, clean_db):
        payload1 = {"email": "uuid1@example.com", "password": "SecurePass1"}
        payload2 = {"email": "uuid2@example.com", "password": "SecurePass2"}

        response1 = await test_client.post("/v1/signup", json=payload1)
        response2 = await test_client.post("/v1/signup", json=payload2)

        data1 = response1.json()
        data2 = response2.json()

        assert data1["user_id"] != data2["user_id"]

        from uuid import UUID
        UUID(data1["user_id"])
        UUID(data2["user_id"])
