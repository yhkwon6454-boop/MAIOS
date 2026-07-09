from __future__ import annotations

from time import sleep
from typing import Any

import pytest

from maios.agents import (
    Agent,
    AgentCapability,
    AgentRegistry,
    AgentRole,
    AgentRoleManager,
    CollaborationManager,
    NegotiationManager,
)
from maios.distributed import DistributedRuntime
from maios.events import EventBus


class NegotiationAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": self.name}


def test_negotiation_manager_creates_sessions_and_proposals_with_history():
    bus = EventBus()
    manager = NegotiationManager(event_bus=bus)

    session = manager.create_session("choose plan", participants=["planner", "executor"])
    proposal = manager.generate_proposal(
        session.session_id,
        proposer_id="planner",
        content={"plan": "A"},
    )

    assert session.status == "OPEN"
    assert session.proposals == [proposal]
    assert manager.history(session.session_id) == [proposal]
    assert [message.event_type for message in bus.history] == [
        "negotiation.session.created",
        "negotiation.proposal.created",
    ]


def test_negotiation_manager_supports_counter_proposals():
    manager = NegotiationManager()
    session = manager.create_session("choose plan", participants=["a", "b"])
    proposal = manager.generate_proposal(session.session_id, "a", "plan A")

    counter = manager.counter_proposal(
        session.session_id,
        proposer_id="b",
        parent_proposal_id=proposal.proposal_id,
        content="plan B",
    )

    assert counter.parent_proposal_id == proposal.proposal_id
    assert session.proposals == [proposal, counter]


def test_negotiation_manager_enforces_timeout():
    manager = NegotiationManager()
    session = manager.create_session("urgent", participants=["a"], timeout_seconds=0.001)
    sleep(0.01)

    with pytest.raises(TimeoutError):
        manager.generate_proposal(session.session_id, "a", "late")

    assert session.status == "TIMED_OUT"
    assert manager.close_expired() == []


def test_negotiation_integrates_with_role_manager_selection():
    registry = AgentRegistry()
    registry.register(
        NegotiationAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
    )
    registry.register(
        NegotiationAgent("observer"),
        [AgentCapability("plan")],
        agent_id="observer-1",
    )
    role_manager = AgentRoleManager(registry)
    role_manager.assign_role("planner-1", AgentRole.PLANNER)
    role_manager.assign_role("observer-1", AgentRole.OBSERVER)
    manager = NegotiationManager(role_manager=role_manager)

    session = manager.create_session(
        "role scoped",
        role=AgentRole.PLANNER,
        capability="plan",
    )

    assert session.participants == ["planner-1"]


def test_negotiation_integrates_with_collaboration_manager():
    registry = AgentRegistry()
    registry.register(NegotiationAgent("planner"), [AgentCapability("plan")], agent_id="p")
    negotiation_manager = NegotiationManager()
    collaboration = CollaborationManager(
        registry,
        negotiation_manager=negotiation_manager,
    )

    session = collaboration.negotiate("plan", proposal="draft")

    assert session.participants == ["p"]
    assert session.proposals[0].content == "draft"
    assert negotiation_manager.session(session.session_id) is session


def test_negotiation_integrates_with_distributed_runtime():
    runtime = DistributedRuntime()
    runtime.register_agent(
        NegotiationAgent("planner"),
        [AgentCapability("plan")],
        agent_id="planner-1",
        primary_role=AgentRole.PLANNER,
    )

    session = runtime.negotiate(
        "distributed plan",
        proposal={"plan": "A"},
        role=AgentRole.PLANNER,
        capability="plan",
    )

    assert session.participants == ["planner-1"]
    assert session.proposals[0].content == {"plan": "A"}
    assert runtime.negotiation_manager.session(session.session_id) is session
