# Architecture Decisions & Technical Analysis

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Algorithm: Journey Routing Engine](#core-algorithm-journey-routing-engine)
3. [Technology Stack Decisions](#technology-stack-decisions)
4. [Architecture Patterns](#architecture-patterns)
5. [Database Design](#database-design)
6. [Security Considerations](#security-considerations)
7. [Trade-offs & Future Improvements](#trade-offs--future-improvements)

---

## System Overview

### Purpose
A full-stack web application for tracking patients through the kidney transplant process. The system uses a **graph-based routing engine** with visit-aware algorithms to guide patients through 14 stages based on clinical criteria and medical assessments.

### High-Level Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │         │                  │         │                 │
│   React SPA     │◄───────►│   FastAPI        │◄───────►│   PostgreSQL    │
│   (nvox-fe)     │  REST   │   (nvox-api)     │  asyncpg│   Database      │
│                 │         │                  │         │                 │
└─────────────────┘         └────────┬─────────┘         └─────────────────┘
      │                              │                           │
      │                              │                           ├─ users
      ├─ Tailwind CSS                ├─ JWT Authentication       ├─ journey_edges 
      ├─ React 18                    ├─ Graph Routing Engine     ├─ stage_transitions
      ├─ Axios                       ├─ Repository Pattern       ├─ user_answers
      └─ Vite                        └─ Dependency Injection     └─ user_journey_path
                                     │
                                     ▼
                              ┌─────────────────┐
                              │                 │
                              │   Redis         │
                              │   (Cache)       │
                              │                 │
                              └─────────────────┘
                                     │
                                     └─ Config Cache (journey_config.json)
```

---

## Core Algorithm: Journey Routing Engine

### Overview

The routing engine is a **graph-based decision system** that determines patient progression through 14 transplant journey stages based on medical criteria. The system uses a **visit-aware algorithm** to prioritize revisit edges (medical urgency loops) over forward progress edges.

### Key Innovation: Visit-Aware Routing

**Problem Solved**: When multiple routing rules match (e.g., BOARD stage with "needs more tests" + "low risk score"), the system must choose deterministically.

**Solution**: Prioritize revisit edges (loops back to already-visited stages) over forward edges, ensuring medical urgency takes precedence.

### Algorithm Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User Submits Answer                                       │
│    ▸ POST /v1/journey/answer                                 │
│    ▸ Answer stored with versioning (version++, is_current)   │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. User Triggers Transition                                  │
│    ▸ POST /v1/journey/continue                               │
│    ▸ Retrieves current stage and all current answers         │
│    ▸ Retrieves visit history (all previously visited stages) │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Query Journey Edges from Database                         │
│    ▸ GraphRepository.get_outgoing_edges(current_stage)       │
│    ▸ SELECT * FROM journey_edges WHERE from_node_id = ?      │
│    ▸ Returns all possible transitions from current stage     │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Match Edges Against Answers                               │
│    ┌───────────────────────────────────────────────────────┐│
│    │ FOR each edge in outgoing_edges:                      ││
│    │   IF edge.condition_type == 'always':                 ││
│    │      → Add to matching_edges                          ││
│    │   ELSE IF edge.question_id in answers:                ││
│    │      answer_value = answers[edge.question_id]         ││
│    │      IF edge.matches(answer_value):  # Range check    ││
│    │        → Add to matching_edges                        ││
│    └───────────────────────────────────────────────────────┘│
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. Apply Visit-Aware Priority Algorithm                    │
│    ┌───────────────────────────────────────────────────────┐│
│    │ # Separate edges by type                              ││
│    │ revisit_edges = [e for e in matching_edges           ││
│    │                   if e.to_node_id in visit_history]   ││
│    │ forward_edges = [e for e in matching_edges           ││
│    │                   if e.to_node_id not in visit_history]││
│    │                                                        ││
│    │ # Prioritize medical urgency (loops mean more work)   ││
│    │ IF revisit_edges:                                     ││
│    │    RETURN revisit_edges[0]  # Loop back               ││
│    │ ELIF forward_edges:                                   ││
│    │    RETURN forward_edges[0]  # Progress forward        ││
│    │ ELSE:                                                 ││
│    │    RETURN None  # No transition                       ││
│    └───────────────────────────────────────────────────────┘│
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Perform Atomic Transition (Database Transaction)          │
│    ┌───────────────────────────────────────────────────────┐│
│    │ BEGIN TRANSACTION                                      ││
│    │   ▸ INSERT stage_transitions (audit trail + edge_id)  ││
│    │   ▸ UPDATE user_journey_state (new stage, visit++)    ││
│    │   ▸ UPDATE user_journey_path (exit old, enter new)    ││
│    │   ▸ UPDATE users.journey_stage (denormalized)         ││
│    │ COMMIT                                                 ││
│    └───────────────────────────────────────────────────────┘│
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. Return New State with Questions                           │
│    ▸ Fetch questions for new stage from journey_config.json  │
│    ▸ Return current_stage, questions, transition metadata    │
└──────────────────────────────────────────────────────────────┘
```

### Example: BOARD Stage with Multiple Matching Rules

**Scenario**: Patient at BOARD stage with conflicting rule matches

```python
# Current Stage: BOARD
# Visit History: ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']
# Current Answers: {
#     "brd_needs_more_tests": 1,  # Matches edge to WORKUP
#     "brd_risk_score": 5.0        # Matches edge to PREOP
# }

# Journey Edges (from database):
# 1. BOARD → WORKUP (brd_needs_more_tests = 1)
# 2. BOARD → PREOP (brd_risk_score 0-6.999)
# 3. BOARD → EXIT (brd_risk_score 7-10)

# Matching Process:
matching_edges = [
    Edge(BOARD → WORKUP, question=brd_needs_more_tests),  # Matches
    Edge(BOARD → PREOP, question=brd_risk_score),          # Matches
]

# Visit-Aware Priority:
revisit_edges = [BOARD → WORKUP]  # WORKUP in visit_history ✓
forward_edges = [BOARD → PREOP]   # PREOP NOT in visit_history

# Decision: Choose WORKUP (revisit edge wins)
# Reason: Medical urgency - more tests needed before progressing

# Result: Patient transitions to WORKUP (visit_number = 2)
```

### Key Algorithm Features

1. **Graph-Based Routing**: Edges stored in `journey_edges` table with explicit conditions
2. **Visit-Aware Algorithm**: Prioritizes revisit edges (loops) over forward edges (medical urgency)
3. **Deterministic Decisions**: Same answers + visit history always produce same transition
4. **Range-Based Matching**: Numeric answers matched against `[min_value, max_value]` ranges
5. **Non-Linear Journeys**: `visit_number` tracks loops (e.g., WORKUP visit 1 → visit 2)
6. **Atomic Transitions**: All database updates in single transaction (ACID guarantees)
7. **Complete Audit Trail**: Every transition recorded with:
   - Edge ID that triggered it (references `journey_edges.id`)
   - Question ID and answer value
   - Timestamps and visit numbers
   - Transition reason (e.g., "revisit loop" vs "forward progress")
8. **Configurable Rules**: CSV file generates SQL migrations (version-controlled, immediate effect)

### Complexity Analysis

- **Time Complexity**: O(E + A) where E = edges from current stage, A = user answers (typically 3-5 + 3-10)
- **Space Complexity**: O(V) where V = visit history length (typically 5-15 stages)
- **Database Operations**:
  - 1 SELECT (edges) + 1 SELECT (answers) + 1 SELECT (visit history) = 3 reads
  - 4 updates + 1 insert = 5 writes per transition (in transaction)

### Solving the Non-Determinism Problem

**Before (CSV-based)**:
- First matching answer wins
- Database query order determines outcome
- Same answers could produce different results ❌

**After (Graph-based with Visit-Aware)**:
- All matching edges found first
- Deterministic priority: revisit > forward
- Same answers + visit history always produce same result ✓

---

## Technology Stack Decisions

### Backend: FastAPI + Python 3.11

**Pros:**
- **Performance**: Async/await support for high concurrency
- **Type Safety**: Pydantic models provide runtime validation + IDE autocomplete
- **Auto-Documentation**: OpenAPI/Swagger UI generated automatically
- **Modern**: Built on Starlette + Uvicorn (production-ready ASGI)
- **Developer Experience**: Clean syntax, excellent error messages
- **Ecosystem**: Rich library support (asyncpg, pytest, testcontainers)

**Cons:**
- **Maturity**: Less mature than Django (fewer batteries included)
- **ORM**: No built-in ORM (we use raw SQL with asyncpg)
- **Community Size**: Smaller than Django ecosystem
- **Migration Tools**: No built-in migration framework (we use custom SQL migrations)

**Why Chosen**:
- Project requirements favor speed and flexibility over admin panels
- Medical data requires strict type safety (Pydantic excels here)
- Graph-based routing logic doesn't fit Django's patterns well

---

### Frontend: React 18 + TypeScript + Vite

**Pros:**
- **Type Safety**: TypeScript catches errors at compile time
- **Performance**: Vite provides <1s HMR (Hot Module Replacement)
- **Component Reusability**: React's component model fits journey stages pattern
- **Ecosystem**: Huge library ecosystem (axios, react-router if needed)
- **Developer Tools**: Excellent browser devtools support

**Cons:**
- **Boilerplate**: More verbose than Vue/Svelte
- **State Management**: Not included (simple project doesn't need Redux/Zustand)
- **Build Complexity**: Vite config can be opaque
- **Bundle Size**: Larger than Svelte/Preact

**Why Chosen**:
- TypeScript ensures API contract adherence
- Vite build speed critical for development iteration
- React skills are most common in hiring pool

---

### Database: PostgreSQL 16 + asyncpg

**Pros:**
- **ACID Compliance**: Critical for medical data integrity
- **JSONB Support**: Flexible storage for `answer_value` (any question type)
- **Performance**: asyncpg is fastest async Postgres driver for Python
- **Constraints**: Rich constraint system (CHECK, UNIQUE, partial indexes)
- **Audit Trail**: Perfect for immutable append-only `stage_transitions` table
- **Indexes**: Comprehensive indexing strategies (partial, composite, GIN for JSONB)
- **Graph Support**: Efficient storage and querying of `journey_edges` table

**Cons:**
- **Operational Complexity**: Requires backup/replication setup for production
- **Vertical Scaling Limits**: Single-server bottleneck (vs distributed NoSQL)
- **Schema Migrations**: Requires careful planning (we use custom SQL)

**Why Chosen**:
- Medical data requires ACID guarantees (no eventual consistency)
- JSONB perfect for evolving question types without schema changes
- Graph routing requires efficient JOIN operations (SQL > NoSQL here)
- Visit history queries require recursive CTEs (Postgres excels here)

**Alternative Considered**: MongoDB
- Rejected: No multi-document transactions until v4.0+
- Rejected: JOIN performance poor for journey history queries
- Rejected: No built-in answer versioning

---

### Authentication: JWT + Session Blacklist

**Pros:**
- **Stateless**: No server-side session storage needed
- **Scalable**: Easy horizontal scaling (no sticky sessions)
- **Standard**: Industry-standard token format
- **Logout Support**: Session table enables token revocation

**Cons:**
- **Token Size**: JWTs larger than session IDs
- **Revocation Complexity**: Requires database lookup (session blacklist)
- **Secret Management**: Requires secure key rotation strategy

**Why Chosen**:
- Stateless tokens enable CDN caching of public endpoints
- Session table hybrid gives logout without full session store

**Alternative Considered**: Server-side sessions
- Rejected: Requires Redis/Memcached for horizontal scaling
- Rejected: Adds infrastructure complexity

---

### Caching: Redis

**Pros:**
- **Performance**: Sub-millisecond response times for configuration lookups
- **Connection Pooling**: Handles concurrent requests efficiently (max 50 connections)
- **Async Support**: Native async/await with redis-py
- **Simple Data Model**: Key-value store perfect for config caching
- **Startup Caching**: Config loaded once at startup, not per-request
- **Development**: Easy local testing with Docker

**Cons:**
- **Additional Infrastructure**: Requires Redis server deployment
- **Cache Invalidation**: Must reload config to pick up changes
- **Memory Usage**: Config stored in RAM
- **Not Persistent**: Data lost on Redis restart (acceptable for cache)

**Why Chosen**:
- Eliminates disk I/O for journey config reads (stages, questions)
- JSON parsing moved from per-request to startup-time
- 100x+ faster than reading JSON files per request

**What's Cached**:
```
route:config                          → Full journey configuration (JSON)
route:stage:{stage_id}:questions      → Questions per stage (JSON)
route:last_reload                     → Last reload timestamp (Unix time)
```

**What's NOT Cached** (loaded from database per-request):
- Journey edges (`journey_edges` table)
- User journey state
- User answers
- Visit history

**Cache Keys Design**:
- `route:*` namespace for easy identification
- Stage-specific keys for granular access
- JSON serialization for complex objects

**Performance Impact**:
- **Config reads without Redis**: ~10ms per request (file I/O + JSON parse)
- **Config reads with Redis**: ~0.1ms per request (memory lookup)
- **Edge queries from PostgreSQL**: ~2-5ms per request (with indexes)
- **Overall improvement**: 5x faster than full file-based system

**Trade-offs**:
- Config changes require app restart (acceptable for infrequent changes)
- Additional ops complexity (Redis monitoring)

**Alternative Considered**: No caching (direct file reads)
- Rejected: JSON parsing on every request wasteful

**Alternative Considered**: Cache edges in Redis
- Rejected: Edges change infrequently; PostgreSQL fast enough with indexes
- Rejected: Cache invalidation complexity when edges update
- Benefit: Single source of truth (database) for routing rules

---

## Architecture Patterns

### 1. Repository Pattern

**Decision**: Abstract database access behind repository classes

**Implementation**:
```python
class UserRepository:
    async def get_user_by_email_hash(self, email_hash: str) -> Optional[UserDB]:
        row = await self.db_client.fetchRow(...)
        return optional_record_to_model(row, UserDB)

class GraphRepository:
    async def find_matching_edge(
        self,
        from_node_id: str,
        answers: Dict[str, Any],
        visit_history: List[str]
    ) -> Optional[JourneyEdge]:
        # Implements visit-aware routing algorithm
        ...
```

**Benefits**:
- **Testability**: Easy to mock repositories in tests
- **Type Safety**: Pydantic models ensure schema compliance
- **Separation of Concerns**: Routes don't know about SQL
- **Reusability**: Same repository across multiple routes
- **Algorithm Encapsulation**: Visit-aware logic isolated in GraphRepository

**Trade-offs**:
- **Boilerplate**: More code than raw SQL in routes
- **Abstraction Leakage**: Still need to understand SQL for complex queries

---

### 2. Dependency Injection (FastAPI)

**Decision**: Use FastAPI's `Depends()` for all dependencies

**Implementation**:
```python
def get_graph_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> GraphRepository:
    return GraphRepository(db_client)

@router.post("/journey/continue")
async def continue_journey(
    current_user: TokenData = Depends(get_current_user),
    journey_repository: JourneyRepository = Depends(get_journey_repository),
    graph_repository: GraphRepository = Depends(get_graph_repository),
):
    engine = RoutingEngine(graph_repository=graph_repository)
    decision = await engine.evaluate_transition_with_graph(...)
```

**Benefits**:
- **Testability**: Override dependencies in tests via `app.dependency_overrides`
- **Composability**: Dependencies can depend on other dependencies
- **Type Safety**: Full IDE autocomplete for injected params
- **Clean Architecture**: Repository layer injected at route level

**Trade-offs**:
- **Magic**: Less explicit than manual instantiation
- **Learning Curve**: New developers must understand FastAPI DI

---

### 3. Monorepo with Shared Packages

**Decision**: Use UV workspace with `packages/db` shared library

**Structure**:
```
nvox-assignment/
├── apps/
│   ├── nvox-api/      # Backend
│   └── nvox-fe/       # Frontend
├── packages/
│   └── db/            # Shared nvox_common.db
└── pyproject.toml     # Workspace root
```

**Benefits**:
- **Code Reuse**: `NvoxDBClient` shared across future services
- **Atomic Changes**: Change DB client + API in single commit
- **Type Safety**: Shared Pydantic models ensure consistency

**Trade-offs**:
- **Complexity**: More complex than single-app repo
- **Build Time**: UV must resolve workspace dependencies
- **Versioning**: Harder to version shared packages independently

---

## Database Design

### Key Design Decisions

#### 1. Graph-Based Routing with `journey_edges` Table

**Decision**: Store routing rules as explicit graph edges in database

**Benefits**:
- **Explicit Graph Structure**: Edges are first-class entities, not implicit in rules
- **Version Control**: Edge changes tracked through SQL migrations
- **Immediate Updates**: No app restart needed to update routing logic
- **Query Performance**: Indexed lookups for edge queries (~2ms)
- **Audit Trail**: Edge IDs stored in `stage_transitions.matched_rule_id`
- **Flexibility**: Easy to add new condition types (complex expressions, etc.)

**Trade-offs**:
- **Migration Required**: Adding edges requires SQL migration
- **No Hot Reload**: Unlike CSV, can't edit in real-time (by design for safety)

**Why This Hybrid Approach**:
- CSV easy to edit for non-technical users
- SQL migrations provide version control + safety
- Database provides runtime performance + immediate effect

---

#### 2. PII Protection via Hashing

**Decision**: Hash email addresses (SHA-256) before storage

**Implementation**:
```python
email_hash = hashlib.sha256(email.lower().encode()).hexdigest()
await user_repository.create_user(email_hash=email_hash, ...)
```

**Benefits**:
- **Privacy**: Email addresses not stored in plaintext
- **Compliance**: Easier GDPR/HIPAA compliance
- **Anonymization**: Can anonymize by replacing hash

**Trade-offs**:
- **Irreversible**: Cannot recover original email (by design)
- **Reset Passwords**: Requires separate email→hash lookup mechanism

---

#### 3. Answer Versioning with `is_current` Flag

**Decision**: Keep all answer versions; mark only one as current

**Implementation**:
```sql
-- Old answer
UPDATE user_answers SET is_current = FALSE WHERE user_id = $1 AND question_id = $2;

-- New answer (version++)
INSERT INTO user_answers (..., version = 3, is_current = TRUE);
```

**Benefits**:
- **Audit Trail**: Complete history of answer changes
- **Rollback**: Can revert to previous answers if needed
- **Analytics**: Can analyze answer patterns over time

**Trade-offs**:
- **Storage**: More rows per user (5-10x growth)
- **Query Complexity**: Must filter `WHERE is_current = TRUE`

---

#### 4. Visit Number for Non-Linear Journeys

**Decision**: Track `visit_number` to support loops (e.g., WORKUP visit 2)

**Scenario**:
```
REFERRAL (v1) → WORKUP (v1) → MATCH (v1) → WORKUP (v2) → MATCH (v2)
                  ↑_______________|
```

**Implementation**:
```python
visit_number = await journey_repository.get_stage_visit_count(user_id, stage_id) + 1
```

**Benefits**:
- **Non-Linear Support**: Handles complex clinical workflows
- **Answer Isolation**: Answers from visit 1 don't mix with visit 2
- **Analytics**: Can measure how often patients loop back
- **Visit-Aware Algorithm**: Enables revisit edge prioritization

**Trade-offs**:
- **Complexity**: More complex queries (`WHERE visit_number = ?`)
- **Edge Cases**: Requires careful handling of "return to same stage"

---

#### 5. Immutable Audit Trail (`stage_transitions`)

**Decision**: Append-only transitions table (never UPDATE/DELETE)

**Enhancement**: Store matched edge ID for complete traceability
```sql
CREATE TABLE stage_transitions (
    ...
    matched_rule_id VARCHAR(100),  -- Stores journey_edges.id
    transition_reason TEXT,         -- E.g., "Matched edge ... (revisit loop)"
    ...
);
```

**Benefits**:
- **Compliance**: Regulatory requirements for medical audit trails
- **Debugging**: Can replay entire journey to find bugs
- **Analytics**: Full dataset for ML/analysis
- **Edge Traceability**: Can query which edge caused each transition

**Trade-offs**:
- **Storage**: Grows indefinitely (requires archival strategy)
- **No Corrections**: Cannot fix mistakes (must add compensating transition)

---

## Security Considerations

### 1. SQL Injection Prevention

**Approach**: 100% parameterized queries via asyncpg

```python
# SAFE: Parameterized query
await db_client.fetchRow("SELECT * FROM users WHERE email_hash = $1", email_hash)

# DANGEROUS: String formatting (NEVER used)
await db_client.fetchRow(f"SELECT * FROM users WHERE email_hash = '{email_hash}'")
```

---

### 2. Password Security

**Approach**: Bcrypt with cost factor 12

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd_context.hash(password)
```

**Benefits**: Slow hashing resists brute-force attacks
**Performance**: ~200ms per hash (acceptable for login)

---

### 3. JWT Security

**Implementation**:
- HS256 signing (symmetric key)
- 1-hour expiration
- JTI claim for revocation via `sessions` table

**Production Improvement**: Consider RS256 (asymmetric) for multi-service auth

---

### 4. CORS Configuration

**Current**: Allow all origins (development only)

**Production Required**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nvox.com"],  # Whitelist only
    allow_credentials=True,
)
```

---

## Graph-Based Routing: Design Decisions

### Why We Migrated from CSV to Graph

**Old System (CSV-based)**:
```csv
stage_id,if_number_id,in_range_min,in_range_max,next_stage
BOARD,brd_needs_more_tests,1.0,1.0,WORKUP
BOARD,brd_risk_score,0.0,6.999,PREOP
```

**Problems**:
1. **Non-deterministic**: First matching answer wins (database query order)
2. **No priority**: Can't express "revisit edges have priority"
3. **Implicit graph**: Edges not queryable as graph structure
4. **Requires restart**: Changing rules requires API restart

**New System (Database graph)**:
```sql
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, ...)
VALUES
  ('BOARD', 'WORKUP', 'range', 'brd_needs_more_tests', 1.0, 1.0),
  ('BOARD', 'PREOP', 'range', 'brd_risk_score', 0.0, 6.999);
```

**Benefits**:
1. **Deterministic**: Visit-aware algorithm provides consistent priority
2. **Explicit priority**: Revisit > forward (medical urgency)
3. **Queryable graph**: Can analyze paths, detect cycles
4. **Immediate updates**: Changes take effect without restart

### Visit-Aware Algorithm Details

**Core Principle**: Medical urgency (need for more tests/work) takes priority over forward progress.

**Implementation** (`GraphRepository.find_matching_edge`):
```python
# 1. Get all edges from current stage
edges = await get_outgoing_edges(current_stage_id)

# 2. Find edges where condition matches answers
matching_edges = [e for e in edges if e.matches(answers[e.question_id])]

# 3. Separate by revisit vs forward
revisit_edges = [e for e in matching_edges if e.to_node_id in visit_history]
forward_edges = [e for e in matching_edges if e.to_node_id not in visit_history]

# 4. Prioritize revisit (loop back for more work)
if revisit_edges:
    return revisit_edges[0]  # Medical urgency
elif forward_edges:
    return forward_edges[0]  # Normal progress
else:
    return None  # No transition
```

**Medical Justification**:
- If patient needs more tests → loop back to WORKUP (revisit)
- Revisit edges represent unmet medical requirements
- Forward edges represent normal progression
- Revisit must take priority for patient safety

---

## Trade-offs & Future Improvements

### Current Limitations

#### 1. No Real-Time Updates
**Current**: Poll-based (user must refresh)
**Improvement**: WebSockets for live journey updates
**Complexity**: Medium (backend websocket support)
**Value**: Low (medical decisions are async, not real-time)

#### 2. Limited User State Caching
**Current**: Config cached in Redis; user journey state hits PostgreSQL every request
**Improvement**: Redis for `user_journey_state` caching with TTL
**Benefit**: 10x faster reads for current state
**Trade-off**: Cache invalidation on every state change (added complexity)

#### 3. Manual Database Migrations
**Current**: Custom SQL files + manual execution
**Improvement**: Alembic for auto-migrations
**Benefit**: Safer schema changes, automatic rollback
**Trade-off**: Steeper learning curve

#### 4. Monolithic Deployment
**Current**: Single FastAPI app
**Improvement**: Microservices (auth service, journey service, graph service)
**Benefit**: Independent scaling, better separation
**Trade-off**: Distributed transactions, service mesh complexity

#### 5. No Observability
**Current**: Basic logging
**Improvement**: OpenTelemetry + Datadog/Grafana
**Benefit**: Production debugging, performance metrics, edge query analytics
**Trade-off**: Cost + operational overhead

#### 6. No Graph Visualizations
**Current**: Graph exists in database but not visualized
**Improvement**: D3.js/Cytoscape.js visualization of journey graph
**Benefit**: Clinical team can see all possible paths
**Implementation**:
  - Query edges from `journey_edges`
  - Render as interactive graph
  - Highlight user's current path

---

### Potential Graph Enhancements

**1. Pathfinding Queries**

**2. Cycle Detection**

**3. "What-If" Analysis**

---

### Scalability Path

**Current Capacity**: Single Postgres instance + Redis

**Growth Path**:
1. **Phase 1**: Add Postgres read replicas for journey history queries
2. **Phase 2**: Partition `stage_transitions` by date (archive old transitions)
3. **Phase 3**: Shard users by `user_id` hash (requires app-level sharding)
4. **Phase 4**: Cache hot edges in Redis

**Bottlenecks**:
- Postgres write throughput
- Redis memory
- Graph query performance

---

## References

- **[ROUTING_FLOW.md](./ROUTING_FLOW.md)**: Detailed explanation of how rules are loaded and used at runtime
- **[ROUTING_MANAGEMENT.md](./ROUTING_MANAGEMENT.md)**: Complete guide to managing routing rules
- **[GRAPH_MIGRATION_PLAN.md](./GRAPH_MIGRATION_PLAN.md)**: Migration plan from CSV to graph (completed)
- **[apps/nvox-api/ROUTING_RULES_GUIDE.md](./apps/nvox-api/ROUTING_RULES_GUIDE.md)**: Quick-start guide for editing routing rules
