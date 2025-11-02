import redis.asyncio as redis
import os
from typing import Optional

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "db": int(os.getenv("REDIS_DB", "0")),
    "decode_responses": True,  # Automatically decode responses to strings
    "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
    "socket_timeout": int(os.getenv("REDIS_TIMEOUT", "5")),
    "socket_connect_timeout": int(os.getenv("REDIS_TIMEOUT", "5")),
}


class RedisClient:
    def __init__(self) -> None:
        self.config = REDIS_CONFIG
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[redis.ConnectionPool] = None

    async def connect(self) -> redis.Redis:
        if self.client is None:
            # Create connection pool
            self.pool = redis.ConnectionPool(**self.config)
            self.client = redis.Redis(connection_pool=self.pool)
            return self.client
        else:
            raise RuntimeError("Redis client is already initialized.")

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None
        if self.pool:
            await self.pool.aclose()
            self.pool = None

    async def check_redis_health(self) -> bool:
        if self.client is None:
            raise RuntimeError("Redis client is not initialized.")

        try:
            await self.client.ping()
            return True
        except Exception:
            return False
