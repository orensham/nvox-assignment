import asyncpg
from typing import Any, Optional
from contextlib import asynccontextmanager


class NvoxDBClient:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchRow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    @asynccontextmanager
    async def transaction(self):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield TransactionClient(conn)


class TransactionClient:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        return await self.conn.fetch(query, *args)

    async def fetchRow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        return await self.conn.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        return await self.conn.execute(query, *args)
