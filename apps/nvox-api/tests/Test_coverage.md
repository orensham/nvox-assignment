# Journey Edge Case Test Coverage

This document maps the edge cases documented in `config/edges-descriptions.md` to the integration tests that verify them.

## Summary of Edge Cases from edges-descriptions.md

**Edge case paths mentioned:**
1. **Entry:** `[ * ] → REFERRAL`
2. **Normal path:** REFERRAL → WORKUP → MATCH → DONOR → BOARD → PREOP → ORSCHED → SURG → ICU → WARD → HOME
3. **Fallbacks:** Routes back to earlier stages (e.g., Workup or Complication)
4. **Loops:** HOME ↔ COMPLX ↔ WARD (monitoring and recovery cycles)
5. **Endings:** EXIT or RELIST for graft failure

---
## Test Statistics

- **Total edge cases documented:** 27 routing rules
- **Edge cases with dedicated tests:** 8
- **Test files:** 2
  - `tests/integration/test_journey_endpoints.py` - 11 tests
  - `tests/integration/test_journey_edge_cases.py` - 4 tests
- **Total integration tests:** 15 ALL PASSING

---

## Recommendations for Additional Test Coverage

To achieve complete coverage of the documented edge cases, consider adding tests for:

1. **High-priority fallback paths:**
   - PREOP → WORKUP (infection or high BP)
   - ORSCHED → PREOP (failed crossmatch)

2. **Loop scenarios (HOME ↔ COMPLX ↔ WARD):**
   - These are critical for demonstrating the monitoring and recovery cycles mentioned in the summary
   - Would require progressing through many stages to reach HOME/WARD/COMPLX

3. **RELIST path:**
   - Important for demonstrating graft failure scenarios
   - Would require progressing through to COMPLX and triggering severe complications

Note: The later-stage paths (PREOP → ORSCHED → SURG → ICU → WARD → HOME) would require very long test scenarios progressing through 8-10 stages. Consider whether the ROI justifies this complexity, or whether the existing tests provide sufficient confidence in the routing engine's behavior.

---

## How to Run Tests

```bash
# Run all journey integration tests
uv run --directory apps/nvox-api pytest tests/integration/ -v -k "journey"

# Run just edge case tests
uv run --directory apps/nvox-api pytest tests/integration/test_journey_edge_cases.py -v

# Run just endpoint tests
uv run --directory apps/nvox-api pytest tests/integration/test_journey_endpoints.py -v
```
