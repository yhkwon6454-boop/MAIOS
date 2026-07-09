from __future__ import annotations

from typing import Any

from maios.kernel import AGIFoundation, CognitiveLoop
from maios.kernel.executive_brain import DecisionContext, ExecutiveBrain, ExecutiveDecision
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge import KnowledgeGraph


class FailingBrain(ExecutiveBrain):
    def _execute_decision(
        self,
        decision: ExecutiveDecision,
        context: DecisionContext,
    ) -> dict[str, Any]:
        return {"status": "FAILED", "error": "boom", "planner": "direct"}


class MetricSpy:
    def __init__(self) -> None:
        self.metrics: list[tuple[str, float]] = []

    def track_metric(self, name: str, value: float) -> None:
        self.metrics.append((name, value))


def test_introspect_reports_capabilities_and_readiness():
    agi = AGIFoundation()

    model = agi.introspect()

    assert model.identity == "maios"
    assert 0.0 < model.readiness < 1.0
    assert "executive_brain" in model.available()
    assert "research" in model.missing()
    assert agi.self_model is model


def test_introspect_persists_self_model():
    graph = KnowledgeGraph()
    memory = MemoryKernel()
    agi = AGIFoundation(knowledge_graph=graph, memory_kernel=memory)

    model = agi.introspect()

    assert graph.get_node(model.model_id) is not None
    assert memory.retrieve_short_term("self_model")
    assert model.capabilities["knowledge_graph"] is True


def test_pursue_completes_goal_through_cognitive_cycles():
    agi = AGIFoundation()

    pursuit = agi.pursue("Ship the release")

    assert pursuit.success
    assert pursuit.status == "COMPLETED"
    assert len(pursuit.cycle_ids) == 1
    assert agi.goals[pursuit.goal_id].completed
    assert pursuit.lessons


def test_pursue_records_failed_cycles_and_lessons():
    brain = FailingBrain(failure_threshold=2)
    agi = AGIFoundation(cognitive_loop=CognitiveLoop(executive_brain=brain))

    pursuit = agi.pursue("Unstable goal", max_cycles=2)

    assert not pursuit.success
    assert pursuit.status == "FAILED"
    assert len(pursuit.cycle_ids) == 2
    assert not agi.goals[pursuit.goal_id].completed
    assert any("Adjust" in lesson for lesson in pursuit.lessons)


def test_pursue_persists_goal_pursuit():
    graph = KnowledgeGraph()
    memory = MemoryKernel()
    agi = AGIFoundation(knowledge_graph=graph, memory_kernel=memory)

    pursuit = agi.pursue("Persist pursuit")

    node = graph.get_node(pursuit.pursuit_id)
    assert node is not None
    assert node.metadata["status"] == "COMPLETED"
    assert memory.retrieve_short_term("goal_pursuit")


def test_evolve_aggregates_pursuit_outcomes():
    graph = KnowledgeGraph()
    memory = MemoryKernel()
    spy = MetricSpy()
    brain = ExecutiveBrain(knowledge_graph=graph, self_improvement_engine=spy)
    agi = AGIFoundation(
        cognitive_loop=CognitiveLoop(executive_brain=brain, knowledge_graph=graph),
        knowledge_graph=graph,
        memory_kernel=memory,
    )
    agi.pursue("First goal")
    agi.pursue("Second goal")

    report = agi.evolve()

    assert report["pursuits"] == 2
    assert report["executed"] == 2
    assert report["success_rate"] == 1.0
    assert len(report["lessons"]) == 1
    assert spy.metrics == [("pursuit_success_rate", 1.0)]
    assert graph.get_node(str(report["evolution_id"])) is not None
    assert memory.retrieve_short_term("evolution")


def test_evolve_without_pursuits_returns_zero_success_rate():
    agi = AGIFoundation()

    report = agi.evolve()

    assert report["pursuits"] == 0
    assert report["executed"] == 0
    assert report["success_rate"] == 0.0
    assert report["lessons"] == []
