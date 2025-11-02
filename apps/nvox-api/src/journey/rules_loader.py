import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RoutingRule:
    stage_id: str
    question_id: str
    range_min: float
    range_max: float
    next_stage: str

    def matches(self, answer_value: float) -> bool:
        return self.range_min <= answer_value <= self.range_max

    def get_rule_id(self) -> str:
        return f"{self.stage_id}_{self.question_id}_{self.range_min}-{self.range_max}"


class RoutingRules:
    def __init__(self, rules: List[RoutingRule]):
        self.rules = rules

        self._rules_by_stage_question: Dict[Tuple[str, str], List[RoutingRule]] = {}

        for rule in rules:
            key = (rule.stage_id, rule.question_id)
            if key not in self._rules_by_stage_question:
                self._rules_by_stage_question[key] = []
            self._rules_by_stage_question[key].append(rule)

        for key in self._rules_by_stage_question:
            self._rules_by_stage_question[key].sort(key=lambda r: r.range_min)

    def find_matching_rule(
        self,
        stage_id: str,
        question_id: str,
        answer_value: float
    ) -> Optional[RoutingRule]:
        key = (stage_id, question_id)
        rules = self._rules_by_stage_question.get(key, [])

        for rule in rules:
            if rule.matches(answer_value):
                return rule

        return None

    def get_rules_for_stage(self, stage_id: str) -> List[RoutingRule]:
        return [
            rule for rule in self.rules
            if rule.stage_id == stage_id
        ]

    def get_rules_for_question(self, stage_id: str, question_id: str) -> List[RoutingRule]:
        key = (stage_id, question_id)
        return self._rules_by_stage_question.get(key, [])

    @classmethod
    def from_csv_file(cls, file_path: Path) -> "RoutingRules":
        rules = []

        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                rule = RoutingRule(
                    stage_id=row['stage_id'],
                    question_id=row['if_number_id'],
                    range_min=float(row['in_range_min']),
                    range_max=float(row['in_range_max']),
                    next_stage=row['next_stage']
                )
                rules.append(rule)

        return cls(rules)

    @classmethod
    def from_csv_string(cls, csv_content: str) -> "RoutingRules":
        rules = []
        lines = csv_content.strip().split('\n')
        reader = csv.DictReader(lines)

        for row in reader:
            rule = RoutingRule(
                stage_id=row['stage_id'],
                question_id=row['if_number_id'],
                range_min=float(row['in_range_min']),
                range_max=float(row['in_range_max']),
                next_stage=row['next_stage']
            )
            rules.append(rule)

        return cls(rules)

    def validate_ranges_non_overlapping(self) -> List[str]:
        errors = []

        for key, rules in self._rules_by_stage_question.items():
            stage_id, question_id = key

            for i, rule1 in enumerate(rules):
                for rule2 in rules[i + 1:]:
                    if (rule1.range_min <= rule2.range_max and
                            rule2.range_min <= rule1.range_max):
                        errors.append(
                            f"Overlapping ranges for {stage_id}.{question_id}: "
                            f"[{rule1.range_min}, {rule1.range_max}] overlaps with "
                            f"[{rule2.range_min}, {rule2.range_max}]"
                        )

        return errors


_routing_rules: Optional[RoutingRules] = None


async def load_routing_rules(csv_path: Path, redis_client=None) -> RoutingRules:
    global _routing_rules
    _routing_rules = RoutingRules.from_csv_file(csv_path)

    errors = _routing_rules.validate_ranges_non_overlapping()
    if errors:
        raise ValueError(f"Invalid routing rules: {'; '.join(errors)}")

    if redis_client:
        import json
        from collections import defaultdict

        rules_by_stage = defaultdict(list)
        for rule in _routing_rules.rules:
            rules_by_stage[rule.stage_id].append({
                "question_id": rule.question_id,
                "range_min": rule.range_min,
                "range_max": rule.range_max,
                "next_stage": rule.next_stage,
                "rule_id": rule.get_rule_id()
            })

        for stage_id, stage_rules in rules_by_stage.items():
            rules_json = json.dumps(stage_rules)
            await redis_client.set(f"route:rules:{stage_id}", rules_json)

        import time
        await redis_client.set("route:last_reload", str(int(time.time())))

    return _routing_rules


def get_routing_rules() -> RoutingRules:
    if _routing_rules is None:
        raise ValueError(
            "Routing rules not loaded. Call load_routing_rules() first."
        )
    return _routing_rules
