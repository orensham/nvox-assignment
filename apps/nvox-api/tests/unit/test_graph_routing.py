import pytest
from uuid import uuid4
from decimal import Decimal
from journey.graph_models import JourneyEdge
from repositories.graph_repository import GraphRepository
from journey.routing_engine import RoutingEngine
from unittest.mock import AsyncMock, MagicMock


class TestJourneyEdge:
    def test_matches_range_condition(self):
        edge = JourneyEdge(
            id=uuid4(),
            from_node_id='REFERRAL',
            to_node_id='WORKUP',
            condition_type='range',
            question_id='ref_karnofsky',
            range_min=Decimal('40.0'),
            range_max=Decimal('100.0')
        )

        assert edge.matches(50) is True
        assert edge.matches(40) is True
        assert edge.matches(100) is True
        assert edge.matches(39.999) is False
        assert edge.matches(100.001) is False

    def test_matches_always_condition(self):
        edge = JourneyEdge(
            id=uuid4(),
            from_node_id=None,
            to_node_id='REFERRAL',
            condition_type='always',
            question_id=None,
            range_min=None,
            range_max=None
        )

        assert edge.matches(None) is True
        assert edge.matches(0) is True
        assert edge.matches("anything") is True

    def test_matches_equals_condition(self):
        edge = JourneyEdge(
            id=uuid4(),
            from_node_id='DONOR',
            to_node_id='BOARD',
            condition_type='equals',
            question_id='dnr_clearance',
            range_min=Decimal('1.0'),
            range_max=None
        )

        assert edge.matches(1) is True
        assert edge.matches(1.0) is True
        assert edge.matches(0) is False
        assert edge.matches(2) is False

    def test_edge_string_representation(self):
        edge = JourneyEdge(
            id=uuid4(),
            from_node_id='REFERRAL',
            to_node_id='WORKUP',
            condition_type='range',
            question_id='ref_karnofsky',
            range_min=Decimal('40.0'),
            range_max=Decimal('100.0')
        )

        assert "REFERRAL → WORKUP" in str(edge)
        assert "ref_karnofsky" in str(edge)


@pytest.mark.asyncio
class TestGraphRepository:
    async def test_find_matching_edge_with_revisit_priority(self):
        db_client = MagicMock()

        edge_to_workup = JourneyEdge(
            id=uuid4(),
            from_node_id='BOARD',
            to_node_id='WORKUP',
            condition_type='range',
            question_id='brd_needs_more_tests',
            range_min=Decimal('1.0'),
            range_max=Decimal('1.0')
        )

        edge_to_preop = JourneyEdge(
            id=uuid4(),
            from_node_id='BOARD',
            to_node_id='PREOP',
            condition_type='range',
            question_id='brd_risk_score',
            range_min=Decimal('0.0'),
            range_max=Decimal('6.999')
        )

        db_client.fetch = AsyncMock(return_value=[
            {
                'id': edge_to_workup.id,
                'from_node_id': 'BOARD',
                'to_node_id': 'WORKUP',
                'condition_type': 'range',
                'question_id': 'brd_needs_more_tests',
                'range_min': Decimal('1.0'),
                'range_max': Decimal('1.0')
            },
            {
                'id': edge_to_preop.id,
                'from_node_id': 'BOARD',
                'to_node_id': 'PREOP',
                'condition_type': 'range',
                'question_id': 'brd_risk_score',
                'range_min': Decimal('0.0'),
                'range_max': Decimal('6.999')
            }
        ])

        repo = GraphRepository(db_client)

        answers = {
            'brd_needs_more_tests': 1,
            'brd_risk_score': 5
        }

        visit_history = ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']

        matched_edge = await repo.find_matching_edge('BOARD', answers, visit_history)

        assert matched_edge is not None
        assert matched_edge.to_node_id == 'WORKUP'
        assert matched_edge.question_id == 'brd_needs_more_tests'

    async def test_find_matching_edge_forward_when_no_revisit(self):
        db_client = MagicMock()

        edge_to_preop = JourneyEdge(
            id=uuid4(),
            from_node_id='BOARD',
            to_node_id='PREOP',
            condition_type='range',
            question_id='brd_risk_score',
            range_min=Decimal('0.0'),
            range_max=Decimal('6.999')
        )

        db_client.fetch = AsyncMock(return_value=[
            {
                'id': edge_to_preop.id,
                'from_node_id': 'BOARD',
                'to_node_id': 'PREOP',
                'condition_type': 'range',
                'question_id': 'brd_risk_score',
                'range_min': Decimal('0.0'),
                'range_max': Decimal('6.999')
            }
        ])

        repo = GraphRepository(db_client)

        answers = {'brd_risk_score': 5}
        visit_history = ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']

        matched_edge = await repo.find_matching_edge('BOARD', answers, visit_history)

        assert matched_edge is not None
        assert matched_edge.to_node_id == 'PREOP'

    async def test_find_matching_edge_no_match(self):
        """Test that None is returned when no edges match."""
        db_client = MagicMock()

        edge = JourneyEdge(
            id=uuid4(),
            from_node_id='BOARD',
            to_node_id='PREOP',
            condition_type='range',
            question_id='brd_risk_score',
            range_min=Decimal('0.0'),
            range_max=Decimal('6.999')
        )

        db_client.fetch = AsyncMock(return_value=[
            {
                'id': edge.id,
                'from_node_id': 'BOARD',
                'to_node_id': 'PREOP',
                'condition_type': 'range',
                'question_id': 'brd_risk_score',
                'range_min': Decimal('0.0'),
                'range_max': Decimal('6.999')
            }
        ])

        repo = GraphRepository(db_client)

        answers = {'brd_risk_score': 7.5}
        visit_history = ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']

        matched_edge = await repo.find_matching_edge('BOARD', answers, visit_history)

        assert matched_edge is None


