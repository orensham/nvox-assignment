# Dependencies Guidelines

Dependencies in nvox-api are used for dependency injection throughout the application.

## Definition

Dependencies are functions that initialize repositories and utilities based on runtime settings, allowing them to be injected where needed.

## Purpose

- Provide easy access to configured components
- Support dependency injection patterns
- Make testing easier by allowing components to be mocked or replaced
- Manage lifecycle of components that need initialization

## Structure

```
src/
└── dependencies/
    ├── auth.py                # Authentication dependencies
    ├── db.py                  # Database client dependency
    └── repositories.py        # Repository dependencies
```

## Example

```python
# src/dependencies/repositories.py
from fastapi import Depends
from nvox_common.db.nvox_db_client import NvoxDBClient
from repositories.user_repository import UserRepository
from repositories.session_repository import SessionRepository
from repositories.journey_repository import JourneyRepository
from dependencies.db import get_db_client


def get_user_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> UserRepository:
    return UserRepository(db_client)


def get_session_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> SessionRepository:
    return SessionRepository(db_client)


def get_journey_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> JourneyRepository:
    return JourneyRepository(db_client)
```

## Using Dependencies in Routes

Inject dependencies into route handlers using FastAPI's `Depends`:

```python
# src/api/routes/auth_router.py
from fastapi import APIRouter, Depends
from repositories.user_repository import UserRepository
from repositories.journey_repository import JourneyRepository
from dependencies.repositories import get_user_repository, get_journey_repository
from api.models.auth import SignupRequest, SignupResponse

router = APIRouter()

@router.post("/signup", response_model=SignupResponse)
async def signup(
    request: SignupRequest,
    user_repository: UserRepository = Depends(get_user_repository),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> SignupResponse:
    user = await user_repository.create_user_with_journey(...)
    return SignupResponse(...)
```

## Authentication Dependency

The `get_current_user` dependency extracts and validates JWT tokens:

```python
# src/dependencies/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID
from api.models.auth import TokenData
from utils.jwt import decode_access_token
from repositories.session_repository import SessionRepository
from dependencies.repositories import get_session_repository

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_repository: SessionRepository = Depends(get_session_repository)
) -> TokenData:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated"
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    jti = payload.get("jti")
    is_active = await session_repository.is_session_active(jti)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    return TokenData(user_id=UUID(payload["sub"]), email_hash=payload["email_hash"])
```

**Using authentication in protected routes**:

```python
from dependencies.auth import get_current_user
from api.models.auth import TokenData

@router.get("/journey/current")
async def get_current_journey(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
):
    journey = await journey_repository.get_user_journey_state(current_user.user_id)
    return journey
```

## Best Practices

1. **Keep Dependencies Simple**: Dependencies should be simple factory functions that create and return instances.

2. **Layer Dependencies**: Build dependencies in layers (db → repositories → services) to avoid circular dependencies.

3. **Type Hints**: Always use proper type hints for dependency return types to enable IDE autocomplete.

4. **Testing**: Use FastAPI's dependency override system to mock components during testing:

    ```python
    import pytest
    from unittest.mock import AsyncMock

    @pytest.fixture
    def mock_user_repository(test_client):
        mock_repo = AsyncMock(spec=UserRepository)
        app.dependency_overrides[get_user_repository] = lambda: mock_repo
        yield mock_repo
        del app.dependency_overrides[get_user_repository]
    ```

## Anti-patterns

- Don't create repository instances directly in routes - always use dependency injection
- Avoid circular dependencies between dependency functions
- Don't add complex business logic in dependency functions - keep them as simple factory functions
- Don't manually manage database connections - let the dependency system handle lifecycle
