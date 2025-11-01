from math import e
import asyncpg
import os
from typing import Optional

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
        self.config = DATABASE_CONFIG
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> asyncpg.Pool:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(**self.config)
            return self.pool
        else:
            raise RuntimeError("Database pool is already initialized.")

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def check_db_health(self) -> bool:
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized.")

        try:
            async with self.pool.acquire() as connection:
                await connection.execute("SELECT 1;")
            return True
        except Exception:
            return False
