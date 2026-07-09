from __future__ import annotations

from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents import RuntimeOrchestrator
from maios.autonomous import AutonomousController
from maios.governance import AuditLog, GovernanceManager, PolicyEngine


class DemoClient:
    def generate(self, prompt):
        return "governance demo output"


def main() -> None:
    governance = GovernanceManager(
        policy_engine=PolicyEngine(blocked_keywords=["forbidden"]),
        audit_log=AuditLog("outputs/governance_audit.json"),
    )
    controller = AutonomousController(
        runtime_orchestrator=RuntimeOrchestrator(gpt_adapter=GPTAdapter(DemoClient())),
        governance_manager=governance,
    )

    decision = controller.run_once(
        {
            "goal": "Review production deployment readiness.",
            "risk": "HIGH",
        }
    )
    print(f"{decision.decision_id}: {decision.status} ({decision.reason})")

    if decision.status == "PENDING_APPROVAL":
        approved = controller.approve(decision.decision_id)
        print(f"{approved.decision_id}: {approved.status}")


if __name__ == "__main__":
    main()
