from dataclasses import dataclass

from maios.autonomous import AutonomousController
from maios.governance import (
    AuditLog,
    GovernanceManager,
    PermissionModel,
    PolicyEngine,
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
        )


def test_permission_model_allows_and_revokes_actions():
    permissions = PermissionModel({"agent": ["READ"]})

    assert permissions.is_allowed("agent", "READ")
    assert not permissions.is_allowed("agent", "EXECUTE_MISSION")

    permissions.allow("agent", "EXECUTE_MISSION")
    assert permissions.is_allowed("agent", "EXECUTE_MISSION")

    permissions.revoke("agent", "EXECUTE_MISSION")
    assert not permissions.is_allowed("agent", "EXECUTE_MISSION")


def test_policy_engine_classifies_risk_from_context_and_goal():
    engine = PolicyEngine()

    assert engine.classify_risk("read local memory") == "LOW"
    assert engine.classify_risk("commit generated code") == "MEDIUM"
    assert engine.classify_risk("deploy to production") == "HIGH"
    assert engine.classify_risk("anything", {"risk": "HIGH"}) == "HIGH"


def test_policy_engine_blocks_missing_permission():
    engine = PolicyEngine(permission_model=PermissionModel({"other": ["EXECUTE_MISSION"]}))

    decision = engine.evaluate("run mission", "EXECUTE_MISSION", "autonomous_controller")

    assert not decision.approved
    assert decision.risk_level == "LOW"
    assert "not allowed" in decision.reason
    assert decision.policy_checks[0].name == "permission"


def test_governance_manager_persists_policy_checks(tmp_path):
    audit_path = tmp_path / "audit.json"
    manager = GovernanceManager(
        policy_engine=PolicyEngine(blocked_keywords=["blocked"]),
        audit_log=AuditLog(audit_path),
    )

    decision = manager.evaluate("run blocked task", "EXECUTE_MISSION")
    reloaded = AuditLog(audit_path)

    assert not decision.approved
    assert "blocked keyword" in decision.reason
    assert reloaded.serialized_entries()[0]["event_type"] == "policy_check"
    assert reloaded.serialized_entries()[0]["payload"]["goal"] == "run blocked task"


def test_high_risk_governance_requires_human_approval_gate():
    manager = GovernanceManager(policy_engine=PolicyEngine())

    decision = manager.evaluate("deploy to production", "EXECUTE_MISSION")

    assert not decision.approved
    assert decision.requires_human_approval
    assert decision.risk_level == "HIGH"

    approved = manager.approve(decision)
    assert approved.approved
    assert not approved.requires_human_approval


def test_autonomous_controller_uses_governance_for_low_risk_execution():
    orchestrator = FakeRuntimeOrchestrator()
    governance = GovernanceManager(policy_engine=PolicyEngine())
    controller = AutonomousController(
        runtime_orchestrator=orchestrator,
        governance_manager=governance,
    )

    decision = controller.run_once({"goal": "summarize local context"})

    assert decision.status == "COMPLETED"
    assert decision.risk_level == "LOW"
    assert decision.policy_checks
    assert orchestrator.calls == ["summarize local context"]
    assert [entry.event_type for entry in governance.history()] == [
        "policy_check",
        "autonomous_decision",
        "autonomous_decision",
    ]


def test_autonomous_controller_holds_high_risk_governance_decision_for_approval():
    orchestrator = FakeRuntimeOrchestrator()
    controller = AutonomousController(
        runtime_orchestrator=orchestrator,
        governance_manager=GovernanceManager(policy_engine=PolicyEngine()),
    )

    decision = controller.run_once({"goal": "deploy to production", "risk": "HIGH"})

    assert decision.status == "PENDING_APPROVAL"
    assert decision.risk_level == "HIGH"
    assert "requires human approval" in decision.reason
    assert orchestrator.calls == []

    approved = controller.approve(decision.decision_id)
    assert approved.status == "COMPLETED"
    assert orchestrator.calls == ["deploy to production"]


def test_governance_audit_log_records_controller_decisions_to_disk(tmp_path):
    audit_path = tmp_path / "governance_audit.json"
    governance = GovernanceManager(audit_log=AuditLog(audit_path))
    controller = AutonomousController(
        runtime_orchestrator=FakeRuntimeOrchestrator(),
        governance_manager=governance,
    )

    decision = controller.run_once({"goal": "persist governed decision"})
    reloaded = AuditLog(audit_path)
    event_types = [entry["event_type"] for entry in reloaded.serialized_entries()]

    assert decision.status == "COMPLETED"
    assert event_types == [
        "policy_check",
        "autonomous_decision",
        "autonomous_decision",
    ]
