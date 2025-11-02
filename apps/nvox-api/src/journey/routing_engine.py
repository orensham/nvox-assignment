from typing import Optional, Any, Dict
from uuid import UUID
from datetime import datetime

from .config_loader import get_journey_config, Question
from .rules_loader import get_routing_rules, RoutingRule


class TransitionDecision:
    def __init__(
        self,
        should_transition: bool,
        next_stage: Optional[str] = None,
        matched_rule: Optional[RoutingRule] = None,
        question_id: Optional[str] = None,
        answer_value: Optional[Any] = None,
        reason: Optional[str] = None
    ):
        self.should_transition = should_transition
        self.next_stage = next_stage
        self.matched_rule = matched_rule
        self.question_id = question_id
        self.answer_value = answer_value
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "should_transition": self.should_transition,
            "next_stage": self.next_stage,
            "matched_rule_id": self.matched_rule.get_rule_id() if self.matched_rule else None,
            "question_id": self.question_id,
            "answer_value": self.answer_value,
            "reason": self.reason
        }


class RoutingEngine:
    def __init__(self, config=None, rules=None):
        self.config = config if config is not None else get_journey_config()
        self.rules = rules if rules is not None else get_routing_rules()

    def validate_answer(
        self,
        stage_id: str,
        question_id: str,
        answer_value: Any
    ) -> tuple[bool, Optional[str]]:
        stage = self.config.get_stage(stage_id)
        if not stage:
            return False, f"Invalid stage: {stage_id}"

        question = stage.get_question(question_id)
        if not question:
            return False, f"Question {question_id} not found in stage {stage_id}"

        return question.validate_answer(answer_value)

    def should_transition(
        self,
        current_stage_id: str,
        question_id: str,
        answer_value: Any
    ) -> TransitionDecision:
        question = self.config.get_question(current_stage_id, question_id)
        if not question:
            return TransitionDecision(
                should_transition=False,
                reason=f"Question {question_id} not found in stage {current_stage_id}"
            )

        if question.type != "number":
            return TransitionDecision(
                should_transition=False,
                reason=f"Question type '{question.type}' does not trigger routing"
            )

        try:
            numeric_value = float(answer_value)
        except (ValueError, TypeError):
            return TransitionDecision(
                should_transition=False,
                reason=f"Cannot convert answer to numeric value: {answer_value}"
            )

        matched_rule = self.rules.find_matching_rule(
            current_stage_id,
            question_id,
            numeric_value
        )

        if not matched_rule:
            return TransitionDecision(
                should_transition=False,
                question_id=question_id,
                answer_value=answer_value,
                reason=f"No routing rule matched for {question_id}={numeric_value}"
            )

        return TransitionDecision(
            should_transition=True,
            next_stage=matched_rule.next_stage,
            matched_rule=matched_rule,
            question_id=question_id,
            answer_value=answer_value,
            reason=f"Matched rule: {matched_rule.get_rule_id()}"
        )

    def get_entry_stage(self) -> str:
        return self.config.entry_stage

    def is_terminal_stage(self, stage_id: str) -> bool:
        stage = self.config.get_stage(stage_id)
        if not stage:
            return False

        if not stage.questions:
            return True

        has_routing_rules = False
        for question in stage.questions:
            rules = self.rules.get_rules_for_question(stage_id, question.id)
            if rules:
                has_routing_rules = True
                break

        return not has_routing_rules

    def get_stage_questions(self, stage_id: str) -> list[Dict[str, Any]]:
        stage = self.config.get_stage(stage_id)
        if not stage:
            return []

        return [q.to_dict() for q in stage.questions]

    def get_stage_info(self, stage_id: str) -> Optional[Dict[str, Any]]:
        stage = self.config.get_stage(stage_id)
        if not stage:
            return None

        return stage.to_dict(include_questions=True)


_routing_engine: Optional[RoutingEngine] = None


def get_routing_engine() -> RoutingEngine:
    global _routing_engine
    if _routing_engine is None:
        _routing_engine = RoutingEngine()
    return _routing_engine


def reset_routing_engine():
    global _routing_engine
    _routing_engine = None
