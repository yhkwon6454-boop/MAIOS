from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from maios.agents.registry import AgentCapability, AgentRegistry, RegisteredAgent


@dataclass
class RuntimeTask:
    capability: str
    context: dict[str, Any]
    task_id: str = field(default_factory=lambda: f"TASK-{uuid4().hex[:8]}")
    agent_id: str = ""
    status: str = "QUEUED"
    result: dict[str, Any] | None = None
    error: str = ""


class RuntimeScheduler:
    """Dispatches runtime tasks to registered agents by capability."""

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self.registry = registry or AgentRegistry()
        self.history: list[RuntimeTask] = []

    def dispatch(
        self,
        capability: str | AgentCapability,
        context: dict[str, Any],
        agent_type: str | None = None,
    ) -> RuntimeTask:
        task = RuntimeTask(
            capability=capability.name if isinstance(capability, AgentCapability) else capability,
            context=context,
        )
        registration = self.select_agent(task.capability, agent_type=agent_type)
        task.agent_id = registration.agent_id
        task.status = "RUNNING"
        registration.active_tasks += 1
        try:
            task.result = registration.agent.execute(context)
        except Exception as exc:
            task.status = "FAILED"
            task.error = str(exc)
        else:
            task.status = "COMPLETED"
        finally:
            registration.active_tasks -= 1
            self.history.append(task)

        return task

    def select_agent(
        self,
        capability: str | AgentCapability,
        agent_type: str | None = None,
    ) -> RegisteredAgent:
        candidates = self.registry.discover(capability=capability, agent_type=agent_type)
        if not candidates:
            capability_name = (
                capability.name if isinstance(capability, AgentCapability) else capability
            )
            raise RuntimeError(f"No registered agent supports capability: {capability_name}")

        return sorted(
            candidates,
            key=lambda item: (
                item.active_tasks,
                item.agent_type,
                item.agent_id,
            ),
        )[0]

    def dispatch_many(
        self,
        tasks: list[tuple[str | AgentCapability, dict[str, Any]]],
    ) -> list[RuntimeTask]:
        return [self.dispatch(capability, context) for capability, context in tasks]
