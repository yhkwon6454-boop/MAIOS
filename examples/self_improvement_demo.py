from __future__ import annotations

from maios.reflection import SelfImprovementEngine
from maios.research import InMemorySourceCollector, ResearchEngine, ResearchSource


def main() -> None:
    research_engine = ResearchEngine(
        source_collector=InMemorySourceCollector(
            [
                ResearchSource(
                    title="Agent evaluation",
                    content="Self-improvement depends on measuring failures and bottlenecks.",
                )
            ]
        )
    )
    report = research_engine.run("agent self improvement")
    task = next(iter(research_engine.tasks.values()))

    engine = SelfImprovementEngine(research_engine=research_engine)
    plan = engine.improve_from_research(task, report)
    evolved_prompt = engine.evolve_prompt(
        "Summarize research findings with evidence.",
        plan,
    )

    print(plan.to_markdown())
    print()
    print(evolved_prompt)


if __name__ == "__main__":
    main()
