from __future__ import annotations

import pytest

from maios.agents import NegotiationManager


def test_weighted_voting_replaces_existing_agent_vote():
    manager = NegotiationManager()
    session = manager.create_session("vote", participants=["a", "b"])
    proposal = manager.generate_proposal(session.session_id, "a", "draft")

    manager.vote(session.session_id, proposal.proposal_id, "a", False, weight=3.0)
    replacement = manager.vote(session.session_id, proposal.proposal_id, "a", True, weight=3.0)

    assert manager.votes_for(session.session_id, proposal.proposal_id) == [replacement]
    assert manager.consensus_score(session.session_id, proposal.proposal_id) == 1.0


def test_weighted_voting_ignores_negative_weights():
    manager = NegotiationManager()
    session = manager.create_session("vote", participants=["a", "b"], consensus_threshold=0.5)
    proposal = manager.generate_proposal(session.session_id, "a", "draft")

    manager.vote(session.session_id, proposal.proposal_id, "a", True, weight=-1.0)
    manager.vote(session.session_id, proposal.proposal_id, "b", False, weight=1.0)

    assert manager.consensus_score(session.session_id, proposal.proposal_id) == 0.0
    assert session.status == "OPEN"


def test_weighted_voting_returns_zero_without_votes():
    manager = NegotiationManager()
    session = manager.create_session("vote")
    proposal = manager.generate_proposal(session.session_id, "a", "draft")

    assert manager.consensus_score(session.session_id, proposal.proposal_id) == 0.0
    assert manager.votes_for("missing", proposal.proposal_id) == []


def test_voting_rejects_unknown_sessions_and_proposals():
    manager = NegotiationManager()
    session = manager.create_session("vote")

    with pytest.raises(KeyError, match="Unknown proposal"):
        manager.counter_proposal(session.session_id, "a", "missing", "counter")

    with pytest.raises(KeyError, match="Unknown proposal"):
        manager.vote(session.session_id, "missing", "a", True)

    with pytest.raises(KeyError, match="Unknown negotiation session"):
        manager.evaluate("missing", "proposal")


def test_voting_rejects_closed_sessions():
    manager = NegotiationManager(default_consensus_threshold=0.5)
    session = manager.create_session("vote", participants=["a"])
    proposal = manager.generate_proposal(session.session_id, "a", "draft")
    manager.vote(session.session_id, proposal.proposal_id, "a", True)

    with pytest.raises(RuntimeError, match="not open"):
        manager.generate_proposal(session.session_id, "a", "after close")
