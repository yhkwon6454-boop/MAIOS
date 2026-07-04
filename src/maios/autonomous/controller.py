from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from maios.agents.runtime_orchestrator import MultiAgentRuntimeResult, RuntimeOrchestrator
from maios.planning import Goal, GoalManager
from maios.reflection import ReflectionEngine
from maios.runtime.models import Mission, MissionType, Priority


@dataclass
class Observation:
    context: dict[str, Any]
    signals: list[str] = field(default_factory=list)
    observation_id: str = field(default_factory=lambda: f"OBS-{uuid4().hex[:8]}")


@dataclass
class Orientation:
    observation_id: str
    goals: list[Goal]
    risk: str = "LOW"
    summary: str = ""


@dataclass
class Decision:
    goal: str
    action: str
    mode: str
    approved: bool
    status: str = "PENDING"
    reason: str = ""
    decision_id: str = field(default_factory=lambda: f"DEC-{uuid4().hex[:8]}")
    result: MultiAgentRuntimeResult | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["result"] = None
        if self.result is not None:
            data["result"] = {
                "mission_id": self.result.mission.mission_id,
                "mission_status": self.result.mission.status.value,
                "final_output": self.result.final_output,
                "qa_score": self.result.qa_result.score,
                "reflection_report_id": (
                    self.result.reflection_report.report_id
                    if self.result.reflection_report
                    else ""
                ),
            }
        return data


class SafetyPolicy(Protocol):
    def evaluate(self, goal: str, context: dict[str, Any]) -> tuple[bool, str]:
        ...


class BlockedKeywordPolicy:
    def __init__(self, blocked_keywords: list[str] | None = None) -> None:
        self.blocked_keywords = [
            keyword.lower()
            for keyword in (blocked_keywords or [])
        ]

    def evaluate(self, goal: str, context: dict[str, Any]) -> tuple[bool, str]:
        goal_text = goal.lower()
        for keyword in self.blocked_keywords:
            if keyword in goal_text:
                return False, f"Goal contains blocked keyword: {keyword}"
        return True, "Allowed by blocked keyword policy."


class SafetyManager:
    """Policy gate for autonomous controller decisions."""

    def __init__(
        self,
        policies: list[SafetyPolicy] | None = None,
        require_human_approval: bool = False,
    ) -> None:
        self.policies = policies or []
        self.require_human_approval = require_human_approval

    @classmethod
    def with_blocked_keywords(
        cls,
        blocked_keywords: list[str],
        require_human_approval: bool = False,
    ) -> "SafetyManager":
        return cls(
            policies=[BlockedKeywordPolicy(blocked_keywords)],
            require_human_approval=require_human_approval,
        )

    def evaluate(self, goal: str, context: dict[str, Any]) -> tuple[bool, str]:
        for policy in self.policies:
            allowed, reason = policy.evaluate(goal, context)
            if not allowed:
                return False, reason

        if self.require_human_approval:
            return False, "Human approval required."

        return True, "Allowed for autonomous execution."


