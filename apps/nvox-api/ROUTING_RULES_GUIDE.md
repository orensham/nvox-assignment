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
✓ Generated migration: migrations/006_update_edges_from_csv.sql
✓ Contains 29 routing rules
```

#### Step 3: Apply Migration
```bash
docker exec -i nvox-postgres psql -U transplant_user -d transplant_journey \
  < migrations/006_update_edges_from_csv.sql
```

✅ **Done!** New rule is active immediately (no API restart needed)

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

✅ **Done!** Updated threshold is live

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

✅ **Done!** Path removed

---

### 4. Validate Changes Before Applying

**Always validate CSV before generating migration:**

```bash
python3 scripts/generate_edge_migration.py --dry-run
```

Output:
```
✓ 28 rules validated successfully
```

Or if errors:
```
❌ Validation errors:
  • Row 5: range_min (7.0) > range_max (6.0)
  • Row 8: Empty next_stage
  • Overlapping ranges for BOARD.brd_risk_score:
    Row 10 [0.0-7.0→PREOP] overlaps Row 11 [6.5-10.0→EXIT]
```

---

## Validation Rules

The generator script checks for:

### ✅ Required Fields
- All columns must have values
- No empty cells allowed

### ✅ Valid Ranges
- `range_min` must be ≤ `range_max`
- No negative ranges
- Numeric values must be valid

### ✅ No Overlaps
**Same stage + question cannot have overlapping ranges:**

❌ **Bad** (overlapping):
```csv
BOARD,brd_risk_score,0.0,7.0,PREOP
BOARD,brd_risk_score,6.5,10.0,EXIT
```
*Problem: Values 6.5-7.0 match both rules*

✅ **Good** (non-overlapping):
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
```
✓ 28 rules validated successfully
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
- ✅ CSV changes are human-readable in diff
- ✅ Generated SQL can be reviewed by DBA
- ✅ Tests verify new behavior

#### 10. Deploy to production
```bash
# Production migration
kubectl exec -i postgres-pod -- psql ... < migrations/006_update_edges_from_csv.sql
```

✅ **Done!** Rules updated in production, takes effect immediately

---

## Tips & Best Practices

### 🎯 Tip 1: Use Descriptive Migration Numbers
```bash
# Use semantic numbering
python3 scripts/generate_edge_migration.py --number 006
```

### 🎯 Tip 2: Always Use Dry Run First
```bash
# Validate before generating
python3 scripts/generate_edge_migration.py --dry-run
```

### 🎯 Tip 3: Keep CSV Clean
- ✅ Sort by stage_id, then question_id
- ✅ No empty rows at end
- ✅ Consistent decimal places (e.g., always use `1.0` not `1`)

### 🎯 Tip 4: Document Major Changes
Add comments in Git commit messages:
```bash
git commit -m "Update BOARD routing rules

- Tightened PREOP admission (risk ≤ 5.5, was 6.999)
- Added emergency ICU path for risk > 9.0
- Removed deprecated EXIT path

Resolves: NVOX-123"
```

### 🎯 Tip 5: Test in Staging First
```bash
# Generate migration
python3 scripts/generate_edge_migration.py

# Apply to staging
psql -h staging-db ... < migrations/006_update_edges_from_csv.sql

# Run integration tests
pytest tests/integration/

# If all pass, promote to production
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

## Troubleshooting

### Q: "CSV file not found"
**A:** Make sure you're running from project root:
```bash
cd /path/to/nvox-assignment
python3 apps/nvox-api/scripts/generate_edge_migration.py
```

### Q: "Overlapping ranges" error
**A:** Two rules for same stage+question have overlapping ranges. Fix by adjusting boundaries:
```csv
# Before (overlaps at 7.0)
BOARD,brd_risk_score,0.0,7.0,PREOP
BOARD,brd_risk_score,7.0,10.0,EXIT

# After (no overlap)
BOARD,brd_risk_score,0.0,6.999,PREOP
BOARD,brd_risk_score,7.0,10.0,EXIT
```

### Q: "Migration already exists"
**A:** Specify a higher number:
```bash
python3 scripts/generate_edge_migration.py --number 999
```

### Q: Changes not taking effect?
**A:** Check migration was applied:
```bash
docker exec nvox-postgres psql -U transplant_user -d transplant_journey \
  -c "SELECT * FROM journey_edges WHERE from_node_id='BOARD';"
```

---

## Summary

### Managing Routing Rules

1. ✅ **Edit** `config/routing_rules.csv` (Excel, Google Sheets, VS Code)
2. ✅ **Validate** with `--dry-run` flag
3. ✅ **Generate** SQL migration
4. ✅ **Apply** to database
5. ✅ **Commit** both CSV and SQL to Git

### Key Points

- 📁 **Source of truth**: CSV file (easy to edit)
- 🔄 **Generator script**: Converts CSV → SQL
- 💾 **Runtime**: Rules loaded from database (not CSV)
- ⚡ **Immediate**: Changes apply without API restart
- 📝 **Version control**: Track changes in Git
- ✅ **Validation**: Automatic checks for errors

---

## Next Steps

- Read [ROUTING_FLOW.md](../../ROUTING_FLOW.md) to understand how rules are used at runtime
- See [ROUTING_MANAGEMENT.md](../../ROUTING_MANAGEMENT.md) for advanced management options
