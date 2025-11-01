from utils.hashing import hash_email, hash_password
from repositories.user_repository import UserRepository
import pytest
import sys
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.asyncio
class TestUserRepositoryCreate:
    async def test_create_user_success(self, user_repository: UserRepository, clean_db):
        user_id = uuid4()
        email_hash = hash_email("test@example.com")
        password_hash = hash_password("password123")
        journey_stage = "REFERRAL"
        journey_started_at = datetime.utcnow()

        await user_repository.create_user(
            user_id=user_id,
            email_hash=email_hash,
            password_hash=password_hash,
            journey_stage=journey_stage,
            journey_started_at=journey_started_at
        )

        user = await user_repository.get_user_by_id(user_id)
        assert user is not None
        assert user["id"] == user_id
        assert user["email_hash"] == email_hash

    async def test_create_user_with_defaults(self, user_repository: UserRepository, clean_db):
        user_id = uuid4()
        email_hash = hash_email("test@example.com")
        password_hash = hash_password("password123")

        await user_repository.create_user(
            user_id=user_id,
            email_hash=email_hash,
            password_hash=password_hash
        )

        user = await user_repository.get_user_by_id(user_id)
        assert user is not None
        assert user["journey_stage"] == "REFERRAL"
        assert user["journey_started_at"] is not None

    async def test_create_duplicate_email_fails(self, user_repository: UserRepository, clean_db):
        email_hash = hash_email("duplicate@example.com")
        password_hash = hash_password("password123")

        await user_repository.create_user(
            user_id=uuid4(),
            email_hash=email_hash,
            password_hash=password_hash
        )

        with pytest.raises(Exception):
            await user_repository.create_user(
                user_id=uuid4(),
                email_hash=email_hash,
                password_hash=password_hash
            )


@pytest.mark.asyncio
class TestUserRepositoryExists:
    async def test_user_exists_returns_true_when_user_exists(self, user_repository: UserRepository, clean_db):
        email_hash = hash_email("existing@example.com")
        password_hash = hash_password("password123")

        await user_repository.create_user(
            user_id=uuid4(),
            email_hash=email_hash,
            password_hash=password_hash
        )

        exists = await user_repository.user_exists_by_email_hash(email_hash)
        assert exists is True

    async def test_user_exists_returns_false_when_user_not_exists(self, user_repository: UserRepository, clean_db):
        email_hash = hash_email("nonexistent@example.com")

        exists = await user_repository.user_exists_by_email_hash(email_hash)
        assert exists is False


@pytest.mark.asyncio
class TestUserRepositoryRetrieve:
    async def test_get_user_by_email_hash_success(self, user_repository: UserRepository, clean_db):
        user_id = uuid4()
        email_hash = hash_email("find@example.com")
        password_hash = hash_password("password123")

        await user_repository.create_user(
            user_id=user_id,
            email_hash=email_hash,
            password_hash=password_hash
        )

        user = await user_repository.get_user_by_email_hash(email_hash)
        assert user is not None
        assert user["id"] == user_id
        assert user["email_hash"] == email_hash
        assert user["password_hash"] == password_hash

    async def test_get_user_by_email_hash_not_found(self, user_repository: UserRepository, clean_db):
        email_hash = hash_email("notfound@example.com")

        user = await user_repository.get_user_by_email_hash(email_hash)
        assert user is None

    async def test_get_user_by_id_success(self, user_repository: UserRepository, clean_db):
        user_id = uuid4()
        email_hash = hash_email("findbyid@example.com")
        password_hash = hash_password("password123")

        await user_repository.create_user(
            user_id=user_id,
            email_hash=email_hash,
            password_hash=password_hash
        )

        user = await user_repository.get_user_by_id(user_id)
        assert user is not None
        assert user["id"] == user_id
        assert user["email_hash"] == email_hash

    async def test_get_user_by_id_not_found(self, user_repository: UserRepository, clean_db):
        user_id = uuid4()

        user = await user_repository.get_user_by_id(user_id)
        assert user is None


@pytest.mark.asyncio
class TestUserRepositoryUpdate:
    async def test_update_journey_stage_success(self, user_repository: UserRepository, clean_db):
        user_id = uuid4()
        email_hash = hash_email("update@example.com")
        password_hash = hash_password("password123")

        await user_repository.create_user(
            user_id=user_id,
            email_hash=email_hash,
            password_hash=password_hash,
            journey_stage="REFERRAL"
        )

        await user_repository.update_journey_stage(user_id, "EVALUATION")

        user = await user_repository.get_user_by_id(user_id)
        assert user["journey_stage"] == "EVALUATION"

    async def test_update_journey_stage_multiple_times(self, user_repository: UserRepository, clean_db):
        user_id = uuid4()
        email_hash = hash_email("multiupdate@example.com")
        password_hash = hash_password("password123")

        await user_repository.create_user(
            user_id=user_id,
            email_hash=email_hash,
            password_hash=password_hash,
            journey_stage="REFERRAL"
        )

        await user_repository.update_journey_stage(user_id, "EVALUATION")
        await user_repository.update_journey_stage(user_id, "TESTING")
        await user_repository.update_journey_stage(user_id, "LISTING")

        user = await user_repository.get_user_by_id(user_id)
        assert user["journey_stage"] == "LISTING"
