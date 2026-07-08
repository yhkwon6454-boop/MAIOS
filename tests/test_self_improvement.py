from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry
from maios.agents.swarm import SwarmManager
from maios.distributed import DistributedRuntime
from maios.reflection import SelfImprovementEngine
from maios.research import InMemorySourceCollector, ResearchEngine, ResearchSource


class ImprovementAgent(Agent):
    name = "improver"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": "ok"}


def test_self_improvement_analyzes_completed_research_task():
    research_engine = ResearchEngine(
        source_collector=InMemorySourceCollector(
            [ResearchSource(title="Evidence", content="Evidence supports the finding.")]
        )
    )
    report = research_engine.run("Evidence")
    task = next(iter(research_engine.tasks.values()))
    engine = SelfImprovementEngine(research_engine=research_engine)

    record = engine.analyze_research_task(task, report=report)
    plan = engine.improve_from_research(task, report)

    assert record.status == "COMPLETED"
    assert record.metrics["finding_count"] > 0
    assert plan.target == task.question
    assert plan.priority == "medium"


def test_self_improvement_detects_research_failures_and_bottlenecks():
    research_engine = ResearchEngine(source_collector=InMemorySourceCollector([]))
    task = research_engine.define_question("Missing evidence")
    research_engine.decompose(task)
    research_engine.collect_sources(task)
    research_engine.summarize_findings(task)
    research_engine.identify_gaps(task)
    engine = SelfImprovementEngine()

    record = engine.analyze_research_task(task)

    assert record.status == "FAILED"
    assert "No findings were generated." in record.failures
    assert "No sources were collected." in record.bottlenecks


def test_self_improvement_analyzes_execution_history_and_runtime_integration():
    runtime = DistributedRuntime()
    runtime.scheduler.submit("queued")
    mission = runtime.run_next()
    assert mission.status == "FAILED"

    plan = runtime.improve_runtime()

    assert plan.target == "distributed_runtime"
    assert plan.priority == "high"
    assert runtime.self_improvement_engine.records[-1].source_type == "execution"


def test_self_improvement_integrates_with_swarm_manager():
    registry = AgentRegistry()
    registry.register(
        ImprovementAgent(),
        [AgentCapability("improve")],
        agent_id="improver-1",
    )
    swarm_manager = SwarmManager(registry=registry)
    swarm = swarm_manager.form_swarm("improvement swarm", ["improve"])
    engine = SelfImprovementEngine(swarm_manager=swarm_manager)

    record = engine.analyze_execution_history(
        [{"status": "COMPLETED", "active_tasks": len(swarm.members)}]
    )

    assert record.status == "COMPLETED"
    assert engine.swarm_manager is swarm_manager
