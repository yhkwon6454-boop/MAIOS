from dataclasses import dataclass

from maios.core import MAIOSCore, MissionResult
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.mesh import (
    CognitiveMesh,
    ConsensusEngine,
    InMemoryMeshTransport,
    KnowledgeSynchronizer,
    MeshNode,
    PlanningProposal,
)
from maios.reflection import ImprovementReport
from maios.runtime.models import Mission, QAResult, Status
from maios.runtime.plan import Plan


@dataclass
class FakeCore:
    node_id: str
    knowledge_store: KnowledgeStore
    memory_kernel: MemoryKernel
    calls: list[str]

    @classmethod
    def build(cls, node_id: str, calls: list[str] | None = None):
        store = KnowledgeStore()
        memory = MemoryKernel(knowledge_store=store)
        return cls(node_id, store, memory, calls if calls is not None else [])

    def run(self, goal: str) -> MissionResult:
        self.calls.append(f"{self.node_id}:{goal}")
        mission = Mission(title=goal, objective=goal, status=Status.COMPLETED)
        return MissionResult(
            goal=goal,
            mission=mission,
            plan=Plan(objective=goal, tasks=[f"{self.node_id} task"]),
            memory_context={},
            model_output=f"{self.node_id} output",
            task_outputs=[f"{self.node_id} task output"],
            execution_result={"status": "EXECUTED"},
            qa_result=QAResult(status=Status.COMPLETED, score=100),
            reflection_report=ImprovementReport(
                mission_id=mission.mission_id,
                success=True,
                score=100,
                summary="ok",
            ),
            final_output=f"{self.node_id}:{goal}",
            status=Status.COMPLETED,
            knowledge_count=self.knowledge_store.count(),
        )


def test_knowledge_synchronizer_copies_memory_and_knowledge():
    source_store = KnowledgeStore()
    target_store = KnowledgeStore()
    source_memory = MemoryKernel(knowledge_store=source_store)
    target_memory = MemoryKernel(knowledge_store=target_store)
    source_memory.remember_short_term("short term mesh fact")
    source_memory.remember_conversation("user", "mesh question")
    document = source_memory.remember_long_term("long term mesh fact", {"node": "a"})
    synchronizer = KnowledgeSynchronizer()

    synchronizer.sync_memory(source_memory, target_memory)
    synchronizer.sync_knowledge(source_store, target_store)

    assert target_memory.session_memory == ["short term mesh fact"]
    assert target_memory.conversation_history == [{"role": "user", "content": "mesh question"}]
    assert target_memory.long_term_memory == [document]
    assert target_store.get(document.document_id).content == "long term mesh fact"


def test_in_memory_mesh_transport_proposes_plan_and_executes_node():
    calls = []
    core = FakeCore.build("node-a", calls)
    transport = InMemoryMeshTransport()
    transport.register_node(MeshNode("node-a", core))

    proposal = transport.propose_plan("node-a", "collaborate")
    result = transport.execute("node-a", "collaborate")

    assert proposal.node_id == "node-a"
    assert proposal.decision == "APPROVE"
    assert proposal.plan.objective == "collaborate"
    assert result.final_output == "node-a:collaborate"
    assert calls == ["node-a:collaborate"]


def test_consensus_engine_uses_majority_vote():
    proposals = [
        PlanningProposal("a", Plan("goal", tasks=["a"]), "APPROVE", 0.6),
        PlanningProposal("b", Plan("goal", tasks=["b"]), "REJECT", 1.0),
        PlanningProposal("c", Plan("goal", tasks=["c"]), "APPROVE", 0.5),
    ]

    result = ConsensusEngine().decide("mission", proposals)

    assert result.accepted
    assert result.decision == "APPROVE"
    assert result.votes == {"APPROVE": 2, "REJECT": 1}
    assert result.selected_node == "a"


def test_consensus_engine_rejects_empty_proposals():
    result = ConsensusEngine().decide("mission", [])

    assert not result.accepted
    assert result.decision == "REJECT"
    assert result.selected_plan is None


def test_cognitive_mesh_registers_nodes_and_syncs_memory_and_knowledge():
    mesh = CognitiveMesh()
    node_a = mesh.register_node("node-a", core=FakeCore.build("node-a"))
    node_b = mesh.register_node("node-b", core=FakeCore.build("node-b"))
    document = node_a.core.memory_kernel.remember_long_term("shared knowledge")
    node_a.core.memory_kernel.remember_short_term("shared memory")

    mesh.synchronize(source_node_id="node-a")

    assert node_b.core.memory_kernel.session_memory == ["shared memory"]
    assert node_b.core.knowledge_store.get(document.document_id).content == "shared knowledge"
    assert mesh.memory_status() == {"node-a": 1, "node-b": 1}
    assert mesh.knowledge_status() == {"node-a": 1, "node-b": 1}


def test_cognitive_mesh_collects_collaborative_plans_from_healthy_nodes():
    mesh = CognitiveMesh()
    mesh.register_node("node-a", core=FakeCore.build("node-a"))
    mesh.register_node("node-b", core=FakeCore.build("node-b"))

    proposals = mesh.collaborative_plan("plan together")

    assert [proposal.node_id for proposal in proposals] == ["node-a", "node-b"]
    assert all(proposal.decision == "APPROVE" for proposal in proposals)


def test_cognitive_mesh_executes_consensus_selected_node_and_syncs_afterward():
    calls = []
    mesh = CognitiveMesh()
    node_a = mesh.register_node("node-a", core=FakeCore.build("node-a", calls))
    node_b = mesh.register_node("node-b", core=FakeCore.build("node-b", calls))
    node_a.core.memory_kernel.remember_long_term("pre mission knowledge")

    result = mesh.execute_mission("mesh goal")

    assert result.final_output == "node-a:mesh goal"
    assert calls == ["node-a:mesh goal"]
    assert mesh.consensus_history[-1].accepted
    assert node_b.core.knowledge_store.count() == node_a.core.knowledge_store.count()


def test_cognitive_mesh_rejects_mission_when_consensus_rejects():
    class RejectingTransport(InMemoryMeshTransport):
        def propose_plan(self, node_id: str, goal: str) -> PlanningProposal:
            return PlanningProposal(node_id, Plan(goal), "REJECT", 1.0)

    mesh = CognitiveMesh(transport=RejectingTransport())
    mesh.register_node("node-a", core=FakeCore.build("node-a"))

    try:
        mesh.execute_mission("rejected")
    except RuntimeError as exc:
        assert "consensus rejected" in str(exc)
    else:
        raise AssertionError("Expected consensus rejection to fail.")
