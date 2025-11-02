from nvox_common.db.redis_client import RedisClient


async def get_redis_client() -> RedisClient:
    raise NotImplementedError("Should be set as an override in application lifespan")
