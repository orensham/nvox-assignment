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

✅ **Result**: Rule active immediately, no API restart needed

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

✅ **Result**: Next request uses new threshold

---

#### 3. **Removing a Rule**

```sql
-- Migration 008: Remove deprecated EXIT path from BOARD
DELETE FROM journey_edges
WHERE from_node_id = 'BOARD'
  AND to_node_id = 'EXIT';
```

✅ **Result**: Path no longer available

---

## Pros & Cons of SQL Migrations Approach

### ✅ Pros

| Benefit | Description |
|---------|-------------|
| **Immediate Effect** | Changes apply instantly without API restart |
| **Version Control** | Migrations tracked in Git like code |
| **Audit Trail** | Each change has timestamp, author, commit message |
| **Rollback Support** | Can write reverse migrations |
| **Database Integrity** | Foreign key constraints prevent invalid rules |
| **Production Safety** | Review process via pull requests |

### ❌ Cons

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

#### Implementation:

<details>
<summary>Click to see Python script</summary>

```python
#!/usr/bin/env python3
"""Generate SQL migration from routing_rules.csv"""

import csv
from datetime import datetime
from pathlib import Path

def generate_migration():
    csv_path = Path("config/routing_rules.csv")

    # Find next migration number
    migrations_dir = Path("migrations")
    existing = sorted(migrations_dir.glob("*.sql"))
    next_num = len(existing) + 1

    output_path = migrations_dir / f"{next_num:03d}_update_edges_from_csv.sql"

    # Read CSV
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rules = list(reader)

    # Generate SQL
    sql = f"""-- Migration {next_num:03d}: Update journey edges from CSV
-- Generated: {datetime.now().isoformat()}
-- Source: {csv_path}

BEGIN;

-- Clear existing edges (except entry edge)
DELETE FROM journey_edges WHERE from_node_id IS NOT NULL;

-- Insert edges from CSV
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
"""

    values = []
    for rule in rules:
        values.append(
            f"  ('{rule['stage_id']}', '{rule['next_stage']}', 'range', "
            f"'{rule['if_number_id']}', {rule['in_range_min']}, {rule['in_range_max']})"
        )

    sql += ",\n".join(values) + ";\n\nCOMMIT;\n"

    # Write migration
    with open(output_path, 'w') as f:
        f.write(sql)

    print(f"✓ Generated migration: {output_path}")
    print(f"✓ {len(rules)} rules converted")
    print("\nNext steps:")
    print(f"  1. Review: cat {output_path}")
    print(f"  2. Apply: docker exec -i nvox-postgres psql ... < {output_path}")

if __name__ == "__main__":
    generate_migration()
```
</details>

**Benefits**:
- ✅ CSV is easy to edit (Excel, Google Sheets)
- ✅ Non-technical users can manage rules
- ✅ Still get migration versioning
- ✅ Can diff CSV changes in Git

---

### Option 2: Admin Web UI (Future Enhancement)

Build an admin interface for rule management:

```
┌─────────────────────────────────────────────┐
│  Admin Panel - Journey Edge Manager         │
├─────────────────────────────────────────────┤
│                                              │
│  [From: BOARD] ──→ [To: PREOP]              │
│                                              │
│  Condition: brd_risk_score                   │
│  Type: [Range ▼]                             │
│  Min: [0.0    ]  Max: [7.5    ]              │
│                                              │
│  [Save]  [Delete]  [Test Rule]               │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │ All Edges from BOARD:                │   │
│  │ • BOARD → WORKUP (brd_needs_more=1)  │   │
│  │ • BOARD → PREOP (brd_risk 0-7.5)     │   │
│  │ • BOARD → EXIT (brd_risk 7.5-10)     │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

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

1. ✅ **Backwards compatible**: Keep familiar CSV format
2. ✅ **Easy to edit**: Anyone can edit CSV in Excel
3. ✅ **Version controlled**: CSV diffs are readable
4. ✅ **Safe**: Generated SQL can be reviewed before applying
5. ✅ **No UI needed**: Minimal implementation effort
6. ✅ **Testable**: Can validate CSV before generating SQL

### Implementation Steps:

1. **Restore routing_rules.csv** (keep it as source of truth)
2. **Create generator script** (`scripts/generate_edge_migration.py`)
3. **Update README** with workflow
4. **Add validation** (check for overlapping ranges, etc.)

---

## Comparison Matrix

| Approach | Ease of Use | Safety | Speed | Technical Skill |
|----------|-------------|--------|-------|-----------------|
| **Direct SQL** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | SQL required |
| **CSV + Generator** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Basic CSV editing |
| **Admin UI** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | None (point & click) |
| **GraphQL** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | GraphQL knowledge |

---

## Current State vs Desired State

### Current (After Migration to Graph)
```
Developer writes SQL migration → Apply to database → Rules immediately active
```

**Problem**: Requires SQL knowledge for every rule change

### Recommended (CSV + Generator)
```
Anyone edits CSV → Run generator script → Review SQL → Apply to database
```

**Benefits**:
- CSV is version controlled (easy to see what changed)
- Non-technical users can propose changes
- Generated SQL can be reviewed for safety
- Best of both worlds

---

## Next Steps

Would you like me to:

1. ✅ **Implement CSV generator script** (Option 1)
2. ✅ **Restore routing_rules.csv** as source of truth
3. ✅ **Add validation** to catch rule conflicts
4. ✅ **Update documentation** with new workflow

Or would you prefer a different approach?
