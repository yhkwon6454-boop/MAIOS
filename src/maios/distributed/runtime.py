from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from queue import Empty, Queue
from time import time
from typing import Any, Protocol
from uuid import uuid4

from maios.agents import (
    Agent,
    AgentCapability,
    AgentRegistry,
    AgentRole,
    AgentRoleManager,
    CollaborationManager,
    NegotiationManager,
    NegotiationSession,
    RegisteredAgent,
    RuntimeScheduler,
    RuntimeTask,
    SharedMemoryManager,
    Swarm,
    SwarmManager,
    SwarmTask,
)
from maios.core import MAIOSCore, MissionResult
from maios.events import EventBus
from maios.protocol import AgentProtocol, AgentProtocolError, MessageType


class Transport(Protocol):
    def execute(self, node: Node, goal: str) -> MissionResult: ...


@dataclass
class RuntimeNode:
    node_id: str
    address: str = "local"
    capacity: int = 1
    active_tasks: int = 0
    healthy: bool = True
    last_heartbeat: float = field(default_factory=time)
    metadata: dict[str, Any] = field(default_factory=dict)
    agent_ids: list[str] = field(default_factory=list)

    def available_capacity(self) -> int:
        return max(0, self.capacity - self.active_tasks)


Node = RuntimeNode


@dataclass
class DistributedMission:
    goal: str
    mission_id: str = field(default_factory=lambda: f"DM-{uuid4().hex[:8]}")
    status: str = "QUEUED"
    assigned_node: str = ""
    result: MissionResult | None = None
    error: str = ""


class InMemoryTransport:
    """Transport that executes missions against in-process MAIOSCore instances."""

    def __init__(self) -> None:
        self.cores: dict[str, MAIOSCore] = {}

    def register_core(self, node_id: str, core: MAIOSCore) -> None:
        self.cores[node_id] = core

    def execute(self, node: Node, goal: str) -> MissionResult:
        core = self.cores.get(node.node_id)
        if core is None:
            raise RuntimeError(f"No MAIOSCore registered for node: {node.node_id}")

        return core.run(goal)


