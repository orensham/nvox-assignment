# Repositories Guidelines

Repositories provide an abstraction layer between your business logic and data storage.

## Definition

A repository is an implementation of a storage interface for a specific business model. Repositories hide the actual storage implementation details (PostgreSQL, Redis, etc.) from the rest of the application.

## Naming
- Repositories should be named after the business model they operate on, suffixed with `Repository`. For example:
  - `UserRepository` for operations related to the `User` model
  - `JourneyRepository` for operations related to journey state and answers
  - `SessionRepository` for operations related to user sessions

## Structure

```
src/
└── repositories/
    ├── db_models.py           # Pydantic models for database rows
    ├── user_repository.py     # User operations
    ├── journey_repository.py  # Journey state and answers
    └── session_repository.py  # Session management
```

## Example: UserRepository

```python
# src/repositories/user_repository.py
from typing import Optional
from uuid import UUID
from datetime import datetime
from nvox_common.db.nvox_db_client import NvoxDBClient
from .db_models import UserDB, optional_record_to_model


class UserRepository:
    def __init__(self, db_client: NvoxDBClient):
        self.db_client = db_client

    async def get_user_by_email_hash(self, email_hash: str) -> Optional[UserDB]:
        row = await self.db_client.fetchRow(
            "SELECT * FROM users WHERE email_hash = $1",
            email_hash
        )
        return optional_record_to_model(row, UserDB)

    async def user_exists_by_email_hash(self, email_hash: str) -> bool:
        result = await self.db_client.fetchRow(
            "SELECT id FROM users WHERE email_hash = $1",
            email_hash
        )
        return result is not None

    async def create_user(
        self,
        user_id: UUID,
        email_hash: str,
        password_hash: str,
        journey_stage: str = "REFERRAL",
        journey_started_at: Optional[datetime] = None
    ) -> None:
        if journey_started_at is None:
            journey_started_at = datetime.utcnow()

        await self.db_client.execute(
            """
            INSERT INTO users (id, email_hash, password_hash, journey_stage, journey_started_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            email_hash,
            password_hash,
            journey_stage,
            journey_started_at
        )

    async def get_user_by_id(self, user_id: UUID) -> Optional[UserDB]:
        row = await self.db_client.fetchRow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )
        return optional_record_to_model(row, UserDB)

    async def update_journey_stage(self, user_id: UUID, new_stage: str) -> None:
        await self.db_client.execute(
            "UPDATE users SET journey_stage = $1, updated_at = NOW() WHERE id = $2",
            new_stage,
            user_id
        )
```

## Using Transactions

For operations that require multiple database changes to succeed or fail together, use transactions:

```python
async def create_user_with_journey(
    self,
    user_id: UUID,
    email_hash: str,
    password_hash: str,
    entry_stage: str,
    journey_started_at: datetime
) -> None:
    async with self.db_client.transaction() as tx:
        await tx.execute(
            """
            INSERT INTO users (id, email_hash, password_hash, journey_stage, journey_started_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            email_hash,
            password_hash,
            entry_stage,
            journey_started_at
        )

        await tx.execute(
            """
            INSERT INTO user_journey_state (user_id, current_stage_id, visit_number, journey_started_at)
            VALUES ($1, $2, 1, $3)
            """,
            user_id,
            entry_stage,
            journey_started_at
        )

        await tx.execute(
            """
            INSERT INTO user_journey_path (user_id, stage_id, visit_number, is_current)
            VALUES ($1, $2, 1, TRUE)
            """,
            user_id,
            entry_stage
        )

        await tx.execute(
            """
            INSERT INTO stage_transitions (
                user_id, from_stage_id, to_stage_id, from_visit_number,
                to_visit_number, transition_reason
            )
            VALUES ($1, NULL, $2, NULL, 1, $3)
            """,
            user_id,
            entry_stage,
            "Initial signup"
        )
```

## Database Models

Repositories use Pydantic models to represent database rows. This provides type safety and runtime validation:

```python
# src/repositories/db_models.py
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class UserDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email_hash: str
    password_hash: str
    journey_stage: str
    journey_started_at: datetime
    created_at: datetime
    updated_at: datetime


class SessionDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    token_jti: str
    expires_at: datetime
    created_at: datetime
    revoked_at: Optional[datetime] = None
    is_active: bool


class UserJourneyStateDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    current_stage_id: str
    visit_number: int = Field(ge=1)
    journey_started_at: datetime
    last_updated_at: datetime
    created_at: datetime
```

