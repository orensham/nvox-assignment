import pytest
from httpx import AsyncClient
from uuid import UUID
import asyncpg
from jose import jwt
from datetime import datetime, timedelta, timezone


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


@pytest.mark.asyncio
class TestLoginEndpoint:
    async def test_login_success(self, test_client: AsyncClient, clean_db):
        signup_payload = {
            "email": "login@example.com",
            "password": "SecurePass1"
        }
        await test_client.post("/v1/signup", json=signup_payload)

        login_payload = {
            "email": "login@example.com",
            "password": "SecurePass1"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert "user_id" in data
        assert data["message"] == "Login successful"

        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

        UUID(data["user_id"])

    async def test_login_with_wrong_password(self, test_client: AsyncClient, clean_db):
        signup_payload = {
            "email": "wrongpass@example.com",
            "password": "CorrectPass1"
        }
        await test_client.post("/v1/signup", json=signup_payload)

        login_payload = {
            "email": "wrongpass@example.com",
            "password": "WrongPass1"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Invalid credentials"

    async def test_login_with_non_existent_user(self, test_client: AsyncClient, clean_db):
        login_payload = {
            "email": "nonexistent@example.com",
            "password": "SomePass1"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid credentials"

    async def test_login_case_insensitive_email(self, test_client: AsyncClient, clean_db):
        signup_payload = {
            "email": "case@example.com",
            "password": "SecurePass1"
        }
        await test_client.post("/v1/signup", json=signup_payload)

        login_payload = {
            "email": "CASE@EXAMPLE.COM",
            "password": "SecurePass1"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_login_creates_session_in_database(self, test_client: AsyncClient, clean_db, db_pool: asyncpg.Pool):
        signup_payload = {
            "email": "session@example.com",
            "password": "SecurePass1"
        }
        signup_response = await test_client.post("/v1/signup", json=signup_payload)
        user_id = signup_response.json()["user_id"]

        login_payload = {
            "email": "session@example.com",
            "password": "SecurePass1"
        }
        login_response = await test_client.post("/v1/login", json=login_payload)

        assert login_response.status_code == 200
        async with db_pool.acquire() as conn:
            sessions = await conn.fetch(
                "SELECT * FROM sessions WHERE user_id = $1 AND is_active = TRUE",
                UUID(user_id)
            )
            assert len(sessions) == 1
            session = sessions[0]
            assert session["is_active"] is True
            assert session["revoked_at"] is None

    async def test_login_password_not_returned(self, test_client: AsyncClient, clean_db):
        signup_payload = {
            "email": "secure@example.com",
            "password": "SecurePass1"
        }
        await test_client.post("/v1/signup", json=signup_payload)

        login_payload = {
            "email": "secure@example.com",
            "password": "SecurePass1"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data

    async def test_login_invalid_email_format(self, test_client: AsyncClient, clean_db):
        login_payload = {
            "email": "not-an-email",
            "password": "SecurePass1"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        assert response.status_code == 422

    async def test_login_missing_email(self, test_client: AsyncClient, clean_db):
        login_payload = {
            "password": "SecurePass1"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        assert response.status_code == 422

    async def test_login_missing_password(self, test_client: AsyncClient, clean_db):
        login_payload = {
            "email": "test@example.com"
        }
        response = await test_client.post("/v1/login", json=login_payload)

        assert response.status_code == 422

    async def test_login_empty_payload(self, test_client: AsyncClient, clean_db):
        response = await test_client.post("/v1/login", json={})

        assert response.status_code == 422

    async def test_login_multiple_times_creates_multiple_sessions(self, test_client: AsyncClient, clean_db, db_pool: asyncpg.Pool):
        signup_payload = {
            "email": "multisession@example.com",
            "password": "SecurePass1"
        }
        signup_response = await test_client.post("/v1/signup", json=signup_payload)
        user_id = signup_response.json()["user_id"]

        login_payload = {
            "email": "multisession@example.com",
            "password": "SecurePass1"
        }

        for _ in range(3):
            response = await test_client.post("/v1/login", json=login_payload)
            assert response.status_code == 200

        async with db_pool.acquire() as conn:
            sessions = await conn.fetch(
                "SELECT * FROM sessions WHERE user_id = $1 AND is_active = TRUE",
                UUID(user_id)
            )
            assert len(sessions) == 3


@pytest.mark.asyncio
class TestLogoutEndpoint:
    async def test_logout_success(self, test_client: AsyncClient, clean_db):
        signup_payload = {
            "email": "logout@example.com",
            "password": "SecurePass1"
        }
        await test_client.post("/v1/signup", json=signup_payload)

        login_payload = {
            "email": "logout@example.com",
            "password": "SecurePass1"
        }
        login_response = await test_client.post("/v1/login", json=login_payload)
        access_token = login_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        response = await test_client.post("/v1/logout", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Logged out successfully"

    async def test_logout_without_token(self, test_client: AsyncClient, clean_db):
        response = await test_client.post("/v1/logout")

        assert response.status_code == 403

    async def test_logout_with_invalid_token(self, test_client: AsyncClient, clean_db):
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await test_client.post("/v1/logout", headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_logout_with_expired_token(self, test_client: AsyncClient, clean_db):
        expired_payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "email_hash": "test_hash",
            "jti": "test_jti",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2)
        }

        expired_token = jwt.encode(expired_payload, "dummy_secret", algorithm="HS256")

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await test_client.post("/v1/logout", headers=headers)

        assert response.status_code == 401

    async def test_logout_revokes_all_user_sessions(self, test_client: AsyncClient, clean_db, db_pool: asyncpg.Pool):
        signup_payload = {
            "email": "revokeall@example.com",
            "password": "SecurePass1"
        }
        signup_response = await test_client.post("/v1/signup", json=signup_payload)
        user_id = signup_response.json()["user_id"]

        login_payload = {
            "email": "revokeall@example.com",
            "password": "SecurePass1"
        }

        tokens = []
        for _ in range(3):
            response = await test_client.post("/v1/login", json=login_payload)
            tokens.append(response.json()["access_token"])

        async with db_pool.acquire() as conn:
            active_sessions_before = await conn.fetch(
                "SELECT * FROM sessions WHERE user_id = $1 AND is_active = TRUE",
                UUID(user_id)
            )
            assert len(active_sessions_before) == 3

        headers = {"Authorization": f"Bearer {tokens[0]}"}
        response = await test_client.post("/v1/logout", headers=headers)
        assert response.status_code == 200

        async with db_pool.acquire() as conn:
            active_sessions_after = await conn.fetch(
                "SELECT * FROM sessions WHERE user_id = $1 AND is_active = TRUE",
                UUID(user_id)
            )
            assert len(active_sessions_after) == 0

            revoked_sessions = await conn.fetch(
                "SELECT * FROM sessions WHERE user_id = $1 AND is_active = FALSE",
                UUID(user_id)
            )
            assert len(revoked_sessions) == 3

    async def test_logout_twice_fails(self, test_client: AsyncClient, clean_db):
        signup_payload = {
            "email": "doublelogout@example.com",
            "password": "SecurePass1"
        }
        await test_client.post("/v1/signup", json=signup_payload)

        login_payload = {
            "email": "doublelogout@example.com",
            "password": "SecurePass1"
        }
        login_response = await test_client.post("/v1/login", json=login_payload)
        access_token = login_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}
        response1 = await test_client.post("/v1/logout", headers=headers)
        assert response1.status_code == 200
        response2 = await test_client.post("/v1/logout", headers=headers)
        assert response2.status_code == 401
        data = response2.json()
        assert "revoked" in data["detail"].lower()

    async def test_logout_with_malformed_authorization_header(self, test_client: AsyncClient, clean_db):
        headers = {"Authorization": "some_token"}
        response = await test_client.post("/v1/logout", headers=headers)

        assert response.status_code == 403
