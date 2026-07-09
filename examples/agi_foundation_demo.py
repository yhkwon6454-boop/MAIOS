"""End-to-end AGI Foundation demo.

Runs the full MAIOS stack from one entry point:
governance gate -> cognitive loop (observe -> understand -> plan -> act ->
reflect -> learn) -> goal pursuit record -> evolution report.
"""

from __future__ import annotations

from maios.governance import GovernanceManager
from maios.kernel.agi_foundation import AGIFoundation
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.graph import KnowledgeGraph


def main() -> None:
    agi = AGIFoundation(
        knowledge_graph=KnowledgeGraph(),
        memory_kernel=MemoryKernel(),
        governance=GovernanceManager(),
    )

    model = agi.introspect()
    print(f"identity={model.identity} readiness={model.readiness:.2f}")
    print(f"available layers: {', '.join(model.available())}")

    pursuit = agi.pursue("Summarize the weekly operations report")
    print(f"\npursuit status: {pursuit.status}")
    for cycle in agi.cognitive_loop.cycles:
        print(f"  cycle {cycle.cycle_id}: {' -> '.join(cycle.phase_order())}")

    blocked = agi.pursue("Deploy the new build to production")
    print(f"\nhigh-risk pursuit without approval: {blocked.status}")

    approved = agi.pursue("Deploy the new build to production", human_approved=True)
    print(f"high-risk pursuit with approval: {approved.status}")

    report = agi.evolve()
    print(
        f"\nevolution: pursuits={report['pursuits']} "
        f"success_rate={report['success_rate']} readiness={report['readiness']:.2f}"
    )


if __name__ == "__main__":
    main()
