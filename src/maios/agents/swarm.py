from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from maios.agents.negotiation import NegotiationManager
from maios.agents.registry import AgentCapability, AgentRegistry, RegisteredAgent
from maios.agents.roles import AgentRole, AgentRoleManager
from maios.agents.shared_memory import SharedMemoryManager
from maios.events import EventBus
from maios.knowledge.graph import KnowledgeGraph
from maios.protocol import AgentProtocolError


@dataclass
class SwarmTask:
    capability: str
    context: dict[str, Any]
    task_id: str = field(default_factory=lambda: f"SWARM-TASK-{uuid4().hex[:8]}")
    assigned_agent_id: str = ""
    replacement_agent_id: str = ""
    status: str = "QUEUED"
    result: dict[str, Any] | None = None
    error: str = ""


@dataclass
class SwarmHealth:
    swarm_id: str
    leader_id: str
    healthy: bool
    active_agents: list[str]
    failed_agents: list[str]
    load_by_agent: dict[str, int]


@dataclass
class Swarm:
    name: str
    capabilities: tuple[str, ...]
    swarm_id: str = field(default_factory=lambda: f"SWARM-{uuid4().hex[:8]}")
    members: list[str] = field(default_factory=list)
    leader_id: str = ""
    failed_agents: set[str] = field(default_factory=set)
    tasks: list[SwarmTask] = field(default_factory=list)
    status: str = "ACTIVE"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class SwarmManager:
    """Forms and coordinates resilient decentralized swarms of registered agents."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        role_manager: AgentRoleManager | None = None,
        negotiation_manager: NegotiationManager | None = None,
        shared_memory_manager: SharedMemoryManager | None = None,
        event_bus: EventBus | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        mission_id: str = "default",
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.role_manager = role_manager
        self.negotiation_manager = negotiation_manager
        self.shared_memory_manager = shared_memory_manager or SharedMemoryManager()
        self.event_bus = event_bus or EventBus()
        self.knowledge_graph = knowledge_graph
        self.mission_id = mission_id
        self._swarms: dict[str, Swarm] = {}
        self.shared_memory_manager.create_workspace(self.mission_id)

    def form_swarm(
        self,
        name: str,
        capabilities: list[str | AgentCapability] | tuple[str | AgentCapability, ...],
        role: AgentRole | str | None = None,
        size: int | None = None,
    ) -> Swarm:
        capability_names = tuple(self._capability_name(capability) for capability in capabilities)
        members = self._select_members(capabilities, role=role, size=size)
        swarm = Swarm(
            name=name,
            capabilities=capability_names,
            members=[member.agent_id for member in members],
        )
        self._swarms[swarm.swarm_id] = swarm
        self.elect_leader(swarm.swarm_id)
        self._record_swarm(swarm)
        self._record_swarm_knowledge(swarm)
        self._publish(
            "swarm.formed",
            {
                "swarm_id": swarm.swarm_id,
                "name": swarm.name,
                "members": list(swarm.members),
                "leader_id": swarm.leader_id,
            },
        )
        return swarm

    def elect_leader(self, swarm_id: str) -> RegisteredAgent | None:
        swarm = self._require_swarm(swarm_id)
        candidates = self._active_members(swarm)
        if not candidates:
            swarm.leader_id = ""
            swarm.status = "DEGRADED"
            self._record_swarm(swarm)
            return None

        leader = sorted(candidates, key=self._leader_key)[0]
        swarm.leader_id = leader.agent_id
        self._record_swarm(swarm)
        self._publish(
            "swarm.leader.elected",
            {"swarm_id": swarm.swarm_id, "leader_id": leader.agent_id},
        )
        return leader

    def allocate_task(
        self,
        swarm_id: str,
        capability: str | AgentCapability,
        context: dict[str, Any],
    ) -> SwarmTask:
        swarm = self._require_swarm(swarm_id)
        capability_name = self._capability_name(capability)
        task = SwarmTask(capability=capability_name, context=context)
        swarm.tasks.append(task)

        registration = self._select_task_agent(swarm, capability_name)
        if registration is None:
            registration = self.replace_agent(swarm_id, "", capability_name)
        if registration is None:
            task.status = "FAILED"
            task.error = f"No swarm agent can handle capability: {capability_name}"
            self._record_swarm(swarm)
            self._record_task_experience(swarm, task)
            return task

        self._execute_task(swarm, task, registration)
        self._record_swarm(swarm)
        self._record_task_experience(swarm, task)
        return task

    def distribute_tasks(
        self,
        swarm_id: str,
        tasks: list[tuple[str | AgentCapability, dict[str, Any]]],
    ) -> list[SwarmTask]:
        return [self.allocate_task(swarm_id, capability, context) for capability, context in tasks]

    def replace_agent(
        self,
        swarm_id: str,
        failed_agent_id: str,
        capability: str | AgentCapability | None = None,
    ) -> RegisteredAgent | None:
        swarm = self._require_swarm(swarm_id)
        if failed_agent_id:
            swarm.failed_agents.add(failed_agent_id)
            if failed_agent_id == swarm.leader_id:
                swarm.leader_id = ""

        replacement = self._replacement_candidate(swarm, capability)
        if replacement is None:
            self.elect_leader(swarm.swarm_id)
            self._record_swarm(swarm)
            return None

        if replacement.agent_id not in swarm.members:
            swarm.members.append(replacement.agent_id)
        if not swarm.leader_id:
            self.elect_leader(swarm.swarm_id)
        self._record_swarm(swarm)
        self._publish(
            "swarm.agent.replaced",
            {
                "swarm_id": swarm.swarm_id,
                "failed_agent_id": failed_agent_id,
                "replacement_agent_id": replacement.agent_id,
            },
        )
        return replacement

    def mark_failed(self, swarm_id: str, agent_id: str) -> None:
        swarm = self._require_swarm(swarm_id)
        swarm.failed_agents.add(agent_id)
        if swarm.leader_id == agent_id:
            self.elect_leader(swarm_id)
        self._record_swarm(swarm)
        self._publish("swarm.agent.failed", {"swarm_id": swarm_id, "agent_id": agent_id})

    def monitor_health(self, swarm_id: str) -> SwarmHealth:
        swarm = self._require_swarm(swarm_id)
        active = [
            agent_id
            for agent_id in swarm.members
            if agent_id not in swarm.failed_agents and self.registry.get(agent_id) is not None
        ]
        load_by_agent = {}
        for agent_id in active:
            registration = self.registry.get(agent_id)
            if registration is not None:
                load_by_agent[agent_id] = registration.active_tasks
        health = SwarmHealth(
            swarm_id=swarm.swarm_id,
            leader_id=swarm.leader_id,
            healthy=bool(active) and bool(swarm.leader_id),
            active_agents=active,
            failed_agents=sorted(swarm.failed_agents),
            load_by_agent=load_by_agent,
        )
        if not health.healthy:
            swarm.status = "DEGRADED"
        self._publish(
            "swarm.health.checked",
            {
                "swarm_id": swarm.swarm_id,
                "healthy": health.healthy,
                "active_agents": list(active),
                "failed_agents": health.failed_agents,
            },
        )
        self._record_swarm(swarm)
        return health

    def swarm(self, swarm_id: str) -> Swarm | None:
        return self._swarms.get(swarm_id)

    def swarms(self) -> list[Swarm]:
        return list(self._swarms.values())

    def _execute_task(
        self,
        swarm: Swarm,
        task: SwarmTask,
        registration: RegisteredAgent,
    ) -> None:
        task.assigned_agent_id = registration.agent_id
        task.status = "RUNNING"
        registration.active_tasks += 1
        try:
            task.result = registration.agent.execute(
                {
                    **task.context,
                    "swarm_id": swarm.swarm_id,
                    "leader_id": swarm.leader_id,
                    "shared_memory": self.shared_memory_manager.read_all(
                        self.mission_id,
                        agent_id="swarm",
                    ),
                    "shared_memory_manager": self.shared_memory_manager,
                }
            )
        except Exception as exc:
            task.error = str(exc)
            self.mark_failed(swarm.swarm_id, registration.agent_id)
            replacement = self.replace_agent(swarm.swarm_id, registration.agent_id, task.capability)
            if replacement is None:
                task.status = "FAILED"
                return
            task.replacement_agent_id = replacement.agent_id
            self._execute_replacement(swarm, task, replacement)
        else:
            task.status = "COMPLETED"
            self._merge_task_result(task, registration.agent_id)
        finally:
            registration.active_tasks -= 1

    def _execute_replacement(
        self,
        swarm: Swarm,
        task: SwarmTask,
        registration: RegisteredAgent,
    ) -> None:
        registration.active_tasks += 1
        try:
            task.result = registration.agent.execute(
                {
                    **task.context,
                    "swarm_id": swarm.swarm_id,
                    "leader_id": swarm.leader_id,
                    "replacement_for": task.assigned_agent_id,
                    "shared_memory": self.shared_memory_manager.read_all(
                        self.mission_id,
                        agent_id="swarm",
                    ),
                    "shared_memory_manager": self.shared_memory_manager,
                }
            )
        except Exception as exc:
            task.status = "FAILED"
            task.error = str(exc)
            self.mark_failed(swarm.swarm_id, registration.agent_id)
        else:
            task.status = "COMPLETED"
            self._merge_task_result(task, registration.agent_id)
        finally:
            registration.active_tasks -= 1

    def _merge_task_result(self, task: SwarmTask, agent_id: str) -> None:
        if task.result is None:
            return
        memory_update = task.result.get("shared_memory")
        if isinstance(memory_update, dict):
            for key, value in memory_update.items():
                self.shared_memory_manager.write(
                    self.mission_id,
                    agent_id=agent_id,
                    key=key,
                    value=value,
                )
        if "output" in task.result:
            self.shared_memory_manager.write(
                self.mission_id,
                agent_id=agent_id,
                key=task.capability,
                value=task.result["output"],
            )

    def _select_members(
        self,
        capabilities: list[str | AgentCapability] | tuple[str | AgentCapability, ...],
        role: AgentRole | str | None,
        size: int | None,
    ) -> list[RegisteredAgent]:
        if not capabilities:
            candidates = self.registry.all()
        elif self.role_manager is not None:
            seen: dict[str, RegisteredAgent] = {}
            for capability in capabilities:
                for agent in self.role_manager.select_agents([capability], role=role):
                    seen[agent.agent_id] = agent
            candidates = list(seen.values())
        else:
            seen = {}
            for capability in capabilities:
                for agent in self.registry.discover(capability=capability):
                    seen[agent.agent_id] = agent
            candidates = list(seen.values())

        selected = sorted(candidates, key=self._load_key)
        return selected if size is None else selected[:size]

    def _select_task_agent(
        self,
        swarm: Swarm,
        capability: str,
    ) -> RegisteredAgent | None:
        candidates = [
            registration
            for registration in self._active_members(swarm)
            if registration.has_capability(capability)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=self._load_key)[0]

    def _replacement_candidate(
        self,
        swarm: Swarm,
        capability: str | AgentCapability | None,
    ) -> RegisteredAgent | None:
        capability_name = self._capability_name(capability) if capability is not None else ""
        candidates = []
        for registration in self.registry.all():
            if registration.agent_id in swarm.members:
                continue
            if registration.agent_id in swarm.failed_agents:
                continue
            if capability_name and not registration.has_capability(capability_name):
                continue
            candidates.append(registration)
        if not candidates:
            return None
        return sorted(candidates, key=self._load_key)[0]

    def _active_members(self, swarm: Swarm) -> list[RegisteredAgent]:
        members = []
        for agent_id in swarm.members:
            registration = self.registry.get(agent_id)
            if registration is not None and agent_id not in swarm.failed_agents:
                members.append(registration)
        return members

    def _leader_key(self, registration: RegisteredAgent) -> tuple[int, int, str]:
        coordinator_score = 0
        if self.role_manager is not None:
            profile = self.role_manager.profile(registration.agent_id)
            if profile is not None and profile.has_role(AgentRole.COORDINATOR):
                coordinator_score = 1
        return (
            -coordinator_score,
            registration.active_tasks,
            registration.agent_id,
        )

    def _load_key(self, registration: RegisteredAgent) -> tuple[int, str]:
        return (registration.active_tasks, registration.agent_id)

    def _capability_name(self, capability: str | AgentCapability) -> str:
        return capability.name if isinstance(capability, AgentCapability) else capability

    def _require_swarm(self, swarm_id: str) -> Swarm:
        swarm = self.swarm(swarm_id)
        if swarm is None:
            raise KeyError(f"Unknown swarm: {swarm_id}")
        return swarm

    def _record_swarm(self, swarm: Swarm) -> None:
        self.shared_memory_manager.write(
            self.mission_id,
            agent_id="swarm",
            key=f"swarm:{swarm.swarm_id}",
            value={
                "swarm_id": swarm.swarm_id,
                "name": swarm.name,
                "leader_id": swarm.leader_id,
                "members": list(swarm.members),
                "failed_agents": sorted(swarm.failed_agents),
                "status": swarm.status,
                "capabilities": list(swarm.capabilities),
            },
        )

    def _record_swarm_knowledge(self, swarm: Swarm) -> None:
        if self.knowledge_graph is None:
            return
        self.knowledge_graph.add_node(
            title=f"Swarm: {swarm.name}",
            content=(
                f"Swarm {swarm.swarm_id} formed with leader {swarm.leader_id} "
                f"and capabilities {', '.join(swarm.capabilities)}."
            ),
            node_type="swarm",
            metadata={
                "swarm_id": swarm.swarm_id,
                "leader_id": swarm.leader_id,
                "members": list(swarm.members),
                "capabilities": list(swarm.capabilities),
            },
            node_id=swarm.swarm_id,
        )

    def _record_task_experience(self, swarm: Swarm, task: SwarmTask) -> None:
        if self.knowledge_graph is None:
            return
        self.knowledge_graph.learn_experience(
            description=(
                f"Swarm {swarm.name} handled {task.capability} task "
                f"{task.task_id} with status {task.status}."
            ),
            outcome="success" if task.status == "COMPLETED" else "failure",
            metadata={
                "swarm_id": swarm.swarm_id,
                "task_id": task.task_id,
                "capability": task.capability,
                "assigned_agent_id": task.assigned_agent_id,
            },
        )

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            self.event_bus.publish(event_type, payload, source="swarm")
        except AgentProtocolError:
            protocol = self.event_bus.protocol
            self.event_bus.protocol = None
            try:
                self.event_bus.publish(event_type, payload, source="swarm")
            finally:
                self.event_bus.protocol = protocol
