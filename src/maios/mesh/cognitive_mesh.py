from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from maios.agents.planner_agent import PlannerAgent
from maios.core import MAIOSCore, MissionResult
from maios.distributed import DistributedRuntime, Node
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.retrieval import Document
from maios.runtime.models import Mission
from maios.runtime.plan import Plan


@dataclass
class MeshNode:
    node_id: str
    core: MAIOSCore
    address: str = "local"
    capacity: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningProposal:
    node_id: str
    plan: Plan
    decision: str
    confidence: float = 1.0
    rationale: str = ""


@dataclass
class ConsensusResult:
    mission_id: str
    decision: str
    accepted: bool
    selected_plan: Plan | None
    proposals: list[PlanningProposal]
    votes: dict[str, int]
    selected_node: str = ""


class MeshTransport(Protocol):
    def register_node(self, node: MeshNode) -> None: ...

    def execute(self, node_id: str, goal: str) -> MissionResult: ...

    def propose_plan(self, node_id: str, goal: str) -> PlanningProposal: ...

    def sync_memory(self, source_node_id: str, target_node_id: str) -> None: ...

    def sync_knowledge(self, source_node_id: str, target_node_id: str) -> None: ...


class KnowledgeSynchronizer:
    """Copies memory and knowledge records between local MAIOS node cores."""

    def sync_memory(self, source: MemoryKernel, target: MemoryKernel) -> None:
        for item in source.session_memory:
            if item not in target.session_memory:
                target.session_memory.append(item)

        existing_documents = {document.document_id for document in target.long_term_memory}
        for document in source.long_term_memory:
            if document.document_id not in existing_documents:
                target.long_term_memory.append(document)

        for message in source.conversation_history:
            if message not in target.conversation_history:
                target.conversation_history.append(message)

    def sync_knowledge(self, source: KnowledgeStore, target: KnowledgeStore) -> None:
        for document in self.export_documents(source):
            target.add(document)

    def export_documents(self, store: KnowledgeStore) -> list[Document]:
        documents = getattr(store, "_documents", {})
        return [
            Document(
                content=record.get("content", ""),
                metadata=record.get("metadata", {}),
                document_id=record.get("document_id", document_id),
            )
            for document_id, record in documents.items()
        ]


class ConsensusEngine:
    """Deterministic majority consensus for collaborative mission decisions."""

    def decide(
        self,
        mission_id: str,
        proposals: list[PlanningProposal],
    ) -> ConsensusResult:
        if not proposals:
            return ConsensusResult(
                mission_id=mission_id,
                decision="REJECT",
                accepted=False,
                selected_plan=None,
                proposals=[],
                votes={},
            )

        votes: dict[str, int] = {}
        for proposal in proposals:
            votes[proposal.decision] = votes.get(proposal.decision, 0) + 1

        selected = sorted(
            proposals,
            key=lambda proposal: (
                -votes[proposal.decision],
                -proposal.confidence,
                proposal.node_id,
            ),
        )[0]

        return ConsensusResult(
            mission_id=mission_id,
            decision=selected.decision,
            accepted=selected.decision == "APPROVE",
            selected_plan=selected.plan,
            proposals=proposals,
            votes=votes,
            selected_node=selected.node_id,
        )


class InMemoryMeshTransport:
    """In-process mesh transport used by tests and local examples."""

    def __init__(
        self,
        synchronizer: KnowledgeSynchronizer | None = None,
    ) -> None:
        self.nodes: dict[str, MeshNode] = {}
        self.synchronizer = synchronizer or KnowledgeSynchronizer()

    def register_node(self, node: MeshNode) -> None:
        self.nodes[node.node_id] = node

    def execute(self, node_id: str, goal: str) -> MissionResult:
        return self.nodes[node_id].core.run(goal)

    def propose_plan(self, node_id: str, goal: str) -> PlanningProposal:
        core = self.nodes[node_id].core
        mission = Mission(title=goal.strip() or "Untitled Goal", objective=goal.strip())
        planner_agent = getattr(getattr(core, "orchestrator", None), "planner_agent", None)
        planner_agent = planner_agent or PlannerAgent()
        context = planner_agent.execute({"mission": mission, "trace": []})
        plan = context["execution_plan"]
        decision = "APPROVE" if plan.tasks else "REJECT"
        confidence = min(1.0, max(0.1, len(plan.tasks) / 5))
        return PlanningProposal(
            node_id=node_id,
            plan=plan,
            decision=decision,
            confidence=confidence,
            rationale=f"{node_id} proposed {len(plan.tasks)} tasks.",
        )

    def sync_memory(self, source_node_id: str, target_node_id: str) -> None:
        source = self.nodes[source_node_id].core.memory_kernel
        target = self.nodes[target_node_id].core.memory_kernel
        self.synchronizer.sync_memory(source, target)

    def sync_knowledge(self, source_node_id: str, target_node_id: str) -> None:
        source = self.nodes[source_node_id].core.knowledge_store
        target = self.nodes[target_node_id].core.knowledge_store
        self.synchronizer.sync_knowledge(source, target)


