from math import e
import asyncpg
import os
from typing import Any, Optional

DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "transplant_journey"),
    "user": os.getenv("DB_USER", "transplant_user"),
    "password": os.getenv("DB_PASSWORD", "change_me_in_production"),
    "min_size": int(os.getenv("DB_POOL_MIN", "10")),
    "max_size": int(os.getenv("DB_POOL_MAX", "50")),
    "command_timeout": int(os.getenv("DB_TIMEOUT", "60"))
}


class PostgresClient:
    def __init__(self) -> None:
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(**self.config)
        else:
            raise RuntimeError("Database pool is already initialized.")

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchRow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
