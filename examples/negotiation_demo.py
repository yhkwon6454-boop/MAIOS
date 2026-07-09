from __future__ import annotations

from typing import Any

from maios.agents import Agent, AgentCapability, AgentRole
from maios.distributed import DistributedRuntime


class DemoAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"output": f"{self.name} reviewed {context.get('topic', 'proposal')}"}


def main() -> None:
    runtime = DistributedRuntime()
    runtime.register_agent(
        DemoAgent("planner-a"),
        [AgentCapability("plan")],
        agent_id="planner-a",
        primary_role=AgentRole.PLANNER,
    )
    runtime.register_agent(
        DemoAgent("planner-b"),
        [AgentCapability("plan")],
        agent_id="planner-b",
        primary_role=AgentRole.PLANNER,
    )

    session = runtime.negotiate(
        "Select launch plan",
        proposal={"plan": "A", "risk": "medium"},
        role=AgentRole.PLANNER,
        capability="plan",
        consensus_threshold=0.75,
    )
    proposal = session.proposals[0]
    runtime.negotiation_manager.counter_proposal(
        session.session_id,
        proposer_id="planner-b",
        parent_proposal_id=proposal.proposal_id,
        content={"plan": "B", "risk": "low"},
    )
    runtime.negotiation_manager.vote(
        session.session_id,
        proposal.proposal_id,
        "planner-a",
        approve=True,
        weight=2.0,
    )
    runtime.negotiation_manager.vote(
        session.session_id,
        proposal.proposal_id,
        "planner-b",
        approve=True,
        weight=1.0,
    )

    print(f"{session.session_id}: {session.status}")
    print(f"accepted proposal: {session.accepted_proposal_id}")


if __name__ == "__main__":
    main()
