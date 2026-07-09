from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from maios.adapters.llm_provider import BaseLLMProvider
from maios.kernel.cognitive_interpreter import CognitiveInterpreter
from maios.kernel.executive_brain import (
    DecisionContext,
    ExecutiveBrain,
    ExecutiveDecision,
)
from maios.kernel.memory_kernel import MemoryKernel
from maios.kernel.memory_recall import MemoryRecall
from maios.kernel.task_executor import TaskExecutor
from maios.kernel.world_model import SystemState, WorldModel
from maios.knowledge.graph import KnowledgeGraph
from maios.reflection import ImprovementReport


def _now() -> str:
    return datetime.now(UTC).isoformat()


class CognitivePhase(StrEnum):
    OBSERVE = "observe"
    UNDERSTAND = "understand"
    PLAN = "plan"
    ACT = "act"
    REFLECT = "reflect"
    LEARN = "learn"


PHASE_ORDER: tuple[CognitivePhase, ...] = (
    CognitivePhase.OBSERVE,
    CognitivePhase.UNDERSTAND,
    CognitivePhase.PLAN,
    CognitivePhase.ACT,
    CognitivePhase.REFLECT,
    CognitivePhase.LEARN,
)


@dataclass(frozen=True)
class PhaseRecord:
    phase: CognitivePhase
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    record_id: str = field(default_factory=lambda: f"CP-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "phase": self.phase.value,
            "summary": self.summary,
            "data": dict(self.data),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CognitiveCycleResult:
    objective: str
    mission_id: str
    status: str
    phases: tuple[PhaseRecord, ...]
    decision: ExecutiveDecision | None = None
    outcome: dict[str, Any] = field(default_factory=dict)
    report: ImprovementReport | None = None
    cycle_id: str = field(default_factory=lambda: f"CC-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=_now)

    @property
    def success(self) -> bool:
        return self.status in {"COMPLETED", "SUCCESS"}

    def phase_order(self) -> tuple[str, ...]:
        return tuple(record.phase.value for record in self.phases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "objective": self.objective,
            "mission_id": self.mission_id,
            "status": self.status,
            "phases": [record.to_dict() for record in self.phases],
            "decision": self.decision.to_dict() if self.decision else None,
            "outcome": dict(self.outcome),
            "report": self.report.to_dict() if self.report else None,
            "created_at": self.created_at,
        }


class CognitiveLoop:
    """Observe -> Understand -> Plan -> Act -> Reflect -> Learn cycle for MAIOS."""

    def __init__(
        self,
        executive_brain: ExecutiveBrain | None = None,
        world_model: WorldModel | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        memory_kernel: MemoryKernel | None = None,
        runtime: Any | None = None,
        success_statuses: tuple[str, ...] = ("COMPLETED", "SUCCESS"),
        interpreter: CognitiveInterpreter | None = None,
        llm_provider: BaseLLMProvider | None = None,
        memory_recall: MemoryRecall | None = None,
    ) -> None:
        self.knowledge_graph = knowledge_graph
        self.memory_kernel = memory_kernel
        self.interpreter = interpreter or CognitiveInterpreter(llm_provider)
        self.memory_recall = memory_recall or MemoryRecall(knowledge_graph)
        self.executive_brain = executive_brain or ExecutiveBrain(
            distributed_runtime=runtime,
            knowledge_graph=knowledge_graph,
            memory_kernel=memory_kernel,
            world_model=world_model,
            task_executor=TaskExecutor(llm_provider),
        )
        if llm_provider is not None and not self.executive_brain.task_executor.available:
            self.executive_brain.task_executor = TaskExecutor(llm_provider)
        if world_model is not None:
            self.executive_brain.world_model = world_model
        self.world_model = self.executive_brain.world_model
        self.runtime = runtime or self.executive_brain.distributed_runtime
        self.success_statuses = tuple(status.upper() for status in success_statuses)
        self.cycles: list[CognitiveCycleResult] = []

    def observe(self, context: DecisionContext) -> PhaseRecord:
        if self.runtime is not None:
            self.world_model.system = SystemState.from_runtime(self.runtime)
        self.world_model.environment.update(
            signals={"observed_objective": context.objective, "observed_at": _now()},
        )
        self.world_model.user.observe_intent(context.objective)
        return PhaseRecord(
            phase=CognitivePhase.OBSERVE,
            summary=f"Observed world state {self.world_model.state_id}.",
            data={"system": self.world_model.system.to_dict()},
        )

    def understand(self, context: DecisionContext) -> PhaseRecord:
        world_context = self.executive_brain.build_world_context(context)
        data: dict[str, Any] = {
            "context_id": world_context.context_id,
            "risk_level": world_context.environment.risk_level,
            "predictions": {
                prediction.target: prediction.outcome for prediction in world_context.predictions
            },
        }
        summary = f"Built world context {world_context.context_id}."
        recall = self.memory_recall.recall(context.objective)
        if recall:
            data["recalled"] = list(recall.entries)
            context.metadata["recalled_knowledge"] = list(recall.entries)
        interpretation = self.interpreter.interpret_situation(
            context.objective,
            world_context,
            recalled=recall.entries,
        )
        if interpretation is not None:
            data["interpretation"] = interpretation
            context.metadata["situation_interpretation"] = interpretation
            summary = interpretation
        return PhaseRecord(
            phase=CognitivePhase.UNDERSTAND,
            summary=summary,
            data=data,
        )

    def plan(self, context: DecisionContext) -> tuple[ExecutiveDecision, PhaseRecord]:
        decision = self.executive_brain.decide(context)
        record = PhaseRecord(
            phase=CognitivePhase.PLAN,
            summary=f"Selected {decision.selected_planner} planner via {decision.action}.",
            data={
                "decision_id": decision.decision_id,
                "planner": str(decision.selected_planner),
                "priority_order": list(decision.priority_order),
            },
        )
        return decision, record

    def act(
        self,
        decision: ExecutiveDecision,
        context: DecisionContext,
    ) -> tuple[dict[str, Any], PhaseRecord]:
        outcome = self.executive_brain.act(decision, context)
        record = PhaseRecord(
            phase=CognitivePhase.ACT,
            summary=f"Executed {decision.action} with status {outcome.get('status')}.",
            data={
                "status": str(outcome.get("status", "")),
                "planner": str(outcome.get("planner", "")),
            },
        )
        return outcome, record

    def reflect(
        self,
        context: DecisionContext,
        outcome: dict[str, Any],
    ) -> tuple[ImprovementReport, PhaseRecord]:
        status = str(outcome.get("status", "")).upper()
        success = status in self.success_statuses
        bottlenecks = [
            str(prior.get("error") or prior.get("status"))
            for prior in context.prior_outcomes
            if str(prior.get("status", "")).upper() in {"FAILED", "BLOCKED"}
        ]
        improvement_points = (
            ["Preserve the current cognitive pattern for similar objectives."]
            if success
            else ["Adjust planner selection or capabilities before the next cycle."]
        )
        summary = (
            f"Cognitive cycle for '{context.objective}' "
            f"{'succeeded' if success else 'needs improvement'}."
        )
        llm_reflection = self.interpreter.reflect_on_outcome(
            context.objective,
            outcome,
            success,
            interpretation=context.metadata.get("situation_interpretation"),
        )
        if llm_reflection is not None:
            summary, lessons = llm_reflection
            if lessons:
                improvement_points = list(lessons)
        report = ImprovementReport(
            mission_id=context.mission_id,
            success=success,
            score=90 if success else 40,
            summary=summary,
            bottlenecks=bottlenecks,
            improvement_points=improvement_points,
        )
        self.executive_brain.reflection_engine.store(report)
        record = PhaseRecord(
            phase=CognitivePhase.REFLECT,
            summary=report.summary,
            data={"report_id": report.report_id, "success": report.success},
        )
        return report, record

    def learn(
        self,
        context: DecisionContext,
        outcome: dict[str, Any],
        report: ImprovementReport,
    ) -> PhaseRecord:
        transition = self.world_model.transition(
            "cognitive_cycle",
            {
                "environment": {
                    "signals": {"last_cycle_status": str(outcome.get("status", ""))},
                },
                "system": {"outcome": outcome},
            },
        )
        escalation = self.executive_brain.learn(context)
        if self.knowledge_graph is not None:
            self.knowledge_graph.learn_experience(
                description=f"Cognitive cycle for {context.objective}: {outcome}",
                outcome="success" if report.success else "failure",
                metadata={"mission_id": context.mission_id},
            )
        return PhaseRecord(
            phase=CognitivePhase.LEARN,
            summary=f"Stored {len(report.improvement_points)} lesson(s) from the cycle.",
            data={
                "transition_id": transition.transition_id,
                "lessons": list(report.improvement_points),
                "escalated": escalation is not None,
            },
        )

    def run_cycle(
        self,
        objective: str | DecisionContext,
        *,
        capabilities: tuple[str, ...] | list[str] = (),
    ) -> CognitiveCycleResult:
        context = (
            objective
            if isinstance(objective, DecisionContext)
            else DecisionContext(objective, requested_capabilities=tuple(capabilities))
        )
        observe_record = self.observe(context)
        understand_record = self.understand(context)
        decision, plan_record = self.plan(context)
        outcome, act_record = self.act(decision, context)
        report, reflect_record = self.reflect(context, outcome)
        learn_record = self.learn(context, outcome, report)
        cycle = CognitiveCycleResult(
            objective=context.objective,
            mission_id=context.mission_id,
            status=str(outcome.get("status", "COMPLETED")).upper(),
            phases=(
                observe_record,
                understand_record,
                plan_record,
                act_record,
                reflect_record,
                learn_record,
            ),
            decision=decision,
            outcome=outcome,
            report=report,
        )
        self.cycles.append(cycle)
        self.persist_cycle(cycle)
        return cycle

    def run(
        self,
        objective: str,
        *,
        capabilities: tuple[str, ...] | list[str] = (),
        max_cycles: int = 3,
        stop_on_success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> list[CognitiveCycleResult]:
        context = DecisionContext(
            objective,
            requested_capabilities=tuple(capabilities),
            metadata=dict(metadata or {}),
        )
        results: list[CognitiveCycleResult] = []
        for _ in range(max(1, max_cycles)):
            cycle = self.run_cycle(context)
            results.append(cycle)
            if stop_on_success and cycle.status in self.success_statuses:
                break
        return results

    def persist_cycle(self, cycle: CognitiveCycleResult) -> None:
        data = cycle.to_dict()
        if self.memory_kernel is not None:
            self.memory_kernel.remember_short_term({"cognitive_cycle": data})
            self.memory_kernel.remember_long_term(
                str(data),
                metadata={"memory_type": "cognitive_cycle", "cycle_id": cycle.cycle_id},
            )
        if self.knowledge_graph is not None:
            self.knowledge_graph.add_node(
                title=f"Cognitive Cycle: {cycle.objective}",
                content=str(data),
                node_type="cognitive_cycle",
                metadata={
                    "cycle_id": cycle.cycle_id,
                    "mission_id": cycle.mission_id,
                    "status": cycle.status,
                },
                node_id=cycle.cycle_id,
            )
