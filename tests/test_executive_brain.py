from __future__ import annotations

from maios.agents import NegotiationManager
from maios.kernel import DecisionContext, ExecutiveBrain
from maios.kernel.executive_brain import PlannerType
from maios.knowledge import KnowledgeGraph
from maios.planning import MetaGoal


class SelfImprovementSpy:
    def __init__(self) -> None:
        self.histories = []
        self.records = [object()]
        self.plans = []

    def analyze_execution_history(self, history):
        self.histories.append(list(history))
        return self.records[-1]

    def generate_plan(self, record, target: str = "maios"):
        self.plans.append((record, target))
        return {"target": target}


def test_executive_brain_runs_meta_planner_for_multi_goal_context():
    graph = KnowledgeGraph()
    negotiation = NegotiationManager()
    brain = ExecutiveBrain(knowledge_graph=graph, negotiation_manager=negotiation)
    context = DecisionContext("Balance portfolio")
    context.add_goal(MetaGoal("Ship patch", urgency=0.9, required_capabilities=("plan",)))
    context.add_goal(MetaGoal("Build research base", impact=0.9, horizon="long_term"))

    decision = brain.execute(context)

    assert decision.selected_planner == PlannerType.META
    assert decision.outcome["plan_id"].startswith("SP-")
    assert decision.outcome["roadmap_id"].startswith("ER-")
    assert graph.get_node(decision.decision_id) is not None
    assert negotiation.sessions()[0].proposals[0].proposer_id == "executive_brain"


def test_executive_brain_persists_execution_outcomes_to_knowledge_graph():
    graph = KnowledgeGraph()
    brain = ExecutiveBrain(knowledge_graph=graph)
    context = DecisionContext("Persist result")

    decision = brain.execute(context)

    assert decision.status == "COMPLETED"
    assert any(node.node_type == "experience" for node in graph.nodes.values())
    assert any(
        "Executive outcome for Persist result" in node.content for node in graph.nodes.values()
    )


def test_executive_brain_triggers_self_improvement_on_repeated_mistakes():
    spy = SelfImprovementSpy()
    brain = ExecutiveBrain(self_improvement_engine=spy, failure_threshold=2)
    context = DecisionContext("Repeated mistake")

    brain.record_outcome(context, {"status": "FAILED", "error": "same bug"})
    brain.record_outcome(context, {"status": "FAILED", "error": "same bug"})

    assert spy.histories
    assert spy.plans == [(spy.records[-1], "Repeated mistake")]


def test_executive_decision_serializes_planner_value():
    context = DecisionContext.from_goal("Plan", capabilities=["plan"])
    decision = ExecutiveBrain().decide(context)
    data = decision.to_dict()

    assert data["selected_planner"] == "meta"
    assert data["priority_order"] == [context.goals[0].goal_id]
