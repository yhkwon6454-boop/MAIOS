from __future__ import annotations

from maios.research import InMemorySourceCollector, ResearchEngine, ResearchSource


def main() -> None:
    collector = InMemorySourceCollector(
        [
            ResearchSource(
                title="Agent coordination",
                content=(
                    "Multi-agent systems coordinate through roles, memory, " "and task allocation."
                ),
                url="https://example.test/coordination",
            ),
            ResearchSource(
                title="Research workflows",
                content="Autonomous research workflows decompose questions and summarize evidence.",
                url="https://example.test/research",
            ),
        ]
    )
    engine = ResearchEngine(source_collector=collector)
    report = engine.run("agent coordination and autonomous research workflows")

    print(report.to_markdown())


if __name__ == "__main__":
    main()
