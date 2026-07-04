from __future__ import annotations

from dataclasses import dataclass, field
from queue import Empty, Queue
from time import time
from typing import Protocol
from uuid import uuid4

from maios.core import MAIOSCore, MissionResult


class Transport(Protocol):
    def execute(self, node: "Node", goal: str) -> MissionResult:
        ...


@dataclass
class Node:
    node_id: str
    address: str = "local"
    capacity: int = 1
    active_tasks: int = 0
    healthy: bool = True
    last_heartbeat: float = field(default_factory=time)
    metadata: dict = field(default_factory=dict)

    def available_capacity(self) -> int:
        return max(0, self.capacity - self.active_tasks)


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
        self.nodes: dict[str, Node] = {}

    def register_node(
        self,
        node_id: str,
        address: str = "local",
        capacity: int = 1,
        metadata: dict | None = None,
    ) -> Node:
        node = Node(
            node_id=node_id,
            address=address,
            capacity=capacity,
            metadata=metadata or {},
        )
        self.nodes[node_id] = node
        return node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

    def get(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def heartbeat(self, node_id: str) -> Node:
        node = self.nodes[node_id]
        node.healthy = True
        node.last_heartbeat = time()
        return node

    def healthy_nodes(self) -> list[Node]:
        return [
            node
            for node in self.nodes.values()
            if node.healthy and node.available_capacity() > 0
        ]

    def select_node(self) -> Node | None:
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

    def heartbeat(self, node_id: str) -> Node:
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

    def complete(self, mission: DistributedMission, result: MissionResult, node: Node) -> None:
        mission.status = "COMPLETED"
        mission.result = result
        mission.assigned_node = node.node_id
        self._missions[mission.mission_id] = mission
        self._queue.task_done()

    def fail(self, mission: DistributedMission, error: str, node: Node | None = None) -> None:
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

    def dispatch(self, goal: str) -> tuple[Node, MissionResult]:
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
    ) -> None:
        self.node_manager = node_manager or NodeManager()
        self.transport = transport or InMemoryTransport()
        self.scheduler = scheduler or MissionScheduler()
        self.health_monitor = health_monitor or HealthMonitor(self.node_manager)
        self.dispatcher = dispatcher or TaskDispatcher(self.node_manager, self.transport)

    def register_node(
        self,
        node_id: str,
        core: MAIOSCore | None = None,
        address: str = "local",
        capacity: int = 1,
        metadata: dict | None = None,
    ) -> Node:
        node = self.node_manager.register_node(
            node_id=node_id,
            address=address,
            capacity=capacity,
            metadata=metadata,
        )
        if core is not None and isinstance(self.transport, InMemoryTransport):
            self.transport.register_core(node_id, core)
        return node

    def heartbeat(self, node_id: str) -> Node:
        return self.health_monitor.heartbeat(node_id)

    def submit_mission(self, goal: str) -> DistributedMission:
        return self.scheduler.submit(goal)

    def execute_mission(self, goal: str) -> DistributedMission:
        mission = self.submit_mission(goal)
        self.run_next()
        return self.scheduler.get(mission.mission_id)

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
