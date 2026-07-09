from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from maios.agents.registry import AgentCapability, AgentRegistry, RegisteredAgent
from maios.agents.shared_memory import SharedMemoryManager


class AgentRole(StrEnum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    MEMORY = "memory"
    QUALITY = "quality"
    REFLECTION = "reflection"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    OBSERVER = "observer"


@dataclass
class AgentProfile:
    agent_id: str
    primary_role: AgentRole | str
    capabilities: tuple[AgentCapability, ...] = ()
    secondary_roles: tuple[AgentRole | str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: AgentRole | str, include_secondary: bool = True) -> bool:
        normalized = self.normalize_role(role)
        if self.normalize_role(self.primary_role) == normalized:
            return True
        return include_secondary and any(
            self.normalize_role(item) == normalized for item in self.secondary_roles
        )

    def has_capability(self, capability: str | AgentCapability) -> bool:
        name = capability.name if isinstance(capability, AgentCapability) else capability
        return any(item.name == name for item in self.capabilities)

    @staticmethod
    def normalize_role(role: AgentRole | str) -> str:
        return role.value if isinstance(role, AgentRole) else role


class AgentRoleManager:
    """Tracks runtime roles and capability profiles for registered agents."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        shared_memory_manager: SharedMemoryManager | None = None,
        mission_id: str = "default",
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.shared_memory_manager = shared_memory_manager
        self.mission_id = mission_id
        self._profiles: dict[str, AgentProfile] = {}
        if self.shared_memory_manager is not None:
            self.shared_memory_manager.create_workspace(self.mission_id)

    def assign_role(
        self,
        agent_id: str,
        primary_role: AgentRole | str,
        capabilities: list[AgentCapability] | tuple[AgentCapability, ...] | None = None,
        secondary_roles: list[AgentRole | str] | tuple[AgentRole | str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentProfile:
        registration = self._require_agent(agent_id)
        profile = AgentProfile(
            agent_id=agent_id,
            primary_role=primary_role,
            secondary_roles=tuple(secondary_roles or ()),
            capabilities=tuple(capabilities or registration.capabilities),
            metadata=metadata or {},
        )
        self._profiles[agent_id] = profile
        self._sync_registration(registration, profile)
        self._record_profile(profile)
        return profile

    def reassign_role(
        self,
        agent_id: str,
        primary_role: AgentRole | str,
        secondary_roles: list[AgentRole | str] | tuple[AgentRole | str, ...] | None = None,
    ) -> AgentProfile:
        current = self._profiles.get(agent_id)
        registration = self._require_agent(agent_id)
        profile = AgentProfile(
            agent_id=agent_id,
            primary_role=primary_role,
            secondary_roles=tuple(
                secondary_roles
                if secondary_roles is not None
                else (current.secondary_roles if current is not None else ())
            ),
            capabilities=current.capabilities if current is not None else registration.capabilities,
            metadata=current.metadata if current is not None else {},
        )
        self._profiles[agent_id] = profile
        self._sync_registration(registration, profile)
        self._record_profile(profile)
        return profile

    def add_secondary_role(self, agent_id: str, role: AgentRole | str) -> AgentProfile:
        profile = self.profile(agent_id)
        if profile is None:
            registration = self._require_agent(agent_id)
            profile = self.assign_role(agent_id, registration.agent_type)

        normalized = AgentProfile.normalize_role(role)
        secondary_roles = list(profile.secondary_roles)
        if normalized not in [AgentProfile.normalize_role(item) for item in secondary_roles]:
            secondary_roles.append(role)
        return self.assign_role(
            agent_id,
            profile.primary_role,
            capabilities=profile.capabilities,
            secondary_roles=secondary_roles,
            metadata=profile.metadata,
        )

    def remove_secondary_role(self, agent_id: str, role: AgentRole | str) -> AgentProfile:
        profile = self._require_profile(agent_id)
        normalized = AgentProfile.normalize_role(role)
        secondary_roles = [
            item
            for item in profile.secondary_roles
            if AgentProfile.normalize_role(item) != normalized
        ]
        return self.assign_role(
            agent_id,
            profile.primary_role,
            capabilities=profile.capabilities,
            secondary_roles=secondary_roles,
            metadata=profile.metadata,
        )

    def profile(self, agent_id: str) -> AgentProfile | None:
        profile = self._profiles.get(agent_id)
        if profile is not None:
            return profile

        registration = self.registry.get(agent_id)
        if registration is None:
            return None

        return AgentProfile(
            agent_id=registration.agent_id,
            primary_role=str(registration.metadata.get("primary_role", registration.agent_type)),
            secondary_roles=tuple(registration.metadata.get("secondary_roles", ())),
            capabilities=registration.capabilities,
            metadata=dict(registration.metadata.get("role_metadata", {})),
        )

    def profiles(self) -> list[AgentProfile]:
        profiles = []
        for agent in self.registry.all():
            profile = self.profile(agent.agent_id)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def select_agents(
        self,
        capabilities: list[str | AgentCapability] | tuple[str | AgentCapability, ...],
        role: AgentRole | str | None = None,
        include_secondary_roles: bool = True,
        limit: int | None = None,
    ) -> list[RegisteredAgent]:
        required = tuple(capabilities)
        candidates = []
        for registration in self.registry.all():
            profile = self.profile(registration.agent_id)
            if profile is None:
                continue
            if role is not None and not profile.has_role(role, include_secondary_roles):
                continue
            if not all(profile.has_capability(capability) for capability in required):
                continue
            candidates.append(registration)

        selected = sorted(
            candidates,
            key=lambda registration: self._selection_key(
                registration,
                role=role,
                include_secondary_roles=include_secondary_roles,
            ),
        )
        return selected if limit is None else selected[:limit]

    def select_best(
        self,
        capability: str | AgentCapability,
        role: AgentRole | str | None = None,
        include_secondary_roles: bool = True,
    ) -> RegisteredAgent | None:
        matches = self.select_agents(
            [capability],
            role=role,
            include_secondary_roles=include_secondary_roles,
            limit=1,
        )
        return matches[0] if matches else None

    def unregister(self, agent_id: str) -> None:
        self._profiles.pop(agent_id, None)

    def _selection_key(
        self,
        registration: RegisteredAgent,
        role: AgentRole | str | None,
        include_secondary_roles: bool,
    ) -> tuple[int, int, int, str]:
        profile = self.profile(registration.agent_id)
        primary_role_match = 0
        secondary_role_match = 0
        if profile is not None and role is not None:
            normalized = AgentProfile.normalize_role(role)
            primary_role_match = int(profile.normalize_role(profile.primary_role) == normalized)
            secondary_role_match = int(
                include_secondary_roles
                and any(
                    profile.normalize_role(item) == normalized for item in profile.secondary_roles
                )
            )
        return (
            -primary_role_match,
            -secondary_role_match,
            registration.active_tasks,
            registration.agent_id,
        )

    def _require_agent(self, agent_id: str) -> RegisteredAgent:
        registration = self.registry.get(agent_id)
        if registration is None:
            raise KeyError(f"Unknown agent: {agent_id}")
        return registration

    def _require_profile(self, agent_id: str) -> AgentProfile:
        profile = self.profile(agent_id)
        if profile is None:
            raise KeyError(f"Unknown agent profile: {agent_id}")
        return profile

    def _sync_registration(
        self,
        registration: RegisteredAgent,
        profile: AgentProfile,
    ) -> None:
        registration.metadata["primary_role"] = AgentProfile.normalize_role(profile.primary_role)
        registration.metadata["secondary_roles"] = [
            AgentProfile.normalize_role(role) for role in profile.secondary_roles
        ]
        registration.metadata["role_metadata"] = dict(profile.metadata)

    def _record_profile(self, profile: AgentProfile) -> None:
        if self.shared_memory_manager is None:
            return

        self.shared_memory_manager.write(
            self.mission_id,
            agent_id="role_manager",
            key=f"agent_profile:{profile.agent_id}",
            value={
                "agent_id": profile.agent_id,
                "primary_role": AgentProfile.normalize_role(profile.primary_role),
                "secondary_roles": [
                    AgentProfile.normalize_role(role) for role in profile.secondary_roles
                ],
                "capabilities": [capability.name for capability in profile.capabilities],
                "metadata": dict(profile.metadata),
            },
        )
