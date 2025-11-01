import asyncpg
from typing import Any, Optional


class NvoxDBClient:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchRow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
