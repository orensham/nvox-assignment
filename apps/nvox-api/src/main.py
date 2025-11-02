from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Any
from pathlib import Path
from nvox_common.db.nvox_db_client import NvoxDBClient
from nvox_common.db.redis_client import RedisClient
import uvicorn

from api.main import api_router
from nvox_common.db.postgres_client import PostgresClient
from journey.config_loader import load_journey_config
from journey.rules_loader import load_routing_rules
import dependencies.db as db
import dependencies.redis as redis_dep


@asynccontextmanager
async def lifespan(_app: FastAPI) -> Any:
    db_client = PostgresClient()
    conn = await db_client.connect()
    _app.dependency_overrides[db.get_db_client] = lambda: NvoxDBClient(conn)

    redis_client = RedisClient()
    redis_conn = await redis_client.connect()
    _app.dependency_overrides[redis_dep.get_redis_client] = lambda: redis_client

    config_path = Path(__file__).parent / "config" / "journey_config.json"
    rules_path = Path(__file__).parent / "config" / "routing_rules.csv"

    await load_journey_config(config_path, redis_conn)
    await load_routing_rules(rules_path, redis_conn)

    try:
        yield
    finally:
        await db_client.disconnect()
        await redis_client.disconnect()


app = FastAPI(
    title="Nvox API",
    description="API service for Nvox application",
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)


app.include_router(api_router, prefix="/v1")


@app.get("/alive")
async def alive() -> dict[str, bool]:
    return {"alive": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
