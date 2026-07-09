from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class AutonomousTask:
    description: str
    priority: int = 50
    status: str = "PENDING"
    task_id: str = field(default_factory=lambda: f"T-{uuid4().hex[:8]}")
    feedback: list[str] = field(default_factory=list)


@dataclass
class Goal:
    objective: str
    goal_id: str = field(default_factory=lambda: f"G-{uuid4().hex[:8]}")
    tasks: list[AutonomousTask] = field(default_factory=list)
    status: str = "CREATED"


class TaskDecomposer:
    """Rule-based goal decomposition for offline autonomous planning."""

    def decompose(self, goal: str) -> list[AutonomousTask]:
        objective = goal.strip()
        return [
            AutonomousTask(f"Understand goal: {objective}", priority=90),
            AutonomousTask(f"Gather relevant memory for: {objective}", priority=80),
            AutonomousTask(f"Generate solution for: {objective}", priority=70),
            AutonomousTask(f"Review output for: {objective}", priority=60),
        ]


class PriorityEngine:
    """Reprioritizes tasks based on execution feedback."""

    def sort(self, tasks: list[AutonomousTask]) -> list[AutonomousTask]:
        return sorted(tasks, key=lambda task: task.priority, reverse=True)

    def reprioritize(
        self,
        tasks: list[AutonomousTask],
        feedback: dict[str, str] | None = None,
    ) -> list[AutonomousTask]:
        feedback = feedback or {}

        for task in tasks:
            message = feedback.get(task.task_id, "")
            if not message:
                continue

            task.feedback.append(message)
            lowered = message.lower()
            if any(token in lowered for token in ["fail", "blocked", "revise", "retry"]):
                task.priority += 40
                task.status = "PENDING"
            elif any(token in lowered for token in ["done", "complete", "success"]):
                task.priority = max(0, task.priority - 50)
                task.status = "COMPLETED"

        return self.sort(tasks)


class GoalManager:
    def __init__(
        self,
        task_decomposer: TaskDecomposer | None = None,
        priority_engine: PriorityEngine | None = None,
    ) -> None:
        self.task_decomposer = task_decomposer or TaskDecomposer()
        self.priority_engine = priority_engine or PriorityEngine()
        self.goals: dict[str, Goal] = {}

    def create_goal(self, objective: str) -> Goal:
        goal = Goal(objective=objective)
        goal.tasks = self.priority_engine.sort(self.task_decomposer.decompose(objective))
        goal.status = "READY"
        self.goals[goal.goal_id] = goal
        return goal

    def next_task(self, goal: Goal) -> AutonomousTask | None:
        pending = [task for task in goal.tasks if task.status == "PENDING"]
        if not pending:
            goal.status = "COMPLETED"
            return None

        task = self.priority_engine.sort(pending)[0]
        task.status = "RUNNING"
        return task

    def complete_task(
        self, goal: Goal, task: AutonomousTask, feedback: str = "done"
    ) -> list[AutonomousTask]:
        task.status = "COMPLETED"
        task.feedback.append(feedback)
        return self.priority_engine.reprioritize(goal.tasks, {task.task_id: feedback})

    def apply_feedback(self, goal: Goal, feedback: dict[str, str]) -> list[AutonomousTask]:
        goal.tasks = self.priority_engine.reprioritize(goal.tasks, feedback)
        return goal.tasks
