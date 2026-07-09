from __future__ import annotations

from maios.kernel import DecisionContext, SystemState, WorldContextBuilder, WorldModel


def test_world_context_builder_combines_state_and_predictions():
    world = WorldModel(system=SystemState(healthy_nodes=1, active_agents=2))
    context = DecisionContext(
        "Investigate",
        mission_id="mission-1",
        requested_capabilities=("research",),
    )

    world_context = WorldContextBuilder().build(world, context)
    data = world_context.to_dict()

    assert world_context.objective == "Investigate"
    assert world_context.mission_id == "mission-1"
    assert {prediction.target for prediction in world_context.predictions} == {
        "runtime",
        "planner",
        "agent",
    }
    assert data["predictions"][1]["outcome"] == "research"


def test_world_model_build_context_persists_to_memory_and_graph():
    from maios.kernel.memory_kernel import MemoryKernel
    from maios.knowledge import KnowledgeGraph

    graph = KnowledgeGraph()
    memory = MemoryKernel()
    world = WorldModel(knowledge_graph=graph, memory_kernel=memory)
    context = DecisionContext("Build context", mission_id="mission-2")

    world_context = world.build_context(context)

    assert graph.get_node(world_context.context_id) is not None
    assert memory.retrieve_short_term("world_context")
