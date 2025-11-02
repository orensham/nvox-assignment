# nvox-api

FastAPI-based backend service for the Transplant Journey System. Provides REST APIs for user authentication, journey management, and stage transitions based on medical criteria.

## Project Structure

```
apps/nvox-api/
├── config/                    # Journey configuration (stages, routing rules, edge cases)
├── guidelines/                # Development guidelines
├── migrations/                # Database migration SQL files
├── src/                       # Source code
│   ├── main.py               # Application entry point
│   ├── api/                  # API layer (routes, models)
│   │   ├── models/           # Pydantic request/response models
│   │   └── routes/           # API route handlers (auth, journey)
│   ├── dependencies/         # FastAPI dependencies (auth, database)
│   ├── journey/              # Journey business logic (config, routing engine, rules)
│   ├── repositories/         # Data access layer (user, journey, session)
│   └── utils/                # Utilities (hashing, JWT)
├── tests/                     # Test suite (integration, unit)
│   ├── integration/          # API endpoint tests with testcontainers
│   └── unit/                 # Unit tests
├── docker-compose.yaml        # Docker Compose configuration
├── Dockerfile                 # Multi-stage Docker build
├── pyproject.toml            # Project dependencies and configuration
└── pytest.ini                # Pytest configuration
```

## Running with Docker

### Prerequisites
- Docker and Docker Compose installed on your system
- Git repository cloned locally

### Build and Run

1. **Start the PostgreSQL database** using Docker Compose:
   ```bash
   docker compose -f apps/nvox-api/docker-compose.yaml up -d postgres
   ```

   This will start the PostgreSQL container with a healthcheck. Wait for it to be healthy before proceeding.

2. **Build the API Docker image** from the root directory of the project:
   ```bash
   docker build -t nvox-api -f apps/nvox-api/Dockerfile .
   ```

3. **Run the API container**:
   ```bash
   docker run -p 8000:8000 \
     --network nvox-api_nvox-network \
     -e DB_HOST=nvox-postgres \
     -e DB_PORT=5432 \
     -e DB_NAME=transplant_journey \
     -e DB_USER=transplant_user \
     -e DB_PASSWORD=change_me_in_production \
     nvox-api
   ```

4. **Access the API**:
   - API will be available at: http://localhost:8000
   - Interactive documentation (Swagger): http://localhost:8000/docs
   - Alternative documentation (ReDoc): http://localhost:8000/redoc

### Alternative: Running Both Services with Docker Compose

You can also run both PostgreSQL and the API together using Docker Compose profiles:

```bash
# Start both database and API
docker compose -f apps/nvox-api/docker-compose.yaml --profile api up -d

# Or just the database (default)
docker compose -f apps/nvox-api/docker-compose.yaml up -d
```

### Testing the API

Once the containers are running, test the endpoints:

**Health check:**
```bash
curl http://localhost:8000/alive
```

Expected response:
```json
{"alive": true}
```

**Signup endpoint:**
```bash
curl -X POST http://localhost:8000/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

Expected response (201 Created):
```json
{
  "success": true,
  "user_id": "uuid-here",
  "email": "hashed-email-here",
  "message": "Account created successfully",
  "journey": {
    "current_stage": "REFERRAL",
    "started_at": "2025-11-01T12:00:00"
  }
}
```

### Stopping the Services

```bash
# Stop the API container (if running separately)
docker ps --filter "publish=8000" --format "{{.ID}}" | xargs -r docker stop

# Stop all services (if using docker-compose)
docker compose -f apps/nvox-api/docker-compose.yaml down
```

## Database Migrations

### Overview

Database migrations are managed through SQL files in the `migrations/` directory. Each migration file follows a naming convention: `<number>_<description>.sql` (e.g., `001_init.sql`).

### Running Migrations

To apply migrations to your database:

```bash
# Ensure PostgreSQL is running
docker compose -f apps/nvox-api/docker-compose.yaml up -d postgres

# Apply a specific migration
docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey < apps/nvox-api/migrations/001_init.sql

