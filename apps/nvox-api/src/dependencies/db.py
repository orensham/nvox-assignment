from nvox_common.db.postgres_client import PostgresClient


async def get_db_client() -> PostgresClient:
    raise NotImplementedError("Should be set as an override in application lifespan")
