from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from maios.agents import AgentRole


class GoalHorizon(StrEnum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class GoalStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class Goal:
    objective: str
    horizon: GoalHorizon | str = GoalHorizon.SHORT_TERM
    urgency: float = 0.5
    impact: float = 0.5
    risk: float = 0.0
    required_capabilities: tuple[str, ...] = ()
    resource_demand: float = 1.0
    dependencies: tuple[str, ...] = ()
    deadline: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    goal_id: str = field(default_factory=lambda: f"MG-{uuid4().hex[:8]}")
    status: GoalStatus | str = GoalStatus.PROPOSED
    progress: float = 0.0
    priority_score: float = 0.0
    completion_metrics: dict[str, float] = field(default_factory=dict)
    execution_results: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        self.objective = self.objective.strip()
        if not self.objective:
            raise ValueError("Goal objective is required.")
        self.horizon = GoalHorizon(self.horizon)
        self.status = GoalStatus(self.status)
        self.urgency = self._clamp(self.urgency)
        self.impact = self._clamp(self.impact)
        self.risk = self._clamp(self.risk)
        self.progress = self._clamp(self.progress)
        self.resource_demand = max(0.1, self.resource_demand)

    @property
    def completed(self) -> bool:
        return self.status == GoalStatus.COMPLETED or self.progress >= 1.0

    def update_progress(self, progress: float, metrics: dict[str, float] | None = None) -> None:
        self.progress = self._clamp(progress)
        if metrics:
            self.completion_metrics.update(metrics)
        if self.progress >= 1.0:
            self.status = GoalStatus.COMPLETED
        elif self.status == GoalStatus.PROPOSED:
            self.status = GoalStatus.ACTIVE
        self.touch()

    def record_execution_result(self, result: dict[str, Any]) -> None:
        self.execution_results.append(dict(result))
        status = str(result.get("status", "")).upper()
        if status in {"FAILED", "BLOCKED"}:
            self.status = GoalStatus.BLOCKED
            self.risk = self._clamp(self.risk + 0.2)
            self.urgency = self._clamp(self.urgency + 0.15)
        elif status in {"COMPLETED", "SUCCESS"}:
            progress_delta = float(result.get("progress_delta", 0.25))
            self.update_progress(self.progress + progress_delta)
            return
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["horizon"] = str(GoalHorizon(self.horizon).value)
        data["status"] = str(GoalStatus(self.status).value)
        if self.deadline is not None:
            data["deadline"] = self.deadline.isoformat()
        return data

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class RoadmapStep:
    goal_id: str
    objective: str
    sequence: int
    priority_score: float
    capabilities: tuple[str, ...]
    assigned_agents: tuple[str, ...] = ()
    assigned_node: str = ""
    swarm_id: str = ""
    resource_share: float = 0.0
    status: str = "PLANNED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategicPlan:
    goals: tuple[Goal, ...]
    mission_id: str = "default"
    plan_id: str = field(default_factory=lambda: f"SP-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    priority_order: tuple[str, ...] = ()
    balance_metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "mission_id": self.mission_id,
            "created_at": self.created_at,
            "priority_order": list(self.priority_order),
            "balance_metrics": dict(self.balance_metrics),
            "goals": [goal.to_dict() for goal in self.goals],
        }


@dataclass(frozen=True)
class ExecutionRoadmap:
    plan_id: str
    steps: tuple[RoadmapStep, ...]
    roadmap_id: str = field(default_factory=lambda: f"ER-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    resource_allocations: dict[str, float] = field(default_factory=dict)
    agent_allocations: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def next_steps(self, limit: int | None = None) -> list[RoadmapStep]:
        pending = [step for step in self.steps if step.status == "PLANNED"]
        return pending if limit is None else pending[:limit]

    def to_dict(self) -> dict[str, Any]:
        return {
            "roadmap_id": self.roadmap_id,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "resource_allocations": dict(self.resource_allocations),
            "agent_allocations": {
                goal_id: list(agent_ids) for goal_id, agent_ids in self.agent_allocations.items()
            },
            "steps": [step.to_dict() for step in self.steps],
        }


class MetaPlanner:
    """Strategic planner for balancing concurrent MAIOS missions."""

    def __init__(
        self,
        research_engine: Any | None = None,
        self_improvement_engine: Any | None = None,
        knowledge_graph: Any | None = None,
        swarm_manager: Any | None = None,
        distributed_runtime: Any | None = None,
        role_manager: Any | None = None,
        negotiation_manager: Any | None = None,
        mission_id: str = "default",
        total_resource_budget: float = 1.0,
    ) -> None:
        self.research_engine = research_engine
        self.self_improvement_engine = self_improvement_engine
        self.knowledge_graph = knowledge_graph
        self.swarm_manager = swarm_manager or getattr(distributed_runtime, "swarm_manager", None)
        self.distributed_runtime = distributed_runtime
        self.role_manager = role_manager or getattr(distributed_runtime, "role_manager", None)
        self.negotiation_manager = negotiation_manager or getattr(
            distributed_runtime,
            "negotiation_manager",
            None,
        )
        self.mission_id = mission_id
        self.total_resource_budget = max(0.1, total_resource_budget)
        self.goals: dict[str, Goal] = {}
        self.plans: list[StrategicPlan] = []
        self.roadmaps: list[ExecutionRoadmap] = []

    def create_goal(
        self,
        objective: str,
        horizon: GoalHorizon | str = GoalHorizon.SHORT_TERM,
        urgency: float = 0.5,
        impact: float = 0.5,
        risk: float = 0.0,
        required_capabilities: list[str] | tuple[str, ...] | None = None,
        resource_demand: float = 1.0,
        dependencies: list[str] | tuple[str, ...] | None = None,
        deadline: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Goal:
        goal = Goal(
            objective=objective,
            horizon=horizon,
            urgency=urgency,
            impact=impact,
            risk=risk,
            required_capabilities=tuple(required_capabilities or ()),
            resource_demand=resource_demand,
            dependencies=tuple(dependencies or ()),
            deadline=deadline,
            metadata=metadata or {},
        )
        goal.priority_score = self.score_goal(goal)
        self.goals[goal.goal_id] = goal
        self._record_goal(goal)
        return goal

    def prioritize_goals(self) -> list[Goal]:
        for goal in self.goals.values():
            goal.priority_score = self.score_goal(goal)
        return sorted(self.goals.values(), key=self._priority_key)

    def score_goal(self, goal: Goal) -> float:
        horizon_bonus = 0.1 if goal.horizon == GoalHorizon.SHORT_TERM else 0.04
        blocked_bonus = 0.12 if goal.status == GoalStatus.BLOCKED else 0.0
        dependency_penalty = self._dependency_penalty(goal)
        deadline_bonus = self._deadline_bonus(goal)
        progress_penalty = goal.progress * 0.45
        score = (
            goal.urgency * 0.35
            + goal.impact * 0.35
            + goal.risk * 0.15
            + horizon_bonus
            + blocked_bonus
            + deadline_bonus
            - progress_penalty
            - dependency_penalty
        )
        return max(0.0, round(score, 4))

    def build_strategic_plan(self) -> StrategicPlan:
        ordered = tuple(self.prioritize_goals())
        metrics = self._balance_metrics(ordered)
        plan = StrategicPlan(
            goals=ordered,
            mission_id=self.mission_id,
            priority_order=tuple(goal.goal_id for goal in ordered),
            balance_metrics=metrics,
        )
        self.plans.append(plan)
        self._record_plan(plan)
        self._negotiate_plan(plan)
        return plan

    def allocate_resources(self, plan: StrategicPlan | None = None) -> ExecutionRoadmap:
        active_plan = plan or self.build_strategic_plan()
        allocatable_goals = [goal for goal in active_plan.goals if not goal.completed]
        score_total = sum(max(goal.priority_score, 0.01) for goal in allocatable_goals) or 1.0
        resource_allocations: dict[str, float] = {}
        agent_allocations: dict[str, tuple[str, ...]] = {}
        steps: list[RoadmapStep] = []

        for sequence, goal in enumerate(allocatable_goals, start=1):
            resource_share = (
                self.total_resource_budget * max(goal.priority_score, 0.01) / score_total
            )
            resource_allocations[goal.goal_id] = round(resource_share, 4)
            assigned_agents = self._select_agents(goal)
            agent_allocations[goal.goal_id] = assigned_agents
            swarm_id = self._form_swarm(goal, assigned_agents)
            assigned_node = self._select_runtime_node()
            steps.append(
                RoadmapStep(
                    goal_id=goal.goal_id,
                    objective=goal.objective,
                    sequence=sequence,
                    priority_score=goal.priority_score,
                    capabilities=goal.required_capabilities,
                    assigned_agents=assigned_agents,
                    assigned_node=assigned_node,
                    swarm_id=swarm_id,
                    resource_share=round(resource_share, 4),
                )
            )

        roadmap = ExecutionRoadmap(
            plan_id=active_plan.plan_id,
            steps=tuple(steps),
            resource_allocations=resource_allocations,
            agent_allocations=agent_allocations,
        )
        self.roadmaps.append(roadmap)
        self._record_roadmap(roadmap)
        return roadmap

    def plan(self) -> tuple[StrategicPlan, ExecutionRoadmap]:
        strategic_plan = self.build_strategic_plan()
        return strategic_plan, self.allocate_resources(strategic_plan)

    def update_goal_progress(
        self,
        goal_id: str,
        progress: float,
        metrics: dict[str, float] | None = None,
    ) -> Goal:
        goal = self._require_goal(goal_id)
        goal.update_progress(progress, metrics=metrics)
        goal.priority_score = self.score_goal(goal)
        self._record_goal(goal)
        return goal

    def apply_execution_result(
        self,
        goal_id: str,
        result: dict[str, Any],
        replan: bool = True,
    ) -> ExecutionRoadmap | None:
        goal = self._require_goal(goal_id)
        previous_score = goal.priority_score
        goal.record_execution_result(result)
        goal.priority_score = self.score_goal(goal)
        self._record_goal(goal)
        self._analyze_execution_feedback(result)
        if not replan:
            return None
        changed = previous_score != goal.priority_score or str(
            result.get("status", "")
        ).upper() in {
            "FAILED",
            "BLOCKED",
            "COMPLETED",
            "SUCCESS",
        }
        return self.replan() if changed else None

    def replan(self) -> ExecutionRoadmap:
        plan = self.build_strategic_plan()
        return self.allocate_resources(plan)

    def progress_report(self) -> dict[str, Any]:
        goals = list(self.goals.values())
        completed = [goal for goal in goals if goal.completed]
        blocked = [goal for goal in goals if goal.status == GoalStatus.BLOCKED]
        average_progress = sum(goal.progress for goal in goals) / len(goals) if goals else 0.0
        return {
            "goal_count": len(goals),
            "completed_count": len(completed),
            "blocked_count": len(blocked),
            "average_progress": round(average_progress, 4),
            "completion_rate": round(len(completed) / len(goals), 4) if goals else 0.0,
            "latest_plan_id": self.plans[-1].plan_id if self.plans else "",
            "latest_roadmap_id": self.roadmaps[-1].roadmap_id if self.roadmaps else "",
        }

    def research_goal(self, goal_id: str) -> Any | None:
        if self.research_engine is None:
            return None
        goal = self._require_goal(goal_id)
        return self.research_engine.run(goal.objective)

    def _priority_key(self, goal: Goal) -> tuple[float, float, float, str]:
        return (-goal.priority_score, goal.progress, -goal.impact, goal.goal_id)

    def _dependency_penalty(self, goal: Goal) -> float:
        unmet = [
            dependency
            for dependency in goal.dependencies
            if dependency in self.goals and not self.goals[dependency].completed
        ]
        return min(0.35, len(unmet) * 0.15)

    def _deadline_bonus(self, goal: Goal) -> float:
        if goal.deadline is None:
            return 0.0
        seconds = (goal.deadline - datetime.now(UTC)).total_seconds()
        if seconds <= 0:
            return 0.2
        days = seconds / 86400
        if days <= 1:
            return 0.18
        if days <= 7:
            return 0.1
        return 0.0

    def _balance_metrics(self, goals: tuple[Goal, ...]) -> dict[str, float]:
        short_term = sum(1 for goal in goals if goal.horizon == GoalHorizon.SHORT_TERM)
        long_term = sum(1 for goal in goals if goal.horizon == GoalHorizon.LONG_TERM)
        total = len(goals)
        return {
            "short_term_count": float(short_term),
            "long_term_count": float(long_term),
            "active_count": float(sum(1 for goal in goals if not goal.completed)),
            "average_priority": (
                sum(goal.priority_score for goal in goals) / total if total else 0.0
            ),
        }

    def _select_agents(self, goal: Goal) -> tuple[str, ...]:
        capabilities = list(goal.required_capabilities)
        if not capabilities:
            capabilities = ["plan"]
        selected: list[str] = []
        if self.role_manager is not None:
            for capability in capabilities:
                agent = self.role_manager.select_best(capability)
                if agent is not None and agent.agent_id not in selected:
                    selected.append(agent.agent_id)
        elif self.distributed_runtime is not None:
            for capability in capabilities:
                for agent in self.distributed_runtime.agent_registry.discover(capability):
                    if agent.agent_id not in selected:
                        selected.append(agent.agent_id)
                        break
        return tuple(selected)

    def _form_swarm(self, goal: Goal, assigned_agents: tuple[str, ...]) -> str:
        if self.swarm_manager is None or not goal.required_capabilities:
            return ""
        swarm = self.swarm_manager.form_swarm(
            name=f"meta:{goal.goal_id}",
            capabilities=list(goal.required_capabilities),
            role=AgentRole.SPECIALIST if assigned_agents else None,
            size=max(1, len(assigned_agents)) if assigned_agents else None,
        )
        return str(swarm.swarm_id)

    def _select_runtime_node(self) -> str:
        if self.distributed_runtime is None:
            return ""
        node = self.distributed_runtime.node_manager.select_node()
        return "" if node is None else str(node.node_id)

    def _negotiate_plan(self, plan: StrategicPlan) -> None:
        if self.negotiation_manager is None or len(plan.goals) < 2:
            return
        participants: list[str] = []
        if self.role_manager is not None:
            participants = [
                agent.agent_id
                for agent in self.role_manager.select_agents([], role=AgentRole.COORDINATOR)
            ]
        session = self.negotiation_manager.create_session(
            topic=f"Meta plan balance for {self.mission_id}",
            participants=participants,
            consensus_threshold=0.5,
        )
        proposer_id = participants[0] if participants else "meta_planner"
        self.negotiation_manager.generate_proposal(
            session.session_id,
            proposer_id=proposer_id,
            content={
                "plan_id": plan.plan_id,
                "priority_order": list(plan.priority_order),
                "balance_metrics": dict(plan.balance_metrics),
            },
        )

    def _analyze_execution_feedback(self, result: dict[str, Any]) -> None:
        if self.self_improvement_engine is None:
            return
        try:
            self.self_improvement_engine.analyze_execution_history([result])
        except AttributeError:
            return

    def _record_goal(self, goal: Goal) -> None:
        if self.knowledge_graph is None:
            return
        self.knowledge_graph.add_node(
            title=f"Meta Goal: {goal.objective}",
            content=str(goal.to_dict()),
            node_type="meta_goal",
            metadata={
                "goal_id": goal.goal_id,
                "status": GoalStatus(goal.status).value,
                "horizon": GoalHorizon(goal.horizon).value,
                "priority_score": goal.priority_score,
            },
            node_id=goal.goal_id,
        )

    def _record_plan(self, plan: StrategicPlan) -> None:
        if self.knowledge_graph is None:
            return
        plan_node = self.knowledge_graph.add_node(
            title=f"Strategic Plan: {plan.plan_id}",
            content=str(plan.to_dict()),
            node_type="strategic_plan",
            metadata={"plan_id": plan.plan_id, "mission_id": plan.mission_id},
            node_id=plan.plan_id,
        )
        for goal in plan.goals:
            if self.knowledge_graph.get_node(goal.goal_id) is not None:
                self.knowledge_graph.add_edge(plan_node.node_id, goal.goal_id, "part_of")

    def _record_roadmap(self, roadmap: ExecutionRoadmap) -> None:
        if self.knowledge_graph is None:
            return
        self.knowledge_graph.add_node(
            title=f"Execution Roadmap: {roadmap.roadmap_id}",
            content=str(roadmap.to_dict()),
            node_type="execution_roadmap",
            metadata={
                "roadmap_id": roadmap.roadmap_id,
                "plan_id": roadmap.plan_id,
                "derived_from": roadmap.plan_id,
            },
            node_id=roadmap.roadmap_id,
        )

    def _require_goal(self, goal_id: str) -> Goal:
        goal = self.goals.get(goal_id)
        if goal is None:
            raise KeyError(f"Unknown goal: {goal_id}")
        return goal
