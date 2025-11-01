-- Migration 003: Add Journey Tracking Tables
-- Description: Creates tables for user journey state, answers, transitions, and path tracking
-- Author: System
-- Date: 2025-01-01

-- ==============================================================================
-- Table: user_journey_state
-- Purpose: Tracks the current stage for each user
-- ==============================================================================
CREATE TABLE IF NOT EXISTS user_journey_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_stage_id VARCHAR(50) NOT NULL,  -- e.g., 'REFERRAL', 'WORKUP', 'MATCH'
    visit_number INT NOT NULL DEFAULT 1,    -- Tracks loops (e.g., return to WORKUP)
    journey_started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT uk_user_journey_state_user UNIQUE (user_id),
    CONSTRAINT chk_visit_number CHECK (visit_number > 0)
);

-- Indexes for user_journey_state
CREATE INDEX IF NOT EXISTS idx_journey_state_user ON user_journey_state(user_id);
CREATE INDEX IF NOT EXISTS idx_journey_state_stage ON user_journey_state(current_stage_id);
CREATE INDEX IF NOT EXISTS idx_journey_state_updated ON user_journey_state(last_updated_at DESC);

-- ==============================================================================
-- Table: user_answers
-- Purpose: Stores all user answers with versioning and audit trail
-- ==============================================================================
CREATE TABLE IF NOT EXISTS user_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stage_id VARCHAR(50) NOT NULL,          -- Stage where answer was given
    question_id VARCHAR(100) NOT NULL,      -- Question identifier from JSON
    answer_value JSONB NOT NULL,            -- Flexible storage for any answer type
    visit_number INT NOT NULL DEFAULT 1,    -- Which visit to this stage
    answered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    version INT NOT NULL DEFAULT 1,         -- Version number for answer updates
    is_current BOOLEAN NOT NULL DEFAULT TRUE, -- Only one current answer per question

    -- Constraints
    CONSTRAINT chk_answer_version CHECK (version > 0),
    CONSTRAINT chk_answer_visit CHECK (visit_number > 0)
);

-- Indexes for user_answers
CREATE INDEX IF NOT EXISTS idx_answers_user_stage ON user_answers(user_id, stage_id);
CREATE INDEX IF NOT EXISTS idx_answers_user_question ON user_answers(user_id, question_id);
CREATE INDEX IF NOT EXISTS idx_answers_current ON user_answers(user_id, question_id) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_answers_answered_at ON user_answers(answered_at DESC);
CREATE INDEX IF NOT EXISTS idx_answers_stage ON user_answers(stage_id);

-- ==============================================================================
-- Table: stage_transitions
-- Purpose: Immutable audit trail of all stage transitions
-- ==============================================================================
CREATE TABLE IF NOT EXISTS stage_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_stage_id VARCHAR(50),              -- NULL for initial entry to journey
    to_stage_id VARCHAR(50) NOT NULL,
    from_visit_number INT,                  -- Visit number at source stage
    to_visit_number INT NOT NULL,           -- Visit number at destination stage
    transition_reason TEXT,                 -- Human-readable reason
    matched_rule_id VARCHAR(100),           -- Which routing rule triggered this
    matched_question_id VARCHAR(100),       -- Which question's answer drove the decision
    matched_answer_value JSONB,             -- The specific answer value that matched
    transitioned_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_transition_visits CHECK (
        from_visit_number IS NULL OR from_visit_number > 0
    ),
    CONSTRAINT chk_to_visit_number CHECK (to_visit_number > 0)
);

-- Indexes for stage_transitions
CREATE INDEX IF NOT EXISTS idx_transitions_user ON stage_transitions(user_id);
CREATE INDEX IF NOT EXISTS idx_transitions_user_time ON stage_transitions(user_id, transitioned_at DESC);
CREATE INDEX IF NOT EXISTS idx_transitions_from_stage ON stage_transitions(from_stage_id);
CREATE INDEX IF NOT EXISTS idx_transitions_to_stage ON stage_transitions(to_stage_id);
CREATE INDEX IF NOT EXISTS idx_transitions_time ON stage_transitions(transitioned_at DESC);

-- ==============================================================================
-- Table: user_journey_path
-- Purpose: Tracks entry and exit timestamps for each stage visit
-- ==============================================================================
CREATE TABLE IF NOT EXISTS user_journey_path (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stage_id VARCHAR(50) NOT NULL,
    visit_number INT NOT NULL DEFAULT 1,
    entered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    exited_at TIMESTAMP,                    -- NULL while still in this stage
    is_current BOOLEAN NOT NULL DEFAULT TRUE, -- Only one current stage per user

    -- Constraints
    CONSTRAINT chk_path_visit_number CHECK (visit_number > 0),
    CONSTRAINT chk_path_exit_after_entry CHECK (
        exited_at IS NULL OR exited_at >= entered_at
    )
);

-- Indexes for user_journey_path
CREATE INDEX IF NOT EXISTS idx_journey_path_user ON user_journey_path(user_id);
CREATE INDEX IF NOT EXISTS idx_journey_path_user_entered ON user_journey_path(user_id, entered_at DESC);
CREATE INDEX IF NOT EXISTS idx_journey_path_current ON user_journey_path(user_id) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_journey_path_stage ON user_journey_path(stage_id);

-- Partial unique index to ensure only one current path per user
CREATE UNIQUE INDEX IF NOT EXISTS uk_user_journey_path_current
    ON user_journey_path(user_id)
    WHERE is_current = TRUE;

-- ==============================================================================
-- Comments for Documentation
-- ==============================================================================
COMMENT ON TABLE user_journey_state IS 'Tracks current stage for each user. One row per user.';
COMMENT ON TABLE user_answers IS 'Stores all user answers with versioning. Supports non-linear journeys.';
COMMENT ON TABLE stage_transitions IS 'Immutable audit trail of all stage changes. Never delete.';
COMMENT ON TABLE user_journey_path IS 'Tracks stage visit history with entry/exit timestamps.';

COMMENT ON COLUMN user_journey_state.visit_number IS 'Increments when user returns to same stage (e.g., WORKUP visit 2)';
COMMENT ON COLUMN user_answers.answer_value IS 'JSONB allows storing numbers, strings, booleans, or complex objects';
COMMENT ON COLUMN user_answers.is_current IS 'FALSE for historical versions, TRUE for current answer';
COMMENT ON COLUMN stage_transitions.matched_rule_id IS 'Format: {stage_id}_{question_id}_{range} for traceability';
COMMENT ON COLUMN user_journey_path.is_current IS 'TRUE only for the stage user is currently in';
