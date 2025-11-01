from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Any
from nvox_common.db.nvox_db_client import NvoxDBClient
import uvicorn

from api.main import api_router
from nvox_common.db.postgres_client import PostgresClient
import dependencies.db as db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> Any:
    conn = await PostgresClient().connect()
    _app.dependency_overrides[db.get_db_client] = lambda: NvoxDBClient(conn)
    try:
        yield
    finally:
        await conn.disconnect()


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
