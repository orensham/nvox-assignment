-- Create users table with PII protection
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_hash VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    journey_stage VARCHAR(50) NOT NULL DEFAULT 'REFERRAL',
    journey_started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create index on email_hash for fast lookups
CREATE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash);

-- Create index on journey_stage for analytics
CREATE INDEX IF NOT EXISTS idx_users_journey_stage ON users(journey_stage);
