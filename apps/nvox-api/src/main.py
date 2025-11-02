from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Any
from pathlib import Path
from nvox_common.db.nvox_db_client import NvoxDBClient
from nvox_common.db.redis_client import RedisClient
import uvicorn
import logging

from api.main import api_router
from nvox_common.db.postgres_client import PostgresClient
from journey.config_loader import load_journey_config
from repositories.schema_validator import validate_all_schemas
import dependencies.db as db
import dependencies.redis as redis_dep

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> Any:
    db_client = PostgresClient()
    conn = await db_client.connect()
    nvox_db_client = NvoxDBClient(conn)
    _app.dependency_overrides[db.get_db_client] = lambda: nvox_db_client

    logger.info("Validating database schema...")
    try:
        await validate_all_schemas(nvox_db_client)
        logger.info("Database schema validation successful")
    except Exception as e:
        logger.error(f"Database schema validation failed: {e}")
        logger.error("Application startup aborted due to schema mismatch")
        raise

    redis_client = RedisClient()
    redis_conn = await redis_client.connect()
    _app.dependency_overrides[redis_dep.get_redis_client] = lambda: redis_client

    config_path = Path(__file__).parent / "config" / "journey_config.json"

    await load_journey_config(config_path, redis_conn)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")


@app.get("/alive")
async def alive() -> dict[str, bool]:
    return {"alive": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
