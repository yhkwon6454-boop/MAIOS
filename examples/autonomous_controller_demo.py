from __future__ import annotations

from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents import RuntimeOrchestrator
from maios.autonomous import AutonomousController, SafetyManager


class DemoClient:
    def generate(self, prompt):
        return "autonomous controller demo output"


def main() -> None:
    orchestrator = RuntimeOrchestrator(gpt_adapter=GPTAdapter(DemoClient()))
    controller = AutonomousController(
        runtime_orchestrator=orchestrator,
        safety_manager=SafetyManager.with_blocked_keywords(["forbidden"]),
        mode="autonomous",
    )

    decision = controller.run_once(
        {
            "goal": "Evaluate the current MAIOS autonomous controller loop.",
            "source": "demo",
        }
    )
    print(f"{decision.decision_id}: {decision.status}")
    if decision.result is not None:
        print(decision.result.final_output)


if __name__ == "__main__":
    main()
