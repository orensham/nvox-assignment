# Journey Routing Rules - Management Guide

## Quick Start

**TL;DR**: Edit `config/routing_rules.csv` → Run generator script → Apply migration

---

## Overview

Routing rules determine how users transition between journey stages based on their answers. Rules are defined in a **CSV file** for easy editing, then converted to **SQL migrations** that populate the `journey_edges` database table.

### Source of Truth
- **File**: `apps/nvox-api/config/routing_rules.csv`
- **Format**: Standard CSV (can edit in Excel, Google Sheets, VS Code)
- **Version Control**: Track changes in Git like any code file

---

## CSV Format

```csv
stage_id,if_number_id,in_range_min,in_range_max,next_stage
BOARD,brd_risk_score,0.0,6.999,PREOP
BOARD,brd_risk_score,7.0,10.0,EXIT
BOARD,brd_needs_more_tests,1.0,1.0,WORKUP
```

### Columns

| Column | Description | Example |
|--------|-------------|---------|
| `stage_id` | Current stage ID | `BOARD` |
| `if_number_id` | Question ID to evaluate | `brd_risk_score` |
| `in_range_min` | Minimum value (inclusive) | `0.0` |
| `in_range_max` | Maximum value (inclusive) | `6.999` |
| `next_stage` | Destination stage if match | `PREOP` |

### Rule Meaning

```csv
BOARD,brd_risk_score,0.0,6.999,PREOP
```
Reads as: **"If user is at BOARD stage and answers `brd_risk_score` with a value between 0.0 and 6.999, transition to PREOP"**

---

## Common Tasks

### 1. Add a New Routing Rule

**Scenario**: Add emergency path from BOARD to ICU for very high risk scores

#### Step 1: Edit CSV
Open `config/routing_rules.csv` and add new row:

```csv
BOARD,brd_emergency_score,8.0,10.0,ICU
```

#### Step 2: Generate Migration
```bash
python3 scripts/generate_edge_migration.py
```

Output:
```
Generated migration: migrations/006_update_edges_from_csv.sql
Contains 29 routing rules
```

#### Step 3: Apply Migration
```bash
docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey \
  < migrations/006_update_edges_from_csv.sql
```

**Done!** New rule is active immediately (no API restart needed)

---

### 2. Modify an Existing Rule

**Scenario**: Change PREOP threshold from 6.999 to 7.5

#### Step 1: Edit CSV
Find the row:
```csv
BOARD,brd_risk_score,0.0,6.999,PREOP
```

Change to:
```csv
BOARD,brd_risk_score,0.0,7.5,PREOP
```

#### Step 2: Generate & Apply
```bash
# Generate migration
python3 scripts/generate_edge_migration.py

# Apply
docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey \
  < migrations/006_update_edges_from_csv.sql
```

**Done!** Updated threshold is live

---

### 3. Remove a Routing Rule

**Scenario**: Remove EXIT path from BOARD stage

#### Step 1: Edit CSV
Delete the row:
```csv
BOARD,brd_risk_score,7.0,10.0,EXIT
```

#### Step 2: Generate & Apply
```bash
python3 scripts/generate_edge_migration.py
docker exec -i nvox-postgres psql ... < migrations/006_update_edges_from_csv.sql
```

**Done!** Path removed

---

### 4. Validate Changes Before Applying

**Always validate CSV before generating migration:**

```bash
python3 scripts/generate_edge_migration.py --dry-run
```
---

## Validation Rules

The generator script checks for:

### Required Fields
- All columns must have values
- No empty cells allowed

### Valid Ranges
- `range_min` must be ≤ `range_max`
- No negative ranges
- Numeric values must be valid

### No Overlaps
**Same stage + question cannot have overlapping ranges:**

**Bad** (overlapping):
```csv
BOARD,brd_risk_score,0.0,7.0,PREOP
BOARD,brd_risk_score,6.5,10.0,EXIT
```
*Problem: Values 6.5-7.0 match both rules*

**Good** (non-overlapping):
```csv
BOARD,brd_risk_score,0.0,6.999,PREOP
BOARD,brd_risk_score,7.0,10.0,EXIT
```

---

## Example Workflow

### Scenario: Medical team wants to tighten PREOP admission criteria

**Current rule:**
```csv
BOARD,brd_risk_score,0.0,6.999,PREOP
```

**New requirement:** Only scores 0-5.5 should go to PREOP, higher scores exit

#### 1. Create branch
```bash
git checkout -b tighten-preop-criteria
```

#### 2. Edit CSV
```csv
# Old
BOARD,brd_risk_score,0.0,6.999,PREOP
BOARD,brd_risk_score,7.0,10.0,EXIT

# New
BOARD,brd_risk_score,0.0,5.5,PREOP
BOARD,brd_risk_score,5.501,10.0,EXIT
```

#### 3. Validate
```bash
python3 scripts/generate_edge_migration.py --dry-run
```

#### 4. Generate migration
```bash
python3 scripts/generate_edge_migration.py
```

#### 5. Review generated SQL
```bash
cat migrations/006_update_edges_from_csv.sql
```

Verify the changes look correct.

#### 6. Test in development
```bash
# Apply migration
docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey \
  < migrations/006_update_edges_from_csv.sql

# Verify count
docker exec nvox-postgres psql -U transplant_user -d transplant_journey \
  -c "SELECT COUNT(*) FROM journey_edges;"
```

#### 7. Test with API
```bash
# Test case: risk_score = 6.0 should now go to EXIT (not PREOP)
curl -X POST http://localhost:8000/v1/journey/continue \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

#### 8. Commit changes
```bash
git add config/routing_rules.csv
git add migrations/006_update_edges_from_csv.sql
git commit -m "Tighten PREOP admission criteria to risk_score ≤ 5.5"
git push origin tighten-preop-criteria
```

#### 9. Create pull request

Review process:
- CSV changes are human-readable in diff
- Generated SQL can be reviewed by DBA
- Tests verify new behavior

**Done!** Rules updated in production, takes effect immediately

---

## Best Practices

### Use Descriptive Migration Numbers
```bash
# Use semantic numbering
python3 scripts/generate_edge_migration.py --number 006
```

### Always Use Dry Run First
```bash
# Validate before generating
python3 scripts/generate_edge_migration.py --dry-run
```
---

## Advantages Over Direct SQL

| Task | CSV Approach | Direct SQL |
|------|-------------|------------|
| **Edit rule** | Change one cell in Excel | Write UPDATE statement |
| **Add rule** | Add one row | Write INSERT statement |
| **View all rules** | Open CSV in Excel | Query database |
| **Diff changes** | Git diff shows changed rows | Hard to see what changed |
| **Non-tech edits** | Anyone can edit CSV | Need SQL knowledge |
| **Validation** | Auto-checked by script | Manual/error-prone |

---

## Summary

### Managing Routing Rules

1. **Edit** `config/routing_rules.csv` (Excel, Google Sheets, VS Code)
2. **Validate** with `--dry-run` flag
3. **Generate** SQL migration
4. **Apply** to database
5. **Commit** both CSV and SQL to Git
---

## Next Steps

- Read [ROUTING_FLOW.md](ROUTING_FLOW.md) to understand how rules are used at runtime
- See [ROUTING_MANAGEMENT.md](ROUTING_MANAGEMENT.md) for advanced management options
