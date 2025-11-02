from dataclasses import dataclass
from typing import Optional, Any
from uuid import UUID
from decimal import Decimal, InvalidOperation


@dataclass
class JourneyEdge:
    id: UUID
    from_node_id: Optional[str]
    to_node_id: str
    condition_type: str
    question_id: Optional[str]
    range_min: Optional[Decimal]
    range_max: Optional[Decimal]

    def matches(self, answer_value: Any) -> bool:
        if self.condition_type == 'always':
            return True

        if self.condition_type == 'range':
            if self.range_min is None or self.range_max is None:
                return False

            try:
                numeric_value = Decimal(str(answer_value))
                return self.range_min <= numeric_value <= self.range_max
            except (ValueError, TypeError, InvalidOperation):
                return False

        if self.condition_type == 'equals':
            if self.range_min is not None:
                try:
                    return Decimal(str(answer_value)) == self.range_min
                except (ValueError, TypeError, InvalidOperation):
                    return False

        return False

    def __str__(self) -> str:
        condition = ""
        if self.condition_type == 'range' and self.question_id:
            condition = f"if {self.question_id} in [{self.range_min}, {self.range_max}]"
        elif self.condition_type == 'always':
            condition = "always"

        from_node = self.from_node_id or "ENTRY"
        return f"{from_node} → {self.to_node_id} ({condition})"

    def __repr__(self) -> str:
        return (
            f"JourneyEdge(id={self.id}, "
            f"from_node_id={self.from_node_id!r}, "
            f"to_node_id={self.to_node_id!r}, "
            f"condition_type={self.condition_type!r}, "
            f"question_id={self.question_id!r})"
        )
