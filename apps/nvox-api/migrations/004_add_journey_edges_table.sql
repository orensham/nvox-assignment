-- Migration 004: Add journey_edges table for graph-based routing
-- This replaces CSV-based routing rules with explicit graph edges

CREATE TABLE IF NOT EXISTS journey_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Edge endpoints
    from_node_id VARCHAR(20),  -- Can be NULL for entry edges (e.g., NULL -> REFERRAL)
    to_node_id VARCHAR(20) NOT NULL,

    -- Condition for this edge to be taken
    condition_type VARCHAR(20) NOT NULL,  -- 'range', 'equals', 'always'
    question_id VARCHAR(50),               -- Question that triggers this edge (NULL for 'always')
    range_min DECIMAL(10, 3),              -- Min value for 'range' conditions
    range_max DECIMAL(10, 3),              -- Max value for 'range' conditions

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_condition_type CHECK (condition_type IN ('range', 'equals', 'always')),
    CONSTRAINT range_condition_has_bounds CHECK (
        condition_type != 'range' OR (range_min IS NOT NULL AND range_max IS NOT NULL)
    ),
    CONSTRAINT range_condition_has_question CHECK (
        condition_type = 'always' OR question_id IS NOT NULL
    )
);

-- Index for fast edge lookup by source node
CREATE INDEX idx_journey_edges_from_node ON journey_edges(from_node_id) WHERE from_node_id IS NOT NULL;

-- Index for finding entry edges
CREATE INDEX idx_journey_edges_entry ON journey_edges(to_node_id) WHERE from_node_id IS NULL;

-- Comments for documentation
COMMENT ON TABLE journey_edges IS 'Graph edges representing valid transitions between journey stages';
COMMENT ON COLUMN journey_edges.from_node_id IS 'Source stage (NULL for entry edges)';
COMMENT ON COLUMN journey_edges.to_node_id IS 'Destination stage';
COMMENT ON COLUMN journey_edges.condition_type IS 'Type of condition: range (numeric), equals (exact), or always (unconditional)';
COMMENT ON COLUMN journey_edges.question_id IS 'Question ID that triggers this edge (from journey_config.json)';
COMMENT ON COLUMN journey_edges.range_min IS 'Minimum value for range conditions (inclusive)';
COMMENT ON COLUMN journey_edges.range_max IS 'Maximum value for range conditions (inclusive)';
