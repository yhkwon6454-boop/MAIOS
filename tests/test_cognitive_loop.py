from __future__ import annotations

from typing import Any

from maios.kernel import CognitiveCycleResult, CognitiveLoop, CognitivePhase
from maios.kernel.cognitive_loop import PHASE_ORDER
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


def test_cognitive_loop_runs_all_phases_in_order():
    loop = CognitiveLoop()

    cycle = loop.run_cycle("Ship release notes")

    assert cycle.phase_order() == tuple(phase.value for phase in PHASE_ORDER)
    assert cycle.status == "COMPLETED"
    assert cycle.success
    assert cycle.decision is not None
    assert cycle.report is not None and cycle.report.success
    assert loop.cycles == [cycle]


def test_cognitive_loop_persists_cycle_to_knowledge_graph_and_memory():
    graph = KnowledgeGraph()
    memory = MemoryKernel()
    loop = CognitiveLoop(knowledge_graph=graph, memory_kernel=memory)

    cycle = loop.run_cycle("Persist cycle")

    node = graph.get_node(cycle.cycle_id)
    assert node is not None
    assert node.metadata["status"] == "COMPLETED"
    assert memory.retrieve_short_term("cognitive_cycle")
    assert memory.retrieve("cognitive_cycle")


def test_cognitive_loop_run_stops_on_success():
    loop = CognitiveLoop()

    cycles = loop.run("Stable objective", max_cycles=3)

    assert len(cycles) == 1
    assert cycles[0].status == "COMPLETED"


def test_cognitive_loop_run_retries_failed_cycles_until_max_cycles():
    brain = FailingBrain(failure_threshold=2)
    loop = CognitiveLoop(executive_brain=brain)

    cycles = loop.run("Unstable objective", max_cycles=2)

    assert len(cycles) == 2
    assert all(cycle.status == "FAILED" for cycle in cycles)
    assert not cycles[0].success
    learn_record = cycles[1].phases[-1]
    assert learn_record.phase == CognitivePhase.LEARN
    assert learn_record.data["escalated"] is True


def test_cognitive_cycle_result_to_dict_serializes_phases_and_outcome():
    loop = CognitiveLoop()

    cycle = loop.run_cycle("Serialize cycle", capabilities=("execute",))
    data = cycle.to_dict()

    assert data["cycle_id"] == cycle.cycle_id
    assert data["status"] == "COMPLETED"
    assert [phase["phase"] for phase in data["phases"]] == list(cycle.phase_order())
    assert data["decision"]["decision_id"] == cycle.decision.decision_id
    assert data["report"]["mission_id"] == cycle.mission_id


def test_cognitive_cycle_result_to_dict_handles_missing_decision_and_report():
    cycle = CognitiveCycleResult(
        objective="Empty cycle",
        mission_id="EB-M-test",
        status="PLANNED",
        phases=(),
    )

    data = cycle.to_dict()

    assert data["decision"] is None
    assert data["report"] is None
    assert not cycle.success
