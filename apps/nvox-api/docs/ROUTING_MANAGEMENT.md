# Managing Routing Rules - Graph-Based System

## Current Approach: SQL Migrations

Since we migrated from CSV to database-backed routing, rules are now managed through **SQL migration files**.

### Adding/Changing/Removing Rules

#### 1. **Adding a New Rule**

Create a new migration file:

```bash
# Create migration 006
touch apps/nvox-api/migrations/006_add_new_board_edge.sql
```

```sql
-- Migration 006: Add high-risk emergency path from BOARD to ICU
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES ('BOARD', 'ICU', 'range', 'brd_emergency_score', 8.0, 10.0);
```

Run the migration:
```bash
docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey \
  < apps/nvox-api/migrations/006_add_new_board_edge.sql
```

**Result**: Rule active immediately, no API restart needed

---

#### 2. **Modifying an Existing Rule**

**Example**: Change BOARD → PREOP threshold from 6.999 to 7.5

```sql
-- Migration 007: Adjust PREOP risk threshold
UPDATE journey_edges
SET range_max = 7.5
WHERE from_node_id = 'BOARD'
  AND to_node_id = 'PREOP'
  AND question_id = 'brd_risk_score';
```

**Result**: Next request uses new threshold

---

#### 3. **Removing a Rule**

```sql
-- Migration 008: Remove deprecated EXIT path from BOARD
DELETE FROM journey_edges
WHERE from_node_id = 'BOARD'
  AND to_node_id = 'EXIT';
```

**Result**: Path no longer available

---

## Pros & Cons of SQL Migrations Approach

### Pros

| Benefit | Description |
|---------|-------------|
| **Immediate Effect** | Changes apply instantly without API restart |
| **Version Control** | Migrations tracked in Git like code |
| **Audit Trail** | Each change has timestamp, author, commit message |
| **Rollback Support** | Can write reverse migrations |
| **Database Integrity** | Foreign key constraints prevent invalid rules |
| **Production Safety** | Review process via pull requests |

### Cons

| Challenge | Description |
|-----------|-------------|
| **SQL Knowledge Required** | Non-technical users can't edit rules |
| **No Visual Editor** | Can't see graph structure visually |
| **Manual Process** | No GUI for rule management |
| **Error-Prone** | Typos can break routing |
| **Testing Complexity** | Must test migrations in staging first |

---

## Alternative Approaches

### Option 1: Keep CSV as Source of Truth (Recommended for Ease of Use)

**Hybrid approach**: CSV file generates migrations

#### Structure:
```
apps/nvox-api/
├── config/
│   └── routing_rules.csv          # Source of truth (human-editable)
├── scripts/
│   └── generate_edge_migration.py # Converts CSV → SQL
└── migrations/
    └── 00X_update_edges.sql       # Generated SQL
```

#### Workflow:

1. **Edit CSV file** (easy for non-technical users):
```csv
stage_id,if_number_id,in_range_min,in_range_max,next_stage
BOARD,brd_risk_score,0.0,7.5,PREOP
BOARD,brd_risk_score,7.5,10.0,EXIT
BOARD,brd_needs_more_tests,1.0,1.0,WORKUP
```

2. **Run generation script**:
```bash
python apps/nvox-api/scripts/generate_edge_migration.py
```

3. **Review generated SQL**:
```sql
-- Generated from routing_rules.csv at 2025-11-02 16:30:00
DELETE FROM journey_edges;  -- Clear old rules

INSERT INTO journey_edges (...) VALUES
  ('BOARD', 'PREOP', 'range', 'brd_risk_score', 0.0, 7.5),
  ('BOARD', 'EXIT', 'range', 'brd_risk_score', 7.5, 10.0),
  ...
```

4. **Apply migration**:
```bash
docker exec -i nvox-postgres psql ... < migrations/00X_update_edges.sql
```

**Benefits**:
- CSV is easy to edit (Excel, Google Sheets)
- Non-technical users can manage rules
- Still get migration versioning
- Can diff CSV changes in Git

---

### Option 2: Admin Web UI (Future Enhancement)

Build an admin interface for rule management:

**Implementation**:
- Add admin routes to FastAPI
- CRUD operations on `journey_edges` table
- Role-based access control
- Audit logging for rule changes

**Endpoints**:
```python
# Admin routes (requires admin role)
POST   /v1/admin/edges         # Create edge
GET    /v1/admin/edges         # List all edges
PUT    /v1/admin/edges/{id}    # Update edge
DELETE /v1/admin/edges/{id}    # Delete edge
POST   /v1/admin/edges/test    # Test edge matching
```

---

### Option 3: GraphQL API (Advanced)

For complex rule queries and management:

```graphql
mutation UpdateEdge {
  updateJourneyEdge(
    id: "uuid-here"
    rangeMax: 7.5
  ) {
    id
    fromNode
    toNode
    condition {
      type
      questionId
      rangeMin
      rangeMax
    }
  }
}

query PreviewImpact {
  simulateEdgeChange(
    edgeId: "uuid"
    newRangeMax: 7.5
  ) {
    affectedUsers
    exampleTransitions {
      userId
      oldDestination
      newDestination
    }
  }
}
```

---

## Recommended Solution: CSV Generator Script

For **this project**, I recommend **Option 1** (CSV + Generator Script):

### Why?

1. **Backwards compatible**: Keep familiar CSV format
2. **Easy to edit**: Anyone can edit CSV in Excel
3. **Version controlled**: CSV diffs are readable
4. **Safe**: Generated SQL can be reviewed before applying
5. **No UI needed**: Minimal implementation effort
6. **Testable**: Can validate CSV before generating SQL
---
