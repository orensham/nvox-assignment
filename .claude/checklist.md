# Implementation Checklist & Quick Start

**For**: Routing Engine & UI Implementation  
**Based on**: Existing auth system completed via Claude Code

---

## ✅ What's Already Done (via Claude Code)

### Authentication System - COMPLETE ✅
- [x] User signup (POST /api/v1/signup)
- [x] User login (POST /api/v1/login)
- [x] User logout (POST /api/v1/logout)
- [x] JWT token generation and verification
- [x] Password hashing (bcrypt, cost 12)
- [x] Email hashing (SHA256)
- [x] Email encryption vault (AES-256)
- [x] Unit tests for auth
- [x] Integration tests for auth endpoints

### Database - PARTIAL ✅
- [x] PostgreSQL setup
- [x] `users` table created
- [x] `email_vault` table created
- [x] asyncpg connection pooling

### Testing Infrastructure - COMPLETE ✅
- [x] pytest configuration
- [x] Testcontainers setup
- [x] Auth test suite (105+ tests)
- [x] Coverage reporting

---

## ❌ What Still Needs to Be Done

### Phase 0: Database Setup (CRITICAL - DO FIRST!)

#### Tables to Create
- [ ] **user_journey_state** - Tracks current stage for each user
- [ ] **user_answers** - Stores all answer history (JSONB)
- [ ] **stage_transitions** - Audit trail of stage changes
- [ ] **user_journey_path** - Detailed visit tracking with timestamps
- [ ] **audit_log** - Comprehensive action logging (no PII)
- [ ] **anonymization_log** - GDPR deletion tracking
- [ ] Transaction support

#### Indexes to Create
- [ ] idx_users_email_hash
- [ ] idx_journey_state_user
- [ ] idx_answers_user_stage
- [ ] idx_answers_user_stage_question_time
- [ ] idx_transitions_user
- [ ] idx_journey_path_user
- [ ] idx_audit_log_user

#### How to Create
```bash
# Option 1: Run provided SQL file
psql -U your_user -d transplant_journey -f updated_database_schema.sql

# Option 2: Use migration tool
alembic upgrade head

# Option 3: Manual creation (copy from updated_database_schema.sql)
```

**Verification**:
```sql
-- Run this to verify all tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Should see 8 tables:
-- 1. anonymization_log
-- 2. audit_log
-- 4. stage_transitions
-- 5. user_answers
-- 6. user_journey_path
-- 7. user_journey_state
-- 8. users
```

---

### Phase 1: Routing Engine (Backend)

#### Infrastructure
- [ ] Use Redis (Docker-compose)
- [ ] Configure Redis connection in app
- [ ] Add Redis client library (redis-py or aioredis)
- [ ] Test Redis connectivity

#### Data Files
- [ ] `task_resources/transplant_journey_routes_only.csv`
- [ ] `task_resources/transplant_journey_questions_only.json`
- [ ] Verify file formats (UTF-8, valid CSV/JSON)

#### Core Routing Engine
- [ ] Create `routing_engine.py` module
- [ ] Implement `load_rules_from_csv()` function
- [ ] Implement `load_config_from_json()` function
- [ ] Implement `cache_rules_in_redis()` function
- [ ] Implement `get_rules_for_stage()` function (with Redis)
- [ ] Implement `determine_next_stage()` function
- [ ] Implement `validate_answers()` function
- [ ] Add error handling (cache miss, invalid data)

#### API Endpoints
- [ ] Create `GET /api/v1/journey/current`
  - Fetch current stage from database
  - Load questions for stage from JSON/Redis
  - Fetch previous answers
  - Return journey state
  
- [ ] Create `POST /api/v1/journey/answer`
  - Validate JWT token
  - Fetch current stage
  - Validate answers against constraints
  - Save answers to database
  - Evaluate routing rules
  - Update stage if transition
  - Log transition to audit tables
  - Return result

