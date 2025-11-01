# Security Guidelines

This document outlines security conventions and best practices for developing new API routes and repository methods in the nvox-api project.

## Table of Contents

- [SQL Injection Prevention](#sql-injection-prevention)
- [PII (Personally Identifiable Information) Protection](#pii-personally-identifiable-information-protection)
- [Password Security](#password-security)
- [Input Validation](#input-validation)
- [API Endpoint Security](#api-endpoint-security)
- [Error Handling](#error-handling)
- [Common Vulnerabilities to Avoid](#common-vulnerabilities-to-avoid)

## SQL Injection Prevention

### DO: Use Parameterized Queries

**Always** use parameterized queries with PostgreSQL placeholders (`$1`, `$2`, `$3`, etc.):

```python
# CORRECT - Safe from SQL injection
async def get_user_by_email(self, email_hash: str):
    return await self.db_client.fetchRow(
        "SELECT id, email_hash FROM users WHERE email_hash = $1",
        email_hash
    )
```

```python
# CORRECT - Multiple parameters
async def create_user(self, user_id: UUID, email_hash: str, password_hash: str):
    await self.db_client.execute(
        "INSERT INTO users (id, email_hash, password_hash) VALUES ($1, $2, $3)",
        user_id,
        email_hash,
        password_hash
    )
```

### DON'T: Use String Interpolation

**Never** build SQL queries using f-strings, string concatenation, or format():

```python
# WRONG - Vulnerable to SQL injection!
async def get_user_by_email(self, email: str):
    query = f"SELECT * FROM users WHERE email = '{email}'"
    return await self.db_client.fetchRow(query)

# WRONG - Vulnerable to SQL injection!
async def get_user_by_email(self, email: str):
    query = "SELECT * FROM users WHERE email = '" + email + "'"
    return await self.db_client.fetchRow(query)

# WRONG - Vulnerable to SQL injection!
async def get_user_by_email(self, email: str):
    query = "SELECT * FROM users WHERE email = '%s'" % email
    return await self.db_client.fetchRow(query)
```

### ⚠️ Special Case: Dynamic Table/Column Names

If you need dynamic table or column names (rare), use **whitelisting**:

```python
# CORRECT - Whitelist validation for table names
ALLOWED_TABLES = {"users", "preferences", "sessions"}

async def get_records(self, table_name: str):
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table_name}")

    # Safe because table_name is validated against whitelist
    query = f"SELECT * FROM {table_name} WHERE active = $1"
    return await self.db_client.fetch(query, True)
```

## PII (Personally Identifiable Information) Protection

### DO: Hash PII Before Storage

**Always** hash emails and other PII before storing in the database:

```python
# CORRECT - Hash email before storage
from utils.hashing import hash_email

async def create_user(self, email: str, password: str):
    email_hash = hash_email(email)  # SHA-256 hash
    password_hash = hash_password(password)  # bcrypt hash

    await self.user_repository.create_user(
        user_id=uuid4(),
        email_hash=email_hash,
        password_hash=password_hash
    )
```

### DON'T: Store Plain Text PII

**Never** store emails, phone numbers, or other PII in plain text:

```python
# WRONG - Stores email in plain text
await self.db_client.execute(
    "INSERT INTO users (email, password_hash) VALUES ($1, $2)",
    email,  # Plain text email - GDPR violation!
    password_hash
)
```

### DO: Return Hashed Values in API Responses

```python
# CORRECT - Return hashed email in response
return {
    "user_id": str(user_id),
    "email": email_hash,  # Hashed, not plain text
    "message": "Account created successfully"
}
```

### DON'T: Log or Return PII

```python
# WRONG - Logs plain text email
logger.info(f"User created: {email}")

# WRONG - Returns plain text email
return {"email": email}
```

## Password Security

### DO: Use Bcrypt for Password Hashing

```python
# CORRECT - Use bcrypt with automatic salting
from utils.hashing import hash_password, verify_password

async def create_user(self, email: str, password: str):
    password_hash = hash_password(password)  # bcrypt automatically salts
    # ... store password_hash
```

### DO: Verify Passwords Securely

```python
# CORRECT - Use constant-time comparison
from utils.hashing import verify_password

async def authenticate_user(self, email: str, password: str):
    user = await self.user_repository.get_user_by_email_hash(hash_email(email))
    if user is None:
        return False

    return verify_password(password, user["password_hash"])
```

### DON'T: Use Weak Hashing Algorithms

```python
#  WRONG - MD5 is broken
password_hash = hashlib.md5(password.encode()).hexdigest()

#  WRONG - SHA-256 without salt is vulnerable to rainbow tables
password_hash = hashlib.sha256(password.encode()).hexdigest()

#  WRONG - Plain text storage
password_hash = password
```

### DON'T: Return Password Hashes

```python
# WRONG - Never return password hashes in API responses
return {
    "user_id": user_id,
    "password_hash": user["password_hash"]  # Security risk!
}
```

## Input Validation

### DO: Use Pydantic Models for Validation

```python
#  CORRECT - Pydantic validates input automatically
from pydantic import BaseModel, EmailStr, Field

class SignupRequest(BaseModel):
    email: EmailStr  # Validates email format
    password: str = Field(min_length=8, max_length=12)  # Enforces length

@router.post("/signup")
async def signup(request: SignupRequest):
    # request.email and request.password are already validated
    ...
```

### DO: Validate Business Logic Constraints

```python
# CORRECT - Additional business logic validation
async def update_journey_stage(self, user_id: UUID, new_stage: str):
    VALID_STAGES = ["REFERRAL", "EVALUATION", "TESTING", "LISTING"]

    if new_stage not in VALID_STAGES:
        raise ValueError(f"Invalid journey stage: {new_stage}")

    await self.db_client.execute(
        "UPDATE users SET journey_stage = $1 WHERE id = $2",
        new_stage,
        user_id
    )
```

### DON'T: Trust User Input

```python
#  WRONG - No validation on user input
async def update_journey_stage(self, user_id: UUID, new_stage: str):
    # Accepts any string, including invalid stages
    await self.db_client.execute(
        "UPDATE users SET journey_stage = $1 WHERE id = $2",
        new_stage,
        user_id
    )
```

## API Endpoint Security

### DO: Use HTTP Status Codes Correctly

```python
#  CORRECT - Appropriate status codes
from fastapi import HTTPException

@router.post("/signup", status_code=201)
async def signup(request: SignupRequest):
    if await user_repository.user_exists_by_email_hash(hash_email(request.email)):
        raise HTTPException(
            status_code=409,  # Conflict
            detail="User with this email already exists"
        )

    # ... create user
    return {"success": True, ...}
```

###  DON'T: Expose Sensitive Error Details

```python
# WRONG - Exposes internal details
try:
    await db_client.execute(query)
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Database error: {str(e)}"  # Exposes DB structure!
    )

# CORRECT - Generic error message
try:
    await db_client.execute(query)
except Exception as e:
    logger.error(f"Database error: {str(e)}")  # Log internally
    raise HTTPException(
        status_code=500,
        detail="An internal error occurred"  # Generic to user
    )
```

### DO: Use HTTPS in Production

```python
#  CORRECT - Force HTTPS redirect in production
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

## Common Vulnerabilities to Avoid

### 2. Insecure Direct Object References (IDOR)

```python
# WRONG - No authorization check
@router.get("/users/{user_id}")
async def get_user(user_id: UUID):
    return await user_repository.get_user_by_id(user_id)  # Any user can access any user!

# CORRECT - Verify ownership
@router.get("/users/{user_id}")
async def get_user(user_id: UUID, current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await user_repository.get_user_by_id(user_id)
```

### 3. Mass Assignment

```python
# WRONG - Allows setting any field
class UserUpdate(BaseModel):
    pass

@router.patch("/users/{user_id}")
async def update_user(user_id: UUID, data: dict):
    # User could set is_admin=True, balance=1000000, etc.
    await user_repository.update_user(user_id, **data)

# CORRECT - Explicit field whitelist
class UserUpdate(BaseModel):
    journey_stage: Optional[str] = None
    # Only allowed fields are defined

@router.patch("/users/{user_id}")
async def update_user(user_id: UUID, data: UserUpdate):
    if data.journey_stage:
        await user_repository.update_journey_stage(user_id, data.journey_stage)
```

## Security Checklist for New Code

Before submitting a PR, verify:

- [ ] All database queries use parameterized queries (`$1`, `$2`, etc.)
- [ ] No f-strings or string concatenation in SQL queries
- [ ] All PII (emails, phone numbers) is hashed before storage
- [ ] Passwords are hashed with bcrypt, never plain text or weak algorithms
- [ ] Input validation uses Pydantic models
- [ ] Business logic constraints are validated
- [ ] HTTP status codes are appropriate (201, 400, 401, 403, 404, 409, 500)
- [ ] Error messages don't expose internal implementation details
- [ ] No password hashes or sensitive data in API responses
- [ ] No PII in logs
- [ ] Authorization checks prevent IDOR vulnerabilities
- [ ] Mass assignment is prevented with explicit Pydantic models
- [ ] Timing attacks are considered for authentication endpoints

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [GDPR Compliance](https://gdpr.eu/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
- [Bcrypt Password Hashing](https://github.com/pyca/bcrypt/)

For more details contact Oren @ Pynt.io :)