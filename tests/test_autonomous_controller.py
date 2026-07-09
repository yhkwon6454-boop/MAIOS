from dataclasses import dataclass

from maios.autonomous import (
    AutonomousController,
    DecisionHistoryStore,
    SafetyManager,
)
from maios.reflection import ImprovementReport
from maios.runtime.models import Mission, QAResult, Status
from maios.runtime.plan import Plan


@dataclass
class FakeRuntimeResult:
    mission: Mission
    plan: Plan
    final_output: str
    qa_result: QAResult
    reflection_report: ImprovementReport | None = None


class FakeRuntimeOrchestrator:
    def __init__(self):
        self.calls = []
        self.reflection_engine = None

    def run(self, mission: Mission):
        self.calls.append(mission.objective)
        mission.status = Status.COMPLETED
        return FakeRuntimeResult(
            mission=mission,
            plan=Plan(objective=mission.objective, tasks=["execute"]),
            final_output=f"executed:{mission.objective}",
            qa_result=QAResult(status=Status.COMPLETED, score=100),
            reflection_report=ImprovementReport(
                mission_id=mission.mission_id,
                success=True,
                score=100,
                summary="ok",
            ),
        )


def test_autonomous_controller_runs_observe_orient_decide_act_cycle():
    orchestrator = FakeRuntimeOrchestrator()
    controller = AutonomousController(runtime_orchestrator=orchestrator)

    decision = controller.run_once({"goal": "run autonomous loop", "source": "test"})

    assert decision.status == "COMPLETED"
    assert decision.approved
    assert decision.result.final_output == "executed:run autonomous loop"
    assert orchestrator.calls == ["run autonomous loop"]
    assert [item.decision_id for item in controller.history()] == [decision.decision_id]


def test_controller_generates_goals_from_reflection_context():
    report = ImprovementReport(
        mission_id="M-1",
        success=False,
        score=60,
        summary="needs work",
        improvement_points=["tighten planning"],
    )
    controller = AutonomousController(runtime_orchestrator=FakeRuntimeOrchestrator())

    goals = controller.generate_goals({"reflection": report})

    assert goals == ["Improve future missions: tighten planning"]


def test_safety_manager_blocks_configured_keywords():
    controller = AutonomousController(
        runtime_orchestrator=FakeRuntimeOrchestrator(),
        safety_manager=SafetyManager.with_blocked_keywords(["blocked"]),
    )

    decision = controller.run_once({"goal": "run blocked operation"})

    assert decision.status == "PENDING_APPROVAL"
    assert not decision.approved
    assert "blocked keyword" in decision.reason
    assert controller.runtime_orchestrator.calls == []


def test_human_approval_mode_waits_until_approved():
    orchestrator = FakeRuntimeOrchestrator()
    controller = AutonomousController(
        runtime_orchestrator=orchestrator,
        mode="human_approval",
    )

    decision = controller.run_once({"goal": "requires approval"})

    assert decision.status == "PENDING_APPROVAL"
    assert orchestrator.calls == []

    approved = controller.approve(decision.decision_id)

    assert approved.status == "COMPLETED"
    assert approved.result.final_output == "executed:requires approval"
    assert orchestrator.calls == ["requires approval"]


def test_decision_history_persists_to_json(tmp_path):
    path = tmp_path / "decisions.json"
    controller = AutonomousController(
        runtime_orchestrator=FakeRuntimeOrchestrator(),
        decision_history=DecisionHistoryStore(path),
    )

    decision = controller.run_once({"goal": "persist decision"})
    reloaded = DecisionHistoryStore(path)

    assert decision.status == "COMPLETED"
    assert reloaded.serialized_history()[0]["decision_id"] == decision.decision_id
    assert reloaded.serialized_history()[0]["result"]["final_output"] == "executed:persist decision"


def test_run_loop_processes_contexts_up_to_cycle_limit():
    orchestrator = FakeRuntimeOrchestrator()
    controller = AutonomousController(runtime_orchestrator=orchestrator)

    decisions = controller.run_loop(
        [
            {"goal": "first"},
            {"goal": "second"},
            {"goal": "third"},
        ],
        max_cycles=2,
    )

    assert [decision.goal for decision in decisions] == ["first", "second"]
    assert orchestrator.calls == ["first", "second"]


def test_controller_skips_when_no_goal_can_be_generated():
    controller = AutonomousController(runtime_orchestrator=FakeRuntimeOrchestrator())

    decision = controller.run_once({"source": "empty"})

    assert decision.status == "SKIPPED"
    assert decision.action == "NOOP"
    assert not decision.approved
