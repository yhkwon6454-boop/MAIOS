from __future__ import annotations

from maios.kernel import EnvironmentState, StateTransitionEngine, WorldModel
from maios.knowledge import KnowledgeGraph


def test_state_transition_engine_applies_changes_and_records_transition():
    graph = KnowledgeGraph()
    world = WorldModel(
        environment=EnvironmentState(risk_level="normal"),
        transition_engine=StateTransitionEngine(),
        knowledge_graph=graph,
    )
    original_state_id = world.state_id

    transition = world.transition(
        "sensor_update",
        {
            "environment": {
                "signals": {"threat": "low"},
                "risk_level": "high",
            },
            "user": {"intent": "Assess risk"},
            "system": {"outcome": {"status": "FAILED"}},
        },
    )

    assert transition.source_state_id == original_state_id
    assert transition.target_state_id == world.state_id
    assert world.environment.risk_level == "HIGH"
    assert world.environment.signals["threat"] == "low"
    assert world.user.intent_history == ["Assess risk"]
    assert world.system.failure_rate == 0.1
    assert graph.get_node(transition.transition_id) is not None


def test_world_model_apply_changes_accepts_direct_system_values():
    world = WorldModel()

    world.apply_changes(
        {
            "system": {
                "healthy_nodes": 3,
                "active_agents": 5,
                "failure_rate": 0.4,
            }
        }
    )

    assert world.system.healthy_nodes == 3
    assert world.system.active_agents == 5
    assert world.system.failure_rate == 0.4
