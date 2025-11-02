import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class Question:
    def __init__(self, data: dict):
        self.id: str = data["id"]
        self.text: str = data["text"]
        self.type: str = data["type"]  # "number", "boolean", "select"
        self.constraints: dict = data.get("constraints", {})
        self.options: Optional[List[dict]] = data.get("options")

    def validate_answer(self, value: Any) -> tuple[bool, Optional[str]]:
        if self.type == "number":
            if not isinstance(value, (int, float)):
                return False, f"Expected number, got {type(value).__name__}"

            if "min" in self.constraints and value < self.constraints["min"]:
                return False, f"Value must be >= {self.constraints['min']}"

            if "max" in self.constraints and value > self.constraints["max"]:
                return False, f"Value must be <= {self.constraints['max']}"

        elif self.type == "boolean":
            if not isinstance(value, (bool, int)):
                return False, f"Expected boolean, got {type(value).__name__}"

            if isinstance(value, int):
                if value not in [0, 1]:
                    return False, "Integer value must be 0 or 1"

        elif self.type == "select":
            if not self.options:
                return False, "Question has no valid options"

            valid_values = [opt["value"] for opt in self.options]
            if value not in valid_values:
                return False, f"Value must be one of: {valid_values}"

        return True, None

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "text": self.text,
            "type": self.type,
            "constraints": self.constraints
        }
        if self.options:
            result["options"] = self.options
        return result


class Stage:
    def __init__(self, data: dict):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.description: Optional[str] = data.get("description")
        self.questions: List[Question] = [
            Question(q) for q in data.get("questions", [])
        ]
        self._questions_by_id: Dict[str, Question] = {
            q.id: q for q in self.questions
        }

    def get_question(self, question_id: str) -> Optional[Question]:
        return self._questions_by_id.get(question_id)

    def to_dict(self, include_questions: bool = True) -> dict:
        result = {
            "id": self.id,
            "name": self.name
        }
        if self.description:
            result["description"] = self.description

        if include_questions:
            result["questions"] = [q.to_dict() for q in self.questions]

        return result


class JourneyConfig:
    def __init__(self, config_data: dict):
        self.version: str = config_data.get("version", "1.0")
        self.domain: str = config_data.get("domain", "")
        self.entry_stage: str = config_data.get("entry_stage", "REFERRAL")

        self.stages: List[Stage] = [
            Stage(s) for s in config_data.get("stages", [])
        ]

        self._stages_by_id: Dict[str, Stage] = {
            s.id: s for s in self.stages
        }

    def get_stage(self, stage_id: str) -> Optional[Stage]:
        return self._stages_by_id.get(stage_id)

    def get_question(self, stage_id: str, question_id: str) -> Optional[Question]:
        stage = self.get_stage(stage_id)
        if not stage:
            return None
        return stage.get_question(question_id)

    def validate_stage_exists(self, stage_id: str) -> bool:
        return stage_id in self._stages_by_id

    def get_all_stage_ids(self) -> List[str]:
        return list(self._stages_by_id.keys())

    @classmethod
    def from_file(cls, file_path: Path) -> "JourneyConfig":
        with open(file_path, "r") as f:
            data = json.load(f)
        return cls(data)

    @classmethod
    def from_json_string(cls, json_string: str) -> "JourneyConfig":
        data = json.loads(json_string)
        return cls(data)


_journey_config: Optional[JourneyConfig] = None


async def load_journey_config(config_path: Path, redis_client=None) -> JourneyConfig:
    global _journey_config
    _journey_config = JourneyConfig.from_file(config_path)

    if redis_client:
        import json

        config_json = json.dumps({
            "version": _journey_config.version,
            "domain": _journey_config.domain,
            "entry_stage": _journey_config.entry_stage,
            "stages": [s.to_dict() for s in _journey_config.stages]
        })
        await redis_client.set("route:config", config_json)

        for stage in _journey_config.stages:
            stage_questions_json = json.dumps([q.to_dict() for q in stage.questions])
            await redis_client.set(f"route:stage:{stage.id}:questions", stage_questions_json)

    return _journey_config


def get_journey_config() -> JourneyConfig:
    if _journey_config is None:
        raise ValueError(
            "Journey configuration not loaded. Call load_journey_config() first."
        )
    return _journey_config
