"""
Routing Rules Loader

Loads and indexes routing rules from CSV file.
Provides efficient lookup of rules for stage transitions.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RoutingRule:
    """
    Represents a single routing rule from the CSV.

    Example CSV row:
    REFERRAL,ref_karnofsky,0.0,39.0,EXIT
    """
    stage_id: str
    question_id: str
    range_min: float
    range_max: float
    next_stage: str

    def matches(self, answer_value: float) -> bool:
        """Check if an answer value falls within this rule's range"""
        return self.range_min <= answer_value <= self.range_max

    def get_rule_id(self) -> str:
        """
        Generate a unique rule ID for audit trail.
        Format: {stage_id}_{question_id}_{min}-{max}
        """
        return f"{self.stage_id}_{self.question_id}_{self.range_min}-{self.range_max}"


class RoutingRules:
    """
    Routing Rules Manager

    Loads routing rules from CSV and provides efficient lookups.
    Rules are indexed by (stage_id, question_id) for fast access.
    """

    def __init__(self, rules: List[RoutingRule]):
        self.rules = rules

        # Index rules by (stage_id, question_id) for efficient lookup
        self._rules_by_stage_question: Dict[Tuple[str, str], List[RoutingRule]] = {}

        for rule in rules:
            key = (rule.stage_id, rule.question_id)
            if key not in self._rules_by_stage_question:
                self._rules_by_stage_question[key] = []
            self._rules_by_stage_question[key].append(rule)

        # Sort rules by range_min for each key (helps with debugging)
        for key in self._rules_by_stage_question:
            self._rules_by_stage_question[key].sort(key=lambda r: r.range_min)

    def find_matching_rule(
        self,
        stage_id: str,
        question_id: str,
        answer_value: float
    ) -> Optional[RoutingRule]:
        """
        Find the routing rule that matches the given answer.

        Args:
            stage_id: Current stage ID
            question_id: Question ID that was answered
            answer_value: Numeric answer value

        Returns:
            Matching RoutingRule or None if no match found
        """
        key = (stage_id, question_id)
        rules = self._rules_by_stage_question.get(key, [])

        for rule in rules:
            if rule.matches(answer_value):
                return rule

        return None

    def get_rules_for_stage(self, stage_id: str) -> List[RoutingRule]:
        """Get all routing rules that apply to a specific stage"""
        return [
            rule for rule in self.rules
            if rule.stage_id == stage_id
        ]

    def get_rules_for_question(self, stage_id: str, question_id: str) -> List[RoutingRule]:
        """Get all routing rules for a specific stage-question combination"""
        key = (stage_id, question_id)
        return self._rules_by_stage_question.get(key, [])

    @classmethod
    def from_csv_file(cls, file_path: Path) -> "RoutingRules":
        """
        Load routing rules from CSV file.

        Expected CSV format:
        stage_id,if_number_id,in_range_min,in_range_max,next_stage
        REFERRAL,ref_karnofsky,0.0,39.0,EXIT
        """
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
        """Load routing rules from CSV string (useful for testing)"""
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
        """
        Validate that ranges don't overlap for the same (stage_id, question_id).

        Returns:
            List of error messages. Empty list means validation passed.
        """
        errors = []

        for key, rules in self._rules_by_stage_question.items():
            stage_id, question_id = key

            # Check each pair of rules for overlap
            for i, rule1 in enumerate(rules):
                for rule2 in rules[i + 1:]:
                    # Check if ranges overlap
                    if (rule1.range_min <= rule2.range_max and
                            rule2.range_min <= rule1.range_max):
                        errors.append(
                            f"Overlapping ranges for {stage_id}.{question_id}: "
                            f"[{rule1.range_min}, {rule1.range_max}] overlaps with "
                            f"[{rule2.range_min}, {rule2.range_max}]"
                        )

        return errors


# Singleton instance - loaded once at application startup
_routing_rules: Optional[RoutingRules] = None


def load_routing_rules(csv_path: Path) -> RoutingRules:
    """
    Load routing rules from CSV file.
    This should be called once at application startup.
    """
    global _routing_rules
    _routing_rules = RoutingRules.from_csv_file(csv_path)

    # Validate that ranges don't overlap
    errors = _routing_rules.validate_ranges_non_overlapping()
    if errors:
        raise ValueError(f"Invalid routing rules: {'; '.join(errors)}")

    return _routing_rules


def get_routing_rules() -> RoutingRules:
    """
    Get the loaded routing rules.
    Raises ValueError if rules haven't been loaded yet.
    """
    if _routing_rules is None:
        raise ValueError(
            "Routing rules not loaded. Call load_routing_rules() first."
        )
    return _routing_rules
