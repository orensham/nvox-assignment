from typing import Optional
from uuid import UUID
from datetime import datetime
from nvox_common.db.nvox_db_client import NvoxDBClient
import asyncpg


class UserRepository:
    def __init__(self, db_client: NvoxDBClient):
        self.db_client = db_client

    async def get_user_by_email_hash(self, email_hash: str) -> Optional[asyncpg.Record]:
        return await self.db_client.fetchRow(
            "SELECT id, email_hash, password_hash, journey_stage, journey_started_at FROM users WHERE email_hash = $1",
            email_hash
        )

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

    async def get_user_by_id(self, user_id: UUID) -> Optional[asyncpg.Record]:
        return await self.db_client.fetchRow(
            "SELECT id, email_hash, journey_stage, journey_started_at, created_at FROM users WHERE id = $1",
            user_id
        )

    async def update_journey_stage(self, user_id: UUID, new_stage: str) -> None:
        await self.db_client.execute(
            "UPDATE users SET journey_stage = $1, updated_at = NOW() WHERE id = $2",
            new_stage,
            user_id
        )
