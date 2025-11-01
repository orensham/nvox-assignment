from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Any
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    # initilize Postgres DB client
    print("Starting up application")

    try:
        yield
    finally:
        print("Shutting down application")


app = FastAPI(
    title="Nvox API",
    description="API service for Nvox application",
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=lifespan,
)


@app.get("/alive")
async def alive() -> dict[str, bool]:
    return {"alive": True}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
