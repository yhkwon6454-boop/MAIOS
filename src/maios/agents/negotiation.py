from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from maios.agents.roles import AgentRole, AgentRoleManager
from maios.events import EventBus


@dataclass(frozen=True)
class Proposal:
    content: Any
    proposer_id: str
    session_id: str
    proposal_id: str = field(default_factory=lambda: f"PROP-{uuid4().hex[:8]}")
    parent_proposal_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class Vote:
    proposal_id: str
    agent_id: str
    approve: bool
    weight: float = 1.0
    rationale: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class NegotiationSession:
    topic: str
    participants: list[str]
    consensus_threshold: float = 0.66
    timeout_seconds: float | None = None
    session_id: str = field(default_factory=lambda: f"NEG-{uuid4().hex[:8]}")
    proposals: list[Proposal] = field(default_factory=list)
    votes: list[Vote] = field(default_factory=list)
    status: str = "OPEN"
    accepted_proposal_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.timeout_seconds is None:
            return False
        current_time = now or datetime.now(UTC)
        return current_time >= self.created_at + timedelta(seconds=self.timeout_seconds)

    def history(self) -> list[Proposal | Vote]:
        return sorted(
            [*self.proposals, *self.votes],
            key=lambda item: item.created_at,
        )


class NegotiationManager:
    """Coordinates proposal, counterproposal, and weighted consensus sessions."""

    def __init__(
        self,
        role_manager: AgentRoleManager | None = None,
        event_bus: EventBus | None = None,
        default_consensus_threshold: float = 0.66,
    ) -> None:
        self.role_manager = role_manager
        self.event_bus = event_bus or EventBus()
        self.default_consensus_threshold = default_consensus_threshold
        self._sessions: dict[str, NegotiationSession] = {}

    def create_session(
        self,
        topic: str,
        participants: list[str] | tuple[str, ...] | None = None,
        role: AgentRole | str | None = None,
        capability: str | None = None,
        consensus_threshold: float | None = None,
        timeout_seconds: float | None = None,
    ) -> NegotiationSession:
        selected_participants = list(participants or ())
        if not selected_participants and self.role_manager is not None:
            selected_participants = [
                agent.agent_id
                for agent in self.role_manager.select_agents(
                    [capability] if capability is not None else [],
                    role=role,
                )
            ]
        session = NegotiationSession(
            topic=topic,
            participants=selected_participants,
            consensus_threshold=consensus_threshold or self.default_consensus_threshold,
            timeout_seconds=timeout_seconds,
        )
        self._sessions[session.session_id] = session
        self._publish("negotiation.session.created", session)
        return session

    def generate_proposal(
        self,
        session_id: str,
        proposer_id: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> Proposal:
        session = self._open_session(session_id)
        proposal = Proposal(
            content=content,
            proposer_id=proposer_id,
            session_id=session_id,
            metadata=metadata or {},
        )
        session.proposals.append(proposal)
        session.updated_at = proposal.created_at
        self._publish("negotiation.proposal.created", session, proposal=proposal)
        return proposal

    def counter_proposal(
        self,
        session_id: str,
        proposer_id: str,
        parent_proposal_id: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> Proposal:
        session = self._open_session(session_id)
        if self.proposal(session_id, parent_proposal_id) is None:
            raise KeyError(f"Unknown proposal: {parent_proposal_id}")
        proposal = Proposal(
            content=content,
            proposer_id=proposer_id,
            session_id=session_id,
            parent_proposal_id=parent_proposal_id,
            metadata=metadata or {},
        )
        session.proposals.append(proposal)
        session.updated_at = proposal.created_at
        self._publish("negotiation.counter_proposal.created", session, proposal=proposal)
        return proposal

    def vote(
        self,
        session_id: str,
        proposal_id: str,
        agent_id: str,
        approve: bool,
        weight: float = 1.0,
        rationale: str = "",
    ) -> Vote:
        session = self._open_session(session_id)
        if self.proposal(session_id, proposal_id) is None:
            raise KeyError(f"Unknown proposal: {proposal_id}")
        vote = Vote(
            proposal_id=proposal_id,
            agent_id=agent_id,
            approve=approve,
            weight=weight,
            rationale=rationale,
        )
        session.votes = [
            item
            for item in session.votes
            if not (item.proposal_id == proposal_id and item.agent_id == agent_id)
        ]
        session.votes.append(vote)
        session.updated_at = vote.created_at
        self._publish("negotiation.vote.cast", session, vote=vote)
        self.evaluate(session_id, proposal_id)
        return vote

    def evaluate(self, session_id: str, proposal_id: str) -> bool:
        session = self.session(session_id)
        if session is None:
            raise KeyError(f"Unknown negotiation session: {session_id}")
        if session.is_expired():
            session.status = "TIMED_OUT"
            self._publish("negotiation.session.timed_out", session)
            return False
        if (
            self._participants_voted(session, proposal_id)
            and self.consensus_score(session_id, proposal_id) >= session.consensus_threshold
        ):
            session.status = "ACCEPTED"
            session.accepted_proposal_id = proposal_id
            self._publish("negotiation.proposal.accepted", session)
            return True
        return False

    def consensus_score(self, session_id: str, proposal_id: str) -> float:
        votes = self.votes_for(session_id, proposal_id)
        total_weight = sum(max(0.0, vote.weight) for vote in votes)
        if total_weight == 0:
            return 0.0
        approved_weight = sum(max(0.0, vote.weight) for vote in votes if vote.approve)
        return approved_weight / total_weight

    def votes_for(self, session_id: str, proposal_id: str) -> list[Vote]:
        session = self.session(session_id)
        if session is None:
            return []
        return [vote for vote in session.votes if vote.proposal_id == proposal_id]

    def proposal(self, session_id: str, proposal_id: str) -> Proposal | None:
        session = self.session(session_id)
        if session is None:
            return None
        for proposal in session.proposals:
            if proposal.proposal_id == proposal_id:
                return proposal
        return None

    def session(self, session_id: str) -> NegotiationSession | None:
        return self._sessions.get(session_id)

    def sessions(self) -> list[NegotiationSession]:
        return list(self._sessions.values())

    def history(self, session_id: str | None = None) -> list[NegotiationSession | Proposal | Vote]:
        if session_id is None:
            return list(self._sessions.values())
        session = self.session(session_id)
        if session is None:
            return []
        items: list[NegotiationSession | Proposal | Vote] = [*session.history()]
        return items

    def close_expired(self) -> list[NegotiationSession]:
        expired = []
        for session in self._sessions.values():
            if session.status == "OPEN" and session.is_expired():
                session.status = "TIMED_OUT"
                expired.append(session)
                self._publish("negotiation.session.timed_out", session)
        return expired

    def _open_session(self, session_id: str) -> NegotiationSession:
        session = self.session(session_id)
        if session is None:
            raise KeyError(f"Unknown negotiation session: {session_id}")
        if session.status != "OPEN":
            raise RuntimeError(f"Negotiation session is not open: {session_id}")
        if session.is_expired():
            session.status = "TIMED_OUT"
            self._publish("negotiation.session.timed_out", session)
            raise TimeoutError(f"Negotiation session timed out: {session_id}")
        return session

    def _participants_voted(
        self,
        session: NegotiationSession,
        proposal_id: str,
    ) -> bool:
        if not session.participants:
            return True
        voters = {vote.agent_id for vote in self.votes_for(session.session_id, proposal_id)}
        return all(participant in voters for participant in session.participants)

    def _publish(
        self,
        event_type: str,
        session: NegotiationSession,
        proposal: Proposal | None = None,
        vote: Vote | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "session_id": session.session_id,
            "topic": session.topic,
            "status": session.status,
        }
        if proposal is not None:
            payload["proposal_id"] = proposal.proposal_id
        if vote is not None:
            payload["proposal_id"] = vote.proposal_id
            payload["agent_id"] = vote.agent_id
            payload["approve"] = vote.approve
            payload["weight"] = vote.weight
        self.event_bus.publish(event_type, payload, source="negotiation")