class NodeManager:
    def __init__(self) -> None:
        self.nodes: dict[str, RuntimeNode] = {}

    def register_node(
        self,
        node_id: str,
        address: str = "local",
        capacity: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeNode:
        node = RuntimeNode(
            node_id=node_id,
            address=address,
            capacity=capacity,
            metadata=metadata or {},
        )
        self.nodes[node_id] = node
        return node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

    def get(self, node_id: str) -> RuntimeNode | None:
        return self.nodes.get(node_id)

    def heartbeat(self, node_id: str) -> RuntimeNode:
        node = self.nodes[node_id]
        node.healthy = True
        node.last_heartbeat = time()
        return node

    def healthy_nodes(self) -> list[RuntimeNode]:
        return [
            node for node in self.nodes.values() if node.healthy and node.available_capacity() > 0
        ]

    def select_node(self) -> RuntimeNode | None:
        candidates = self.healthy_nodes()
        if not candidates:
            return None

        return sorted(
            candidates,
            key=lambda node: (
                -node.available_capacity(),
                -node.capacity,
                node.active_tasks,
                node.node_id,
            ),
        )[0]


class HealthMonitor:
    def __init__(self, node_manager: NodeManager, timeout_seconds: float = 30.0) -> None:
        self.node_manager = node_manager
        self.timeout_seconds = timeout_seconds

    def heartbeat(self, node_id: str) -> RuntimeNode:
        return self.node_manager.heartbeat(node_id)

    def check(self) -> dict[str, bool]:
        now = time()
        health: dict[str, bool] = {}
        for node in self.node_manager.nodes.values():
            node.healthy = node.healthy and (now - node.last_heartbeat) <= self.timeout_seconds
            health[node.node_id] = node.healthy
        return health


class MissionScheduler:
    """Distributed mission queue."""

    def __init__(self) -> None:
        self._queue: Queue[DistributedMission] = Queue()
        self._missions: dict[str, DistributedMission] = {}

    def submit(self, goal: str) -> DistributedMission:
        mission = DistributedMission(goal=goal)
        self._missions[mission.mission_id] = mission
        self._queue.put(mission)
        return mission

    def next(self) -> DistributedMission | None:
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    def complete(
        self,
        mission: DistributedMission,
        result: MissionResult,
        node: RuntimeNode,
    ) -> None:
        mission.status = "COMPLETED"
        mission.result = result
        mission.assigned_node = node.node_id
        self._missions[mission.mission_id] = mission
        self._queue.task_done()

    def fail(
        self,
        mission: DistributedMission,
        error: str,
        node: RuntimeNode | None = None,
    ) -> None:
        mission.status = "FAILED"
        mission.error = error
        mission.assigned_node = node.node_id if node else ""
        self._missions[mission.mission_id] = mission
        self._queue.task_done()

    def get(self, mission_id: str) -> DistributedMission | None:
        return self._missions.get(mission_id)

    def history(self) -> list[DistributedMission]:
        return list(self._missions.values())

    def pending_count(self) -> int:
        return self._queue.qsize()


class TaskDispatcher:
    def __init__(
        self,
        node_manager: NodeManager,
        transport: Transport,
    ) -> None:
        self.node_manager = node_manager
        self.transport = transport

    def dispatch(self, goal: str) -> tuple[RuntimeNode, MissionResult]:
        node = self.node_manager.select_node()
        if node is None:
            raise RuntimeError("No healthy MAIOS nodes available.")

        node.active_tasks += 1
        try:
            result = self.transport.execute(node, goal)
        finally:
            node.active_tasks -= 1

        return node, result


class DistributedRuntime:
    def __init__(
        self,
        node_manager: NodeManager | None = None,
        transport: Transport | None = None,
        scheduler: MissionScheduler | None = None,
        health_monitor: HealthMonitor | None = None,
        dispatcher: TaskDispatcher | None = None,
        agent_registry: AgentRegistry | None = None,
        runtime_scheduler: RuntimeScheduler | None = None,
        event_bus: EventBus | None = None,
        agent_protocol: AgentProtocol | None = None,
        shared_memory_manager: SharedMemoryManager | None = None,
        collaboration_manager: CollaborationManager | None = None,
        role_manager: AgentRoleManager | None = None,
        negotiation_manager: NegotiationManager | None = None,
        swarm_manager: SwarmManager | None = None,
        mission_id: str = "default",
    ) -> None:
        self.node_manager = node_manager or NodeManager()
        self.transport = transport or InMemoryTransport()
        self.scheduler = scheduler or MissionScheduler()
        self.health_monitor = health_monitor or HealthMonitor(self.node_manager)
        self.dispatcher = dispatcher or TaskDispatcher(self.node_manager, self.transport)
        self.agent_registry = agent_registry or AgentRegistry()
        self.runtime_scheduler = runtime_scheduler or RuntimeScheduler(self.agent_registry)
        self.event_bus = event_bus or EventBus()
        self.agent_protocol = agent_protocol or AgentProtocol()
        self.shared_memory_manager = shared_memory_manager or SharedMemoryManager()
        self.mission_id = mission_id
        self.shared_memory_manager.create_workspace(self.mission_id)
        self.role_manager = role_manager or AgentRoleManager(
            registry=self.agent_registry,
            shared_memory_manager=self.shared_memory_manager,
            mission_id=self.mission_id,
        )
        self.negotiation_manager = negotiation_manager or NegotiationManager(
            role_manager=self.role_manager,
            event_bus=self.event_bus,
        )
        self.swarm_manager = swarm_manager or SwarmManager(
            registry=self.agent_registry,
            role_manager=self.role_manager,
            negotiation_manager=self.negotiation_manager,
            shared_memory_manager=self.shared_memory_manager,
            event_bus=self.event_bus,
            mission_id=self.mission_id,
        )
        self.collaboration_manager = collaboration_manager or CollaborationManager(
            registry=self.agent_registry,
            scheduler=self.runtime_scheduler,
            shared_memory_manager=self.shared_memory_manager,
            role_manager=self.role_manager,
            negotiation_manager=self.negotiation_manager,
            swarm_manager=self.swarm_manager,
            mission_id=self.mission_id,
        )

    def register_node(
        self,
        node_id: str,
        core: MAIOSCore | None = None,
        address: str = "local",
        capacity: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeNode:
        node = self.node_manager.register_node(
            node_id=node_id,
            address=address,
            capacity=capacity,
            metadata=metadata,
        )
        if core is not None and isinstance(self.transport, InMemoryTransport):
            self.transport.register_core(node_id, core)
        self._publish_runtime_event(
            "distributed.node.registered",
            {"node_id": node.node_id, "address": node.address, "capacity": node.capacity},
        )
        return node

    def unregister_node(self, node_id: str) -> bool:
        node = self.node_manager.get(node_id)
        if node is None:
            return False

        for agent_id in list(node.agent_ids):
            self.agent_registry.unregister(agent_id)
            self.role_manager.unregister(agent_id)
        self.node_manager.remove_node(node_id)
        self._publish_runtime_event(
            "distributed.node.unregistered",
            {"node_id": node_id},
        )
        return True

    def heartbeat(self, node_id: str) -> RuntimeNode:
        return self.health_monitor.heartbeat(node_id)

    def register_agent(
        self,
        agent: Agent,
        capabilities: list[AgentCapability] | tuple[AgentCapability, ...] | None = None,
        agent_id: str | None = None,
        agent_type: str | None = None,
        node_id: str = "local",
        metadata: dict[str, Any] | None = None,
        primary_role: AgentRole | str | None = None,
        secondary_roles: list[AgentRole | str] | tuple[AgentRole | str, ...] | None = None,
    ) -> RegisteredAgent:
        node = self.node_manager.get(node_id)
        if node is None:
            node = self.register_node(node_id)

        registration = self.agent_registry.register(
            agent,
            capabilities=capabilities,
            agent_id=agent_id,
            agent_type=agent_type,
            metadata={**(metadata or {}), "node_id": node.node_id},
        )
        node.agent_ids.append(registration.agent_id)
        if primary_role is not None:
            self.role_manager.assign_role(
                registration.agent_id,
                primary_role=primary_role,
                capabilities=registration.capabilities,
                secondary_roles=secondary_roles,
            )
        self._publish_runtime_event(
            "distributed.agent.registered",
            {
                "agent_id": registration.agent_id,
                "agent_type": registration.agent_type,
                "node_id": node.node_id,
                "capabilities": [capability.name for capability in registration.capabilities],
            },
        )
        return registration

    def unregister_agent(self, agent_id: str) -> bool:
        removed = self.agent_registry.unregister(agent_id)
        if not removed:
            return False
        self.role_manager.unregister(agent_id)

        for node in self.node_manager.nodes.values():
            if agent_id in node.agent_ids:
                node.agent_ids.remove(agent_id)
        self._publish_runtime_event(
            "distributed.agent.unregistered",
            {"agent_id": agent_id},
        )
        return True

    def execute_agent(
        self,
        capability: str | AgentCapability,
        context: dict[str, Any],
        agent_type: str | None = None,
        mission_id: str | None = None,
        role: AgentRole | str | None = None,
    ) -> RuntimeTask:
        active_mission_id = mission_id or self.mission_id
        capability_name = capability.name if isinstance(capability, AgentCapability) else capability
        self.shared_memory_manager.create_workspace(active_mission_id)
        self._publish_protocol_request(capability_name, context)
        if role is not None:
            selected = self.role_manager.select_best(capability, role=role)
            if selected is not None:
                agent_type = selected.agent_type

        merged_context = {
            **context,
            "mission_id": active_mission_id,
            "shared_memory": self.shared_memory_manager.read_all(
                active_mission_id,
                agent_id="distributed_runtime",
            ),
            "shared_memory_manager": self.shared_memory_manager,
        }
        task = self.runtime_scheduler.dispatch(
            capability,
            merged_context,
            agent_type=agent_type,
        )
        self._merge_agent_result(task, active_mission_id)
        self._publish_runtime_event(
            "distributed.agent.completed",
            {
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "capability": task.capability,
                "status": task.status,
            },
        )
        return task

    def execute_agent_tasks(
        self,
        tasks: list[tuple[str | AgentCapability, dict[str, Any]]],
        max_workers: int | None = None,
        mission_id: str | None = None,
    ) -> list[RuntimeTask]:
        if not tasks:
            return []

        with ThreadPoolExecutor(max_workers=max_workers or len(tasks)) as executor:
            futures = [
                executor.submit(self.execute_agent, capability, context, None, mission_id)
                for capability, context in tasks
            ]
            return [future.result() for future in futures]

    def assign_role(
        self,
        agent_id: str,
        primary_role: AgentRole | str,
        secondary_roles: list[AgentRole | str] | tuple[AgentRole | str, ...] | None = None,
    ):
        registration = self.agent_registry.get(agent_id)
        if registration is None:
            raise KeyError(f"Unknown agent: {agent_id}")
        return self.role_manager.assign_role(
            agent_id,
            primary_role=primary_role,
            capabilities=registration.capabilities,
            secondary_roles=secondary_roles,
        )

    def reassign_role(
        self,
        agent_id: str,
        primary_role: AgentRole | str,
        secondary_roles: list[AgentRole | str] | tuple[AgentRole | str, ...] | None = None,
    ):
        return self.role_manager.reassign_role(
            agent_id,
            primary_role=primary_role,
            secondary_roles=secondary_roles,
        )

    def collaborate(
        self,
        steps: list[tuple[str | AgentCapability, dict[str, Any]]],
    ):
        return self.collaboration_manager.execute_pipeline(steps)

    def negotiate(
        self,
        topic: str,
        proposal: Any,
        role: AgentRole | str | None = None,
        capability: str | None = None,
        consensus_threshold: float | None = None,
        timeout_seconds: float | None = None,
    ) -> NegotiationSession:
        session = self.negotiation_manager.create_session(
            topic,
            role=role,
            capability=capability,
            consensus_threshold=consensus_threshold,
            timeout_seconds=timeout_seconds,
        )
        proposer_id = session.participants[0] if session.participants else "distributed_runtime"
        self.negotiation_manager.generate_proposal(
            session.session_id,
            proposer_id=proposer_id,
            content=proposal,
        )
        return session

    def form_swarm(
        self,
        name: str,
        capabilities: list[str | AgentCapability],
        role: AgentRole | str | None = None,
        size: int | None = None,
    ) -> Swarm:
        return self.swarm_manager.form_swarm(
            name=name,
            capabilities=capabilities,
            role=role,
            size=size,
        )

    def allocate_swarm_task(
        self,
        swarm_id: str,
        capability: str | AgentCapability,
        context: dict[str, Any],
    ) -> SwarmTask:
        return self.swarm_manager.allocate_task(swarm_id, capability, context)

    def submit_mission(self, goal: str) -> DistributedMission:
        return self.scheduler.submit(goal)

    def execute_mission(self, goal: str) -> DistributedMission:
        mission = self.submit_mission(goal)
        self.run_next()
        completed = self.scheduler.get(mission.mission_id)
        if completed is None:
            raise RuntimeError(f"Distributed mission not found: {mission.mission_id}")
        return completed

    def run_next(self) -> DistributedMission | None:
        self.health_monitor.check()
        mission = self.scheduler.next()
        if mission is None:
            return None

        mission.status = "RUNNING"
        try:
            node, result = self.dispatcher.dispatch(mission.goal)
        except Exception as exc:
            self.scheduler.fail(mission, str(exc))
            return mission

        self.scheduler.complete(mission, result, node)
        return mission

    def run_pending(self) -> list[DistributedMission]:
        missions = []
        while True:
            mission = self.run_next()
            if mission is None:
                break
            missions.append(mission)
        return missions

    def health(self) -> dict[str, bool]:
        return self.health_monitor.check()

    def history(self) -> list[DistributedMission]:
        return self.scheduler.history()

    def _merge_agent_result(self, task: RuntimeTask, mission_id: str) -> None:
        if task.result is None:
            return

        memory_update = task.result.get("shared_memory")
        if isinstance(memory_update, dict):
            for key, value in memory_update.items():
                self.shared_memory_manager.write(
                    mission_id,
                    agent_id=task.agent_id or "distributed_runtime",
                    key=key,
                    value=value,
                )

        if "output" in task.result:
            self.shared_memory_manager.write(
                mission_id,
                agent_id=task.agent_id or "distributed_runtime",
                key=task.capability,
                value=task.result["output"],
            )

    def _publish_runtime_event(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            self.event_bus.publish(event_type, payload, source="distributed_runtime")
        except AgentProtocolError:
            protocol = self.event_bus.protocol
            self.event_bus.protocol = None
            try:
                self.event_bus.publish(event_type, payload, source="distributed_runtime")
            finally:
                self.event_bus.protocol = protocol

    def _publish_protocol_request(
        self,
        capability: str,
        context: dict[str, Any],
    ) -> None:
        request = self._protocol_request_for(capability)
        if request is None:
            return

        message_type, target = request
        try:
            message = self.agent_protocol.create_message(
                message_type,
                payload={"context": context},
                source="runtime",
                target=target,
            )
        except AgentProtocolError:
            return

        self.event_bus.publish(message)

    def _protocol_request_for(self, capability: str) -> tuple[MessageType, str] | None:
        return {
            "plan": (MessageType.PLAN_REQUEST, "planner"),
            "execute": (MessageType.EXECUTION_REQUEST, "executor"),
            "remember": (MessageType.MEMORY_QUERY, "memory"),
            "memory": (MessageType.MEMORY_QUERY, "memory"),
            "quality": (MessageType.QUALITY_CHECK, "quality"),
            "reflect": (MessageType.REFLECTION_REQUEST, "reflection"),
        }.get(capability)
