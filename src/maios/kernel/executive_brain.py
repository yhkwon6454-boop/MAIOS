from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from maios.knowledge.graph import KnowledgeGraph
from maios.planning import GoalHorizon, MetaGoal, MetaPlanner
from maios.reflection import ImprovementReport, ReflectionEngine


class PlannerType(StrEnum):
    META = "meta"
    DISTRIBUTED = "distributed"
    RESEARCH = "research"
    SWARM = "swarm"
    DIRECT = "direct"


@dataclass
class DecisionContext:
    objective: str
    goals: list[MetaGoal] = field(default_factory=list)
    mission_id: str = field(default_factory=lambda: f"EB-M-{uuid4().hex[:8]}")
    requested_capabilities: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    risk_level: str = "NORMAL"
    metadata: dict[str, Any] = field(default_factory=dict)
    prior_outcomes: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        self.objective = self.objective.strip()
        if not self.objective:
            raise ValueError("Decision objective is required.")
        self.risk_level = self.risk_level.upper()
        self.requested_capabilities = tuple(self.requested_capabilities)
        self.constraints = tuple(self.constraints)

    @classmethod
    def from_goal(
        cls,
        objective: str,
        *,
        urgency: float = 0.5,
        impact: float = 0.5,
        risk: float = 0.0,
        capabilities: list[str] | tuple[str, ...] | None = None,
        mission_id: str | None = None,
    ) -> DecisionContext:
        goal = MetaGoal(
            objective=objective,
            horizon=GoalHorizon.SHORT_TERM,
            urgency=urgency,
            impact=impact,
            risk=risk,
            required_capabilities=tuple(capabilities or ()),
        )
        return cls(
            objective=objective,
            goals=[goal],
            mission_id=mission_id or f"EB-M-{uuid4().hex[:8]}",
            requested_capabilities=tuple(capabilities or ()),
        )

    def add_goal(self, goal: MetaGoal) -> None:
        self.goals.append(goal)

    def record_outcome(self, outcome: dict[str, Any]) -> None:
        self.prior_outcomes.append(dict(outcome))

    def failure_count(self) -> int:
        return sum(
            1
            for outcome in self.prior_outcomes
            if str(outcome.get("status", "")).upper() in {"FAILED", "BLOCKED"}
        )

    def repeated_mistakes(self) -> tuple[str, ...]:
        counts: dict[str, int] = {}
        for outcome in self.prior_outcomes:
            issue = str(outcome.get("error") or outcome.get("mistake") or "").strip().lower()
            if not issue:
                continue
            counts[issue] = counts.get(issue, 0) + 1
        return tuple(issue for issue, count in counts.items() if count > 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "mission_id": self.mission_id,
            "requested_capabilities": list(self.requested_capabilities),
            "constraints": list(self.constraints),
            "risk_level": self.risk_level,
            "metadata": dict(self.metadata),
            "prior_outcomes": [dict(outcome) for outcome in self.prior_outcomes],
            "goals": [goal.to_dict() for goal in self.goals],
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class ExecutiveDecision:
    context_id: str
    objective: str
    selected_planner: PlannerType | str
    priority_order: tuple[str, ...]
    action: str
    rationale: str
    status: str = "PLANNED"
    decision_id: str = field(default_factory=lambda: f"ED-{uuid4().hex[:8]}")
    outcome: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["selected_planner"] = PlannerType(self.selected_planner).value
        data["priority_order"] = list(self.priority_order)
        return data


class ExecutivePriorityEngine:
    """Scores executive goals using urgency, impact, risk, progress, and failures."""

    def score(self, goal: MetaGoal, context: DecisionContext | None = None) -> float:
        failure_pressure = min(0.25, (context.failure_count() if context else 0) * 0.08)
        capability_bonus = 0.0
        if context is not None:
            overlap = set(goal.required_capabilities) & set(context.requested_capabilities)
            capability_bonus = min(0.12, len(overlap) * 0.04)
        score = (
            goal.urgency * 0.32
            + goal.impact * 0.34
            + goal.risk * 0.16
            + capability_bonus
            + failure_pressure
            - goal.progress * 0.35
        )
        return max(0.0, round(score, 4))

    def prioritize(
        self,
        goals: list[MetaGoal] | tuple[MetaGoal, ...],
        context: DecisionContext | None = None,
    ) -> list[MetaGoal]:
        for goal in goals:
            goal.priority_score = self.score(goal, context)
        return sorted(goals, key=lambda goal: (-goal.priority_score, goal.progress, goal.goal_id))


class ExecutiveBrain:
    """Top-level MAIOS decision engine coordinating planning and runtime control."""

    def __init__(
        self,
        meta_planner: MetaPlanner | None = None,
        distributed_runtime: Any | None = None,
        research_engine: Any | None = None,
        negotiation_manager: Any | None = None,
        swarm_manager: Any | None = None,
        reflection_engine: ReflectionEngine | None = None,
        self_improvement_engine: Any | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        priority_engine: ExecutivePriorityEngine | None = None,
        failure_threshold: int = 2,
        mission_id: str = "executive",
    ) -> None:
        self.distributed_runtime = distributed_runtime
        self.research_engine = research_engine
        self.negotiation_manager = negotiation_manager or getattr(
            distributed_runtime,
            "negotiation_manager",
            None,
        )
        self.swarm_manager = swarm_manager or getattr(distributed_runtime, "swarm_manager", None)
        self.knowledge_graph = knowledge_graph
        self.reflection_engine = reflection_engine or ReflectionEngine(
            knowledge_graph=knowledge_graph
        )
        self.self_improvement_engine = self_improvement_engine
        self.priority_engine = priority_engine or ExecutivePriorityEngine()
        self.failure_threshold = max(1, failure_threshold)
        self.mission_id = mission_id
        self.meta_planner = meta_planner or MetaPlanner(
            research_engine=research_engine,
            self_improvement_engine=self_improvement_engine,
            knowledge_graph=knowledge_graph,
            swarm_manager=self.swarm_manager,
            distributed_runtime=distributed_runtime,
            negotiation_manager=self.negotiation_manager,
            mission_id=mission_id,
        )
        self.decisions: list[ExecutiveDecision] = []

    def prioritize_goals(self, context: DecisionContext) -> list[MetaGoal]:
        if not context.goals:
            context.add_goal(
                MetaGoal(
                    objective=context.objective,
                    required_capabilities=context.requested_capabilities,
                )
            )
        return self.priority_engine.prioritize(context.goals, context)

    def select_planner(self, context: DecisionContext) -> PlannerType:
        capabilities = set(context.requested_capabilities)
        if len(context.goals) > 1 or "meta" in capabilities or "plan" in capabilities:
            return PlannerType.META
        if capabilities & {"research", "investigate"} and self.research_engine is not None:
            return PlannerType.RESEARCH
        if capabilities and self.swarm_manager is not None:
            return PlannerType.SWARM
        if self.distributed_runtime is not None:
            return PlannerType.DISTRIBUTED
        return PlannerType.DIRECT

    def decide(self, context: DecisionContext) -> ExecutiveDecision:
        ordered_goals = self.prioritize_goals(context)
        planner = self.select_planner(context)
        rationale = self._rationale(planner, context)
        decision = ExecutiveDecision(
            context_id=context.mission_id,
            objective=context.objective,
            selected_planner=planner,
            priority_order=tuple(goal.goal_id for goal in ordered_goals),
            action=self._action_for(planner),
            rationale=rationale,
        )
        self.decisions.append(decision)
        self._record_decision(decision, context)
        self._negotiate_decision(decision)
        return decision

    def execute(self, context: DecisionContext) -> ExecutiveDecision:
        decision = self.decide(context)
        outcome = self._execute_decision(decision, context)
        context.record_outcome(outcome)
        final_decision = ExecutiveDecision(
            context_id=decision.context_id,
            objective=decision.objective,
            selected_planner=decision.selected_planner,
            priority_order=decision.priority_order,
            action=decision.action,
            rationale=decision.rationale,
            status=str(outcome.get("status", "COMPLETED")),
            decision_id=decision.decision_id,
            outcome=outcome,
            created_at=decision.created_at,
        )
        self.decisions[-1] = final_decision
        self._record_outcome(final_decision, context)
        self._trigger_learning_if_needed(context)
        return final_decision

    def record_outcome(
        self,
        context: DecisionContext,
        outcome: dict[str, Any],
    ) -> ImprovementReport | None:
        context.record_outcome(outcome)
        self._persist_execution_outcome(context, outcome)
        return self._trigger_learning_if_needed(context)

    def _execute_decision(
        self,
        decision: ExecutiveDecision,
        context: DecisionContext,
    ) -> dict[str, Any]:
        planner = PlannerType(decision.selected_planner)
        if planner == PlannerType.META:
            self._sync_meta_goals(context)
            plan, roadmap = self.meta_planner.plan()
            return {
                "status": "COMPLETED",
                "planner": planner.value,
                "plan_id": plan.plan_id,
                "roadmap_id": roadmap.roadmap_id,
                "steps": [step.to_dict() for step in roadmap.steps],
            }
        if planner == PlannerType.RESEARCH and self.research_engine is not None:
            report = self.research_engine.run(context.objective)
            return {
                "status": "COMPLETED",
                "planner": planner.value,
                "report": report.to_dict() if hasattr(report, "to_dict") else report,
            }
        if planner == PlannerType.SWARM and self.swarm_manager is not None:
            capabilities = list(context.requested_capabilities or ("plan",))
            swarm = self.swarm_manager.form_swarm(
                name=f"executive:{context.mission_id}",
                capabilities=capabilities,
            )
            tasks = self.swarm_manager.distribute_tasks(
                swarm.swarm_id,
                [(capability, {"task": context.objective}) for capability in capabilities],
            )
            failed = [task for task in tasks if task.status == "FAILED"]
            return {
                "status": "FAILED" if failed else "COMPLETED",
                "planner": planner.value,
                "swarm_id": swarm.swarm_id,
                "task_ids": [task.task_id for task in tasks],
            }
        if planner == PlannerType.DISTRIBUTED and self.distributed_runtime is not None:
            mission = self.distributed_runtime.execute_mission(context.objective)
            return {
                "status": mission.status,
                "planner": planner.value,
                "mission_id": mission.mission_id,
                "assigned_node": mission.assigned_node,
                "error": mission.error,
            }
        return {
            "status": "COMPLETED",
            "planner": PlannerType.DIRECT.value,
            "output": context.objective,
        }

    def _sync_meta_goals(self, context: DecisionContext) -> None:
        for goal in context.goals:
            if goal.goal_id not in self.meta_planner.goals:
                self.meta_planner.goals[goal.goal_id] = goal

    def _trigger_learning_if_needed(self, context: DecisionContext) -> ImprovementReport | None:
        if context.failure_count() < self.failure_threshold:
            return None

        report = ImprovementReport(
            mission_id=context.mission_id,
            success=False,
            score=30,
            summary=f"Repeated execution failures for '{context.objective}'.",
            bottlenecks=[
                str(outcome.get("error") or outcome.get("status"))
                for outcome in context.prior_outcomes
                if str(outcome.get("status", "")).upper() in {"FAILED", "BLOCKED"}
            ],
            improvement_points=["Escalate repeated failures through executive replanning."],
        )
        self.reflection_engine.store(report)
        mistakes = context.repeated_mistakes()
        if mistakes and self.self_improvement_engine is not None:
            self.self_improvement_engine.analyze_execution_history(context.prior_outcomes)
            try:
                record = self.self_improvement_engine.records[-1]
                self.self_improvement_engine.generate_plan(record, target=context.objective)
            except (AttributeError, IndexError):
                pass
        return report

    def _record_decision(self, decision: ExecutiveDecision, context: DecisionContext) -> None:
        if self.knowledge_graph is None:
            return
        self.knowledge_graph.add_node(
            title=f"Executive Decision: {decision.objective}",
            content=str(decision.to_dict()),
            node_type="executive_decision",
            metadata={
                "decision_id": decision.decision_id,
                "context_id": context.mission_id,
                "planner": PlannerType(decision.selected_planner).value,
            },
            node_id=decision.decision_id,
        )

    def _record_outcome(self, decision: ExecutiveDecision, context: DecisionContext) -> None:
        self._persist_execution_outcome(context, decision.outcome)
        if self.knowledge_graph is None:
            return
        node = self.knowledge_graph.get_node(decision.decision_id)
        if node is not None:
            node.content = str(decision.to_dict())
            node.metadata["status"] = decision.status

    def _persist_execution_outcome(
        self,
        context: DecisionContext,
        outcome: dict[str, Any],
    ) -> None:
        if self.knowledge_graph is None:
            return
        node = self.knowledge_graph.learn_experience(
            description=f"Executive outcome for {context.objective}: {outcome}",
            outcome=(
                "failure"
                if str(outcome.get("status", "")).upper() in {"FAILED", "BLOCKED"}
                else "success"
            ),
            metadata={
                "mission_id": context.mission_id,
                "planner": str(outcome.get("planner", "")),
            },
        )
        for goal in context.goals:
            if self.knowledge_graph.get_node(goal.goal_id) is not None:
                self.knowledge_graph.add_edge(node.node_id, goal.goal_id, "derived_from")

    def _negotiate_decision(self, decision: ExecutiveDecision) -> None:
        if self.negotiation_manager is None:
            return
        session = self.negotiation_manager.create_session(
            topic=f"Executive decision for {decision.objective}",
            consensus_threshold=0.5,
        )
        self.negotiation_manager.generate_proposal(
            session.session_id,
            proposer_id="executive_brain",
            content=decision.to_dict(),
        )

    def _rationale(self, planner: PlannerType, context: DecisionContext) -> str:
        return (
            f"Selected {planner.value} planner for {len(context.goals)} goal(s), "
            f"capabilities={list(context.requested_capabilities)}, "
            f"failures={context.failure_count()}."
        )

    def _action_for(self, planner: PlannerType) -> str:
        return {
            PlannerType.META: "BUILD_STRATEGIC_PLAN",
            PlannerType.DISTRIBUTED: "EXECUTE_DISTRIBUTED_MISSION",
            PlannerType.RESEARCH: "RUN_RESEARCH",
            PlannerType.SWARM: "COORDINATE_SWARM",
            PlannerType.DIRECT: "DIRECT_COMPLETE",
        }[planner]