class CognitiveMesh:
    """Collaborative reasoning network for multiple MAIOS nodes."""

    def __init__(
        self,
        distributed_runtime: DistributedRuntime | None = None,
        transport: MeshTransport | None = None,
        consensus_engine: ConsensusEngine | None = None,
    ) -> None:
        self.distributed_runtime = distributed_runtime or DistributedRuntime()
        self.transport = transport or InMemoryMeshTransport()
        self.consensus_engine = consensus_engine or ConsensusEngine()
        self.nodes: dict[str, MeshNode] = {}
        self.consensus_history: list[ConsensusResult] = []

    def register_node(
        self,
        node_id: str,
        core: MAIOSCore | None = None,
        address: str = "local",
        capacity: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> MeshNode:
        mesh_node = MeshNode(
            node_id=node_id,
            core=core or MAIOSCore(),
            address=address,
            capacity=capacity,
            metadata=metadata or {},
        )
        self.nodes[node_id] = mesh_node
        self.transport.register_node(mesh_node)
        self.distributed_runtime.register_node(
            node_id=node_id,
            core=mesh_node.core,
            address=address,
            capacity=capacity,
            metadata=metadata,
        )
        return mesh_node

    def heartbeat(self, node_id: str) -> Node:
        return self.distributed_runtime.heartbeat(node_id)

    def sync_memory(self, source_node_id: str | None = None) -> None:
        pairs = self._sync_pairs(source_node_id)
        for source, target in pairs:
            self.transport.sync_memory(source, target)

    def sync_knowledge(self, source_node_id: str | None = None) -> None:
        pairs = self._sync_pairs(source_node_id)
        for source, target in pairs:
            self.transport.sync_knowledge(source, target)

    def synchronize(self, source_node_id: str | None = None) -> None:
        self.sync_memory(source_node_id)
        self.sync_knowledge(source_node_id)

    def collaborative_plan(self, goal: str) -> list[PlanningProposal]:
        return [self.transport.propose_plan(node_id, goal) for node_id in self._healthy_node_ids()]

    def reach_consensus(self, goal: str) -> ConsensusResult:
        mission_id = f"CM-{uuid4().hex[:8]}"
        proposals = self.collaborative_plan(goal)
        result = self.consensus_engine.decide(mission_id, proposals)
        self.consensus_history.append(result)
        return result

    def execute_mission(self, goal: str) -> MissionResult:
        self.synchronize()
        consensus = self.reach_consensus(goal)
        if not consensus.accepted:
            raise RuntimeError("Cognitive mesh consensus rejected the mission.")

        node_id = consensus.selected_node or self._healthy_node_ids()[0]
        result = self.transport.execute(node_id, goal)
        self.synchronize(source_node_id=node_id)
        return result

    def knowledge_status(self) -> dict[str, int]:
        return {node_id: node.core.knowledge_store.count() for node_id, node in self.nodes.items()}

    def memory_status(self) -> dict[str, int]:
        return {
            node_id: len(node.core.memory_kernel.session_memory)
            for node_id, node in self.nodes.items()
        }

    def _healthy_node_ids(self) -> list[str]:
        health = self.distributed_runtime.health()
        return [node_id for node_id in self.nodes if health.get(node_id, False)]

    def _sync_pairs(self, source_node_id: str | None = None) -> list[tuple[str, str]]:
        node_ids = list(self.nodes)
        if source_node_id is not None:
            return [
                (source_node_id, target_node_id)
                for target_node_id in node_ids
                if target_node_id != source_node_id
            ]

        return [
            (source_node_id, target_node_id)
            for source_node_id in node_ids
            for target_node_id in node_ids
            if source_node_id != target_node_id
        ]
