from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from maios.agents import Agent, AgentCapability
from maios.core import MissionResult
from maios.distributed import DistributedRuntime
from maios.kernel.executive_brain import DecisionContext, ExecutiveBrain, PlannerType
from maios.reflection import ImprovementReport
from maios.runtime.models import Mission, QAResult, Status
from maios.runtime.plan import Plan


@dataclass
class FakeCore:
    calls: list[str]

    def run(self, goal: str) -> MissionResult:
        self.calls.append(goal)
        mission = Mission(title=goal, objective=goal, status=Status.COMPLETED)
        return MissionResult(
            goal=goal,
            mission=mission,
            plan=Plan(objective=goal),
            memory_context={},
            model_output="ok",
            task_outputs=["ok"],
            execution_result={"status": "EXECUTED"},
            qa_result=QAResult(status=Status.COMPLETED, score=100),
            reflection_report=None,
            final_output="ok",
            status=Status.COMPLETED,
            knowledge_count=0,
        )


class SwarmAgent(Agent):
    name = "swarm-agent"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": context["task"]}


class ResearchReport:
    def __init__(self, question: str) -> None:
        self.question = question

    def to_dict(self) -> dict[str, str]:
        return {"question": self.question}


class ResearchEngineSpy:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def run(self, question: str) -> ResearchReport:
        self.questions.append(question)
        return ResearchReport(question)


def test_executive_brain_executes_distributed_runtime():
    calls: list[str] = []
    runtime = DistributedRuntime()
    runtime.register_node("node-a", core=FakeCore(calls))
    brain = ExecutiveBrain(distributed_runtime=runtime)
    context = DecisionContext("Remote mission")

    decision = brain.execute(context)

    assert decision.selected_planner == PlannerType.DISTRIBUTED
    assert decision.status == "COMPLETED"
    assert decision.outcome["assigned_node"] == "node-a"
    assert calls == ["Remote mission"]


def test_executive_brain_executes_research_engine():
    research = ResearchEngineSpy()
    brain = ExecutiveBrain(research_engine=research)
    context = DecisionContext("Find evidence", requested_capabilities=("research",))

    decision = brain.execute(context)

    assert decision.selected_planner == PlannerType.RESEARCH
    assert decision.outcome["report"] == {"question": "Find evidence"}
    assert research.questions == ["Find evidence"]


def test_executive_brain_executes_swarm_manager():
    runtime = DistributedRuntime()
    runtime.register_agent(
        SwarmAgent(),
        [AgentCapability("execute")],
        agent_id="agent-1",
    )
    brain = ExecutiveBrain(swarm_manager=runtime.swarm_manager)
    context = DecisionContext("Swarm task", requested_capabilities=("execute",))

    decision = brain.execute(context)

    assert decision.selected_planner == PlannerType.SWARM
    assert decision.outcome["status"] == "COMPLETED"
    assert decision.outcome["swarm_id"].startswith("SWARM-")


def test_executive_brain_direct_execution_preserves_basic_operation():
    decision = ExecutiveBrain().execute(DecisionContext("Direct task"))

    assert decision.selected_planner == PlannerType.DIRECT
    assert decision.outcome["output"] == "Direct task"


def test_executive_brain_record_outcome_triggers_reflection_after_repeated_failures():
    brain = ExecutiveBrain(failure_threshold=2)
    context = DecisionContext("Unstable mission")

    assert brain.record_outcome(context, {"status": "FAILED", "error": "timeout"}) is None
    report = brain.record_outcome(context, {"status": "FAILED", "error": "timeout"})

    assert isinstance(report, ImprovementReport)
    assert report.mission_id == context.mission_id
    assert "timeout" in report.bottlenecks
