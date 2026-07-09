from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRegistry, AgentRole, AgentRoleManager
from maios.agents.swarm import SwarmManager


class LeaderAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": self.name}


def test_leader_election_prefers_coordinator_role():
    registry = AgentRegistry()
    role_manager = AgentRoleManager(registry)
    registry.register(LeaderAgent("worker"), [AgentCapability("plan")], agent_id="worker-1")
    registry.register(
        LeaderAgent("coordinator"),
        [AgentCapability("plan")],
        agent_id="coordinator-1",
    )
    role_manager.assign_role("worker-1", AgentRole.PLANNER)
    role_manager.assign_role(
        "coordinator-1",
        AgentRole.PLANNER,
        secondary_roles=[AgentRole.COORDINATOR],
    )
    manager = SwarmManager(registry=registry, role_manager=role_manager)

    swarm = manager.form_swarm("leader swarm", ["plan"])

    assert swarm.leader_id == "coordinator-1"


def test_leader_election_reelects_after_leader_failure():
    registry = AgentRegistry()
    role_manager = AgentRoleManager(registry)
    registry.register(LeaderAgent("a"), [AgentCapability("plan")], agent_id="a")
    registry.register(LeaderAgent("b"), [AgentCapability("plan")], agent_id="b")
    role_manager.assign_role("a", AgentRole.COORDINATOR)
    role_manager.assign_role("b", AgentRole.PLANNER)
    manager = SwarmManager(registry=registry, role_manager=role_manager)
    swarm = manager.form_swarm("leader swarm", ["plan"])

    manager.mark_failed(swarm.swarm_id, "a")

    assert swarm.leader_id == "b"
    assert "a" in swarm.failed_agents


def test_leader_election_degrades_when_no_active_members_remain():
    registry = AgentRegistry()
    registry.register(LeaderAgent("a"), [AgentCapability("plan")], agent_id="a")
    manager = SwarmManager(registry=registry)
    swarm = manager.form_swarm("leader swarm", ["plan"])

    manager.mark_failed(swarm.swarm_id, "a")
    leader = manager.elect_leader(swarm.swarm_id)

    assert leader is None
    assert swarm.leader_id == ""
    assert swarm.status == "DEGRADED"
