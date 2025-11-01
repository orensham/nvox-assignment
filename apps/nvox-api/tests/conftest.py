import dependencies.db as db_deps
from repositories.user_repository import UserRepository
from nvox_common.db.nvox_db_client import NvoxDBClient
from main import app
import pytest
import sys
from pathlib import Path
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest_plugins = ["nvox_common.db.tests.conftest"]


@pytest.fixture(scope="function")
def user_repository(db_pool) -> UserRepository:
    db_client = NvoxDBClient(db_pool)
    return UserRepository(db_client)


@pytest.fixture(scope="function")
async def test_client(db_pool) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[db_deps.get_db_client] = lambda: NvoxDBClient(db_pool)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_email() -> str:
    return "test@example.com"


@pytest.fixture
def sample_password() -> str:
    return "TestPass1"


@pytest.fixture
def another_email() -> str:
    return "another@example.com"
