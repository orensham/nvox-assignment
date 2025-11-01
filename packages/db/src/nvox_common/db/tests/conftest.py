# tests/conftest.py - Pytest Configuration and Fixtures
"""
Shared fixtures for all tests.

Fixtures provided:
- db: Database connection (integration tests)
- client: FastAPI test client
- test_user: Pre-created test user
- routing_engine: Routing engine instance
- postgres_container: PostgreSQL testcontainer
"""

from auth import get_password_hash, hash_email, encrypt_email
from routing_engine import RoutingEngine
from database import Database, init_database, close_database
from main import app
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from uuid import uuid4
import os
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


@pytest.fixture(scope="session")
async def db_schema(postgres_container: PostgresContainer):
    conn_url = postgres_container.get_connection_url()

    import urllib.parse
    parsed = urllib.parse.urlparse(conn_url)

    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:]
    )

    schema_file = os.path.join(os.path.dirname(__file__), '..', 'updated_database_schema.sql')

    await conn.execute("""
        -- Users table
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email_hash VARCHAR(64) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            is_anonymized BOOLEAN DEFAULT FALSE,
            anonymized_at TIMESTAMP NULL
        );
        
        -- Email vault
        CREATE TABLE email_vault (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            encrypted_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            last_accessed TIMESTAMP NULL,
            accessed_by VARCHAR(255) NULL
        );
        
        -- Journey state
        CREATE TABLE user_journey_state (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            current_stage_id VARCHAR(50) NOT NULL,
            started_at TIMESTAMP DEFAULT NOW(),
            last_updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- User answers
        CREATE TABLE user_answers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            stage_id VARCHAR(50) NOT NULL,
            question_id VARCHAR(100) NOT NULL,
            answer_value JSONB NOT NULL,
            answered_at TIMESTAMP DEFAULT NOW(),
            session_id UUID NOT NULL
        );
        
        -- Stage transitions
        CREATE TABLE stage_transitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            from_stage_id VARCHAR(50) NOT NULL,
            to_stage_id VARCHAR(50) NOT NULL,
            routing_rule JSONB NOT NULL,
            transitioned_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Journey path
        CREATE TABLE user_journey_path (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            stage_id VARCHAR(50) NOT NULL,
            visit_number INT NOT NULL CHECK (visit_number > 0),
            entered_at TIMESTAMP DEFAULT NOW(),
            exited_at TIMESTAMP NULL,
            next_stage_id VARCHAR(50) NULL,
            routing_rule_id INT NULL
        );
        
        -- Anonymization log
        CREATE TABLE anonymization_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            original_user_id UUID NOT NULL,
            anonymized_hash VARCHAR(64) NOT NULL,
            anonymized_at TIMESTAMP DEFAULT NOW(),
            requesting_ip INET NULL
        );
        
        -- Audit log
        CREATE TABLE audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(100) NOT NULL,
            details JSONB NOT NULL,
            ip_address INET NULL,
            timestamp TIMESTAMP DEFAULT NOW()
        );
        
        -- Indexes
        CREATE INDEX idx_users_email_hash ON users(email_hash);
        CREATE INDEX idx_journey_state_user ON user_journey_state(user_id);
        CREATE INDEX idx_answers_user_stage ON user_answers(user_id, stage_id);
        CREATE INDEX idx_transitions_user ON stage_transitions(user_id, transitioned_at DESC);
        CREATE INDEX idx_journey_path_user ON user_journey_path(user_id, entered_at);
        CREATE INDEX idx_audit_log_user ON audit_log(user_id, timestamp DESC);
    """)

    await conn.close()

    yield


@pytest.fixture(scope="class")
async def db_pool(postgres_container: PostgresContainer, db_schema) -> AsyncGenerator[asyncpg.Pool, None]:
    conn_url = postgres_container.get_connection_url()

    import urllib.parse
    parsed = urllib.parse.urlparse(conn_url)

    test_db_config = {
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "min_size": 5,
        "max_size": 10,
    }

    pool = await asyncpg.create_pool(**test_db_config)

    yield pool

    await pool.close()


@pytest.fixture(scope="function")
async def db(db_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Connection, None]:
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            yield conn


@pytest.fixture(scope="function")
async def clean_db(db: asyncpg.Connection):
    await db.execute("TRUNCATE users, user_journey_state, user_answers, stage_transitions, user_journey_path, email_vault, anonymization_log, audit_log CASCADE")
    yield db
