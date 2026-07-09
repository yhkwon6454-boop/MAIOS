from __future__ import annotations

from typing import Any

from maios.distributed import DistributedRuntime
from maios.kernel import CognitiveLoop, CognitivePhase
from maios.kernel.executive_brain import DecisionContext, ExecutiveBrain, ExecutiveDecision
from maios.knowledge import KnowledgeGraph


class FailingBrain(ExecutiveBrain):
    def _execute_decision(
        self,
        decision: ExecutiveDecision,
        context: DecisionContext,
    ) -> dict[str, Any]:
        return {"status": "FAILED", "error": "boom", "planner": "direct"}


def test_observe_refreshes_system_state_from_runtime():
    runtime = DistributedRuntime()
    runtime.register_node("node-a")
    loop = CognitiveLoop(runtime=runtime)
    context = DecisionContext("Observe runtime")

    record = loop.observe(context)

    assert record.phase == CognitivePhase.OBSERVE
    assert loop.world_model.system.healthy_nodes == 1
    assert loop.world_model.user.intent_history[-1] == "Observe runtime"
    assert loop.world_model.environment.signals["observed_objective"] == "Observe runtime"


def test_understand_builds_world_context_for_decision():
    loop = CognitiveLoop()
    context = DecisionContext("Understand world", requested_capabilities=("execute",))

    record = loop.understand(context)

    assert record.phase == CognitivePhase.UNDERSTAND
    assert "world_context" in context.metadata
    assert set(record.data["predictions"]) == {"runtime", "planner", "agent"}


def test_plan_reuses_world_context_built_during_understand():
    loop = CognitiveLoop()
    context = DecisionContext("Plan once")

    loop.understand(context)
    first_context_id = context.metadata["world_context"]["context_id"]
    decision, record = loop.plan(context)

    assert record.phase == CognitivePhase.PLAN
    assert record.data["decision_id"] == decision.decision_id
    assert context.metadata["world_context"]["context_id"] == first_context_id


def test_act_executes_decision_and_records_outcome():
    loop = CognitiveLoop()
    context = DecisionContext("Act directly")
    decision, _ = loop.plan(context)

    outcome, record = loop.act(decision, context)

    assert record.phase == CognitivePhase.ACT
    assert outcome["status"] == "COMPLETED"
    assert context.prior_outcomes[-1] == outcome


def test_reflect_reports_success_for_completed_outcome():
    loop = CognitiveLoop()
    context = DecisionContext("Reflect success")

    report, record = loop.reflect(context, {"status": "COMPLETED"})

    assert record.phase == CognitivePhase.REFLECT
    assert report.success
    assert report.score == 90


def test_reflect_reports_bottlenecks_for_failed_outcome():
    loop = CognitiveLoop()
    context = DecisionContext("Reflect failure")
    context.record_outcome({"status": "FAILED", "error": "timeout"})

    report, record = loop.reflect(context, {"status": "FAILED", "error": "timeout"})

    assert not report.success
    assert "timeout" in report.bottlenecks
    assert record.data["success"] is False


def test_learn_transitions_world_model_and_stores_experience():
    graph = KnowledgeGraph()
    loop = CognitiveLoop(knowledge_graph=graph)
    context = DecisionContext("Learn cycle")

    report, _ = loop.reflect(context, {"status": "COMPLETED"})
    record = loop.learn(context, {"status": "COMPLETED"}, report)

    assert record.phase == CognitivePhase.LEARN
    assert loop.world_model.transitions[-1].event == "cognitive_cycle"
    assert record.data["escalated"] is False
    assert any(node.node_type == "experience" for node in graph.nodes.values())


def test_learn_escalates_after_repeated_failures():
    brain = FailingBrain(failure_threshold=2)
    loop = CognitiveLoop(executive_brain=brain)
    context = DecisionContext("Escalate learning")
    context.record_outcome({"status": "FAILED", "error": "boom"})
    context.record_outcome({"status": "FAILED", "error": "boom"})

    report, _ = loop.reflect(context, {"status": "FAILED", "error": "boom"})
    record = loop.learn(context, {"status": "FAILED", "error": "boom"}, report)

    assert record.data["escalated"] is True
    assert "boom" in record.data["lessons"] or record.data["lessons"]


def test_cognitive_loop_reuses_world_model_from_executive_brain():
    brain = ExecutiveBrain()
    loop = CognitiveLoop(executive_brain=brain)

    assert loop.world_model is brain.world_model
