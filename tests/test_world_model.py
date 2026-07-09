from __future__ import annotations

from maios.kernel import DecisionContext, ExecutiveBrain, SystemState, WorldModel
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge import KnowledgeGraph


def test_world_model_persists_state_to_knowledge_graph_and_memory():
    graph = KnowledgeGraph()
    memory = MemoryKernel()
    world = WorldModel(
        system=SystemState(healthy_nodes=1),
        knowledge_graph=graph,
        memory_kernel=memory,
    )

    world.persist()

    assert graph.get_node(world.state_id) is not None
    assert memory.retrieve_short_term("world_state")
    assert memory.retrieve("world_state")


def test_world_model_predict_returns_runtime_planner_and_agent_predictions():
    world = WorldModel(system=SystemState(healthy_nodes=1, active_agents=1))

    predictions = world.predict(("execute",))

    assert set(predictions) == {"runtime", "planner", "agent"}
    assert predictions["runtime"].outcome == "stable"


def test_world_model_from_runtime_uses_runtime_system_state():
    from maios.distributed import DistributedRuntime

    runtime = DistributedRuntime()
    runtime.register_node("node-a")

    world = WorldModel.from_runtime(runtime)

    assert world.system.healthy_nodes == 1


def test_executive_brain_builds_world_context_before_planner_selection():
    graph = KnowledgeGraph()
    memory = MemoryKernel()
    world = WorldModel(
        system=SystemState(healthy_nodes=1, active_agents=1),
        knowledge_graph=graph,
        memory_kernel=memory,
    )
    brain = ExecutiveBrain(world_model=world, knowledge_graph=graph)
    context = DecisionContext("Use world", requested_capabilities=("execute",))

    decision = brain.decide(context)

    assert decision.selected_planner == "direct"
    assert context.metadata["world_predictions"]["runtime"] == "stable"
    assert "world_context" in context.metadata
    assert memory.retrieve_short_term("world_context")


def test_executive_brain_transitions_world_model_after_outcome():
    world = WorldModel()
    brain = ExecutiveBrain(world_model=world)
    context = DecisionContext("Transition world")

    decision = brain.execute(context)

    assert decision.status == "COMPLETED"
    assert world.transitions[-1].event == "executive_outcome"
    assert world.user.intent_history[-1] == "Transition world"