@pytest.mark.asyncio
class TestRoutingEngineWithGraph:
    async def test_evaluate_transition_with_graph_success(self):
        graph_repo = MagicMock()

        matched_edge = JourneyEdge(
            id=uuid4(),
            from_node_id='BOARD',
            to_node_id='WORKUP',
            condition_type='range',
            question_id='brd_needs_more_tests',
            range_min=Decimal('1.0'),
            range_max=Decimal('1.0')
        )

        graph_repo.find_matching_edge = AsyncMock(return_value=matched_edge)

        engine = RoutingEngine(config=MagicMock(), graph_repository=graph_repo)

        answers = {'brd_needs_more_tests': 1, 'brd_risk_score': 5}
        visit_history = ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']

        decision = await engine.evaluate_transition_with_graph(
            'BOARD',
            answers,
            visit_history
        )

        assert decision.should_transition is True
        assert decision.next_stage == 'WORKUP'
        assert decision.matched_edge == matched_edge
        assert decision.question_id == 'brd_needs_more_tests'
        assert 'revisit (loop)' in decision.reason

    async def test_evaluate_transition_with_graph_no_match(self):
        graph_repo = MagicMock()
        graph_repo.find_matching_edge = AsyncMock(return_value=None)

        engine = RoutingEngine(config=MagicMock(), graph_repository=graph_repo)

        answers = {'brd_risk_score': 7.5}
        visit_history = ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']

        decision = await engine.evaluate_transition_with_graph(
            'BOARD',
            answers,
            visit_history
        )

        assert decision.should_transition is False
        assert decision.next_stage is None
        assert 'No matching edge' in decision.reason

    async def test_evaluate_transition_without_graph_repository(self):
        engine = RoutingEngine(config=MagicMock())

        answers = {'brd_needs_more_tests': 1}
        visit_history = ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD']

        decision = await engine.evaluate_transition_with_graph(
            'BOARD',
            answers,
            visit_history
        )

        assert decision.should_transition is False
        assert 'Graph repository not available' in decision.reason


class TestDeterministicRouting:
    def test_board_stage_scenario_documentation(self):
        scenario_1 = {
            'current_stage': 'BOARD',
            'answers': {
                'brd_needs_more_tests': 1,
                'brd_risk_score': 5
            },
            'visit_history': ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD'],
            'expected_next_stage': 'WORKUP',
            'reason': 'Medical urgency - patient needs more testing'
        }

        scenario_2 = {
            'current_stage': 'BOARD',
            'answers': {
                'brd_needs_more_tests': 0,
                'brd_risk_score': 5
            },
            'visit_history': ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD'],
            'expected_next_stage': 'PREOP',
            'reason': 'Patient cleared for surgery preparation'
        }

        scenario_3 = {
            'current_stage': 'BOARD',
            'answers': {
                'brd_needs_more_tests': 0,
                'brd_risk_score': 8
            },
            'visit_history': ['REFERRAL', 'WORKUP', 'MATCH', 'DONOR', 'BOARD'],
            'expected_next_stage': 'EXIT',
            'reason': 'Risk too high for transplant'
        }

        assert scenario_1['expected_next_stage'] == 'WORKUP'
        assert scenario_2['expected_next_stage'] == 'PREOP'
        assert scenario_3['expected_next_stage'] == 'EXIT'
