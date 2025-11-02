# Nvox Transplant Journey System

A full-stack web application for tracking and managing patient journeys through the kidney transplant process. The system uses a sophisticated routing engine to guide patients through various stages based on clinical criteria and medical assessments.

## Architecture Overview

This is a monorepo containing multiple services and shared packages:

```
nvox-assignment/
├── apps/                      # Application services
│   ├── nvox-api/             # Backend API (FastAPI + Python)
│   └── nvox-fe/              # Frontend UI (React + TypeScript + Vite)
├── packages/                  # Shared packages
│   └── db/                   # Database client library (nvox-db)
├── pyproject.toml            # Workspace configuration
└── uv.lock                   # Dependency lock file
```

## Documentation

- **[Architecture Decisions](./ARCHITECTURE_DECISIONS.md)** - Technical analysis of architecture patterns, technology stack decisions, core routing algorithm, and trade-offs
- **[Database ERD](./apps/nvox-api/DATABASE_ERD.md)** - Entity Relationship Diagram with detailed table descriptions and design patterns

## Services

### 1. Backend API (nvox-api)

**Location**: [`apps/nvox-api/`](./apps/nvox-api/)
**Documentation**: [apps/nvox-api/README.md](./apps/nvox-api/README.md)

FastAPI-based REST API that powers the transplant journey system.

**Key Features**:
- User authentication with JWT tokens
- Journey stage management and transitions
- Dynamic routing engine based on medical criteria
- PostgreSQL database with asyncpg
- Comprehensive test coverage (15 integration tests)

**Technology Stack**:
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15+
- **ORM**: asyncpg (native async PostgreSQL driver)
- **Authentication**: JWT with passlib + bcrypt
- **Testing**: pytest, pytest-asyncio, testcontainers

**API Endpoints**:
- `POST /v1/signup` - Create account and initialize journey
- `POST /v1/login` - Authenticate and get JWT token
- `GET /v1/journey/current` - Get current journey state and questions
- `POST /v1/journey/answer` - Submit answer to a question
- `POST /v1/journey/continue` - Trigger stage transition
- `DELETE /v1/user` - Anonymize user data

**Quick Start**:
```bash
# Start with Docker Compose (Recommended)
docker compose -f apps/nvox-api/docker-compose.yaml --profile api up -d

# Access API
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
```

**Testing**:
- **Test Coverage Documentation**: [apps/nvox-api/tests/TEST_COVERAGE.md](./apps/nvox-api/tests/TEST_COVERAGE.md)
- **Run Tests**: `uv run --directory apps/nvox-api pytest tests/integration/ -v`
- **Test Stats**: 15 integration tests (all passing)

### 2. Frontend UI (nvox-fe)

**Location**: [`apps/nvox-fe/`](./apps/nvox-fe/)
**Documentation**: [apps/nvox-fe/README.md](./apps/nvox-fe/README.md)

React-based single-page application for the patient journey interface.

**Key Features**:
- Responsive authentication forms (signup/login)
- Real-time journey progress tracking
- Dynamic question cards with validation
- Stage transition notifications
- Mobile-friendly design with Tailwind CSS

**Technology Stack**:
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Deployment**: Docker + Nginx

**Quick Start**:
```bash
# Development mode
cd apps/nvox-fe
npm install
npm run dev

# Or with Docker (production build)
docker build -t nvox-frontend -f apps/nvox-fe/Dockerfile .
docker run -p 3000:80 nvox-frontend
```

**Access**: http://localhost:3000

### 3. Database Package (nvox-db)

**Location**: [`packages/db/`](./packages/db/)

Shared Python package providing database client functionality used across the API service.

**Features**:
- PostgreSQL connection pooling
- Common database utilities
- Shared repository patterns

## Journey System

### Journey Stages

The system guides patients through the following stages:

