import pytest
from journey.routing_engine import RoutingEngine, TransitionDecision
from journey.config_loader import JourneyConfig
from journey.rules_loader import RoutingRules


@pytest.fixture
def sample_config():
    config_json = """
{
    "version": "1.0",
    "entry_stage": "REFERRAL",
    "stages": [
        {
            "id": "REFERRAL",
            "name": "Referral",
            "questions": [
                {"id": "ref_karnofsky", "text": "Karnofsky score", "type": "number", "constraints": {"min": 0, "max": 100}},
                {"id": "ref_eligible", "text": "Is eligible?", "type": "boolean"}
            ]
        },
        {
            "id": "WORKUP",
            "name": "Workup",
            "questions": [
                {"id": "wu_age", "text": "Age", "type": "number", "constraints": {"min": 0, "max": 120}}
            ]
        },
        {
            "id": "EXIT",
            "name": "Exit",
            "questions": []
        }
    ]
}
"""
    return JourneyConfig.from_json_string(config_json)


@pytest.fixture
def sample_rules():
    rules_csv = """stage_id,if_number_id,in_range_min,in_range_max,next_stage
REFERRAL,ref_karnofsky,0.0,39.0,EXIT
REFERRAL,ref_karnofsky,40.0,100.0,WORKUP
WORKUP,wu_age,0.0,17.0,EXIT
WORKUP,wu_age,18.0,120.0,EXIT
"""
    return RoutingRules.from_csv_string(rules_csv)


@pytest.fixture
def routing_engine(sample_config, sample_rules):
    return RoutingEngine(sample_config, sample_rules)


def test_routing_engine_should_transition_number_triggers_rule(routing_engine):
    decision = routing_engine.should_transition("REFERRAL", "ref_karnofsky", 30.0)

    assert decision.should_transition
    assert decision.next_stage == "EXIT"
    assert decision.matched_rule is not None
    assert decision.matched_rule.range_min == 0.0
    assert decision.matched_rule.range_max == 39.0
    assert decision.question_id == "ref_karnofsky"
    assert decision.answer_value == 30.0


def test_routing_engine_should_transition_high_score(routing_engine):
    decision = routing_engine.should_transition("REFERRAL", "ref_karnofsky", 80.0)

    assert decision.should_transition
    assert decision.next_stage == "WORKUP"
    assert decision.matched_rule is not None


def test_routing_engine_boolean_no_transition(routing_engine):
    decision = routing_engine.should_transition("REFERRAL", "ref_eligible", True)

    assert not decision.should_transition
    assert decision.next_stage is None
    assert decision.matched_rule is None
    assert "does not trigger routing" in decision.reason


def test_routing_engine_no_matching_rule(routing_engine):
    empty_rules = RoutingRules.from_csv_string("""stage_id,if_number_id,in_range_min,in_range_max,next_stage""")
    engine = RoutingEngine(routing_engine.config, empty_rules)

    decision = engine.should_transition("REFERRAL", "ref_karnofsky", 50.0)

    assert not decision.should_transition
    assert decision.next_stage is None
    assert decision.matched_rule is None
    assert "No routing rule matched" in decision.reason


def test_routing_engine_question_not_found(routing_engine):
    decision = routing_engine.should_transition("REFERRAL", "nonexistent_question", 50.0)

    assert not decision.should_transition
    assert "Question nonexistent_question not found" in decision.reason


def test_routing_engine_stage_not_found(routing_engine):
    decision = routing_engine.should_transition("NONEXISTENT_STAGE", "ref_karnofsky", 50.0)

    assert not decision.should_transition
    assert "NONEXISTENT_STAGE" in decision.reason and "not found" in decision.reason


def test_routing_engine_get_stage_info(routing_engine):
    stage_info = routing_engine.get_stage_info("REFERRAL")

    assert stage_info["id"] == "REFERRAL"
    assert stage_info["name"] == "Referral"
    assert len(stage_info["questions"]) == 2
    assert stage_info["questions"][0]["id"] == "ref_karnofsky"


def test_routing_engine_get_stage_info_not_found(routing_engine):
    stage_info = routing_engine.get_stage_info("NONEXISTENT")
    assert stage_info is None


def test_transition_decision_to_dict():
    decision = TransitionDecision(
        should_transition=True,
        next_stage="WORKUP",
        matched_rule=None,
        question_id="ref_karnofsky",
        answer_value=80.0,
        reason="Matched routing rule"
    )

    result = decision.to_dict()
    assert result["should_transition"] is True
    assert result["next_stage"] == "WORKUP"
    assert result["question_id"] == "ref_karnofsky"
    assert result["answer_value"] == 80.0
