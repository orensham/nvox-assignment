from typing import Optional
from uuid import UUID
from datetime import datetime
from nvox_common.db.nvox_db_client import NvoxDBClient
import asyncpg


class SessionRepository:
    def __init__(self, db_client: NvoxDBClient):
        self.db_client = db_client

    async def create_session(
        self,
        user_id: UUID,
        token_jti: str,
        expires_at: datetime
    ) -> None:

        await self.db_client.execute(
            """
            INSERT INTO sessions (user_id, token_jti, expires_at, is_active)
            VALUES ($1, $2, $3, TRUE)
            """,
            user_id,
            token_jti,
            expires_at
        )

    async def revoke_session(self, token_jti: str) -> bool:
        result = await self.db_client.execute(
            """
            UPDATE sessions
            SET is_active = FALSE, revoked_at = NOW()
            WHERE token_jti = $1 AND is_active = TRUE
            """,
            token_jti
        )

        rows_updated = int(result.split()[-1]) if result else 0
        return rows_updated > 0

    async def is_session_active(self, token_jti: str) -> bool:
        session = await self.db_client.fetchRow(
            """
            SELECT is_active, expires_at
            FROM sessions
            WHERE token_jti = $1
            """,
            token_jti
        )

        if session is None:
            return False

        is_active = session["is_active"]
        expires_at = session["expires_at"]
        now = datetime.utcnow()

        return is_active and expires_at > now

    async def get_user_active_sessions(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self.db_client.fetch(
            """
            SELECT id, token_jti, expires_at, created_at
            FROM sessions
            WHERE user_id = $1 AND is_active = TRUE AND expires_at > NOW()
            ORDER BY created_at DESC
            """,
            user_id
        )

    async def revoke_all_user_sessions(self, user_id: UUID) -> int:
        result = await self.db_client.execute(
            """
            UPDATE sessions
            SET is_active = FALSE, revoked_at = NOW()
            WHERE user_id = $1 AND is_active = TRUE
            """,
            user_id
        )

        rows_updated = int(result.split()[-1]) if result else 0
        return rows_updated

    async def cleanup_expired_sessions(self) -> int:
        result = await self.db_client.execute(
            """
            DELETE FROM sessions
            WHERE expires_at < NOW()
            """
        )

        rows_deleted = int(result.split()[-1]) if result else 0
        return rows_deleted
