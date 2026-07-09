from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry
from maios.agents.swarm import SwarmManager
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge import KnowledgeGraph, KnowledgeStore
from maios.reflection import ImprovementReport, ReflectionEngine, SelfImprovementEngine
from maios.research import InMemorySourceCollector, ResearchEngine, ResearchSource


class GraphAgent(Agent):
    name = "graph-agent"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": f"handled:{context.get('task')}"}


def test_knowledge_graph_persists_nodes_edges_and_clusters(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.json")
    planning = graph.add_node("Agent Planning", "Agents decompose goals into tasks.")
    memory = graph.add_node("Agent Memory", "Memory stores task evidence for agents.")
    graph.add_edge(memory.node_id, planning.node_id, "supports", weight=0.7)
    graph.build_clusters(min_similarity=0.1)

    loaded = KnowledgeGraph(tmp_path / "graph.json")

    assert loaded.get_node(planning.node_id) == planning
    assert loaded.edges_for(memory.node_id, ["supports"], direction="out")[0].target_id == (
        planning.node_id
    )
    assert loaded.clusters


def test_knowledge_graph_merges_duplicate_knowledge():
    graph = KnowledgeGraph()
    first = graph.add_node("Planner", "Planning decomposes work into subtasks.")
    duplicate = graph.add_node("Planner", "Planning decomposes work into subtasks with memory.")

    assert duplicate.node_id == first.node_id
    assert len(graph.nodes) == 1
    assert "with memory" in first.content


def test_knowledge_graph_explicit_merge_rewires_edges():
    graph = KnowledgeGraph()
    target = graph.add_node("Target", "Runtime scheduling target concept.")
    first = graph.add_node(
        "Scheduling A",
        "Runtime scheduling balances agent task load.",
        merge_duplicates=False,
    )
    duplicate = graph.add_node(
        "Scheduling B",
        "Runtime scheduling balances agent task load.",
        merge_duplicates=False,
    )
    graph.add_edge(duplicate.node_id, target.node_id, "supports")
    graph.add_edge(target.node_id, duplicate.node_id, "depends_on")

    merged = graph.merge_duplicates(threshold=0.8)

    assert merged == [first]
    assert duplicate.node_id not in graph.nodes
    assert graph.edges_for(first.node_id, direction="out")[0].target_id == target.node_id
    assert graph.edges_for(first.node_id, direction="in")[0].source_id == target.node_id


def test_knowledge_graph_integrates_with_store_memory_and_reflection():
    store = KnowledgeStore()
    memory = MemoryKernel(knowledge_store=store)
    graph = KnowledgeGraph(knowledge_store=store, memory_kernel=memory)
    reflection = ReflectionEngine(store, knowledge_graph=graph)

    node = graph.add_node("Long-term Memory", "Persistent graph memory supports retrieval.")
    reflection.store(
        ImprovementReport(
            mission_id="mission-1",
            success=True,
            score=95,
            summary="Reflection improves graph memory.",
        )
    )

    assert store.exists(node.node_id)
    assert any(item.metadata["node_id"] == node.node_id for item in memory.long_term_memory)
    assert graph.semantic_search("reflection graph memory")[0].node_type == "reflection"


def test_knowledge_graph_integrates_with_research_self_improvement_and_swarm():
    graph = KnowledgeGraph(auto_link_threshold=0.1)
    collector = InMemorySourceCollector(
        [ResearchSource(title="Swarm Research", content="Swarm agents collect evidence.")]
    )
    research = ResearchEngine(source_collector=collector, knowledge_graph=graph)
    report = research.run("Swarm agents")
    task = next(iter(research.tasks.values()))
    improver = SelfImprovementEngine(research_engine=research, knowledge_graph=graph)
    plan = improver.improve_from_research(task, report)
    registry = AgentRegistry()
    registry.register(GraphAgent(), [AgentCapability("research")], agent_id="agent-1")
    swarm = SwarmManager(registry=registry, knowledge_graph=graph).form_swarm(
        "research swarm",
        ["research"],
    )

    assert graph.get_node(report.report_id) is not None
    assert graph.get_node(plan.plan_id) is not None
    assert graph.get_node(swarm.swarm_id) is not None
    assert graph.semantic_search("Swarm agents")