### Helper Functions for Type Conversion

Convert asyncpg records to Pydantic models:

```python
# src/repositories/db_models.py
from typing import Any

def record_to_model(record: Any, model_class: type[BaseModel]) -> BaseModel:
    if record is None:
        raise ValueError("Cannot convert None record to model")
    return model_class(**dict(record))


def optional_record_to_model(
    record: Any | None,
    model_class: type[BaseModel]
) -> BaseModel | None:
    if record is None:
        return None
    return record_to_model(record, model_class)


def records_to_models(records: list[Any], model_class: type[BaseModel]) -> list[BaseModel]:
    return [record_to_model(record, model_class) for record in records]
```

**Usage in repositories**:

```python
async def get_user_by_id(self, user_id: UUID) -> Optional[UserDB]:
    row = await self.db_client.fetchRow(
        "SELECT * FROM users WHERE id = $1",
        user_id
    )
    return optional_record_to_model(row, UserDB)  


async def get_current_answers(self, user_id: UUID) -> List[UserAnswerDB]:
    rows = await self.db_client.fetch(
        "SELECT * FROM user_answers WHERE user_id = $1 AND is_current = TRUE",
        user_id
    )
    return records_to_models(rows, UserAnswerDB)  
```

## Best Practices

1. **Type Safety with Pydantic Models**: Always use Pydantic DB models for type safety. This catches schema mismatches early and provides IDE autocomplete.

2. **Parameterized Queries**: Always use parameterized queries (`$1`, `$2`, etc.) to prevent SQL injection:
   ```python
   # DO: Use parameterized queries
   await self.db_client.fetchRow(
       "SELECT * FROM users WHERE email_hash = $1",
       email_hash
   )

   # DON'T: Use string formatting
   await self.db_client.fetchRow(
       f"SELECT * FROM users WHERE email_hash = '{email_hash}'" 
   )
   ```

3. **Transactions for Multi-Step Operations**: Use transactions when multiple database operations must succeed or fail together:
   ```python
   async with self.db_client.transaction() as tx:
       await tx.execute("INSERT INTO users ...")
       await tx.execute("INSERT INTO user_journey_state ...")
   ```

4. **Helper Functions for Type Conversion**: Use helper functions like `optional_record_to_model()` and `records_to_models()` to keep code DRY.

5. **Clear Return Types**: Always specify return types (`Optional[UserDB]`, `List[UserAnswerDB]`, etc.) for better IDE support and type checking.

6. **Storage Technology Agnostic**: Services using repositories should not be aware of the underlying storage technology (PostgreSQL, Redis, etc.).

## Anti-patterns

- Don't expose database-specific details (asyncpg Records, SQL queries) to services or routes
- Avoid mixing business logic with data access code - keep repositories focused on data operations
- Don't bypass repositories by accessing the database directly from routes or services
- Don't use string formatting for queries - always use parameterized queries
- Don't return raw asyncpg Records - convert to Pydantic models for type safety

## Method Naming Conventions

Repositories should follow consistent CRUD naming patterns:

- **Get single record**: `get_<entity>_by_<property>`
  - Examples: `get_user_by_email_hash()`, `get_user_by_id()`

- **Check existence**: `<entity>_exists_by_<property>`
  - Examples: `user_exists_by_email_hash()`, `session_exists()`

- **List multiple records**: `get_<entities>` or `get_<entities>_by_<property>`
  - Examples: `get_current_answers()`, `get_transition_history()`

- **Create**: `create_<entity>`
  - Examples: `create_user()`, `create_journey_state()`

- **Update**: `update_<property>` or `update_<entity>`
  - Examples: `update_journey_stage()`, `update_user()`

- **Delete/Remove**: `delete_<entity>` or `remove_<entity>`
  - Examples: `anonymize_user_data()`, `revoke_session()`

- **Complex operations**: Use descriptive action names
  - Examples: `create_user_with_journey()`, `perform_stage_transition()`, `save_answer()`

## Repository Principles

1. **Single Responsibility**: Each repository manages one entity or closely related entities
   - `UserRepository`: User account operations
   - `JourneyRepository`: Journey state, answers, transitions, path
   - `SessionRepository`: Session management

2. **Type Safety**: Use Pydantic models for all database row representations

3. **Implementation Hiding**: The underlying database technology (PostgreSQL, asyncpg) should not leak outside the repository

4. **Transactional Integrity**: Complex operations that modify multiple tables should use transactions to maintain data consistency
