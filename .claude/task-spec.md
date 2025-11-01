# Technical Specification: Routing Engine & UI Implementation
## Living-Donor Kidney Transplant Journey System

**Version:** 1.0  
**Date:** November 2025  
**Status:** Implementation Ready  
**Previous Work:** Authentication system complete (signup, login, logout with tests)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Context](#project-context)
3. [Current State](#current-state)
4. [Scope of This Phase](#scope-of-this-phase)
5. [Routing Engine Specification](#routing-engine-specification)
6. [User Interface Specification](#user-interface-specification)
7. [Technical Constraints](#technical-constraints)
8. [Performance Requirements](#performance-requirements)
9. [Security Requirements](#security-requirements)
10. [Data Flow Architecture](#data-flow-architecture)
11. [Testing Requirements](#testing-requirements)
12. [Deployment Considerations](#deployment-considerations)
13. [Success Criteria](#success-criteria)

---

## Executive Summary

### What We're Building

A **dynamic routing engine** and **patient-facing web UI** for the Living-Donor Kidney Transplant Journey System. This phase completes the full patient journey experience by:

1. **Routing Engine**: Evaluates patient answers against clinical rules to determine next care stage
2. **Web UI**: Interactive interface for patients to answer questions and track their journey progress

### Key Objectives

- ✅ Enable non-linear patient journeys based on clinical criteria
- ✅ Support real-time routing decisions without code changes
- ✅ Provide intuitive patient experience with progress tracking
- ✅ Maintain HIPAA compliance and PII protection
- ✅ Achieve <200ms routing decision latency
- ✅ Support 1000+ concurrent users

---

## Project Context

### The Medical Problem

Living-donor kidney transplant is a complex, multi-month journey involving:
- **14 distinct stages** (REFERRAL → WORKUP → MATCH → ... → EXIT)
- **Multiple clinical decision points** (e.g., infection status, kidney function)
- **Non-linear paths** (patients can loop back, skip stages, or exit early)
- **Dynamic routing** based on test results and clinical criteria

### Business Requirements

1. **Clinical Flexibility**: Clinicians need to update routing rules without engineering changes
2. **Patient Autonomy**: Patients need to see their progress and next steps clearly
3. **Data Integrity**: All decisions must be auditable and reproducible
4. **Privacy Compliance**: HIPAA-compliant handling of all medical data
5. **Scalability**: Support multiple hospitals/clinics with different rule sets

### What Makes This Complex

- **Non-deterministic routing**: Same stage can lead to different next stages based on answers
- **Priority-based evaluation**: Multiple rules may match; highest priority wins
- **Loop detection**: Patients can revisit stages (track visit numbers)
- **State persistence**: Users must be able to pause and resume their journey
- **Real-time validation**: Answers must be validated against constraints immediately

---

## Current State

### ✅ Completed Components (via Claude Code)

#### Authentication System - COMPLETE
- **Signup**: Email/password with bcrypt hashing (cost factor 12)
- **Login**: JWT tokens (1-hour expiration, HS256)
- **Logout**: Session termination with audit logging
- **PII Protection**: Email stored as SHA256 hash, encrypted vault for recovery
- **Tests**: Comprehensive unit and integration tests
- **Endpoints**: POST /signup, POST /login, POST /logout

#### Database - PARTIAL
**Completed:**
- ✅ **users**: Hashed credentials, anonymization flags
- ✅ Basic PostgreSQL setup with asyncpg
- ✅ Connection pooling

**NOT YET CREATED (need to be added):**
- ❌ Transaction support
- ❌ **user_journey_state**: Current stage tracking
- ❌ **user_answers**: Versioned answer history (JSONB)
- ❌ **stage_transitions**: Audit trail of all transitions
- ❌ **user_journey_path**: Visit tracking with entry/exit timestamps
- ❌ **audit_log**: Comprehensive action logging (no PII)
- ❌ **anonymization_log**: GDPR deletion tracking

**Schema SQL Available**: `updated_database_schema.sql` contains all table definitions but tables haven't been created yet.

#### Test Suite - COMPLETE
- **105+ tests**: Unit, integration, API tests for auth
- **Testcontainers**: Automatic PostgreSQL setup
- **Coverage**: >85% for auth components

### 📋 Pending Components (This Phase)

#### 1. Database Tables (Must be created first)
**CRITICAL**: The following tables from `updated_database_schema.sql` need to be created before implementing routing engine:

```sql
-- Core journey tables
CREATE TABLE user_journey_state (...)
CREATE TABLE user_answers (...)
CREATE TABLE stage_transitions (...)
CREATE TABLE user_journey_path (...)

-- Audit tables
CREATE TABLE audit_log (...)
CREATE TABLE anonymization_log (...)

-- Indexes
CREATE INDEX idx_journey_state_user ON user_journey_state(user_id);
CREATE INDEX idx_answers_user_stage ON user_answers(user_id, stage_id);
-- ... etc
```

**Recommendation**: Run the complete schema creation as first step of implementation.

#### 2. Routing Engine Implementation
- Rule evaluation logic
- CSV rule loading and caching (Redis)
- Priority-based decision making
- Answer validation engine
- Integration with journey tables

#### 3. API Endpoints (New endpoints needed)
- **GET /api/v1/journey/current** - Get current stage and questions
- **POST /api/v1/journey/answer** - Submit answers and trigger routing
- **GET /api/v1/journey/history** - Get journey path history
- **DELETE /api/v1/user** - Anonymize user (already designed, not implemented)

#### 4. User Interface
- Patient dashboard
- Question presentation
- Progress visualization
- Journey path display

---

## Scope of This Phase

### In Scope ✅

#### Routing Engine
- Load routing rules from CSV (cached in Redis)
- Load journey configuration from JSON (stage definitions, questions)
- Evaluate patient answers against routing rules
- Determine next stage based on priority and matching criteria
- Validate answer values against question constraints
- Support partial answer submission (save progress)
- Detect and handle stage loops (track visit numbers)
- Log all routing decisions for audit trail

#### User Interface
- Patient dashboard showing current stage
- Dynamic question form rendering (from JSON)
- Answer submission with real-time validation
- Previous answer pre-filling
- Accessibility (WCAG 2.1 AA compliance)

### Out of Scope ❌

- Admin portal for rule management (future phase)
- Clinician dashboard (future phase)
- Multi-language support (future phase)
- Email notifications (future phase)
- Document upload functionality (future phase)
- Video consultation scheduling (future phase)

---

## Routing Engine Specification

### Overview

The routing engine is the **decision-making core** of the system. It evaluates patient answers against clinical routing rules to determine the next appropriate stage in their transplant journey.

### Core Responsibilities

1. **Rule Loading & Caching**
   - Load routing rules from CSV file at startup
   - Cache rules in Redis for fast lookups
   - Support hot-reloading without service restart
   - Validate rule completeness on load

2. **Answer Evaluation**
   - Compare answer values against rule ranges
   - Handle numeric ranges (e.g., eGFR 16-150 → MATCH)
   - Handle categorical values (e.g., infection_cleared: yes/no)
   - Support complex conditions (AND/OR logic if needed)

3. **Priority Resolution**
   - When multiple rules match, select highest priority
   - Priority determined by clinical importance (e.g., infections > kidney function)
   - Tie-breaking: first rule wins

4. **Stage Determination**
   - Return next stage based on matched rule
   - Return "stay in current stage" if insufficient answers
   - Return missing questions list if transition not possible
   - Provide reason for decision (for audit and patient feedback)

### Data Sources

#### CSV Format: Routing Rules

**Location**: `task_resources/transplant_journey_routes_only.csv`

**Structure**:
```csv
stage_id,if_number_id,in_range_min,in_range_max,next_stage,evaluation_order
REFERRAL,ref_karnofsky,0,49,EXIT,1
REFERRAL,ref_karnofsky,50,100,WORKUP,1
WORKUP,wrk_infections_cleared,0,0,COMPLX,1
WORKUP,wrk_egfr,0,15,EXIT,2
WORKUP,wrk_egfr,16,150,MATCH,2
```

**Columns**:
- `stage_id`: Current stage (e.g., REFERRAL, WORKUP)
- `if_number_id`: Question ID to evaluate (e.g., ref_karnofsky)
- `in_range_min`: Minimum value (inclusive)
- `in_range_max`: Maximum value (inclusive)
- `next_stage`: Target stage if rule matches
- `evaluation_order`: Order to check rules (lower = check first). Optional, defaults to 999.

**Important Notes**:
- Each row is one routing rule
- Ranges for **same question** never overlap (mutually exclusive)
- Multiple questions can exist for same stage (use evaluation_order)
- Ranges are inclusive on both ends [min, max]
- Boolean values: 0 = no/false, 1 = yes/true
- `evaluation_order`: Safety-critical questions (infections) = 1, Clinical tests = 2, etc.

**Why evaluation_order?**
- Different questions in same stage may lead to different next stages
- Safety checks (infections) should be evaluated before clinical thresholds
- Same question rules can have same evaluation_order (they don't overlap anyway)

#### JSON Format: Journey Configuration

**Location**: `task_resources/transplant_journey_questions_only.json`

**Structure**:
```json
{
  "version": "1.0",
  "domain": "living-donor-kidney-transplant",
  "entry_stage": "REFERRAL",
  "stages": [
    {
      "id": "REFERRAL",
      "name": "Referral",
      "description": "Initial patient referral and assessment",
      "questions": [
        {
          "id": "ref_karnofsky",
          "text": "What is the patient's Karnofsky Performance Score?",
          "type": "number",
          "constraints": {
            "min": 0,
            "max": 100,
            "step": 10
          },
          "help_text": "Score from 0-100 indicating functional status",
          "required": true
        }
      ]
    }
  ]
}
```

**Key Elements**:
- `stages[]`: Array of all journey stages
- `questions[]`: Questions for each stage
- `constraints`: Validation rules (min, max, allowed values, etc.)
- `required`: Whether question must be answered for transition

### Redis Caching Strategy

**Purpose**: Fast rule lookups without file I/O on every request

#### Cache Structure

```
Key Pattern: route:rules:{stage_id}
Value: JSON array of routing rules for that stage
TTL: No expiration (manually invalidated on rule updates)

Example:
Key: route:rules:REFERRAL
Value: [
  {
    "rule_id": 1,
    "question_id": "ref_karnofsky",
    "range_min": 0,
    "range_max": 49,
    "next_stage": "EXIT",
    "evaluation_order": 1
  },
  {
    "rule_id": 2,
    "question_id": "ref_karnofsky",
    "range_min": 50,
    "range_max": 100,
    "next_stage": "WORKUP",
    "evaluation_order": 1
  }
]

Note: Rules are stored sorted by evaluation_order for efficient lookup
```

#### Additional Cache Keys

```
Key: route:config
Value: Full JSON journey configuration
TTL: No expiration

Key: route:stage:{stage_id}:questions
Value: Questions for specific stage
TTL: No expiration

Key: route:last_reload
Value: Timestamp of last rule reload
TTL: No expiration
```

#### Cache Invalidation

- **On Application Start**: Load CSV → Cache all rules
- **On Rule Update**: Clear `route:rules:*` keys → Reload CSV
- **Manual Trigger**: Admin endpoint to force reload
- **Versioning**: Include version number in cache key if needed

#### Redis Configuration

```
Host: localhost (dev) / redis-cluster (prod)
Port: 6379
Database: 0
Max Connections: 50
Connection Timeout: 5 seconds
Command Timeout: 1 second
Retry Strategy: Exponential backoff (3 attempts)
```

### Rule Evaluation Logic

**Important Clarification**: The routing rules are designed with **non-overlapping ranges** for each question. This means:

- Each question ID has mutually exclusive ranges
- No two rules for the same question will have overlapping min/max values
- Priority mechanism is **NOT needed** - there will always be exactly 0 or 1 matching rule per question

**Example** (No Overlap):
```csv
REFERRAL,ref_karnofsky,0,49,EXIT     # Range: 0-49
REFERRAL,ref_karnofsky,50,100,WORKUP # Range: 50-100
# No overlap! Value 49 → EXIT, Value 50 → WORKUP
```

**Rule Design Principles**:
1. Ranges are **comprehensive** (cover all valid values)
2. Ranges are **mutually exclusive** (no overlaps)
3. Ranges are **inclusive** on both ends [min, max]

### Routing Algorithm (Simplified)

**High-Level Flow**:

```
1. Get current stage from user_journey_state
2. Fetch all routing rules for current stage from Redis
3. Get all user answers for current stage from database
4. For each routing rule:
   a. Check if the question required by this rule is answered
   b. Check if answer value falls within rule's range
   c. If match found → return next_stage and rule details
   d. Continue to next rule (no priority needed)
5. If no rule matched:
   a. Check if all required questions are answered
   b. If no → return missing_questions list
   c. If yes but no match → This indicates a RULE GAP (error condition)
6. Save routing decision to audit log
```

**Example Evaluation**:

```
Current Stage: WORKUP
User Answers: {
  "wrk_egfr": 25,
  "wrk_infections_cleared": 1  // No infection
}

Rules for WORKUP:
1. wrk_infections_cleared: 0-0 → COMPLX  (if infection exists)
2. wrk_egfr: 0-15 → EXIT                (very low kidney function)
3. wrk_egfr: 16-150 → MATCH             (acceptable kidney function)

Evaluation:
- Check wrk_infections_cleared = 1
  - Rule 1: Needs 0-0, but answer is 1 → No match
- Check wrk_egfr = 25
  - Rule 2: Needs 0-15, but answer is 25 → No match
  - Rule 3: Needs 16-150, answer is 25 → MATCH!

Result: Transition to MATCH
Reason: "Kidney function (eGFR=25) meets criteria for donor matching"
```

### Multiple Questions in Same Stage

**Important**: A stage may have multiple questions, but typically only ONE question drives the routing decision. Other questions may be for informational purposes only.

**Example**:
```csv
WORKUP,wrk_egfr,0,15,EXIT
WORKUP,wrk_egfr,16,150,MATCH
WORKUP,wrk_infections_cleared,0,0,COMPLX
```

In this example:
- **Primary routing**: Based on eGFR value (determines MATCH vs EXIT)
- **Override rule**: Active infection (value=0) always routes to COMPLX regardless of eGFR
- **Evaluation order**: Check override conditions first, then primary routing

**Solution**: While ranges don't overlap within the same question, we DO need order of evaluation when DIFFERENT questions can route from the same stage.

### Rule Evaluation Order (Corrected)

When a stage has rules based on **different questions**, evaluate in this order:

**Order of Importance**:
1. **Safety-critical conditions** (infections, contraindications)
2. **Required clearances** (donor approval, board decisions)
3. **Clinical thresholds** (lab values, test results)
4. **Administrative** (documentation, appointments)

**Implementation**: Add an `order` column to CSV (not priority within same question, but order across different questions):

```csv
stage_id,if_number_id,in_range_min,in_range_max,next_stage,evaluation_order
WORKUP,wrk_infections_cleared,0,0,COMPLX,1        # Check safety first
WORKUP,wrk_egfr,0,15,EXIT,2                      # Then check kidney function
WORKUP,wrk_egfr,16,150,MATCH,2                   # (same question, same order)
```

**Evaluation Algorithm** (Corrected):

```python
def determine_next_stage(current_stage: str, answers: dict) -> dict:
    # Get all rules for current stage
    rules = get_rules_from_redis(current_stage)
    
    # Group rules by evaluation_order
    rules_by_order = group_by_order(rules)
    
    # Evaluate in order
    for order_group in sorted(rules_by_order.keys()):
        rules_in_group = rules_by_order[order_group]
        
        # Check each rule in this order group
        for rule in rules_in_group:
            question_id = rule.question_id
            
            # Is this question answered?
            if question_id not in answers:
                continue  # Skip to next rule
            
            answer_value = answers[question_id]
            
            # Does answer fall in range?
            if rule.range_min <= answer_value <= rule.range_max:
                # MATCH FOUND!
                return {
                    "transition": True,
                    "next_stage": rule.next_stage,
                    "matched_rule": rule,
                    "reason": f"{question_id}={answer_value} routes to {rule.next_stage}"
                }
    
    # No rules matched - check if all questions answered
    required_questions = get_required_questions(current_stage)
    missing = [q for q in required_questions if q not in answers]
    
    if missing:
        return {
            "transition": False,
            "missing_questions": missing,
            "reason": "Additional information required"
        }
    else:
        # All answered but no match = RULE GAP (error!)
        return {
            "transition": False,
            "error": "RULE_GAP",
            "reason": "No routing rule matched despite all questions answered"
        }
```

### Why This Works

1. **No overlaps within same question** → Exactly 0 or 1 match per question
2. **Evaluation order across questions** → Safety checks before clinical checks
3. **Early exit on first match** → As soon as one rule matches, we're done
4. **Rule gap detection** → All answered but no match = configuration error

### Edge Cases & Handling

#### Case 1: No Rules Match (Some Questions Unanswered)
**Solution**: Return missing_questions list, do NOT transition

#### Case 2: No Rules Match (All Questions Answered)
**Solution**: **RULE GAP ERROR** - Log critical error, notify admin, stay in current stage. This indicates CSV configuration is incomplete.

#### Case 3: Partial Answers
**Solution**: Save answers, return missing_questions list, do NOT transition

#### Case 4: Invalid Answer Values
**Solution**: Reject submission with validation errors before routing evaluation

#### Case 5: Stage Loops (Same Stage Visited Twice)
**Solution**: Increment visit_number in user_journey_path, allow transition

#### Case 6: Redis Cache Miss
**Solution**: Fallback to loading from CSV (slower but reliable)

#### Case 7: Multiple Questions in Same Stage
**Solution**: Evaluate in order (evaluation_order column). First match wins.

#### Case 8: Answer Type Mismatch
**Example**: Question expects number, user submits string
**Solution**: Validation layer catches this before routing evaluation

### Performance Targets

- **Rule Evaluation**: <50ms (cache hit)
- **Rule Evaluation**: <200ms (cache miss, load from CSV)
- **Cache Population**: <5 seconds on startup
- **Answer Validation**: <10ms
- **Concurrent Evaluations**: 1000+ per second

### Error Handling

```
Error Type: Redis Connection Failure
Action: Fallback to loading rules from CSV file
Log: ERROR level, alert monitoring

Error Type: CSV Parse Error
Action: Fail fast on startup, prevent service start
Log: CRITICAL level, require manual fix

Error Type: Rule Validation Failure
Action: Skip invalid rules, log warnings
Log: WARNING level, continue with valid rules

Error Type: JSON Schema Invalid
Action: Fail fast on startup
Log: CRITICAL level, require manual fix
```

## User Interface Specification

### Overview

The UI provides patients with an **intuitive, guided experience** through their transplant journey. It must be simple enough for non-technical users while handling complex medical questions.

### Core Pages

#### 1. Dashboard / Landing Page

**Purpose**: Show current status and next steps

**Components**:
- **Journey Progress Bar**: Visual representation of stage progression
- **Current Stage Card**: Large, prominent display of current stage name
- **Next Steps Section**: Clear call-to-action for answering questions
- **Journey Path History**: Timeline showing completed stages with option to go back and forward

**Layout**:
```
┌────────────────────────────────────────────┐
│ [Logo]  Transplant Journey     [Logout]   │
├────────────────────────────────────────────┤
│                                            │
│  Progress: ●━━━○──○──○──○──○──○  (Stage 2/9)│
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │                                      │ │
│  │   📍 You are at: WORKUP              │ │
│  │   Baseline Clinical Assessment       │ │
│  │                                      │ │
│  │   [Continue to Questions →]          │ │
│  │                                      │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  Your Journey So Far:                     │
│  ✓ REFERRAL - Completed Jan 15, 2025     │
│  ✓ WORKUP - Started Jan 20, 2025 (current)│
│                                            │
└────────────────────────────────────────────┘
```

#### 2. Questions Page

**Purpose**: Present stage-specific questions for user to answer

**Components**:
- **Progress Indicator**: "Question 2 of 5"
- **Question Card**: Large, readable question text
- **Input Field**: Appropriate control based on question type
- **Help Text**: Tooltips explaining medical terms
- **Validation Feedback**: Real-time inline validation
- **Navigation**: Previous/Next buttons
- **Save Progress**: Auto-save draft answers

**Question Types & Rendering**:

```
Number Input:
┌────────────────────────────────────┐
│ What is your current eGFR?         │
│ ℹ️ eGFR measures kidney function    │
│                                    │
│ [    25    ] ml/min/1.73m²        │
│  (Range: 0-150)                    │
│                                    │
│ ✓ Valid value                      │
└────────────────────────────────────┘

Boolean (Yes/No):
┌────────────────────────────────────┐
│ Have all infections been cleared?  │
│ ℹ️ This includes any active infections│
│                                    │
│  ○ Yes                             │
│  ● No                              │
│                                    │
└────────────────────────────────────┘

Text Input:
┌────────────────────────────────────┐
│ Describe your support system       │
│ ℹ️ Who can help during recovery?   │
│                                    │
│ ┌────────────────────────────────┐│
│ │ Spouse available full-time,    ││
│ │ adult children nearby          ││
│ └────────────────────────────────┘│
│  (0/500 characters)                │
└────────────────────────────────────┘
```

**Pre-filling Previous Answers**:
- Fetch latest answer for each question from `user_answers`
- Display in form field (allow editing)
- Show "Last answered: Jan 20, 2025" timestamp
- Highlight if answer was changed

**Validation**:
- **Client-side**: Immediate feedback on input
- **Server-side**: Final validation before save
- **Constraints**: Enforced from JSON config
  - `min`/`max` for numbers
  - `max_length` for text
  - `allowed_values` for categorical

**Error States**:
```
┌────────────────────────────────────┐
│ What is your current eGFR?         │
│                                    │
│ [   999   ] ml/min/1.73m²         │
│                                    │
│ ❌ Value must be between 0 and 150 │
└────────────────────────────────────┘
```

#### 3. Review & Submit Page

**Purpose**: Show all answers before final submission

**Layout**:
```
┌────────────────────────────────────────────┐
│ Review Your Answers - WORKUP               │
├────────────────────────────────────────────┤
│                                            │
│  Current eGFR:                            │
│  25 ml/min/1.73m² [Edit]                  │
│                                            │
│  Infections cleared:                       │
│  No [Edit]                                 │
│                                            │
│  Support system:                           │
│  Spouse available full-time [Edit]         │
│                                            │
├────────────────────────────────────────────┤
│  [← Back]              [Submit Answers →] │
└────────────────────────────────────────────┘
```

#### 4. Transition Confirmation Page

**Purpose**: Inform user of stage transition or next steps

**Success Transition**:
```
┌────────────────────────────────────────────┐
│          ✓ Stage Complete                  │
│                                            │
│  You are moving forward!                   │
│                                            │
│  WORKUP → MATCH                           │
│                                            │
│  Next Step: Donor Matching Process        │
│                                            │
│  Reason: Your kidney function (eGFR=25)   │
│  meets the criteria for donor matching.    │
│                                            │
│  [Continue to Next Stage →]                │
└────────────────────────────────────────────┘
```

**Needs More Info**:
```
┌────────────────────────────────────────────┐
│          ℹ️ More Information Needed        │
│                                            │
│  Your answers have been saved.             │
│                                            │
│  To proceed, please answer:                │
│  • Infection clearance status              │
│  • Recent lab results                      │
│                                            │
│  [Continue Answering Questions]            │
└────────────────────────────────────────────┘
```

**Loop Detected**:
```
┌────────────────────────────────────────────┐
│          ⟲ Returning to Previous Stage     │
│                                            │
│  WORKUP → COMPLX (visit #2)              │
│                                            │
│  You're being referred to our complexity   │
│  management team due to active infection.  │
│                                            │
│  This is a temporary step to ensure your   │
│  safety. You'll return to WORKUP once      │
│  resolved.                                 │
│                                            │
│  [Understand and Continue →]               │
└────────────────────────────────────────────┘
```

#### 5. Journey Path Visualization

**Purpose**: Show complete journey history with loops

**Visual Representation**:
```
Your Journey Timeline:

Jan 15 ──● REFERRAL
         │ (Entered: Jan 15, Exited: Jan 17)
         │
Jan 17 ──● WORKUP (visit 1)
         │ (Entered: Jan 17, Exited: Jan 20)
         │
Jan 20 ──● COMPLX ⟲ (complexity management)
         │ (Entered: Jan 20, Exited: Jan 25)
         │
Jan 25 ──● WORKUP (visit 2)
         │ (Current stage)
         ↓
         ?  Next stage pending...
```

### Design Principles

#### Progressive Enhancement
- **Works Without JS**: Basic functionality without JavaScript
- **Loading States**: Show spinners during API calls
- **Auto-Save**: Draft answers saved every 30 seconds

#### Performance
- **First Contentful Paint**: <1.5 seconds
- **Time to Interactive**: <3 seconds
- **Bundle Size**: <200KB gzipped
- **Code Splitting**: Route-based lazy loading

### Technical Stack Recommendations

#### Frontend Framework
- **React** (with TypeScript) - Component-based, large ecosystem
- **Next.js** 

#### Styling
- **Tailwind CSS** - Utility-first, fast development
- **CSS Modules** - Scoped styles

#### State Management
- **React Query** - Server state management (API calls)
- **Zustand** or **Context API** - Local state
- **Avoid**: Redux (too complex for this use case)

#### Form Management
- **React Hook Form** - Performance, validation
- **Zod** - Schema validation (matches backend)
- **Alternative**: Formik (more features, slower)

#### API Client
- **Axios** or **Fetch API** - HTTP requests
- **React Query** - Caching, automatic retries

#### Testing
- **Jest** - Unit tests
- **React Testing Library** - Component tests

### API Integration

#### Endpoints Used

```
GET /api/v1/journey/current
→ Fetch current stage, questions, previous answers

POST /api/v1/journey/answer
→ Submit answers, trigger routing evaluation
→ Receive transition result or missing questions list

GET /api/v1/journey/history
→ Fetch complete journey path for visualization
→ (New endpoint to be added)
```

#### Request/Response Examples

**Get Current Journey**:
```json
GET /api/v1/journey/current
Authorization: Bearer <jwt_token>

Response 200:
{
  "success": true,
  "journey": {
    "current_stage": {
      "id": "WORKUP",
      "name": "Baseline Workup",
      "description": "Clinical assessment...",
      "visit_number": 2
    },
    "questions": [
      {
        "id": "wrk_egfr",
        "text": "Current eGFR?",
        "type": "number",
        "constraints": { "min": 0, "max": 150 },
        "required": true
      }
    ],
    "previous_answers": {
      "wrk_egfr": 25,
      "wrk_support": "Spouse available"
    },
    "journey_path": [...]
  }
}
```

**Submit Answers**:
```json
POST /api/v1/journey/answer
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "answers": {
    "wrk_egfr": 25,
    "wrk_infections_cleared": 0
  }
}

Response 200 (Transition):
{
  "success": true,
  "transition": true,
  "previous_stage": "WORKUP",
  "current_stage": "COMPLX",
  "reason": "Active infection detected",
  "matched_rule": {
    "rule_id": 5,
    "question_id": "wrk_infections_cleared",
    "range": [0, 0]
  }
}

Response 200 (More Info Needed):
{
  "success": true,
  "transition": false,
  "current_stage": "WORKUP",
  "reason": "Additional information required",
  "missing_questions": [
    "wrk_egfr",
    "wrk_support"
  ]
}
```

### User Experience Flow

```
1. User logs in → Redirected to Dashboard

2. Dashboard shows:
   - Current stage: WORKUP
   - Progress: 2 of 9 stages
   - "Continue to Questions" button

3. Click "Continue" → Questions Page
   - Load questions from /api/v1/journey/current
   - Pre-fill previous answers if exist
   - Show "Question 1 of 3"

4. User fills out question → Auto-save draft

5. User clicks "Next" → Client-side validation
   - If valid: Move to next question
   - If invalid: Show error, stay on question

6. After all questions → Review Page
   - Show all answers
   - Allow editing individual answers

7. User clicks "Submit" → POST /api/v1/journey/answer
   - Show loading spinner
   - Wait for response

8a. If transition = true → Transition Confirmation
    - Show success message
    - Animate stage change
    - Show reason for transition
    - "Continue" button → Back to Dashboard (new stage)

8b. If transition = false → Missing Info Message
    - Show which questions still needed
    - "Continue Answering" → Back to Questions Page

9. User can always:
    - View dashboard (current stage)
    - View journey timeline (history)
    - Logout
```

---

## Technical Constraints

### System Constraints

1. **Database**: PostgreSQL 15+ (already provisioned)
   - Connection pool: 50 max connections
   - Query timeout: 30 seconds

2. **Redis**: Version 6+ (to be added)
   - Single instance (dev)

3. **Backend**: Python 3.11+ with FastAPI
   - Already implemented: auth routes
   - To add: routing engine logic


### Technology Stack (Given)

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Database**: PostgreSQL 15
- **ORM**: asyncpg (direct SQL)
- **Cache**: Redis 6+
- **Authentication**: JWT (already implemented)
- **Testing**: pytest with testcontainers

### Data Constraints

#### Answer Data Constraints
- **JSONB Storage**: Max 5KB per answer value
- **History Retention**: Unlimited (never delete answers)
- **Query Performance**: Index on (user_id, stage_id, answered_at)


## Security Requirements

### Authentication & Authorization

- ✅ **JWT Tokens**: Already implemented (1-hour expiration)
- ✅ **Bcrypt**: Password hashing (cost factor 12)
- ✅ **Email Hashing**: SHA256 for storage
- ⚠️ **CORS**: Configure for production domain only

### Data Protection

#### PII Handling
- ✅ **Email**: Stored as hash, encrypted vault for recovery
- ⚠️ **Answers**: May contain PII - encrypt sensitive fields
- ⚠️ **Audit Logs**: Never log full PII, partial hashes only

#### HIPAA Compliance
- **Encryption at Rest**: Database encryption enabled
- **Data Retention**: Medical records retained per legal requirements
- **Audit Trail**: Immutable audit log of all actions

### Input Validation

- **Client-Side**: Immediate feedback, not trusted
- **Server-Side**: Final authority, all inputs validated
- **SQL Injection**: Prevented by parameterized queries
- **XSS**: Prevented by React's automatic escaping
- **CSRF**: JWT in header (not cookies), no CSRF needed

## Data Flow Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Patient Browser                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │         React UI (Next.js)                      │   │
│  │  ┌────────────┬──────────────┬──────────────┐  │   │
│  │  │ Dashboard  │  Questions   │   Timeline   │  │   │
│  │  └────────────┴──────────────┴──────────────┘  │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────┘
                 │ HTTPS (JWT in header)
                 ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Authentication Middleware             │   │
│  │  (JWT verification, rate limiting)              │   │
│  └─────────────┬───────────────────────────────────┘   │
│                │                                         │
│  ┌─────────────▼───────────────┬──────────────────┐   │
│  │   API Routes               │  Routing Engine  │   │
│  │ - GET /journey/current     │  - Load rules    │   │
│  │ - POST /journey/answer     │  - Evaluate      │   │
│  │ - GET /journey/history     │  - Decide stage  │   │
│  └─────────────┬───────────────┴──────────────────┘   │
└────────────────┼────────────────────────────────────────┘
                 │
      ┌──────────┴─────────────┐
      ▼                        ▼
┌─────────────┐         ┌──────────────┐
│ PostgreSQL  │         │    Redis     │
│  Database   │         │    Cache     │
│             │         │              │
│ - users     │         │ - Rules      │
│ - answers   │         │ - Config     │
│ - journeys  │         │ - Sessions   │
└─────────────┘         └──────────────┘
```

### Request Flow: Submit Answers

```
1. User fills form → Click "Submit"
   ↓
2. React validates client-side
   ↓ (if valid)
3. POST /api/v1/journey/answer
   {answers: {wrk_egfr: 25, ...}}
   ↓
4. FastAPI receives request
   ↓
5. JWT middleware verifies token → Extract user_id
   ↓
6. Fetch current stage from PostgreSQL
   SELECT current_stage_id FROM user_journey_state WHERE user_id = ?
   ↓
7. Validate answers against JSON schema
   (Load from Redis cache or fallback to file)
   ↓ (if valid)
8. Save answers to PostgreSQL
   INSERT INTO user_answers (user_id, stage_id, question_id, answer_value, ...)
   ↓
9. Fetch routing rules from Redis
   GET route:rules:{current_stage}
   ↓
10. Evaluate rules (Routing Engine)
    - Get all answers for current stage (including new ones)
    - Match against rules (priority order)
    - Determine next stage or return missing questions
    ↓
11a. If transition → Update database
     - UPDATE user_journey_state SET current_stage_id = ?
     - INSERT INTO stage_transitions (from_stage, to_stage, ...)
     - UPDATE user_journey_path (close old, create new)
     ↓
11b. If no transition → Return missing questions
     ↓
12. Return response to frontend
    {transition: true/false, next_stage: ?, reason: ?, ...}
    ↓
13. React updates UI
    - Show transition confirmation OR
    - Show missing questions message
```

### Caching Strategy

## Testing Requirements

### Unit Tests

**Routing Engine**:
- Test rule matching logic (all combinations)
- Test answer validation
- Test edge cases (empty answers, out of range, etc.)
- **Target**: >90% code coverage

**UI Components**:
- Test form rendering (all question types)
- Test validation (client-side)
- Test navigation (next/prev buttons)
- Test pre-filling logic
- **Target**: >85% component coverage

### Integration Tests

**API Endpoints**:
- Test complete answer submission flow
- Test transition logic with real database
- **Target**: All endpoints tested

**Database**:
- Test answer storage and retrieval
- Test journey state updates
- Test audit log completeness

### End-to-End backend flow Tests

**User Flows**:
- Complete journey from REFERRAL to MATCH
- Handle loops (WORKUP → COMPLX → WORKUP)
- Submit partial answers, resume later



**End of Specification**

All implementation decisions should reference this spec. Updates to requirements must be reflected here before implementation.