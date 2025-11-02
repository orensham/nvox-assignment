# Journey Routing Flow - Graph-Based System

## Overview

The routing system has migrated from CSV-based rules to a **database-driven graph-based architecture**. Rules are now stored in the `journey_edges` table and loaded dynamically per request.

---

## How Rules Are Loaded

### Old System (CSV) ❌
```
API Startup → Load routing_rules.csv → In-memory RoutingRules object → Used for all requests
```

### New System (Database Graph) ✅
```
API Request → Inject GraphRepository → Query journey_edges table → Evaluate edges → Return transition decision
```

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. API Startup                                                          │
│    - No rule loading at startup                                         │
│    - No in-memory cache of rules                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. User Request: POST /v1/journey/continue                             │
│    - User has answered all questions in current stage                   │
│    - Ready to transition to next stage                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. FastAPI Dependency Injection                                         │
│                                                                          │
│    graph_repository: GraphRepository = Depends(get_graph_repository)    │
│                                    │                                     │
│                                    ▼                                     │
│    def get_graph_repository(db_client: NvoxDBClient):                   │
│        return GraphRepository(db_client)                                │
│                                                                          │
│    Creates GraphRepository with database client                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. Create RoutingEngine with GraphRepository                           │
│                                                                          │
│    engine = RoutingEngine(graph_repository=graph_repository)            │
│                                                                          │
│    - RoutingEngine holds reference to GraphRepository                   │
│    - No rules loaded yet - just a connection to the database            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. Prepare Routing Evaluation Data                                     │
│                                                                          │
│    # Get all current answers                                            │
│    answers = await journey_repository.get_current_answers(...)          │
│    # Example: {'brd_needs_more_tests': 1, 'brd_risk_score': 5}         │
│                                                                          │
│    # Get visit history (for visit-aware routing)                        │
│    visit_history = await journey_repository.get_visit_history(...)      │
│    # Example: ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. Evaluate Transition (Graph-Based)                                   │
│                                                                          │
│    decision = await engine.evaluate_transition_with_graph(              │
│        'BOARD',                    # Current stage                      │
│        answers_dict,               # User's answers                     │
│        visit_history               # Visited stages                     │
│    )                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. GraphRepository Loads Edges from Database (Just-in-Time)            │
│                                                                          │
│    # Inside graph_repository.find_matching_edge()                       │
│    edges = await self.db_client.fetch("""                               │
│        SELECT id, from_node_id, to_node_id, condition_type,             │
│               question_id, range_min, range_max                         │
│        FROM journey_edges                                               │
│        WHERE from_node_id = $1                                          │
│        ORDER BY created_at ASC                                          │
│    """, 'BOARD')                                                         │
│                                                                          │
│    Result:                                                              │
│    [                                                                    │
│      Edge(BOARD → WORKUP, brd_needs_more_tests, 1.0-1.0),              │
│      Edge(BOARD → PREOP, brd_risk_score, 0.0-6.999),                   │
│      Edge(BOARD → EXIT, brd_risk_score, 7.0-10.0)                      │
│    ]                                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 8. Match Edges Against Answers                                         │
│                                                                          │
│    matching_edges = []                                                  │
│    for edge in edges:                                                   │
│        if edge.question_id in answers:                                  │
│            if edge.matches(answers[edge.question_id]):                  │
│                matching_edges.append(edge)                              │
│                                                                          │
│    Result:                                                              │
│    - Edge to WORKUP matches (brd_needs_more_tests = 1)                 │
│    - Edge to PREOP matches (brd_risk_score = 5)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 9. Apply Visit-Aware Priority Algorithm                                │
│                                                                          │
│    # Separate into revisit vs forward edges                             │
│    revisit_edges = [e for e in matching_edges                           │
│                     if e.to_node_id in visit_history]                   │
│    forward_edges = [e for e in matching_edges                           │
│                     if e.to_node_id not in visit_history]               │
│                                                                          │
│    # Prioritize revisit edges (medical urgency)                         │
│    if revisit_edges:                                                    │
│        return revisit_edges[0]  # WORKUP (revisit)                      │
│    elif forward_edges:                                                  │
│        return forward_edges[0]  # PREOP (forward)                       │
│                                                                          │
│    Result: Returns edge to WORKUP (loop back for more tests)           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 10. Create TransitionDecision                                          │
│                                                                          │
│     return TransitionDecision(                                          │
│         should_transition=True,                                         │
│         next_stage='WORKUP',                                            │
│         matched_edge=edge,                                              │
│         question_id='brd_needs_more_tests',                             │
│         answer_value=1,                                                 │
│         reason="Matched edge ... → WORKUP (revisit loop)"               │
│     )                                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 11. Perform Stage Transition                                           │
│                                                                          │
│     await journey_repository.perform_stage_transition(                  │
│         user_id=user_id,                                                │
│         from_stage_id='BOARD',                                          │
│         to_stage_id='WORKUP',                                           │
│         transition_reason="Matched edge ... → WORKUP (revisit loop)",   │
│         matched_rule_id=str(edge.id)                                    │
│     )                                                                   │
│                                                                          │
│     Updates:                                                            │
│     - user_journey_state (current_stage, visit_number)                  │
│     - user_journey_path (add new entry, mark old as not current)        │
│     - stage_transitions (record the transition with edge ID)            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 12. Return Response to User                                            │
│                                                                          │
│     {                                                                   │
│       "success": true,                                                  │
│       "transitioned": true,                                             │
│       "current_stage": "WORKUP",                                        │
│       "previous_stage": "BOARD",                                        │
│       "questions": [...],  // Questions for WORKUP stage                │
│       "transition_reason": "Matched edge ... → WORKUP (revisit loop)"   │
│     }                                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Differences from CSV System

