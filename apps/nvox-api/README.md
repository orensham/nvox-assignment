# nvox-api

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