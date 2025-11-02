import pytest
from journey.rules_loader import RoutingRule, RoutingRules


@pytest.fixture
def sample_rules_csv():
    return """stage_id,if_number_id,in_range_min,in_range_max,next_stage
REFERRAL,ref_karnofsky,0.0,39.0,EXIT
REFERRAL,ref_karnofsky,40.0,100.0,WORKUP
WORKUP,wu_age,0.0,17.0,EXIT
WORKUP,wu_age,18.0,70.0,TRANSPLANT
"""


def test_routing_rule_matches():
    rule = RoutingRule(
        stage_id="REFERRAL",
        question_id="ref_karnofsky",
        range_min=40.0,
        range_max=100.0,
        next_stage="WORKUP"
    )

    assert rule.matches(40.0)
    assert rule.matches(50.0)
    assert rule.matches(100.0)
    assert not rule.matches(39.9)
    assert not rule.matches(100.1)


def test_routing_rule_get_rule_id():
    rule = RoutingRule(
        stage_id="REFERRAL",
        question_id="ref_karnofsky",
        range_min=40.0,
        range_max=100.0,
        next_stage="WORKUP"
    )

    rule_id = rule.get_rule_id()
    assert rule_id == "REFERRAL_ref_karnofsky_40.0-100.0"


def test_routing_rules_from_csv_string(sample_rules_csv):
    rules = RoutingRules.from_csv_string(sample_rules_csv)

    assert len(rules.rules) == 4
    assert rules.rules[0].stage_id == "REFERRAL"
    assert rules.rules[0].question_id == "ref_karnofsky"
    assert rules.rules[0].range_min == 0.0
    assert rules.rules[0].range_max == 39.0
    assert rules.rules[0].next_stage == "EXIT"


def test_routing_rules_find_matching_rule(sample_rules_csv):
    rules = RoutingRules.from_csv_string(sample_rules_csv)

    rule = rules.find_matching_rule("REFERRAL", "ref_karnofsky", 30.0)
    assert rule is not None
    assert rule.next_stage == "EXIT"

    rule = rules.find_matching_rule("REFERRAL", "ref_karnofsky", 80.0)
    assert rule is not None
    assert rule.next_stage == "WORKUP"

    rule = rules.find_matching_rule("REFERRAL", "ref_karnofsky", 39.5)
    assert rule is None

    rule = rules.find_matching_rule("NONEXISTENT", "ref_karnofsky", 50.0)
    assert rule is None


def test_routing_rules_get_rules_for_stage(sample_rules_csv):
    rules = RoutingRules.from_csv_string(sample_rules_csv)

    referral_rules = rules.get_rules_for_stage("REFERRAL")
    assert len(referral_rules) == 2
    assert all(r.stage_id == "REFERRAL" for r in referral_rules)

    workup_rules = rules.get_rules_for_stage("WORKUP")
    assert len(workup_rules) == 2
    assert all(r.stage_id == "WORKUP" for r in workup_rules)


def test_routing_rules_get_rules_for_question(sample_rules_csv):
    rules = RoutingRules.from_csv_string(sample_rules_csv)

    karnofsky_rules = rules.get_rules_for_question("REFERRAL", "ref_karnofsky")
    assert len(karnofsky_rules) == 2
    assert all(r.question_id == "ref_karnofsky" for r in karnofsky_rules)

    age_rules = rules.get_rules_for_question("WORKUP", "wu_age")
    assert len(age_rules) == 2
    assert all(r.question_id == "wu_age" for r in age_rules)


def test_routing_rules_validate_non_overlapping_valid():
    csv_content = """stage_id,if_number_id,in_range_min,in_range_max,next_stage
REFERRAL,ref_karnofsky,0.0,39.0,EXIT
REFERRAL,ref_karnofsky,40.0,100.0,WORKUP
"""
    rules = RoutingRules.from_csv_string(csv_content)
    errors = rules.validate_ranges_non_overlapping()
    assert len(errors) == 0


def test_routing_rules_validate_overlapping_invalid():
    csv_content = """stage_id,if_number_id,in_range_min,in_range_max,next_stage
REFERRAL,ref_karnofsky,0.0,50.0,EXIT
REFERRAL,ref_karnofsky,40.0,100.0,WORKUP
"""
    rules = RoutingRules.from_csv_string(csv_content)
    errors = rules.validate_ranges_non_overlapping()
    assert len(errors) > 0
    assert "Overlapping ranges" in errors[0]


def test_routing_rules_sorted_by_range_min(sample_rules_csv):
    rules = RoutingRules.from_csv_string(sample_rules_csv)

    karnofsky_rules = rules.get_rules_for_question("REFERRAL", "ref_karnofsky")
    # Should be sorted by range_min
    assert karnofsky_rules[0].range_min == 0.0
    assert karnofsky_rules[1].range_min == 40.0
