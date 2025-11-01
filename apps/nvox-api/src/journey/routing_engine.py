"""
Journey Routing Engine

Core logic for determining stage transitions based on user answers.
Evaluates routing rules and manages journey state.
"""

from typing import Optional, Any, Dict
from uuid import UUID
from datetime import datetime

from .config_loader import get_journey_config, Question
from .rules_loader import get_routing_rules, RoutingRule


class TransitionDecision:
    """Represents a decision about stage transition"""

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
        """Convert to dictionary for database storage"""
        return {
            "should_transition": self.should_transition,
            "next_stage": self.next_stage,
            "matched_rule_id": self.matched_rule.get_rule_id() if self.matched_rule else None,
            "question_id": self.question_id,
            "answer_value": self.answer_value,
            "reason": self.reason
        }


class RoutingEngine:
    """
    Journey Routing Engine

    Determines stage transitions based on:
    - Journey configuration (stages and questions)
    - Routing rules (CSV rules)
    - User answers
    """

    def __init__(self):
        self.config = get_journey_config()
        self.rules = get_routing_rules()

    def validate_answer(
        self,
        stage_id: str,
        question_id: str,
        answer_value: Any
    ) -> tuple[bool, Optional[str]]:
        """
        Validate an answer against question constraints.

        Returns:
            (is_valid, error_message)
        """
        # Check if stage exists
        stage = self.config.get_stage(stage_id)
        if not stage:
            return False, f"Invalid stage: {stage_id}"

        # Check if question exists in this stage
        question = stage.get_question(question_id)
        if not question:
            return False, f"Question {question_id} not found in stage {stage_id}"

        # Validate answer value against question constraints
        return question.validate_answer(answer_value)

    def should_transition(
        self,
        current_stage_id: str,
        question_id: str,
        answer_value: Any
    ) -> TransitionDecision:
        """
        Determine if a stage transition should occur based on an answer.

        Args:
            current_stage_id: Current stage the user is in
            question_id: Question that was just answered
            answer_value: The answer value provided

        Returns:
            TransitionDecision with routing information
        """
        # Get the question to check if it's a routing question
        question = self.config.get_question(current_stage_id, question_id)
        if not question:
            return TransitionDecision(
                should_transition=False,
                reason=f"Question {question_id} not found in stage {current_stage_id}"
            )

        # Only number questions trigger routing rules
        if question.type != "number":
            return TransitionDecision(
                should_transition=False,
                reason=f"Question type '{question.type}' does not trigger routing"
            )

        # Convert answer to float for rule matching
        try:
            numeric_value = float(answer_value)
        except (ValueError, TypeError):
            return TransitionDecision(
                should_transition=False,
                reason=f"Cannot convert answer to numeric value: {answer_value}"
            )

        # Find matching routing rule
        matched_rule = self.rules.find_matching_rule(
            current_stage_id,
            question_id,
            numeric_value
        )

        if not matched_rule:
            # No matching rule found - stay in current stage
            return TransitionDecision(
                should_transition=False,
                question_id=question_id,
                answer_value=answer_value,
                reason=f"No routing rule matched for {question_id}={numeric_value}"
            )

        # Rule matched - transition to next stage
        return TransitionDecision(
            should_transition=True,
            next_stage=matched_rule.next_stage,
            matched_rule=matched_rule,
            question_id=question_id,
            answer_value=answer_value,
            reason=f"Matched rule: {matched_rule.get_rule_id()}"
        )

    def get_entry_stage(self) -> str:
        """Get the entry stage for new journeys"""
        return self.config.entry_stage

    def is_terminal_stage(self, stage_id: str) -> bool:
        """
        Check if a stage is terminal (no outgoing transitions).
        Terminal stages are those with no questions or no routing rules.
        """
        stage = self.config.get_stage(stage_id)
        if not stage:
            return False

        # If stage has no questions, it's terminal
        if not stage.questions:
            return True

        # Check if any questions have routing rules
        has_routing_rules = False
        for question in stage.questions:
            rules = self.rules.get_rules_for_question(stage_id, question.id)
            if rules:
                has_routing_rules = True
                break

        # If no questions have routing rules, stage is terminal
        return not has_routing_rules

    def get_stage_questions(self, stage_id: str) -> list[Dict[str, Any]]:
        """Get all questions for a stage"""
        stage = self.config.get_stage(stage_id)
        if not stage:
            return []

        return [q.to_dict() for q in stage.questions]

    def get_stage_info(self, stage_id: str) -> Optional[Dict[str, Any]]:
        """Get full information about a stage"""
        stage = self.config.get_stage(stage_id)
        if not stage:
            return None

        return stage.to_dict(include_questions=True)


# Singleton instance
_routing_engine: Optional[RoutingEngine] = None


def get_routing_engine() -> RoutingEngine:
    """
    Get the routing engine instance.
    Raises ValueError if journey config and rules haven't been loaded yet.
    """
    global _routing_engine
    if _routing_engine is None:
        _routing_engine = RoutingEngine()
    return _routing_engine


def reset_routing_engine():
    """Reset the routing engine (useful for testing)"""
    global _routing_engine
    _routing_engine = None
