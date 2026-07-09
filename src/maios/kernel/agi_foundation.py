from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from maios.governance import GovernanceManager
from maios.kernel.cognitive_loop import CognitiveLoop
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.graph import KnowledgeGraph
from maios.planning import GoalHorizon, MetaGoal


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class SelfModel:
    identity: str
    version: str
    capabilities: dict[str, bool]
    readiness: float
    model_id: str = field(default_factory=lambda: f"SM-{uuid4().hex[:8]}")
    updated_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.readiness = max(0.0, min(1.0, float(self.readiness)))

    def available(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, ok in self.capabilities.items() if ok))

    def missing(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, ok in self.capabilities.items() if not ok))

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "identity": self.identity,
            "version": self.version,
            "capabilities": dict(self.capabilities),
            "readiness": self.readiness,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class GoalPursuit:
    objective: str
    goal_id: str
    status: str
    cycle_ids: tuple[str, ...] = ()
    lessons: tuple[str, ...] = ()
    governance: dict[str, Any] | None = None
    pursuit_id: str = field(default_factory=lambda: f"GP-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=_now)

    @property
    def success(self) -> bool:
        return self.status in {"COMPLETED", "SUCCESS"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "pursuit_id": self.pursuit_id,
            "objective": self.objective,
            "goal_id": self.goal_id,
            "status": self.status,
            "cycle_ids": list(self.cycle_ids),
            "lessons": list(self.lessons),
            "governance": dict(self.governance) if self.governance else None,
            "created_at": self.created_at,
        }


class AGIFoundation:
    """Unified autonomous core combining cognition, governance, and evolution."""

    def __init__(
        self,
        cognitive_loop: CognitiveLoop | None = None,
        governance: GovernanceManager | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        memory_kernel: MemoryKernel | None = None,
        runtime: Any | None = None,
        identity: str = "maios",
        version: str = "1.0.0",
        max_cycles: int = 3,
    ) -> None:
        self.cognitive_loop = cognitive_loop or CognitiveLoop(
            knowledge_graph=knowledge_graph,
            memory_kernel=memory_kernel,
            runtime=runtime,
        )
        self.knowledge_graph = knowledge_graph or self.cognitive_loop.knowledge_graph
        self.memory_kernel = memory_kernel or self.cognitive_loop.memory_kernel
        self.governance = governance
        self.identity = identity
        self.version = version
        self.max_cycles = max(1, max_cycles)
        self.goals: dict[str, MetaGoal] = {}
        self.pursuits: list[GoalPursuit] = []
        self.self_model: SelfModel | None = None
        if self.governance is not None:
            self.governance.policy_engine.permission_model.allow(self.identity, "PURSUE_GOAL")

    @property
    def executive_brain(self) -> Any:
        return self.cognitive_loop.executive_brain

    @property
    def world_model(self) -> Any:
        return self.cognitive_loop.world_model

    def introspect(self) -> SelfModel:
        brain = self.executive_brain
        capabilities = {
            "executive_brain": brain is not None,
            "world_model": self.world_model is not None,
            "cognitive_loop": self.cognitive_loop is not None,
            "meta_planner": brain.meta_planner is not None,
            "reflection": brain.reflection_engine is not None,
            "distributed_runtime": brain.distributed_runtime is not None,
            "research": brain.research_engine is not None,
            "negotiation": brain.negotiation_manager is not None,
            "swarm": brain.swarm_manager is not None,
            "self_improvement": brain.self_improvement_engine is not None,
            "knowledge_graph": self.knowledge_graph is not None,
            "memory": self.memory_kernel is not None,
            "governance": self.governance is not None,
        }
        readiness = sum(capabilities.values()) / len(capabilities)
        self.self_model = SelfModel(
            identity=self.identity,
            version=self.version,
            capabilities=capabilities,
            readiness=readiness,
        )
        self._persist_self_model(self.self_model)
        return self.self_model

    def pursue(
        self,
        objective: str,
        *,
        capabilities: tuple[str, ...] | list[str] = (),
        max_cycles: int | None = None,
        human_approved: bool = False,
    ) -> GoalPursuit:
        governance_data: dict[str, Any] | None = None
        if self.governance is not None:
            decision = self.governance.evaluate(
                objective,
                action="PURSUE_GOAL",
                subject=self.identity,
            )
            if decision.requires_human_approval and human_approved:
                decision = self.governance.approve(decision)
            governance_data = decision.to_dict()
            if not decision.approved:
                status = "PENDING_APPROVAL" if decision.requires_human_approval else "BLOCKED"
                pursuit = GoalPursuit(
                    objective=objective,
                    goal_id="",
                    status=status,
                    governance=governance_data,
                )
                self.pursuits.append(pursuit)
                self._persist_pursuit(pursuit)
                return pursuit
        goal = MetaGoal(
            objective=objective,
            horizon=GoalHorizon.LONG_TERM,
            required_capabilities=tuple(capabilities),
        )
        self.goals[goal.goal_id] = goal
        cycles = self.cognitive_loop.run(
            objective,
            capabilities=tuple(capabilities),
            max_cycles=max_cycles or self.max_cycles,
        )
        last_cycle = cycles[-1]
        if last_cycle.success:
            goal.update_progress(1.0)
        lessons: list[str] = []
        for cycle in cycles:
            if cycle.report is None:
                continue
            for lesson in cycle.report.improvement_points:
                if lesson not in lessons:
                    lessons.append(lesson)
        pursuit = GoalPursuit(
            objective=objective,
            goal_id=goal.goal_id,
            status=last_cycle.status,
            cycle_ids=tuple(cycle.cycle_id for cycle in cycles),
            lessons=tuple(lessons),
            governance=governance_data,
        )
        self.pursuits.append(pursuit)
        self._persist_pursuit(pursuit)
        return pursuit

    def evolve(self) -> dict[str, Any]:
        executed = [pursuit for pursuit in self.pursuits if pursuit.cycle_ids]
        successes = [pursuit for pursuit in executed if pursuit.success]
        success_rate = len(successes) / len(executed) if executed else 0.0
        lessons: list[str] = []
        for pursuit in self.pursuits:
            for lesson in pursuit.lessons:
                if lesson not in lessons:
                    lessons.append(lesson)
        report = {
            "evolution_id": f"EV-{uuid4().hex[:8]}",
            "identity": self.identity,
            "pursuits": len(self.pursuits),
            "executed": len(executed),
            "cycles": sum(len(pursuit.cycle_ids) for pursuit in self.pursuits),
            "success_rate": round(success_rate, 4),
            "lessons": lessons,
            "readiness": self.introspect().readiness,
            "created_at": _now(),
        }
        engine = self.executive_brain.self_improvement_engine
        if engine is not None and hasattr(engine, "track_metric"):
            engine.track_metric("pursuit_success_rate", success_rate)
        self._persist_evolution(report)
        return report

    def _persist_self_model(self, model: SelfModel) -> None:
        data = model.to_dict()
        if self.memory_kernel is not None:
            self.memory_kernel.remember_short_term({"self_model": data})
        if self.knowledge_graph is not None:
            self.knowledge_graph.add_node(
                title=f"Self Model: {model.identity}",
                content=str(data),
                node_type="self_model",
                metadata={"model_id": model.model_id, "readiness": model.readiness},
                node_id=model.model_id,
            )

    def _persist_pursuit(self, pursuit: GoalPursuit) -> None:
        data = pursuit.to_dict()
        if self.memory_kernel is not None:
            self.memory_kernel.remember_short_term({"goal_pursuit": data})
            self.memory_kernel.remember_long_term(
                str(data),
                metadata={"memory_type": "goal_pursuit", "pursuit_id": pursuit.pursuit_id},
            )
        if self.knowledge_graph is not None:
            self.knowledge_graph.add_node(
                title=f"Goal Pursuit: {pursuit.objective}",
                content=str(data),
                node_type="goal_pursuit",
                metadata={
                    "pursuit_id": pursuit.pursuit_id,
                    "goal_id": pursuit.goal_id,
                    "status": pursuit.status,
                },
                node_id=pursuit.pursuit_id,
            )

    def _persist_evolution(self, report: dict[str, Any]) -> None:
        if self.memory_kernel is not None:
            self.memory_kernel.remember_short_term({"evolution": report})
        if self.knowledge_graph is not None:
            self.knowledge_graph.add_node(
                title=f"Evolution Report: {report['evolution_id']}",
                content=str(report),
                node_type="evolution",
                metadata={
                    "evolution_id": str(report["evolution_id"]),
                    "success_rate": float(report["success_rate"]),
                },
                node_id=str(report["evolution_id"]),
            )