# Or apply all migrations in order
for file in apps/nvox-api/migrations/*.sql; do
  echo "Applying migration: $file"
  docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey < "$file"
done
```

### Migration Best Practices

**DO:**
- Use sequential numbering (001, 002, 003, etc.), will be automated later
- Name migrations descriptively (e.g., `002_add_user_preferences.sql`)
- Include `IF NOT EXISTS` clauses for idempotency
- Add indexes for frequently queried columns
- Use constraints to enforce data integrity
- Document complex migrations with SQL comments
- Test migrations on a copy of production data before deploying
- Keep migrations small and focused on a single change
- Use transactions when possible to ensure atomicity

**DON'T:**
- Modify existing migration files after they've been deployed
- Skip migration numbers (maintain sequential order)
- Store sensitive data (passwords, keys) in migrations
- Use `DROP TABLE` or `DROP COLUMN` without careful consideration
- Create migrations that depend on application code
- Forget to update both `up` and `down` migration paths (if using reversible migrations)
- Ignore migration failures in CI/CD pipelines
- Mix schema changes with data migrations in a single file

### Creating a New Migration

1. Create a new SQL file in `apps/nvox-api/migrations/`:
   ```bash
   touch apps/nvox-api/migrations/002_add_user_preferences.sql
   ```

2. Write your migration with proper safety checks:
   ```sql
   -- Add user preferences table
   CREATE TABLE IF NOT EXISTS user_preferences (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       preference_key VARCHAR(100) NOT NULL,
       preference_value TEXT,
       created_at TIMESTAMP NOT NULL DEFAULT NOW(),
       updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
       UNIQUE(user_id, preference_key)
   );

   -- Add index for faster lookups
   CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id
   ON user_preferences(user_id);
   ```

3. Test the migration locally:
   ```bash
   docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey < apps/nvox-api/migrations/002_add_user_preferences.sql
   ```

4. Verify the migration:
   ```bash
   docker exec -it nvox-postgres psql -U transplant_user -d transplant_journey -c "\dt"
   ```

### Migration Rollback

If you need to undo a migration:

```sql
-- Create a rollback script (e.g., 002_add_user_preferences_rollback.sql)
DROP TABLE IF EXISTS user_preferences;
```

Apply the rollback:
```bash
docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey < apps/nvox-api/migrations/002_add_user_preferences_rollback.sql
```

### PII and Security Considerations

When working with migrations:
- Never store plain text emails or passwords
- Always use hashing for sensitive data (see `utils/hashing.py`)
- Consider GDPR/compliance requirements for user data
- Use appropriate PostgreSQL column types for sensitive data
- Implement proper access controls at the database level

## Running the server locally

When running locally, the `.env` file is used automatically with sane defaults for running locally with the
infrastructure from Docker Compose.

1. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2. Sync the project dependencies

    ```bash
    uv sync --package nvox-api
    ```

3. Run the required infrastructure with Docker Compose

    ```bash
    docker-compose -d --profile infra up
    ```

### Via PyCharm

Create a new _FastAPI run configuration_ with the following properties:

| Setting               | Value                                                                                                                                                                      |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Name                  | nvox-api                                                                                                                                                                  |
| Script path           | /path/to/nvox-api/src/nvox_api/main.py                                                                                                                     |
| Uvicorn options       | `--reload --host 0.0.0.0`                                                                                                                                                  |
| Python interpreter    | (select your project's UV virtual env)                                                                                                                                     |
| Environment variables ||
| Working directory     | `$ProjectFileDir$/nvox-api/src`                                                                                                                                      |

### Via Terminal

1. Set the required environment variables
   use `export KEY=value`

2. Run the service

    ```bash
    uv run fastapi run ./src/main.py
    ```

## Running Tests

The project includes comprehensive unit and integration tests using pytest, pytest-asyncio, and testcontainers for isolated database testing.

### Prerequisites

Tests are automatically set up with dependencies when you sync the project:

```bash
uv sync --package nvox-api
```

Test dependencies include:
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `testcontainers` - Docker-based test isolation
- `httpx` - Async HTTP client for integration tests

### Test Structure

```
apps/nvox-api/tests/
├── conftest.py              # Test fixtures and configuration
├── unit/                    # Unit tests (no external dependencies)
│   ├── test_hashing.py      # Hashing utility tests
│   └── test_user_repository.py  # Repository layer tests
└── integration/             # Integration tests (API endpoints)
    └── test_auth_endpoints.py   # Authentication endpoint tests
```

### Running All Tests

Run the complete test suite (41 tests):

```bash
# From repository root
pytest apps/nvox-api/tests/ -v

# Or with coverage report
pytest apps/nvox-api/tests/ -v --cov=apps/nvox-api/src --cov-report=term-missing
```

Expected output:
```
============================== 41 passed in 17.04s ==============================
```

### Running Only Unit Tests

Unit tests are fast and don't require Docker containers:

```bash
# Run all unit tests
pytest apps/nvox-api/tests/unit/ -v

# Run specific unit test file
pytest apps/nvox-api/tests/unit/test_hashing.py -v
pytest apps/nvox-api/tests/unit/test_user_repository.py -v
```

### Running Only Integration Tests

Integration tests use testcontainers to spin up a PostgreSQL database:

```bash
# Run all integration tests
pytest apps/nvox-api/tests/integration/ -v

# Run specific integration test file
pytest apps/nvox-api/tests/integration/test_auth_endpoints.py -v
```

Note: Integration tests will automatically:
- Start a PostgreSQL container
- Initialize the schema
- Run tests with isolated databases
- Clean up containers after tests

### Running Specific Tests

**Run a specific test class:**
```bash
pytest apps/nvox-api/tests/unit/test_hashing.py::TestHashEmail -v
pytest apps/nvox-api/tests/integration/test_auth_endpoints.py::TestSignupEndpoint -v
```

**Run a specific test function:**
```bash
pytest apps/nvox-api/tests/unit/test_hashing.py::TestHashEmail::test_hash_email_returns_consistent_hash -v
pytest apps/nvox-api/tests/integration/test_auth_endpoints.py::TestSignupEndpoint::test_signup_success -v
```

**Run tests matching a pattern:**
```bash
# Run all tests with "password" in the name
pytest apps/nvox-api/tests/ -k "password" -v

# Run all tests with "duplicate" in the name
pytest apps/nvox-api/tests/ -k "duplicate" -v
```

### Useful pytest Options

```bash
# Show print statements and logging output
pytest apps/nvox-api/tests/ -v -s

# Stop at first failure
pytest apps/nvox-api/tests/ -v -x

# Run last failed tests only
pytest apps/nvox-api/tests/ -v --lf

# Show slowest 10 tests
pytest apps/nvox-api/tests/ -v --durations=10

# Run tests in parallel (requires pytest-xdist)
pytest apps/nvox-api/tests/ -v -n auto

# Generate HTML coverage report
pytest apps/nvox-api/tests/ -v --cov=apps/nvox-api/src --cov-report=html
# Then open htmlcov/index.html in browser
```

### Test Coverage Summary

| Test Suite | Tests | Coverage |
|------------|-------|----------|
| Unit Tests - Hashing | 16 | Password hashing, email hashing, verification |
| Unit Tests - Repository | 12 | User CRUD operations, journey stage management |
| Integration Tests - Auth | 14 | Signup endpoint, validation, error handling |
| **Total** | **41** | **All tests passing** |

### Continuous Integration

Tests run automatically in CI/CD pipelines. To run tests the same way CI does:

```bash
# Clean environment test run
uv sync --package nvox-api
pytest apps/nvox-api/tests/ -v --cov=apps/nvox-api/src --cov-report=term-missing
```

### Troubleshooting Tests

**Issue: Tests hang or timeout**
- Check Docker is running: `docker ps`
- Clean up old test containers: `docker ps -a | grep testcontainers`
- Restart Docker daemon

**Issue: Port conflicts**
- Stop services using the same ports
- Testcontainers uses random ports by default

**Issue: Event loop errors**
- Tests are configured with function-scoped event loops
- See `pytest.ini` for asyncio configuration

**Issue: Database connection errors**
- Ensure Docker has enough resources (memory/CPU)
- Check testcontainer logs in test output