#### Database Integration

#### Testing
- [ ] Unit tests for routing engine logic
- [ ] Unit tests for rule matching
- [ ] Unit tests for validation
- [ ] Integration tests with Redis
- [ ] Integration tests with database (journey tables)
- [ ] API endpoint tests
- [ ] Performance tests (< 50ms routing)
- [ ] Load tests (1000+ concurrent users)

---

### Phase 2: User Interface (Frontend)

#### Project Setup
- [ ] Initialize Next.js project
- [ ] Install dependencies (React Query, Tailwind, etc.)
- [ ] Configure TypeScript
- [ ] Set up routing
- [ ] Configure environment variables

#### Authentication Pages (May already exist)
- [ ] Login page
- [ ] Signup page
- [ ] Logout functionality

#### Journey Pages
- [ ] **Dashboard** (`/dashboard`)
  - Current stage display
  - Progress bar
  - "Continue to Questions" button
  - Journey timeline
  
- [ ] **Questions Page** (`/journey/questions`)
  - Dynamic form rendering based on JSON
  - Question type handlers (number, boolean, text)
  - Real-time validation
  - Previous answer pre-filling
  - Navigation (next/prev)
  - Auto-save drafts
  
- [ ] **Review Page** (`/journey/review`)
  - Display all answers
  - Edit functionality
  - Submit button
  
- [ ] **Transition Page** (`/journey/transition`)
  - Success message
  - Stage change animation
  - Reason display
  - Continue button
  
#### Components
- [ ] ProgressBar component
- [ ] StageCard component
- [ ] QuestionForm component
- [ ] NumberInput component
- [ ] BooleanInput component
- [ ] TextInput component
- [ ] ValidationError component
- [ ] LoadingSpinner component

#### State Management
- [ ] API client setup (axios/fetch)
- [ ] React Query hooks
  - `useCurrentJourney`
  - `useSubmitAnswers`
  - `useJourneyHistory`
- [ ] Local form state (React Hook Form)
- [ ] Global auth state (Context or Zustand)

#### Styling
- [ ] Tailwind CSS setup
- [ ] Responsive design (mobile-first)
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] Loading states
- [ ] Error states
- [ ] Empty states

#### Testing
- [ ] Component unit tests (Jest + RTL)
- [ ] Form validation tests
- [ ] API integration tests
---

### Phase 3: Integration & Deployment

#### Integration Testing
- [ ] End-to-end user flow (signup → answer → transition)
- [ ] Test all stage transitions
- [ ] Test loops (WORKUP → COMPLX → WORKUP)
- [ ] Test partial answer submission
- [ ] Test session timeout handling
- [ ] Test concurrent user scenarios

#### Security
- [ ] CORS configuration
- [ ] Rate limiting
- [ ] Input sanitization
- [ ] SQL injection prevention verification
- [ ] XSS prevention verification
- [ ] HIPAA compliance audit

#### Deployment
- [ ] Docker images (backend + frontend)
- [ ] Docker Compose for local development
- [ ] Database migration strategy
- [ ] Redis configuration
---

## 🎯 Definition of Done

**Phase 0 Complete When**:
- [ ] All 8 database tables exist
- [ ] All indexes created
- [ ] Sample data can be inserted
- [ ] Queries run successfully

**Phase 1 Complete When**:
- [ ] Routing engine evaluates rules correctly
- [ ] All API endpoints functional
- [ ] Answer validation works
- [ ] Stage transitions logged correctly

**Phase 2 Complete When**:
- [ ] All UI pages render correctly
- [ ] Forms submit successfully
- [ ] Validation shows errors
- [ ] Progress bar updates
- [ ] Journey history displays
- [ ] Mobile responsive
- [ ] Accessibility compliant (WCAG 2.1 AA)
- [ ] E2E tests pass

**Phase 3 Complete When**:
- [ ] End-to-end flows work
---