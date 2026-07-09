from __future__ import annotations

from typing import Any

from maios.agents import (
    Agent,
    AgentCapability,
    AgentRegistry,
    AgentRole,
    AgentRoleManager,
    NegotiationManager,
)
from maios.agents.swarm import SwarmManager
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.reflection import ReflectionEngine
from maios.research import InMemorySourceCollector, ResearchEngine, ResearchSource


class ResearchAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[str] = []

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        task = str(context.get("task"))
        self.calls.append(task)
        return {"output": f"{self.name}:{task}"}


def test_research_engine_runs_full_workflow_and_persists_artifacts():
    knowledge_store = KnowledgeStore()
    memory_kernel = MemoryKernel(knowledge_store=knowledge_store)
    reflection_engine = ReflectionEngine(knowledge_store)
    collector = InMemorySourceCollector(
        [
            ResearchSource(
                title="Planning",
                content="AI planning uses task decomposition and evaluation.",
            ),
            ResearchSource(
                title="Memory",
                content="Agent memory stores findings for future retrieval.",
            ),
        ]
    )
    engine = ResearchEngine(
        source_collector=collector,
        knowledge_store=knowledge_store,
        memory_kernel=memory_kernel,
        reflection_engine=reflection_engine,
    )

    report = engine.run("AI planning and memory")

    assert report.question == "AI planning and memory"
    assert report.findings
    assert report.report_id in engine.reports
    assert knowledge_store.exists(report.report_id)
    assert any(
        item.metadata.get("memory_type") == "research_report"
        for item in memory_kernel.long_term_memory
    )
    assert any(
        document.metadata.get("memory_type") == "reflection"
        for document in knowledge_store.search("Research completed", top_k=10)
    )


def test_research_engine_identifies_gaps_when_sources_are_missing():
    engine = ResearchEngine(source_collector=InMemorySourceCollector([]))
    task = engine.define_question("Sparse topic")

    engine.decompose(task)
    engine.collect_sources(task)
    engine.summarize_findings(task)
    gaps = engine.identify_gaps(task)

    assert "No research sources were collected." in gaps
    assert task.status == "GAPS_IDENTIFIED"


def test_research_engine_integrates_swarm_roles_and_negotiation():
    registry = AgentRegistry()
    agent = ResearchAgent("researcher")
    registry.register(agent, [AgentCapability("research")], agent_id="researcher-1")
    role_manager = AgentRoleManager(registry)
    role_manager.assign_role("researcher-1", AgentRole.SPECIALIST)
    negotiation_manager = NegotiationManager(role_manager=role_manager)
    swarm_manager = SwarmManager(
        registry=registry,
        role_manager=role_manager,
        negotiation_manager=negotiation_manager,
    )
    engine = ResearchEngine(
        source_collector=InMemorySourceCollector(
            [ResearchSource(title="Research", content="Research agents gather evidence.")]
        ),
        swarm_manager=swarm_manager,
        role_manager=role_manager,
        negotiation_manager=negotiation_manager,
    )

    report = engine.run("Research agents")

    assert report.findings
    assert agent.calls
    assert swarm_manager.swarms()
    assert negotiation_manager.sessions()
