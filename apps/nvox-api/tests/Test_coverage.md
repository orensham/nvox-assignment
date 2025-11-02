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

## Test Coverage Matrix

### ✅ Entry Point
| Edge Case | Test File | Test Function | Status |
|-----------|-----------|---------------|--------|
| `[ * ] → REFERRAL` (signup initializes journey) | `test_journey_endpoints.py` | `test_signup_initializes_journey` | ✅ PASS |

### ✅ Exit Paths
| Edge Case | Test File | Test Function | Status |
|-----------|-----------|---------------|--------|
| **REFERRAL → EXIT** (ref_karnofsky 0-39.999) | `test_journey_endpoints.py` | `test_submit_answer_low_score_exit` | ✅ PASS |
| **BOARD → EXIT** (brd_risk_score 7-10) | `test_journey_edge_cases.py` | `test_board_high_risk_to_exit` | ✅ PASS |

### ✅ Normal Path Progression
| Edge Case | Test File | Test Function | Status |
|-----------|-----------|---------------|--------|
| **REFERRAL → WORKUP** (ref_karnofsky 40-100) | `test_journey_endpoints.py` | `test_submit_answer_with_transition`<br>`test_journey_flow_complete_path` | ✅ PASS |
| **WORKUP → MATCH** (wrk_egfr 0-15.999) | `test_journey_edge_cases.py` | `test_fallback_board_to_workup` (step 2)<br>`test_fallback_donor_to_match` (step 2) | ✅ PASS |
| **MATCH → DONOR** (mtc_pra 0-79.999) | `test_journey_edge_cases.py` | `test_fallback_board_to_workup` (step 3)<br>`test_fallback_donor_to_match` (step 3) | ✅ PASS |
| **MATCH → BOARD** (mtc_pra 80-100) - High PRA path | `test_journey_edge_cases.py` | `test_match_high_pra_to_board` | ✅ PASS |
| **DONOR → BOARD** (dnr_clearance=1) | `test_journey_edge_cases.py` | `test_fallback_board_to_workup` (step 4) | ✅ PASS |

### ✅ Fallback Paths (Returning to Earlier Stages)
| Edge Case | Test File | Test Function | Status |
|-----------|-----------|---------------|--------|
| **BOARD → WORKUP** (brd_needs_more_tests=1) | `test_journey_edge_cases.py` | `test_fallback_board_to_workup` | ✅ PASS |
| **DONOR → MATCH** (dnr_clearance=0) | `test_journey_edge_cases.py` | `test_fallback_donor_to_match` | ✅ PASS |

### 📝 Documented but Not Yet Tested

The following edge cases from `edges-descriptions.md` are documented but don't have dedicated integration tests yet:

#### Later Stage Progressions
- **BOARD → PREOP** (brd_risk_score 0-6.999)
- **PREOP → ORSCHED** (prp_bp 60-179.999)
- **PREOP → WORKUP** (prp_infection_status=1 or prp_bp 180-240)
- **ORSCHED → SURG** (ors_final_crossmatch=1)
- **ORSCHED → PREOP** (ors_final_crossmatch=0)
- **SURG → ICU** (srg_warm_isch_time 0-120)
- **ICU → WARD** (icu_airway_stable=1)
- **ICU → COMPLX** (icu_airway_stable=0)

#### Loop Paths
- **WARD → HOME** (wrd_walk_meters 150-2000)
- **WARD → COMPLX** (wrd_walk_meters 0-149.999)
- **HOME → HOME** (hom_creatinine 0.1-2.0) - stable monitoring
- **HOME → COMPLX** (hom_creatinine 2.0001-15.0) - rejection/complication
- **COMPLX → HOME** (cpx_severity 0-4.999) - mild, resolved
- **COMPLX → WARD** (cpx_severity 5-7) - moderate, needs rehab
- **COMPLX → RELIST** (cpx_severity 8-10) - severe, graft failure

#### RELIST Paths
- **RELIST → MATCH** (rlt_new_pra 0-79.999)
- **RELIST → BOARD** (rlt_new_pra 80-100)

---

## Test Statistics

- **Total edge cases documented:** 27 routing rules
- **Edge cases with dedicated tests:** 8
- **Test files:** 2
  - `tests/integration/test_journey_endpoints.py` - 11 tests
  - `tests/integration/test_journey_edge_cases.py` - 4 tests
- **Total integration tests:** 15 ✅ ALL PASSING

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
