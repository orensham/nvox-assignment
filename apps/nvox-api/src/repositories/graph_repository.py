from typing import List, Optional, Dict, Any
from uuid import UUID
from nvox_common.db.nvox_db_client import NvoxDBClient
from journey.graph_models import JourneyEdge
import json


class GraphRepository:
    def __init__(self, db_client: NvoxDBClient):
        self.db_client = db_client

    async def get_outgoing_edges(self, from_node_id: Optional[str]) -> List[JourneyEdge]:
        rows = await self.db_client.fetch(
            """
            SELECT id, from_node_id, to_node_id, condition_type,
                   question_id, range_min, range_max
            FROM journey_edges
            WHERE from_node_id = $1 OR ($1 IS NULL AND from_node_id IS NULL)
            ORDER BY created_at ASC
            """,
            from_node_id
        )

        return [
            JourneyEdge(
                id=row["id"],
                from_node_id=row["from_node_id"],
                to_node_id=row["to_node_id"],
                condition_type=row["condition_type"],
                question_id=row["question_id"],
                range_min=row["range_min"],
                range_max=row["range_max"]
            )
            for row in rows
        ]

    async def find_matching_edge(
        self,
        from_node_id: str,
        answers: Dict[str, Any],
        visit_history: List[str]
    ) -> Optional[JourneyEdge]:
        edges = await self.get_outgoing_edges(from_node_id)

        matching_edges = []
        for edge in edges:

            if edge.condition_type == 'always':
                matching_edges.append(edge)
            elif edge.question_id and edge.question_id in answers:
                answer_value = answers[edge.question_id]
                if edge.matches(answer_value):
                    matching_edges.append(edge)

        if not matching_edges:
            return None

        revisit_edges = [e for e in matching_edges if e.to_node_id in visit_history]
        forward_edges = [e for e in matching_edges if e.to_node_id not in visit_history]

        if revisit_edges:
            return revisit_edges[0]

        if forward_edges:
            return forward_edges[0]

        return None

    async def get_entry_edge(self) -> Optional[JourneyEdge]:
        edges = await self.get_outgoing_edges(None)
        return edges[0] if edges else None

    async def get_all_edges(self) -> List[JourneyEdge]:
        rows = await self.db_client.fetch(
            """
            SELECT id, from_node_id, to_node_id, condition_type,
                   question_id, range_min, range_max
            FROM journey_edges
            ORDER BY from_node_id, created_at ASC
            """
        )

        return [
            JourneyEdge(
                id=row["id"],
                from_node_id=row["from_node_id"],
                to_node_id=row["to_node_id"],
                condition_type=row["condition_type"],
                question_id=row["question_id"],
                range_min=row["range_min"],
                range_max=row["range_max"]
            )
            for row in rows
        ]
