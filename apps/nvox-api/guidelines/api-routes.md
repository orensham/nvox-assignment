# API Routes Guidelines

This document outlines conventions and best practices for creating new API routes in the nvox-api project.

## Table of Contents

- [Router Structure](#router-structure)
- [Naming Conventions](#naming-conventions)
- [Request and Response Models](#request-and-response-models)
- [HTTP Methods and Status Codes](#http-methods-and-status-codes)
- [Dependency Injection](#dependency-injection)
- [Authentication and Authorization](#authentication-and-authorization)
- [Error Handling](#error-handling)
- [Route Documentation](#route-documentation)
- [Best Practices](#best-practices)
- [Anti-patterns](#anti-patterns)
- [Checklist for New Routes](#checklist-for-new-routes)

## Router Structure

### DO: Organize Routes by Domain

Group related endpoints into separate router files based on business domain:

```python
# src/api/routes/auth_router.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/signup")
async def signup(...):
    pass

@router.post("/login")
async def login(...):
    pass

@router.post("/logout")
async def logout(...):
    pass
```

```python
# src/api/routes/journey_router.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/journey/current")
async def get_current_journey(...):
    pass

@router.post("/journey/answer")
async def submit_answer(...):
    pass
```

### DO: Register Routers with Prefixes

Register routers in `main.py` with appropriate prefixes and tags:

```python
# src/main.py
from api.routes import auth_router, journey_router

app.include_router(
    auth_router.router,
    prefix="/v1",
    tags=["Authentication"]
)

app.include_router(
    journey_router.router,
    prefix="/v1",
    tags=["Journey"]
)
```

### DON'T: Mix Unrelated Endpoints

```python
router = APIRouter()

@router.post("/signup")
async def signup(...):
    pass

@router.get("/journey/current")  # Different domain!
async def get_current_journey(...):
    pass
```

## Naming Conventions

### DO: Use Clear, RESTful Endpoint Names

```python
@router.get("/journey/current")           # GET current state
@router.post("/journey/answer")            # POST a new answer
@router.get("/journey/history")            # GET historical data
@router.get("/journey/stage/{stage_id}")   # GET specific resource
@router.delete("/user")                    # DELETE user resource
```

### DO: Use Consistent URL Patterns

- Resources should be **nouns**, not verbs
- Use **plural** for collections: `/users`, `/answers`
- Use **singular** for specific resources: `/user`, `/journey/current`
- Use **kebab-case** for multi-word endpoints: `/journey-history` (or nested paths)

```python
@router.get("/users")                 # Collection
@router.get("/users/{user_id}")       # Specific resource
@router.post("/journey/answer")       # Action on resource
@router.post("/journey/continue")     # Explicit action
```

### DON'T: Use Verbs in Endpoint Names

```python
@router.post("/create-user")       # Use POST /users
@router.get("/get-journey")        # Use GET /journey/current
@router.post("/submit-answer")     # Use POST /journey/answer
@router.post("/delete-account")    # Use DELETE /user
```

### DO: Use Path Parameters for Resource IDs

```python
@router.get("/journey/stage/{stage_id}")
async def get_stage_details(
    stage_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    pass
```

### DO: Use Query Parameters for Filtering

```python
@router.get("/journey/history")
async def get_journey_history(
    limit: int = 10,
    offset: int = 0,
    current_user: TokenData = Depends(get_current_user)
):
    pass
```

## Request and Response Models

### DO: Define Pydantic Models for All Requests and Responses

```python
# src/api/models/auth.py
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class SignupResponse(BaseModel):
    success: bool
    user_id: UUID
    email: str
    message: str
    journey: dict
```

### DO: Use Type Annotations and Response Models

```python
@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    user_repository: UserRepository = Depends(get_user_repository),
) -> SignupResponse:
    return SignupResponse(...)
```

### DON'T: Use Generic Dictionaries

```python
@router.post("/signup")
async def signup(request: dict) -> dict:
    email = request.get("email")  # No validation!
    password = request.get("password")  # No constraints!
    return {"status": "ok"}  # Unclear response structure
```

### DO: Include Success Flags and Messages

```python
class LoginResponse(BaseModel):
    success: bool
    access_token: str
    token_type: str
    expires_in: int
    user_id: UUID
    message: str

return LoginResponse(
    success=True,
    access_token=token,
    token_type="bearer",
    expires_in=3600,
    user_id=user.id,
    message="Login successful"
)
```

## HTTP Methods and Status Codes

### DO: Use Appropriate HTTP Methods

| Method | Purpose | Example |
|--------|---------|---------|
| GET | Retrieve data | `GET /journey/current` |
| POST | Create resource or action | `POST /signup`, `POST /journey/answer` |
| PUT | Replace entire resource | `PUT /user/{id}` |
| PATCH | Update partial resource | `PATCH /user/{id}` |
| DELETE | Remove resource | `DELETE /user` |

### DO: Return Appropriate Status Codes

```python
@router.post("/signup", status_code=status.HTTP_201_CREATED)  # Resource created
@router.get("/journey/current", status_code=status.HTTP_200_OK)  # Success
@router.delete("/user", status_code=status.HTTP_200_OK)  # Deleted with response
@router.post("/journey/answer", status_code=status.HTTP_200_OK)  # Action completed

raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,  # Resource conflict
    detail="User with this email already exists"
)

raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,  # Invalid credentials
    detail="Invalid credentials"
)

raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,  # Missing auth
    detail="Not authenticated"
)

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,  # Resource not found
    detail="Journey state not found"
)

raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,  # Validation error
    detail="Invalid answer value"
)
```

### Common Status Codes

- **200 OK** - Successful GET, PUT, PATCH, DELETE (with response body)
- **201 Created** - Successful POST that creates a resource
- **204 No Content** - Successful DELETE (no response body)
- **400 Bad Request** - Invalid request format
- **401 Unauthorized** - Invalid authentication credentials
- **403 Forbidden** - Missing authentication or insufficient permissions
- **404 Not Found** - Resource doesn't exist
- **409 Conflict** - Resource already exists or conflict with current state
- **422 Unprocessable Entity** - Validation error on valid JSON
- **500 Internal Server Error** - Server error (handled by exception handlers)

## Dependency Injection

### DO: Use FastAPI's Dependency Injection

```python
@router.post("/signup")
async def signup(
    request: SignupRequest,
    user_repository: UserRepository = Depends(get_user_repository),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
) -> SignupResponse:
    await user_repository.create_user(...)
    await journey_repository.create_journey_state(...)
```

### DO: Define Dependencies in Separate Module

```python
# src/dependencies/repositories.py
from nvox_common.db.nvox_db_client import NvoxDBClient

async def get_user_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> UserRepository:
    return UserRepository(db_client)

async def get_journey_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> JourneyRepository:
    return JourneyRepository(db_client)
```

### DON'T: Create Dependencies Inline

```python
@router.post("/signup")
async def signup(request: SignupRequest):
    db_client = PostgresClient()  # Tightly coupled!
    user_repo = UserRepository(db_client)  # Can't be mocked!
    await user_repo.create_user(...)
```

## Authentication and Authorization

### DO: Protect Routes with Authentication

```python
from dependencies.auth import get_current_user

@router.get("/journey/current")
async def get_current_journey(
    current_user: TokenData = Depends(get_current_user),  # Required auth
    journey_repository: JourneyRepository = Depends(get_journey_repository),
):
    journey = await journey_repository.get_user_journey_state(current_user.user_id)
    return journey
```

### DO: Verify Resource Ownership

```python
@router.get("/journey/stage/{stage_id}")
async def get_stage_details(
    stage_id: str,
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
):
    stage = await journey_repository.get_stage_for_user(
        user_id=current_user.user_id,
        stage_id=stage_id
    )

    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage not found or not accessible"
        )

    return stage
```

### DON'T: Allow Unauthenticated Access to Protected Data

```python
@router.get("/journey/current")
async def get_current_journey(user_id: UUID):  # Anyone can access any user's journey!
    journey = await journey_repository.get_user_journey_state(user_id)
    return journey
```

### Public vs Protected Routes

```python
# Public routes (no authentication)
@router.post("/signup")          # New user registration
@router.post("/login")           # User authentication
@router.get("/health")           # Health check

# Protected routes (require authentication)
@router.post("/logout")          # Requires valid token
@router.get("/journey/current")  # Requires user context
@router.post("/journey/answer")  # Requires user context
@router.delete("/user")          # Requires user context
```

## Error Handling

### DO: Provide Meaningful Error Messages

```python
if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Journey state not found. Please contact support."
    )

if not is_valid:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Invalid answer: {error_message}"
    )
```

### DO: Handle Exceptions Gracefully

```python
try:
    result = await journey_repository.perform_stage_transition(...)
except ValueError as e:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(e)
    )
except Exception as e:
    logger.error(f"Unexpected error in stage transition: {e}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An internal error occurred"
    )
```

### DON'T: Expose Internal Details in Errors

```python
try:
    await db_client.execute(query)
except asyncpg.PostgresError as e:
    raise HTTPException(
        status_code=500,
        detail=f"Database error: {e.sqlstate} - {e.message}"  # Exposes DB internals!
    )
```

## Best Practices

### 1. Keep Routes Thin

Routes should orchestrate, not implement:

```python
@router.post("/journey/continue")
async def continue_journey(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
):
    journey_state = await journey_repository.get_user_journey_state(current_user.user_id)

    if not journey_state:
        raise HTTPException(status_code=404, detail="Journey state not found")

    # Repository handles the complex logic
    result = await journey_repository.evaluate_and_transition(
        user_id=current_user.user_id,
        current_stage=journey_state.current_stage_id
    )

    return result
```

### 2. Use Consistent Response Structures

```python
class BaseResponse(BaseModel):
    success: bool
    message: str

class JourneyResponse(BaseResponse):
    current_stage: str
    questions: list[dict]
    

class AnswerResponse(BaseResponse):
    answer_saved: bool
    transitioned: bool
    
```

### 3. Version Your API

```python
app.include_router(auth_router.router, prefix="/v1", tags=["Authentication"])
app.include_router(journey_router.router, prefix="/v1", tags=["Journey"])

```

### 4. Use Proper Logging

```python
import logging

logger = logging.getLogger(__name__)

@router.post("/journey/answer")
async def submit_answer(...):
    logger.info(f"User {current_user.user_id} submitting answer for question {request.question_id}")

    try:
        result = await journey_repository.save_answer(...)
        logger.info(f"Answer saved successfully for user {current_user.user_id}")
        return result
    except Exception as e:
        logger.error(f"Error saving answer: {e}", exc_info=True)
        raise
```

## Anti-patterns

### Returning Different Response Types

```python
@router.get("/journey/current")
async def get_current_journey(...):
    if not journey:
        return {"error": "Not found"}  # Different structure!
    return {"data": journey}  # Different structure!
```

### Not Using Type Hints

```python
@router.post("/signup")
async def signup(request):  # What is request?
    user_id = create_user(request)  # What does this return?
    return user_id  # What type is this?
```

###  Mixing Business Logic in Routes

```python
@router.post("/journey/answer")
async def submit_answer(...):
    # Complex validation logic here
    if answer_value > 100 or answer_value < 0:
        raise HTTPException(...)

    # Complex calculation logic here
    score = calculate_risk_score(answer_value)

    # Complex database operations here
    await db.execute("UPDATE...")
    await db.execute("INSERT...")

    # This should all be in a repository or service!
```

### Not Handling Edge Cases

```python
@router.get("/journey/current")
async def get_current_journey(...):
    journey = await journey_repository.get_user_journey_state(user_id)
    # What if journey is None? 
    return journey.current_stage  # AttributeError if journey is None!
```

## Checklist for New Routes

Before submitting a PR with new routes, verify:

- [ ] Route is in the correct router file (auth, journey, etc.)
- [ ] Endpoint name follows RESTful conventions (noun-based, not verb-based)
- [ ] HTTP method is appropriate (GET, POST, PUT, PATCH, DELETE)
- [ ] Status code is explicitly set and appropriate
- [ ] Request model defined with Pydantic (if accepting body)
- [ ] Response model defined with Pydantic
- [ ] Type hints on all parameters and return type
- [ ] Docstring explains what the route does
- [ ] Authentication dependency added if route is protected
- [ ] User ownership verified for resource access
- [ ] Error cases handled with appropriate status codes
- [ ] Error messages are clear and don't expose internal details
- [ ] Repositories injected via dependencies (not created inline)
- [ ] Business logic delegated to repositories/services
- [ ] Route is registered in `main.py` with appropriate prefix and tags
- [ ] Logging added for important operations
- [ ] Consider idempotency for state-changing operations

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [REST API Best Practices](https://restfulapi.net/)
