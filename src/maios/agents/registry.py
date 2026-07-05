from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from maios.agents.base import Agent


@dataclass(frozen=True)
class AgentCapability:
    name: str
    description: str = ""
    input_types: tuple[str, ...] = ()
    output_types: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegisteredAgent:
    agent: Agent
    agent_id: str
    agent_type: str
    capabilities: tuple[AgentCapability, ...] = ()
    active_tasks: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_capability(self, capability: str | AgentCapability) -> bool:
        name = capability.name if isinstance(capability, AgentCapability) else capability
        return any(item.name == name for item in self.capabilities)


class AgentRegistry:
    """Registry for dynamically discovering executable agent instances."""

    def __init__(self) -> None:
        self._agents: dict[str, RegisteredAgent] = {}

    def register(
        self,
        agent: Agent,
        capabilities: list[AgentCapability] | tuple[AgentCapability, ...] | None = None,
        agent_id: str | None = None,
        agent_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RegisteredAgent:
        registration = RegisteredAgent(
            agent=agent,
            agent_id=agent_id or f"AGENT-{uuid4().hex[:8]}",
            agent_type=agent_type or agent.name,
            capabilities=tuple(capabilities or ()),
            metadata=metadata or {},
        )
        self._agents[registration.agent_id] = registration
        return registration

    def unregister(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def get(self, agent_id: str) -> RegisteredAgent | None:
        return self._agents.get(agent_id)

    def all(self) -> list[RegisteredAgent]:
        return list(self._agents.values())

    def discover(
        self,
        capability: str | AgentCapability | None = None,
        agent_type: str | None = None,
    ) -> list[RegisteredAgent]:
        agents = self.all()
        if capability is not None:
            agents = [agent for agent in agents if agent.has_capability(capability)]
        if agent_type is not None:
            agents = [agent for agent in agents if agent.agent_type == agent_type]
        return agents
