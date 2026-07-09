from __future__ import annotations

from maios.kernel import PredictionEngine, SystemState


def test_prediction_engine_predicts_runtime_health():
    engine = PredictionEngine()

    degraded = engine.predict_runtime(SystemState())
    risky = engine.predict_runtime(SystemState(healthy_nodes=1, failure_rate=0.7))
    stable = engine.predict_runtime(SystemState(healthy_nodes=1, active_agents=2))

    assert degraded.outcome == "degraded"
    assert risky.outcome == "risky"
    assert stable.outcome == "stable"


def test_prediction_engine_predicts_planner_by_capability_and_capacity():
    engine = PredictionEngine()

    assert engine.predict_planner(("research",), SystemState()).outcome == "research"
    assert engine.predict_planner(("plan", "execute"), SystemState()).outcome == "meta"
    assert (
        engine.predict_planner(("execute",), SystemState(healthy_nodes=1)).outcome == "distributed"
    )
    assert engine.predict_planner(("execute",), SystemState()).outcome == "swarm"
    assert engine.predict_planner((), SystemState()).outcome == "direct"


def test_prediction_engine_predicts_agent_availability():
    engine = PredictionEngine()

    assert engine.predict_agent("plan", SystemState()).outcome == "unavailable"
    assert (
        engine.predict_agent("plan", SystemState(active_agents=2, failed_agents=1)).outcome
        == "replacement_needed"
    )
    assert engine.predict_agent("plan", SystemState(active_agents=2)).outcome == "available"
