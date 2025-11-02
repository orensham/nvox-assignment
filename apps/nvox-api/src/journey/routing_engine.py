from typing import Optional, Any, Dict, List
from uuid import UUID
from datetime import datetime

from .config_loader import get_journey_config, Question
from .graph_models import JourneyEdge


class TransitionDecision:
    def __init__(
        self,
        should_transition: bool,
        next_stage: Optional[str] = None,
        matched_edge: Optional[JourneyEdge] = None,
        question_id: Optional[str] = None,
        answer_value: Optional[Any] = None,
        reason: Optional[str] = None
    ):
        self.should_transition = should_transition
        self.next_stage = next_stage
        self.matched_edge = matched_edge
        self.question_id = question_id
        self.answer_value = answer_value
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "should_transition": self.should_transition,
            "next_stage": self.next_stage,
            "matched_edge_id": str(self.matched_edge.id) if self.matched_edge else None,
            "question_id": self.question_id,
            "answer_value": self.answer_value,
            "reason": self.reason
        }


class RoutingEngine:
    def __init__(self, config=None, graph_repository=None):
        self.config = config if config is not None else get_journey_config()
        self.graph_repository = graph_repository  # For graph-based routing

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

    def get_entry_stage(self) -> str:
        return self.config.entry_stage

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

    async def evaluate_transition_with_graph(
        self,
        current_stage_id: str,
        answers: Dict[str, Any],
        visit_history: List[str]
    ) -> TransitionDecision:
        if not self.graph_repository:
            return TransitionDecision(
                should_transition=False,
                reason="Graph repository not available. Cannot evaluate transition."
            )

        matched_edge = await self.graph_repository.find_matching_edge(
            current_stage_id,
            answers,
            visit_history
        )

        if not matched_edge:
            return TransitionDecision(
                should_transition=False,
                reason=f"No matching edge found for stage {current_stage_id}"
            )

        is_revisit = matched_edge.to_node_id in visit_history
        edge_type = "revisit (loop)" if is_revisit else "forward progress"

        return TransitionDecision(
            should_transition=True,
            next_stage=matched_edge.to_node_id,
            matched_edge=matched_edge,
            question_id=matched_edge.question_id,
            answer_value=answers.get(matched_edge.question_id) if matched_edge.question_id else None,
            reason=f"Matched edge {matched_edge.id} → {matched_edge.to_node_id} ({edge_type})"
        )


_routing_engine: Optional[RoutingEngine] = None


def get_routing_engine() -> RoutingEngine:
    global _routing_engine
    if _routing_engine is None:
        _routing_engine = RoutingEngine()
    return _routing_engine


def reset_routing_engine():
    global _routing_engine
    _routing_engine = None