| Aspect | CSV System (Old) | Database Graph (New) |
|--------|------------------|---------------------|
| **Storage** | `routing_rules.csv` file | `journey_edges` table in PostgreSQL |
| **Loading** | At API startup (once) | Per request from database (just-in-time) |
| **Caching** | In-memory cache of all rules | No caching (database queries are fast) |
| **Deployment** | Requires API restart to update rules | Update database, changes immediate |
| **Algorithm** | First-match-wins (non-deterministic) | Visit-aware priority (deterministic) |
| **Data Structure** | Flat CSV rows | Graph with nodes and edges |
| **Flexibility** | Limited to range conditions | Supports range, equals, always conditions |
| **Audit Trail** | No edge tracking in transitions | Edge ID stored in `stage_transitions` table |

---

## Database Schema

### journey_edges Table
```sql
CREATE TABLE journey_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id VARCHAR(50),          -- Source stage (NULL for entry edge)
    to_node_id VARCHAR(50) NOT NULL,   -- Destination stage
    condition_type VARCHAR(20) NOT NULL, -- 'range', 'equals', 'always'
    question_id VARCHAR(100),           -- Question to evaluate (NULL for 'always')
    range_min DECIMAL(10, 3),          -- Min value (for 'range' type)
    range_max DECIMAL(10, 3),          -- Max value (for 'range' type)
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Example Edges for BOARD Stage
```sql
-- Revisit WORKUP if more tests needed
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES ('BOARD', 'WORKUP', 'range', 'brd_needs_more_tests', 1.0, 1.0);

-- Forward to PREOP if low risk
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES ('BOARD', 'PREOP', 'range', 'brd_risk_score', 0.0, 6.999);

-- Exit if high risk
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES ('BOARD', 'EXIT', 'range', 'brd_risk_score', 7.0, 10.0);
```

---

## Advantages of New System

### 1. **Just-in-Time Loading**
- Rules loaded from database only when needed
- No API restart required to update routing logic
- Always uses latest rules from database

### 2. **Deterministic Routing**
- Visit-aware algorithm ensures consistent transitions
- Prioritizes revisit edges (medical urgency)
- Resolves non-determinism of old CSV system

### 3. **Better Audit Trail**
- Edge IDs stored in `stage_transitions` table
- Can track exactly which rule caused each transition
- Full traceability for compliance and debugging

### 4. **Scalability**
- Database queries are highly optimized
- PostgreSQL indexes on `from_node_id`
- No memory overhead from caching all rules

### 5. **Flexibility**
- Easy to add new edge types (e.g., complex conditions)
- Can query edges dynamically for analytics
- Version control through database migrations

---

## Code References

### Dependencies Injection
- **File:** `apps/nvox-api/src/dependencies/repositories.py:28-31`
- Creates `GraphRepository` with database client

### Routing Evaluation
- **File:** `apps/nvox-api/src/api/routes/journey_router.py:193`
- Creates `RoutingEngine` with `GraphRepository`
- **File:** `apps/nvox-api/src/api/routes/journey_router.py:212`
- Calls `evaluate_transition_with_graph()`

### Graph Edge Loading
- **File:** `apps/nvox-api/src/repositories/graph_repository.py:20-51`
- `get_outgoing_edges()` queries `journey_edges` table
- **File:** `apps/nvox-api/src/repositories/graph_repository.py:53-110`
- `find_matching_edge()` implements visit-aware algorithm

### Migration
- **File:** `apps/nvox-api/migrations/005_populate_journey_edges.sql`
- Populates `journey_edges` table with routing rules

---

## Summary

**Rules are no longer "loaded" at startup.** Instead:

1. ✅ Rules live in the `journey_edges` database table
2. ✅ Each request queries the database for relevant edges
3. ✅ Visit-aware algorithm selects the correct edge
4. ✅ Transition decision is returned with matched edge ID
5. ✅ Changes to rules take effect immediately (no restart needed)

This is a **pull model** (query when needed) instead of a **push model** (load at startup).
