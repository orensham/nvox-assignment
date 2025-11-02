-- Migration 005: Populate journey_edges from routing_rules.csv
-- This migration converts CSV routing rules into database graph edges

-- Entry edge: User always starts at REFERRAL
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES (NULL, 'REFERRAL', 'always', NULL, NULL, NULL);

-- REFERRAL stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('REFERRAL', 'EXIT', 'range', 'ref_karnofsky', 0.0, 39.999),
    ('REFERRAL', 'WORKUP', 'range', 'ref_karnofsky', 40.0, 100.0);

-- WORKUP stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('WORKUP', 'WORKUP', 'range', 'wrk_infections_active', 1.0, 1.0),
    ('WORKUP', 'MATCH', 'range', 'wrk_egfr', 0.0, 15.999);

-- MATCH stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('MATCH', 'DONOR', 'range', 'mtc_pra', 0.0, 79.999),
    ('MATCH', 'BOARD', 'range', 'mtc_pra', 80.0, 100.0);

-- DONOR stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('DONOR', 'BOARD', 'range', 'dnr_clearance', 1.0, 1.0),
    ('DONOR', 'MATCH', 'range', 'dnr_clearance', 0.0, 0.0);

-- BOARD stage edges (multi-question stage)
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('BOARD', 'WORKUP', 'range', 'brd_needs_more_tests', 1.0, 1.0),
    ('BOARD', 'PREOP', 'range', 'brd_risk_score', 0.0, 6.999),
    ('BOARD', 'EXIT', 'range', 'brd_risk_score', 7.0, 10.0);

-- PREOP stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('PREOP', 'WORKUP', 'range', 'prp_infection_status', 1.0, 1.0),
    ('PREOP', 'ORSCHED', 'range', 'prp_bp', 60.0, 179.999),
    ('PREOP', 'WORKUP', 'range', 'prp_bp', 180.0, 240.0);

-- ORSCHED stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('ORSCHED', 'SURG', 'range', 'ors_final_crossmatch', 1.0, 1.0),
    ('ORSCHED', 'PREOP', 'range', 'ors_final_crossmatch', 0.0, 0.0);

-- SURG stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('SURG', 'ICU', 'range', 'srg_warm_isch_time', 0.0, 120.0);

-- ICU stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('ICU', 'WARD', 'range', 'icu_airway_stable', 1.0, 1.0),
    ('ICU', 'COMPLX', 'range', 'icu_airway_stable', 0.0, 0.0);

-- WARD stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('WARD', 'COMPLX', 'range', 'wrd_walk_meters', 0.0, 149.999),
    ('WARD', 'HOME', 'range', 'wrd_walk_meters', 150.0, 2000.0);

-- HOME stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('HOME', 'HOME', 'range', 'hom_creatinine', 0.1, 2.0),
    ('HOME', 'COMPLX', 'range', 'hom_creatinine', 2.0001, 15.0);

-- COMPLX stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('COMPLX', 'HOME', 'range', 'cpx_severity', 0.0, 4.999),
    ('COMPLX', 'WARD', 'range', 'cpx_severity', 5.0, 7.0),
    ('COMPLX', 'RELIST', 'range', 'cpx_severity', 8.0, 10.0);

-- RELIST stage edges
INSERT INTO journey_edges (from_node_id, to_node_id, condition_type, question_id, range_min, range_max)
VALUES
    ('RELIST', 'MATCH', 'range', 'rlt_new_pra', 0.0, 79.999),
    ('RELIST', 'BOARD', 'range', 'rlt_new_pra', 80.0, 100.0);

-- Verify data integrity
DO $$
DECLARE
    edge_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO edge_count FROM journey_edges;
    RAISE NOTICE 'Created % journey edges', edge_count;

    -- Should have 29 edges (1 entry + 28 from CSV)
    IF edge_count != 29 THEN
        RAISE WARNING 'Expected 29 edges but found %', edge_count;
    END IF;
END $$;