1. **REFERRAL** - Initial patient referral
2. **WORKUP** - Medical workup and evaluation
3. **MATCH** - Donor matching process
4. **DONOR** - Donor evaluation
5. **BOARD** - Medical board review
6. **PREOP** - Pre-operative preparation
7. **ORSCHED** - OR scheduling
8. **SURG** - Surgery
9. **ICU** - Intensive care unit
10. **WARD** - Ward recovery
11. **HOME** - Home monitoring
12. **COMPLX** - Complication management
13. **RELIST** - Re-listing for transplant
14. **EXIT** - Journey termination

### Routing Engine

The routing engine uses a rules-based system to determine stage transitions based on:
- Patient medical assessments (Karnofsky score, eGFR, PRA, etc.)
- Clinical criteria (blood pressure, infection status, etc.)
- Boolean flags (donor clearance, board approval, etc.)

**Edge Case Documentation**: [apps/nvox-api/config/edges-descriptions.md](./apps/nvox-api/config/edges-descriptions.md)

**Example Routing Rules**:
- Low Karnofsky score (< 40) → EXIT
- Normal Karnofsky score (≥ 40) → WORKUP
- High PRA (≥ 80) → BOARD (skips DONOR)
- Board needs more tests → WORKUP (fallback)
- Failed donor clearance → MATCH (fallback)

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** (required)
- **Python 3.11** (for local development)
- **Node.js 20+** (for frontend development)
- **uv** - Python package manager ([installation](https://docs.astral.sh/uv/getting-started/installation/))

### Quick Start - Full Stack

Start all services (PostgreSQL, API, Frontend):

```bash

git clone <repository-url>
cd nvox-assignment

docker compose -f apps/nvox-api/docker-compose.yaml --profile api up -d

# Services will be available at:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - PostgreSQL: localhost:5432
```

### Demo Data

The system includes a seed script that creates 3 pre-configured demo users at different stages of the transplant journey. This is useful for testing the UI and demonstrating the full journey flow.

#### Demo Users

| Email | Password | Current Stage | Description |
|-------|----------|---------------|-------------|
| demo1@nvox.com | Demo1234 | BOARD | Mid-journey patient ready for board review |
| demo2@nvox.com | Demo1234 | WARD | Post-surgery patient in recovery |
| demo3@nvox.com | Demo1234 | HOME | Successfully completed transplant journey |

**Journey Path**: All demo users follow the normal journey path:
```
REFERRAL → WORKUP → MATCH → DONOR → BOARD → PREOP → ORSCHED → SURG → ICU → WARD → HOME
```

#### Populate Demo Data

Run the seed script to populate the database with demo users:

```bash
# Make sure the database is running
docker compose -f apps/nvox-api/docker-compose.yaml up -d postgres

# Run the seed script
python apps/nvox-api/scripts/seed_demo_data.py
```

The script is **idempotent** - it will skip seeding if demo users already exist.

#### Clean Demo Data

To remove all demo data and start fresh:

```bash
# Clear all users (including demo data)
docker exec nvox-postgres psql -U transplant_user -d transplant_journey -c "TRUNCATE TABLE users CASCADE;"

# Or reset the entire database
docker compose -f apps/nvox-api/docker-compose.yaml down -v
docker compose -f apps/nvox-api/docker-compose.yaml up -d
```

**Note**: `TRUNCATE TABLE users CASCADE` will remove ALL users and their associated data (sessions, journey state, answers, transitions, etc.)

### Development Setup

**Backend Development**:
```bash

curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync --package nvox-api

docker compose -f apps/nvox-api/docker-compose.yaml up -d postgres

cd apps/nvox-api
uv run fastapi dev src/main.py
```

**Frontend Development**:
```bash

cd apps/nvox-fe
npm install

npm run dev
# Access at http://localhost:3000
```

## Testing

### Backend Tests

Run the complete test suite:

```bash
# All tests (15 integration tests)
uv run --directory apps/nvox-api pytest tests/integration/ -v

# Specific test files
uv run --directory apps/nvox-api pytest tests/integration/test_journey_endpoints.py -v
uv run --directory apps/nvox-api pytest tests/integration/test_journey_edge_cases.py -v

# With coverage
uv run --directory apps/nvox-api pytest tests/ -v --cov=apps/nvox-api/src --cov-report=term-missing
```

**Test Coverage**: See [apps/nvox-api/tests/TEST_COVERAGE.md](./apps/nvox-api/tests/TEST_COVERAGE.md) for detailed coverage matrix mapping edge cases to tests.

### Manual Testing

Use the provided Postman collection:
- **Location**: `apps/nvox-api/Nvox_Journey_API.postman_collection.json`
- **Guide**: [apps/nvox-api/POSTMAN_GUIDE.md](./apps/nvox-api/POSTMAN_GUIDE.md) (if available)

## Project Structure Details

### Configuration Files

- **`pyproject.toml`** - Workspace configuration and dependencies
- **`uv.lock`** - Locked dependency versions
- **`apps/nvox-api/docker-compose.yaml`** - Docker Compose configuration
- **`apps/nvox-api/migrations/`** - Database migration scripts
- **`apps/nvox-api/config/`** - Journey configuration (stages, questions, routing rules)

### Journey Configuration

Located in `apps/nvox-api/config/`:
- **`journey_config.json`** - Stage definitions and questions
- **`journey_edges` table** - Graph-based routing rules for stage transitions (see migration 005)
- **`edges-descriptions.md`** - Edge case documentation

## Database Migrations

Migrations are SQL-based and located in `apps/nvox-api/migrations/`.

**Run migrations**:
```bash
# Apply all migrations
for file in apps/nvox-api/migrations/*.sql; do
  echo "Applying migration: $file"
  docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey < "$file"
done
```

See [apps/nvox-api/README.md#database-migrations](./apps/nvox-api/README.md#database-migrations) for detailed migration guide.

## Technology Stack Summary

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | FastAPI (Python 3.11) |
| **Frontend Framework** | React 18 + TypeScript |
| **Build Tool** | Vite |
| **Styling** | Tailwind CSS |
| **Database** | PostgreSQL 15+ |
| **Database Driver** | asyncpg |
| **Authentication** | JWT (passlib + bcrypt) |
| **Testing** | pytest + testcontainers |
| **Package Manager** | uv (Python), npm (Node) |
| **Container Runtime** | Docker + Docker Compose |
| **Web Server** | Uvicorn (dev), Nginx (prod) |

## API Documentation

Interactive API documentation is available when the API is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Stopping Services

```bash

docker compose -f apps/nvox-api/docker-compose.yaml down


docker compose -f apps/nvox-api/docker-compose.yaml down -v


docker ps --filter "publish=8000" --format "{{.ID}}" | xargs -r docker stop
```

## Troubleshooting

### Common Issues

**Port conflicts**:
```bash
# Check what's using the port
lsof -i :8000  # API port
lsof -i :3000  # Frontend port
lsof -i :5432  # PostgreSQL port

# Kill the process
kill -9 <PID>
```

**Docker container issues**:
```bash
docker compose -f apps/nvox-api/docker-compose.yaml logs -f

docker compose -f apps/nvox-api/docker-compose.yaml restart

docker compose -f apps/nvox-api/docker-compose.yaml down -v
docker compose -f apps/nvox-api/docker-compose.yaml --profile api up -d --build
```

**Database connection errors**:
- Ensure PostgreSQL container is healthy: `docker ps`
- Check database logs: `docker logs nvox-postgres`
- Verify connection parameters in `.env` files

## Development Workflow

1. **Start infrastructure**: `docker compose -f apps/nvox-api/docker-compose.yaml up -d postgres`
2. **Run API locally**: `cd apps/nvox-api && uv run fastapi dev src/main.py`
3. **Run frontend locally**: `cd apps/nvox-fe && npm run dev`
4. **Make changes** to code
5. **Run tests**: `uv run --directory apps/nvox-api pytest tests/integration/ -v`
6. **Test manually** via browser or Postman
7. **Commit changes**