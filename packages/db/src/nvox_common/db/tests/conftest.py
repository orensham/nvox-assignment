import pytest
from typing import AsyncGenerator, Generator
import asyncpg
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="class")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer(
        image="postgres:15-alpine",
        username="test_user",
        password="test_password",
        dbname="test_db"
    ) as postgres:
        postgres.get_connection_url()
        yield postgres


@pytest.fixture(scope="class")
def db_connection_params(postgres_container: PostgresContainer):
    import urllib.parse
    conn_url = postgres_container.get_connection_url()
    parsed = urllib.parse.urlparse(conn_url)

    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
    }


@pytest.fixture(scope="function")
async def db_schema(db_connection_params):
    conn = await asyncpg.connect(**db_connection_params)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email_hash VARCHAR(64) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            journey_stage VARCHAR(50) NOT NULL DEFAULT 'REFERRAL',
            journey_started_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash);
        CREATE INDEX IF NOT EXISTS idx_users_journey_stage ON users(journey_stage);
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_jti VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_token_jti ON sessions(token_jti);
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active) WHERE is_active = TRUE;
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_journey_state (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            current_stage_id VARCHAR(50) NOT NULL,
            visit_number INT NOT NULL DEFAULT 1,
            journey_started_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT uk_user_journey_state_user UNIQUE (user_id),
            CONSTRAINT chk_visit_number CHECK (visit_number > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_journey_state_user ON user_journey_state(user_id);
        CREATE INDEX IF NOT EXISTS idx_journey_state_stage ON user_journey_state(current_stage_id);
        CREATE INDEX IF NOT EXISTS idx_journey_state_updated ON user_journey_state(last_updated_at DESC);
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_answers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            stage_id VARCHAR(50) NOT NULL,
            question_id VARCHAR(100) NOT NULL,
            answer_value JSONB NOT NULL,
            visit_number INT NOT NULL DEFAULT 1,
            answered_at TIMESTAMP NOT NULL DEFAULT NOW(),
            version INT NOT NULL DEFAULT 1,
            is_current BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT chk_answer_version CHECK (version > 0),
            CONSTRAINT chk_answer_visit CHECK (visit_number > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_answers_user_stage ON user_answers(user_id, stage_id);
        CREATE INDEX IF NOT EXISTS idx_answers_user_question ON user_answers(user_id, question_id);
        CREATE INDEX IF NOT EXISTS idx_answers_current ON user_answers(user_id, question_id) WHERE is_current = TRUE;
        CREATE INDEX IF NOT EXISTS idx_answers_answered_at ON user_answers(answered_at DESC);
        CREATE INDEX IF NOT EXISTS idx_answers_stage ON user_answers(stage_id);
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS stage_transitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            from_stage_id VARCHAR(50),
            to_stage_id VARCHAR(50) NOT NULL,
            from_visit_number INT,
            to_visit_number INT NOT NULL,
            transition_reason TEXT,
            matched_rule_id VARCHAR(100),
            matched_question_id VARCHAR(100),
            matched_answer_value JSONB,
            transitioned_at TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_transition_visits CHECK (
                from_visit_number IS NULL OR from_visit_number > 0
            ),
            CONSTRAINT chk_to_visit_number CHECK (to_visit_number > 0)
        );

        CREATE INDEX IF NOT EXISTS idx_transitions_user ON stage_transitions(user_id);
        CREATE INDEX IF NOT EXISTS idx_transitions_user_time ON stage_transitions(user_id, transitioned_at DESC);
        CREATE INDEX IF NOT EXISTS idx_transitions_from_stage ON stage_transitions(from_stage_id);
        CREATE INDEX IF NOT EXISTS idx_transitions_to_stage ON stage_transitions(to_stage_id);
        CREATE INDEX IF NOT EXISTS idx_transitions_time ON stage_transitions(transitioned_at DESC);
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_journey_path (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            stage_id VARCHAR(50) NOT NULL,
            visit_number INT NOT NULL DEFAULT 1,
            entered_at TIMESTAMP NOT NULL DEFAULT NOW(),
            exited_at TIMESTAMP,
            is_current BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT chk_path_visit_number CHECK (visit_number > 0),
            CONSTRAINT chk_path_exit_after_entry CHECK (
                exited_at IS NULL OR exited_at >= entered_at
            )
        );

        CREATE INDEX IF NOT EXISTS idx_journey_path_user ON user_journey_path(user_id);
        CREATE INDEX IF NOT EXISTS idx_journey_path_user_entered ON user_journey_path(user_id, entered_at DESC);
        CREATE INDEX IF NOT EXISTS idx_journey_path_current ON user_journey_path(user_id) WHERE is_current = TRUE;
        CREATE INDEX IF NOT EXISTS idx_journey_path_stage ON user_journey_path(stage_id);
        CREATE UNIQUE INDEX IF NOT EXISTS uk_user_journey_path_current
            ON user_journey_path(user_id)
            WHERE is_current = TRUE;
    """)

    await conn.close()
    yield


@pytest.fixture(scope="function")
async def db_pool(db_connection_params, db_schema) -> AsyncGenerator[asyncpg.Pool, None]:
    _ = db_schema

    pool = await asyncpg.create_pool(
        **db_connection_params,
        min_size=1,
        max_size=3,
    )
    yield pool
    await pool.close()


@pytest.fixture(scope="function", autouse=False)
async def clean_db(db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        try:
            await conn.execute("TRUNCATE users, user_journey_state, user_answers, stage_transitions, user_journey_path CASCADE")
        except Exception:
            pass
    yield
