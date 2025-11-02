from typing import Optional, Any, List, Dict
from uuid import UUID
from datetime import datetime
from nvox_common.db.nvox_db_client import NvoxDBClient
import asyncpg
import json


class JourneyRepository:
    def __init__(self, db_client: NvoxDBClient):
        self.db_client = db_client

    async def get_user_journey_state(self, user_id: UUID) -> Optional[asyncpg.Record]:
        """Get current journey state for a user"""
        return await self.db_client.fetchRow(
            """
            SELECT id, user_id, current_stage_id, visit_number,
                   journey_started_at, last_updated_at, created_at
            FROM user_journey_state
            WHERE user_id = $1
            """,
            user_id
        )

    async def create_journey_state(
        self,
        user_id: UUID,
        stage_id: str,
        visit_number: int = 1
    ) -> None:
        await self.db_client.execute(
            """
            INSERT INTO user_journey_state (user_id, current_stage_id, visit_number)
            VALUES ($1, $2, $3)
            """,
            user_id,
            stage_id,
            visit_number
        )

    async def update_journey_stage(
        self,
        user_id: UUID,
        new_stage_id: str,
        new_visit_number: int
    ) -> None:
        await self.db_client.execute(
            """
            UPDATE user_journey_state
            SET current_stage_id = $1,
                visit_number = $2,
                last_updated_at = NOW()
            WHERE user_id = $3
            """,
            new_stage_id,
            new_visit_number,
            user_id
        )

    async def save_answer(
        self,
        user_id: UUID,
        stage_id: str,
        question_id: str,
        answer_value: Any,
        visit_number: int
    ) -> None:

        await self.db_client.execute(
            """
            UPDATE user_answers
            SET is_current = FALSE
            WHERE user_id = $1 AND question_id = $2
            """,
            user_id,
            question_id
        )

        version_result = await self.db_client.fetchRow(
            """
            SELECT COALESCE(MAX(version), 0) + 1 as next_version
            FROM user_answers
            WHERE user_id = $1 AND question_id = $2
            """,
            user_id,
            question_id
        )
        next_version = version_result["next_version"] if version_result else 1

        await self.db_client.execute(
            """
            INSERT INTO user_answers (
                user_id, stage_id, question_id, answer_value,
                visit_number, version, is_current
            )
            VALUES ($1, $2, $3, $4, $5, $6, TRUE)
            """,
            user_id,
            stage_id,
            question_id,
            json.dumps(answer_value),
            visit_number,
            next_version
        )

    async def get_current_answers(
        self,
        user_id: UUID,
        stage_id: Optional[str] = None
    ) -> List[asyncpg.Record]:

        if stage_id:
            return await self.db_client.fetch(
                """
                SELECT question_id, answer_value, stage_id, visit_number, answered_at
                FROM user_answers
                WHERE user_id = $1 AND stage_id = $2 AND is_current = TRUE
                ORDER BY answered_at DESC
                """,
                user_id,
                stage_id
            )
        else:
            return await self.db_client.fetch(
                """
                SELECT question_id, answer_value, stage_id, visit_number, answered_at
                FROM user_answers
                WHERE user_id = $1 AND is_current = TRUE
                ORDER BY answered_at DESC
                """,
                user_id
            )

    async def get_answer(
        self,
        user_id: UUID,
        question_id: str
    ) -> Optional[asyncpg.Record]:
        return await self.db_client.fetchRow(
            """
            SELECT question_id, answer_value, stage_id, visit_number,
                   answered_at, version, is_current
            FROM user_answers
            WHERE user_id = $1 AND question_id = $2 AND is_current = TRUE
            """,
            user_id,
            question_id
        )

    async def get_answer_history(
        self,
        user_id: UUID,
        question_id: str
    ) -> List[asyncpg.Record]:
        return await self.db_client.fetch(
            """
            SELECT question_id, answer_value, stage_id, visit_number,
                   answered_at, version, is_current
            FROM user_answers
            WHERE user_id = $1 AND question_id = $2
            ORDER BY version DESC
            """,
            user_id,
            question_id
        )

    async def record_transition(
        self,
        user_id: UUID,
        from_stage_id: Optional[str],
        to_stage_id: str,
        from_visit_number: Optional[int],
        to_visit_number: int,
        transition_reason: Optional[str] = None,
        matched_rule_id: Optional[str] = None,
        matched_question_id: Optional[str] = None,
        matched_answer_value: Optional[Any] = None
    ) -> None:
        await self.db_client.execute(
            """
            INSERT INTO stage_transitions (
                user_id, from_stage_id, to_stage_id, from_visit_number,
                to_visit_number, transition_reason, matched_rule_id,
                matched_question_id, matched_answer_value
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            user_id,
            from_stage_id,
            to_stage_id,
            from_visit_number,
            to_visit_number,
            transition_reason,
            matched_rule_id,
            matched_question_id,
            json.dumps(matched_answer_value) if matched_answer_value is not None else None
        )

    async def get_transition_history(
        self,
        user_id: UUID
    ) -> List[asyncpg.Record]:
        return await self.db_client.fetch(
            """
            SELECT from_stage_id, to_stage_id, from_visit_number, to_visit_number,
                   transition_reason, matched_rule_id, matched_question_id,
                   matched_answer_value, transitioned_at
            FROM stage_transitions
            WHERE user_id = $1
            ORDER BY transitioned_at ASC
            """,
            user_id
        )

    async def enter_stage(
        self,
        user_id: UUID,
        stage_id: str,
        visit_number: int
    ) -> None:

        await self.db_client.execute(
            """
            UPDATE user_journey_path
            SET exited_at = NOW(), is_current = FALSE
            WHERE user_id = $1 AND is_current = TRUE
            """,
            user_id
        )

        await self.db_client.execute(
            """
            INSERT INTO user_journey_path (user_id, stage_id, visit_number, is_current)
            VALUES ($1, $2, $3, TRUE)
            """,
            user_id,
            stage_id,
            visit_number
        )

    async def get_current_path_entry(
        self,
        user_id: UUID
    ) -> Optional[asyncpg.Record]:
        return await self.db_client.fetchRow(
            """
            SELECT id, stage_id, visit_number, entered_at, exited_at, is_current
            FROM user_journey_path
            WHERE user_id = $1 AND is_current = TRUE
            """,
            user_id
        )

    async def get_path_history(
        self,
        user_id: UUID
    ) -> List[asyncpg.Record]:
        return await self.db_client.fetch(
            """
            SELECT stage_id, visit_number, entered_at, exited_at, is_current
            FROM user_journey_path
            WHERE user_id = $1
            ORDER BY entered_at ASC
            """,
            user_id
        )

    async def get_stage_visit_count(
        self,
        user_id: UUID,
        stage_id: str
    ) -> int:
        result = await self.db_client.fetchRow(
            """
            SELECT COUNT(*) as visit_count
            FROM user_journey_path
            WHERE user_id = $1 AND stage_id = $2
            """,
            user_id,
            stage_id
        )
        return result["visit_count"] if result else 0

    async def anonymize_user_data(self, user_id: UUID, anonymized_email_hash: str) -> None:

        await self.db_client.execute(
            """
            UPDATE users
            SET email_hash = $1,
                password_hash = 'ANONYMIZED',
                updated_at = NOW()
            WHERE id = $2
            """,
            anonymized_email_hash,
            user_id
        )