class DecisionHistoryStore:
    """JSON-backed decision history for autonomous controller runs."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._decisions: dict[str, Decision] = {}
        self._serialized_decisions: list[dict[str, Any]] = []
        self._load()

    def add(self, decision: Decision) -> Decision:
        self._decisions[decision.decision_id] = decision
        self._persist()
        return decision

    def get(self, decision_id: str) -> Decision | None:
        return self._decisions.get(decision_id)

    def history(self) -> list[Decision]:
        return list(self._decisions.values())

    def serialized_history(self) -> list[dict[str, Any]]:
        if self._decisions:
            return [decision.to_dict() for decision in self._decisions.values()]
        return list(self._serialized_decisions)

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return

        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._serialized_decisions = data.get("decisions", [])

    def _persist(self) -> None:
        if self.path is None:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"decisions": [decision.to_dict() for decision in self._decisions.values()]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


class AutonomousController:
    """Continuous Observe -> Orient -> Decide -> Act controller."""

    def __init__(
        self,
        goal_manager: GoalManager | None = None,
        runtime_orchestrator: RuntimeOrchestrator | None = None,
        reflection_engine: ReflectionEngine | None = None,
        safety_manager: SafetyManager | None = None,
        decision_history: DecisionHistoryStore | None = None,
        mode: str = "autonomous",
    ) -> None:
        self.goal_manager = goal_manager or GoalManager()
        self.runtime_orchestrator = runtime_orchestrator or RuntimeOrchestrator(
            goal_manager=self.goal_manager
        )
        self.reflection_engine = reflection_engine or self.runtime_orchestrator.reflection_engine
        self.safety_manager = safety_manager or SafetyManager()
        self.decision_history = decision_history or DecisionHistoryStore()
        self.mode = mode

    def observe(self, mission_context: dict[str, Any]) -> Observation:
        signals = [
            key
            for key, value in mission_context.items()
            if value not in (None, "", [], {})
        ]
        return Observation(context=dict(mission_context), signals=signals)

    def orient(self, observation: Observation) -> Orientation:
        goals = [
            self.goal_manager.create_goal(goal)
            for goal in self.generate_goals(observation.context)
        ]
        risk = "HIGH" if observation.context.get("risk") == "HIGH" else "LOW"
        return Orientation(
            observation_id=observation.observation_id,
            goals=goals,
            risk=risk,
            summary=f"Generated {len(goals)} goal(s) from mission context.",
        )

    def decide(self, orientation: Orientation) -> Decision:
        if not orientation.goals:
            decision = Decision(
                goal="",
                action="NOOP",
                mode=self.mode,
                approved=False,
                status="SKIPPED",
                reason="No goals generated from context.",
            )
            self.decision_history.add(decision)
            return decision

        goal = orientation.goals[0].objective
        approved, reason = self.safety_manager.evaluate(
            goal,
            {"orientation": orientation},
        )
        if self.mode == "human_approval" and approved:
            approved = False
            reason = "Human approval required."

        decision = Decision(
            goal=goal,
            action="EXECUTE_MISSION",
            mode=self.mode,
            approved=approved,
            status="APPROVED" if approved else "PENDING_APPROVAL",
            reason=reason,
        )
        self.decision_history.add(decision)
        return decision

    def act(self, decision: Decision) -> Decision:
        if decision.action == "NOOP":
            return decision

        if not decision.approved:
            return decision

        mission = self._create_mission(decision.goal)
        result = self.runtime_orchestrator.run(mission)
        decision.result = result
        decision.status = "COMPLETED"
        decision.reason = "Mission executed."
        self.decision_history.add(decision)
        return decision

    def run_once(self, mission_context: dict[str, Any]) -> Decision:
        observation = self.observe(mission_context)
        orientation = self.orient(observation)
        decision = self.decide(orientation)
        return self.act(decision)

    def run_loop(
        self,
        mission_contexts: list[dict[str, Any]],
        max_cycles: int | None = None,
    ) -> list[Decision]:
        decisions: list[Decision] = []
        limit = max_cycles if max_cycles is not None else len(mission_contexts)
        for context in mission_contexts[:limit]:
            decisions.append(self.run_once(context))
        return decisions

    def approve(self, decision_id: str) -> Decision:
        decision = self.decision_history.get(decision_id)
        if decision is None:
            raise KeyError(f"Unknown decision: {decision_id}")

        decision.approved = True
        decision.status = "APPROVED"
        decision.reason = "Approved by human operator."
        self.decision_history.add(decision)
        return self.act(decision)

    def generate_goals(self, mission_context: dict[str, Any]) -> list[str]:
        explicit_goal = mission_context.get("goal") or mission_context.get("objective")
        if explicit_goal:
            return [str(explicit_goal)]

        reflection = mission_context.get("reflection")
        if reflection is not None:
            points = getattr(reflection, "improvement_points", None)
            if points:
                return [f"Improve future missions: {point}" for point in points]

        signals = mission_context.get("signals", [])
        if signals:
            return [f"Investigate signal: {signal}" for signal in signals]

        return []

    def history(self) -> list[Decision]:
        return self.decision_history.history()

    def _create_mission(self, goal: str) -> Mission:
        return Mission(
            title=goal.strip() or "Untitled Autonomous Goal",
            objective=goal.strip(),
            mission_type=MissionType.GENERAL,
            priority=Priority.NORMAL,
            expected_output="brief",
        )
