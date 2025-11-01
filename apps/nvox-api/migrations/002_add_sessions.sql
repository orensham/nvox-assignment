-- Migration: Add sessions table for JWT token blacklist

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,  
    expires_at TIMESTAMP NOT NULL,            
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMP,                     
    is_active BOOLEAN NOT NULL DEFAULT TRUE 
);

-- Index for fast lookups by token JTI (used during authentication)
CREATE INDEX IF NOT EXISTS idx_sessions_token_jti ON sessions(token_jti);

-- Index for fast lookups by user_id (useful for getting user's active sessions)
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- Index for fast lookups of active sessions
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active) WHERE is_active = TRUE;

-- Index for cleanup queries (finding expired sessions)
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- Comment on table
COMMENT ON TABLE sessions IS 'Stores user session information and JWT token blacklist for logout functionality';
COMMENT ON COLUMN sessions.token_jti IS 'JWT ID (jti) claim - unique identifier for each token';
COMMENT ON COLUMN sessions.expires_at IS 'Token expiration timestamp (from JWT exp claim)';
COMMENT ON COLUMN sessions.revoked_at IS 'Timestamp when the session was revoked (user logged out)';
COMMENT ON COLUMN sessions.is_active IS 'Whether the session is still active (false after logout)';
