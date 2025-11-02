import pytest
from journey.config_loader import JourneyConfig, Stage, Question


@pytest.fixture
def sample_config_json():
    return """
{
    "version": "1.0",
    "domain": "transplant_journey",
    "entry_stage": "REFERRAL",
    "stages": [
        {
            "id": "REFERRAL",
            "name": "Referral Stage",
            "description": "Initial referral",
            "questions": [
                {
                    "id": "ref_karnofsky",
                    "text": "Karnofsky score",
                    "type": "number",
                    "constraints": {"min": 0, "max": 100}
                },
                {
                    "id": "ref_eligible",
                    "text": "Is eligible?",
                    "type": "boolean"
                }
            ]
        },
        {
            "id": "EXIT",
            "name": "Exit Stage",
            "questions": []
        }
    ]
}
"""


def test_question_validation_number_valid():
    question = Question({"id": "q1", "text": "Test", "type": "number", "constraints": {"min": 0, "max": 100}})
    is_valid, error = question.validate_answer(50)
    assert is_valid
    assert error is None


def test_question_validation_number_too_low():
    question = Question({"id": "q1", "text": "Test", "type": "number", "constraints": {"min": 0, "max": 100}})
    is_valid, error = question.validate_answer(-10)
    assert not is_valid
    assert "must be >=" in error


def test_question_validation_number_too_high():
    question = Question({"id": "q1", "text": "Test", "type": "number", "constraints": {"min": 0, "max": 100}})
    is_valid, error = question.validate_answer(150)
    assert not is_valid
    assert "must be <=" in error


def test_question_validation_boolean_valid():
    question = Question({"id": "q1", "text": "Test", "type": "boolean"})
    assert question.validate_answer(True)[0]
    assert question.validate_answer(False)[0]
    assert question.validate_answer(1)[0]
    assert question.validate_answer(0)[0]


def test_question_validation_boolean_invalid():
    question = Question({"id": "q1", "text": "Test", "type": "boolean"})
    is_valid, error = question.validate_answer(2)
    assert not is_valid
    assert "must be 0 or 1" in error


def test_question_validation_select_valid():
    question = Question({
        "id": "q1",
        "text": "Test",
        "type": "select",
        "options": [{"value": "A", "label": "Option A"}, {"value": "B", "label": "Option B"}]
    })
    assert question.validate_answer("A")[0]
    assert question.validate_answer("B")[0]


def test_question_validation_select_invalid():
    question = Question({
        "id": "q1",
        "text": "Test",
        "type": "select",
        "options": [{"value": "A", "label": "Option A"}]
    })
    is_valid, error = question.validate_answer("C")
    assert not is_valid
    assert "must be one of" in error


def test_stage_get_question():
    stage = Stage({
        "id": "STAGE1",
        "name": "Stage 1",
        "questions": [
            {"id": "q1", "text": "Question 1", "type": "number"},
            {"id": "q2", "text": "Question 2", "type": "boolean"}
        ]
    })

    q1 = stage.get_question("q1")
    assert q1 is not None
    assert q1.id == "q1"

    q_missing = stage.get_question("q99")
    assert q_missing is None


def test_journey_config_from_json_string(sample_config_json):
    config = JourneyConfig.from_json_string(sample_config_json)

    assert config.version == "1.0"
    assert config.domain == "transplant_journey"
    assert config.entry_stage == "REFERRAL"
    assert len(config.stages) == 2


def test_journey_config_get_stage(sample_config_json):
    config = JourneyConfig.from_json_string(sample_config_json)

    referral = config.get_stage("REFERRAL")
    assert referral is not None
    assert referral.id == "REFERRAL"
    assert referral.name == "Referral Stage"
    assert len(referral.questions) == 2

    missing = config.get_stage("NONEXISTENT")
    assert missing is None


def test_journey_config_get_question(sample_config_json):
    config = JourneyConfig.from_json_string(sample_config_json)

    question = config.get_question("REFERRAL", "ref_karnofsky")
    assert question is not None
    assert question.id == "ref_karnofsky"
    assert question.type == "number"

    missing = config.get_question("REFERRAL", "nonexistent")
    assert missing is None


def test_journey_config_validate_stage_exists(sample_config_json):
    config = JourneyConfig.from_json_string(sample_config_json)

    assert config.validate_stage_exists("REFERRAL")
    assert config.validate_stage_exists("EXIT")
    assert not config.validate_stage_exists("NONEXISTENT")


def test_journey_config_get_all_stage_ids(sample_config_json):
    config = JourneyConfig.from_json_string(sample_config_json)

    stage_ids = config.get_all_stage_ids()
    assert "REFERRAL" in stage_ids
    assert "EXIT" in stage_ids
    assert len(stage_ids) == 2
