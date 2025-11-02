from typing import Optional
from uuid import UUID
from datetime import datetime
from nvox_common.db.nvox_db_client import NvoxDBClient

from .db_models import UserDB, optional_record_to_model


class UserRepository:
    def __init__(self, db_client: NvoxDBClient):
        self.db_client = db_client

    async def get_user_by_email_hash(self, email_hash: str) -> Optional[UserDB]:
        row = await self.db_client.fetchRow(
            "SELECT * FROM users WHERE email_hash = $1",
            email_hash
        )
        return optional_record_to_model(row, UserDB)

    async def user_exists_by_email_hash(self, email_hash: str) -> bool:
        result = await self.db_client.fetchRow(
            "SELECT id FROM users WHERE email_hash = $1",
            email_hash
        )
        return result is not None

    async def create_user(
        self,
        user_id: UUID,
        email_hash: str,
        password_hash: str,
        journey_stage: str = "REFERRAL",
        journey_started_at: Optional[datetime] = None
    ) -> None:
        if journey_started_at is None:
            journey_started_at = datetime.utcnow()

        await self.db_client.execute(
            """
            INSERT INTO users (id, email_hash, password_hash, journey_stage, journey_started_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            email_hash,
            password_hash,
            journey_stage,
            journey_started_at
        )

    async def get_user_by_id(self, user_id: UUID) -> Optional[UserDB]:
        row = await self.db_client.fetchRow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
        return optional_record_to_model(row, UserDB)

    async def update_journey_stage(self, user_id: UUID, new_stage: str) -> None:
        await self.db_client.execute(
            "UPDATE users SET journey_stage = $1, updated_at = NOW() WHERE id = $2",
            new_stage,
            user_id
        )

    async def create_user_with_journey(
        self,
        user_id: UUID,
        email_hash: str,
        password_hash: str,
        entry_stage: str,
        journey_started_at: datetime
    ) -> None:
        async with self.db_client.transaction() as tx:
            # Create user
            await tx.execute(
                """
                INSERT INTO users (id, email_hash, password_hash, journey_stage, journey_started_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                email_hash,
                password_hash,
                entry_stage,
                journey_started_at
            )

            await tx.execute(
                """
                INSERT INTO user_journey_state (user_id, current_stage_id, visit_number, journey_started_at)
                VALUES ($1, $2, 1, $3)
                """,
                user_id,
                entry_stage,
                journey_started_at
            )

            await tx.execute(
                """
                INSERT INTO user_journey_path (user_id, stage_id, visit_number, is_current)
                VALUES ($1, $2, 1, TRUE)
                """,
                user_id,
                entry_stage
            )

            await tx.execute(
                """
                INSERT INTO stage_transitions (
                    user_id, from_stage_id, to_stage_id, from_visit_number,
                    to_visit_number, transition_reason
                )
                VALUES ($1, NULL, $2, NULL, 1, $3)
                """,
                user_id,
                entry_stage,
                "Initial signup"
            )
