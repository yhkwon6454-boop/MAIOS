from __future__ import annotations

from typing import Any

from maios.kernel import CognitiveLoop
from maios.kernel.executive_brain import DecisionContext, ExecutiveBrain, ExecutiveDecision
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge import KnowledgeGraph


class BigOutcomeBrain(ExecutiveBrain):
    def _execute_decision(
        self,
        decision: ExecutiveDecision,
        context: DecisionContext,
    ) -> dict[str, Any]:
        return {
            "status": "COMPLETED",
            "planner": "research",
            "report": {"sources": ["x" * 100_000]},
            "output": "y" * 5_000,
        }


def test_add_node_caps_content_length():
    graph = KnowledgeGraph(max_content_chars=1000)

    node = graph.add_node(title="Big", content="z" * 50_000, auto_link=False)

    assert len(node.content) == 1000


def test_compact_outcome_drops_report_and_trims_fields():
    outcome = {
        "status": "COMPLETED",
        "planner": "research",
        "report": {"huge": "x" * 100_000},
        "output": "y" * 5_000,
        "error": "e" * 5_000,
    }

    compact = ExecutiveBrain.compact_outcome(outcome)

    assert "report" not in compact
    assert len(compact["output"]) == 300
    assert len(compact["error"]) == 300
    assert compact["status"] == "COMPLETED"


def test_world_transitions_store_compact_outcomes_only():
    brain = BigOutcomeBrain()
    loop = CognitiveLoop(executive_brain=brain)

    loop.run_cycle("Big outcome goal")

    transition = loop.world_model.transitions[-1]
    stored = transition.changes["system"]["outcome"]
    assert "report" not in stored
    assert len(str(stored)) < 1000


def test_experience_nodes_stay_bounded_for_large_outcomes():
    graph = KnowledgeGraph()
    brain = BigOutcomeBrain(knowledge_graph=graph)
    loop = CognitiveLoop(executive_brain=brain, knowledge_graph=graph)

    loop.run_cycle("Big outcome goal")

    experiences = [node for node in graph.nodes.values() if node.node_type == "experience"]
    assert experiences
    assert all(len(node.content) < 2000 for node in experiences)


def test_long_term_memory_entries_are_truncated():
    memory = MemoryKernel()
    brain = BigOutcomeBrain(memory_kernel=memory)
    loop = CognitiveLoop(executive_brain=brain, memory_kernel=memory)

    loop.run_cycle("Big outcome goal")

    assert memory.long_term_memory
    assert all(len(document.content) <= 8000 for document in memory.long_term_memory)
