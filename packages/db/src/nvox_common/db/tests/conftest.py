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
            await conn.execute("TRUNCATE users CASCADE")
        except Exception:
            pass
    yield
