# Database Entity Relationship Diagram

This document provides a visual representation of the database schema for the Nvox Transplant Journey System.

## Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ sessions : "has many"
    users ||--|| user_journey_state : "has one"
    users ||--o{ user_answers : "has many"
    users ||--o{ stage_transitions : "has many"
    users ||--o{ user_journey_path : "has many"

    journey_edges ||--o{ stage_transitions : "references"

    users {
        UUID id PK
        VARCHAR email_hash UK "SHA-256 hash of email"
        VARCHAR password_hash "Bcrypt hash"
        VARCHAR journey_stage "Current stage (denormalized)"
        TIMESTAMP journey_started_at
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    sessions {
        UUID id PK
        UUID user_id FK
        VARCHAR token_jti UK "JWT ID claim"
        TIMESTAMP expires_at "Token expiration"
        TIMESTAMP created_at
        TIMESTAMP revoked_at "NULL if active"
        BOOLEAN is_active "FALSE after logout"
    }

    journey_edges {
        UUID id PK
        VARCHAR from_node_id "NULL for entry edge"
        VARCHAR to_node_id "Target stage"
        VARCHAR condition_type "always, range"
        VARCHAR question_id "Question to evaluate"
        NUMERIC range_min "Minimum value (inclusive)"
        NUMERIC range_max "Maximum value (inclusive)"
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    user_journey_state {
        UUID id PK
        UUID user_id FK "UNIQUE - one per user"
        VARCHAR current_stage_id "e.g., REFERRAL, WORKUP"
        INT visit_number "Increments on loops"
        TIMESTAMP journey_started_at
        TIMESTAMP last_updated_at
        TIMESTAMP created_at
    }

    user_answers {
        UUID id PK
        UUID user_id FK
        VARCHAR stage_id "Stage where answered"
        VARCHAR question_id "Question identifier"
        JSONB answer_value "Flexible answer type"
        INT visit_number "Which stage visit"
        TIMESTAMP answered_at
        INT version "Answer version number"
        BOOLEAN is_current "TRUE for latest"
    }

    stage_transitions {
        UUID id PK
        UUID user_id FK
        VARCHAR from_stage_id "NULL for initial"
        VARCHAR to_stage_id
        INT from_visit_number
        INT to_visit_number
        TEXT transition_reason
        VARCHAR matched_rule_id "Journey edge ID"
        VARCHAR matched_question_id "Question that triggered"
        JSONB matched_answer_value "Answer that matched"
        TIMESTAMP transitioned_at
    }

    user_journey_path {
        UUID id PK
        UUID user_id FK
        VARCHAR stage_id
        INT visit_number
        TIMESTAMP entered_at
        TIMESTAMP exited_at "NULL while current"
        BOOLEAN is_current "TRUE for current stage"
    }
```

## Table Descriptions

### Core Tables

#### `users`
- **Purpose**: Stores user accounts with PII protection
- **Indexes**: `email_hash` (unique), `journey_stage`
- **Key Fields**:
  - `email_hash`: SHA-256 hashed email for anonymization support
  - `password_hash`: Bcrypt hashed password with salt
  - `journey_stage`: Denormalized current stage for quick access

#### `sessions`
- **Purpose**: JWT token management and logout functionality
- **Indexes**: `token_jti` (unique), `user_id`, `is_active`, `expires_at`
- **Key Fields**:
  - `token_jti`: JWT ID claim for token tracking
  - `is_active`: FALSE after logout, enables token revocation
  - `revoked_at`: Timestamp of logout for audit trail

### Journey Routing Tables

#### `journey_edges`
- **Purpose**: Graph-based routing rules defining stage transitions
- **Indexes**: Composite on `(from_node_id, to_node_id)`, `from_node_id`, `to_node_id`
- **Key Fields**:
  - `from_node_id`: Source stage (NULL for entry edge)
  - `to_node_id`: Destination stage
  - `condition_type`: Type of condition (`always`, `range`)
  - `question_id`: Question to evaluate for routing decision
  - `range_min`, `range_max`: Numeric range for `range` condition type
- **Design**:
  - Entry edge: `from_node_id = NULL → to_node_id = 'REFERRAL'` (condition_type: `always`)
  - Conditional edges: Use `range` type to evaluate numeric question answers
  - Managed via CSV → SQL migration workflow (see `ROUTING_RULES_GUIDE.md`)
- **Relationships**:
  - Referenced by `stage_transitions.matched_rule_id` (stores which edge was used)

### Journey Tracking Tables

#### `user_journey_state`
- **Purpose**: Tracks current journey state for each user (single source of truth)
- **Indexes**: `user_id` (unique), `current_stage_id`, `last_updated_at`
- **Key Fields**:
  - `current_stage_id`: Current stage in journey (e.g., 'REFERRAL', 'WORKUP')
  - `visit_number`: Increments on revisits to same stage (supports non-linear paths)
  - `journey_started_at`: When user first began the journey
  - `last_updated_at`: Last stage transition timestamp

#### `user_answers`
- **Purpose**: Stores all user answers with full versioning and audit trail
- **Indexes**: Composite on `(user_id, stage_id)`, `(user_id, question_id)`, partial on `is_current`
- **Key Fields**:
  - `answer_value`: JSONB field for flexible answer types (numbers, text, arrays)
  - `visit_number`: Which visit to the stage this answer belongs to
  - `version`: Answer version number (increments on changes)
  - `is_current`: TRUE only for the latest answer per question
- **Versioning**: Previous answers are kept with `is_current = FALSE` for audit

#### `stage_transitions`
- **Purpose**: Immutable audit trail of all stage changes
- **Indexes**: `user_id`, composite on `(user_id, transitioned_at)`, `from_stage_id`, `to_stage_id`
- **Key Fields**:
  - `from_stage_id`: Previous stage (NULL for initial entry)
  - `to_stage_id`: New stage after transition
  - `from_visit_number`, `to_visit_number`: Visit numbers for both stages
  - `matched_rule_id`: UUID of the `journey_edges` row that triggered transition
  - `matched_question_id`: Question ID that satisfied the routing condition
  - `matched_answer_value`: The actual answer value that matched the edge condition
  - `transition_reason`: Human-readable explanation of why transition occurred
- **Immutability**: Never updated or deleted, provides complete audit trail

#### `user_journey_path`
- **Purpose**: Tracks detailed timeline of stage visits (entry/exit timestamps)
- **Indexes**: `user_id`, composite on `(user_id, entered_at)`, partial unique on `is_current`
- **Key Fields**:
  - `entered_at`: When user entered this stage
  - `exited_at`: When user left (NULL while still in stage)
  - `is_current`: TRUE only for the current stage (enforced by unique constraint)
  - `visit_number`: Which visit to this stage (1st, 2nd, 3rd, etc.)
- **Timeline**: Complete record of time spent in each stage

## Design Patterns

### 1. Graph-Based Routing Engine
- **Journey Edges Table**: Defines stage transitions as directed graph edges
- **Condition Types**:
  - `always`: Unconditional transition (entry edge)
  - `range`: Numeric range condition on question answers
- **Visit-Aware Algorithm**: Prioritizes revisit edges (loops) over forward edges
  - Ensures medical urgency (e.g., need more tests) takes precedence
  - Deterministic routing when multiple edges match
- **Runtime Loading**: Edges loaded from database at startup for performance
- **Management**: CSV → SQL migration workflow for non-technical rule editing
- **Audit Trail**: `stage_transitions.matched_rule_id` references the edge used

### 2. PII Protection
- Email addresses are hashed before storage (SHA-256)
- No reversible PII stored in database
- Anonymization support via hash replacement
- Password hashing with bcrypt (salt + cost factor)

### 3. Comprehensive Audit Trail
- `stage_transitions`: Immutable record of all stage changes with matched edge details
- `user_answers`: Full version history with timestamps (no deletions)
- `user_journey_path`: Complete timeline with entry/exit times
- Enables compliance, analytics, and debugging

### 4. Non-Linear Journey Support
- `visit_number`: Tracks returns to same stage (1st visit, 2nd visit, etc.)
- Version history allows comparing answers across visits
- Path tracking shows complete journey including loops and revisits
- Graph edges support any transition pattern (forward, backward, loops)

### 5. Denormalization for Performance
- `users.journey_stage`: Quick access without JOIN to `user_journey_state`
- `user_journey_state`: Single source of truth for current state
- Trade-off: Consistency managed via atomic transactions
- Caching strategy: Current state optimized for read-heavy workloads

### 6. Flexible Data Model
- JSONB columns for `answer_value` and `matched_answer_value`
- Supports evolving question types without schema migrations
- Enables complex answer formats (numbers, text, arrays, objects)
- Query flexibility: Can use JSONB operators for advanced filtering

## Constraints and Data Integrity

### Foreign Keys
- All journey tracking tables reference `users(id)` with `ON DELETE CASCADE`
- Session cleanup happens automatically when user is deleted
- Journey data is preserved for analytics until user deletion
- `journey_edges` has no foreign keys (independent graph definition)

### Check Constraints
- `visit_number > 0`: Ensures valid visit numbers
- `version > 0`: Ensures valid version numbers
- `exited_at >= entered_at`: Ensures valid time ranges in journey path
- `range_min <= range_max`: Ensures valid numeric ranges in journey edges

### Unique Constraints
- `users.email_hash`: One account per email
- `sessions.token_jti`: One session per token
- `user_journey_state.user_id`: One state per user
- `user_journey_path.user_id WHERE is_current = TRUE`: One current stage per user

### Data Integrity for Graph Routing
- **No Overlapping Ranges**: CSV validation script ensures no overlapping ranges for same (stage, question) pair
- **Valid Stage IDs**: Edge validation ensures all stage IDs reference valid stages in `journey_config.json`
- **Entry Edge**: Exactly one entry edge (from_node_id = NULL) ensures journey always starts at REFERRAL
- **Atomic Transitions**: All stage transitions use database transactions to ensure consistency

## Scalability Considerations

### Performance Optimizations
- **Indexes**: Comprehensive indexing for all common access patterns
- **Graph Loading**: `journey_edges` loaded at startup and cached in memory
- **Query Optimization**: Composite indexes on frequent JOIN columns
- **Connection Pooling**: Database connection pool for concurrent requests

### Long-Term Scalability
- **Partitioning**: `stage_transitions` can be partitioned by date (e.g., monthly) for large datasets
- **Archival**: Old journey data can be archived after completion (cold storage)
- **Caching**: Current state (`user_journey_state`) is optimized for Redis/Memcached caching
- **Read Replicas**: Journey history and analytics can use read replicas

### Routing Engine Scalability
- **Graph Size**: Current design supports hundreds of edges efficiently (in-memory loading)
- **Rule Complexity**: O(N) evaluation where N = number of outgoing edges from current stage (typically 2-5)
- **Hot Paths**: Most common transitions cached in application memory
- **Migration Workflow**: CSV → SQL migration allows rule updates without API restart (database reload)

---

## Graph-Based Routing Examples

### Example 1: Entry Edge (Unconditional)
```sql
-- Entry edge: All users start at REFERRAL stage
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES (NULL, 'REFERRAL', 'always', NULL, NULL, NULL);
```

### Example 2: Conditional Transition (Range-Based)
```sql
-- If Karnofsky score is 0-39.999, transition from REFERRAL to EXIT
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES ('REFERRAL', 'EXIT', 'range', 'ref_karnofsky', 0.0, 39.999);

-- If Karnofsky score is 40-100, transition from REFERRAL to WORKUP
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES ('REFERRAL', 'WORKUP', 'range', 'ref_karnofsky', 40.0, 100.0);
```

### Example 3: Revisit Edge (Loop Back)
```sql
-- If board decides more tests needed, loop back to WORKUP
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES ('BOARD', 'WORKUP', 'range', 'brd_needs_more_tests', 1.0, 1.0);
```

### Example 4: Complete Routing Flow

**Scenario**: User at BOARD stage answers `brd_risk_score = 5.5`

1. **Query Outgoing Edges**:
   ```sql
   SELECT * FROM journey_edges WHERE from_node_id = 'BOARD';
   ```
   Returns:
   - `BOARD → WORKUP` (if `brd_needs_more_tests` in [1.0, 1.0])
   - `BOARD → PREOP` (if `brd_risk_score` in [0.0, 6.999])
   - `BOARD → EXIT` (if `brd_risk_score` in [7.0, 10.0])

2. **Evaluate Conditions**:
   - `brd_needs_more_tests`: No answer → No match
   - `brd_risk_score = 5.5`: Matches [0.0, 6.999] → `BOARD → PREOP` edge matches

3. **Check Visit History**:
   ```sql
   SELECT stage_id FROM user_journey_path WHERE user_id = $1 GROUP BY stage_id ORDER BY MIN(entered_at);
   ```
   Returns: `['REFERRAL', 'WORKUP', 'BOARD']`

4. **Visit-Aware Decision**:
   - Matching edge: `BOARD → PREOP`
   - Is `PREOP` in visit history? **No** → Forward edge
   - Decision: Transition to `PREOP`

5. **Record Transition**:
   ```sql
   -- Record in stage_transitions
   INSERT INTO stage_transitions (
     user_id, from_stage_id, to_stage_id, from_visit_number, to_visit_number,
     matched_rule_id, matched_question_id, matched_answer_value, transition_reason
   ) VALUES (
     $user_id, 'BOARD', 'PREOP', 1, 1,
     $edge_id, 'brd_risk_score', '5.5', 'Risk score 5.5 is within acceptable range [0.0-6.999]'
   );

   -- Update current state
   UPDATE user_journey_state
   SET current_stage_id = 'PREOP', visit_number = 1, last_updated_at = NOW()
   WHERE user_id = $user_id;

   -- Update journey path
   UPDATE user_journey_path SET exited_at = NOW(), is_current = FALSE
   WHERE user_id = $user_id AND is_current = TRUE;

   INSERT INTO user_journey_path (user_id, stage_id, visit_number, is_current)
   VALUES ($user_id, 'PREOP', 1, TRUE);
   ```

---

## Related Documentation

- **Routing Flow**: See `ROUTING_FLOW.md` for detailed routing algorithm
- **Rule Management**: See `ROUTING_RULES_GUIDE.md` for CSV → SQL migration workflow
- **Architecture**: See `ARCHITECTURE_DECISIONS.md` for system design rationale
- **Edge Descriptions**: See `config/edges-descriptions.md` for business logic documentation
- **Migrations**: See `migrations/004_add_journey_edges_table.sql` and `migrations/005_populate_journey_edges.sql`
