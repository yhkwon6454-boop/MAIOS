from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from maios.agents.registry import AgentCapability, AgentRegistry, RegisteredAgent
from maios.agents.scheduler import RuntimeScheduler, RuntimeTask


@dataclass
class CollaborationTask:
    capability: str
    context: dict[str, Any]
    task_id: str = field(default_factory=lambda: f"COLLAB-{uuid4().hex[:8]}")
    agent_id: str = ""
    status: str = "QUEUED"
    result: dict[str, Any] | None = None
    error: str = ""


@dataclass
class Conflict:
    key: str
    values: dict[str, Any]
    resolved_value: Any = None
    strategy: str = ""


@dataclass
class ConsensusResult:
    decision: Any
    votes: dict[str, Any]
    approved: bool
    tie: bool = False


@dataclass
class CollaborationResult:
    team: list[RegisteredAgent]
    tasks: list[CollaborationTask]
    shared_memory: dict[str, Any]
    conflicts: list[Conflict] = field(default_factory=list)
    consensus: ConsensusResult | None = None


class CollaborationManager:
    """Coordinates collaborative execution across registered agents."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        scheduler: RuntimeScheduler | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.scheduler = scheduler or RuntimeScheduler(self.registry)
        self.shared_memory: dict[str, Any] = {}
        self.conflicts: list[Conflict] = []

    def form_team(
        self,
        capabilities: list[str | AgentCapability],
        include_all_instances: bool = False,
    ) -> list[RegisteredAgent]:
        team: list[RegisteredAgent] = []
        seen: set[str] = set()

        for capability in capabilities:
            matches = self.registry.discover(capability=capability)
            selected = matches if include_all_instances else matches[:1]
            for registration in selected:
                if registration.agent_id not in seen:
                    team.append(registration)
                    seen.add(registration.agent_id)

        return team

    def remember(self, key: str, value: Any) -> None:
        self.shared_memory[key] = value

    def recall(self, key: str, default: Any = None) -> Any:
        return self.shared_memory.get(key, default)

    def delegate(
        self,
        capability: str | AgentCapability,
        context: dict[str, Any],
        agent_type: str | None = None,
    ) -> CollaborationTask:
        merged_context = {
            **context,
            "shared_memory": dict(self.shared_memory),
        }
        runtime_task = self.scheduler.dispatch(
            capability,
            merged_context,
            agent_type=agent_type,
        )
        task = self._collaboration_task(runtime_task)
        self._merge_result(task)
        return task

    def execute_pipeline(
        self,
        steps: list[tuple[str | AgentCapability, dict[str, Any]]],
    ) -> CollaborationResult:
        tasks = []
        for capability, context in steps:
            tasks.append(self.delegate(capability, context))

        conflicts = self.detect_conflicts(
            [task.result for task in tasks if task.result is not None]
        )
        if conflicts:
            self.resolve_conflicts(conflicts)

        return CollaborationResult(
            team=self.form_team([capability for capability, _context in steps]),
            tasks=tasks,
            shared_memory=dict(self.shared_memory),
            conflicts=conflicts,
        )

    def detect_conflicts(self, results: list[dict[str, Any]]) -> list[Conflict]:
        observed: dict[str, dict[str, Any]] = {}
        for index, result in enumerate(results):
            source = str(result.get("agent_id", f"result-{index}"))
            for key, value in result.items():
                if key.startswith("_") or key in {"agent_id", "shared_memory"}:
                    continue
                observed.setdefault(key, {})[source] = value

        conflicts = []
        for key, values in observed.items():
            unique_values = {repr(value) for value in values.values()}
            if len(unique_values) > 1:
                conflicts.append(Conflict(key=key, values=values))

        self.conflicts = conflicts
        return conflicts

    def resolve_conflicts(
        self,
        conflicts: list[Conflict] | None = None,
        strategy: str = "majority",
    ) -> list[Conflict]:
        resolved_conflicts = conflicts if conflicts is not None else self.conflicts
        for conflict in resolved_conflicts:
            decision = self._majority_value(list(conflict.values.values()))
            conflict.resolved_value = decision
            conflict.strategy = strategy
            self.shared_memory[conflict.key] = decision
        return resolved_conflicts

    def vote(
        self,
        proposal: Any,
        votes: dict[str, Any],
        quorum: int | None = None,
    ) -> ConsensusResult:
        if not votes:
            result = ConsensusResult(decision=None, votes={}, approved=False)
            self.shared_memory["last_consensus"] = result
            return result

        quorum_size = quorum or ((len(votes) // 2) + 1)
        decision = self._majority_value(list(votes.values()))
        approval_count = sum(1 for vote in votes.values() if vote == decision)
        tie = self._is_tie(list(votes.values()))
        result = ConsensusResult(
            decision=decision,
            votes=dict(votes),
            approved=not tie and approval_count >= quorum_size and decision == proposal,
            tie=tie,
        )
        self.shared_memory["last_consensus"] = result
        return result

    def _collaboration_task(self, task: RuntimeTask) -> CollaborationTask:
        return CollaborationTask(
            capability=task.capability,
            context=task.context,
            task_id=task.task_id,
            agent_id=task.agent_id,
            status=task.status,
            result=task.result,
            error=task.error,
        )

    def _merge_result(self, task: CollaborationTask) -> None:
        if task.result is None:
            return

        task.result.setdefault("agent_id", task.agent_id)
        memory_update = task.result.get("shared_memory")
        if isinstance(memory_update, dict):
            self.shared_memory.update(memory_update)
        if "output" in task.result:
            self.shared_memory[task.capability] = task.result["output"]

    def _majority_value(self, values: list[Any]) -> Any:
        ordered_counts: list[tuple[Any, int]] = []
        for value in values:
            for index, (existing, count) in enumerate(ordered_counts):
                if existing == value:
                    ordered_counts[index] = (existing, count + 1)
                    break
            else:
                ordered_counts.append((value, 1))

        return sorted(ordered_counts, key=lambda item: -item[1])[0][0]

    def _is_tie(self, values: list[Any]) -> bool:
        counts: dict[str, int] = {}
        for value in values:
            key = repr(value)
            counts[key] = counts.get(key, 0) + 1
        return len([count for count in counts.values() if count == max(counts.values())]) > 1
