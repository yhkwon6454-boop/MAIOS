from __future__ import annotations

from datetime import UTC, datetime, timedelta

from maios.agents import NegotiationManager


def test_consensus_threshold_accepts_proposal_when_weighted_votes_pass():
    manager = NegotiationManager(default_consensus_threshold=0.75)
    session = manager.create_session("consensus", participants=["a", "b", "c"])
    proposal = manager.generate_proposal(session.session_id, "a", "approve")

    manager.vote(session.session_id, proposal.proposal_id, "a", True, weight=2.0)
    manager.vote(session.session_id, proposal.proposal_id, "b", True, weight=1.0)
    manager.vote(session.session_id, proposal.proposal_id, "c", False, weight=1.0)

    assert manager.consensus_score(session.session_id, proposal.proposal_id) == 0.75
    assert session.status == "ACCEPTED"
    assert session.accepted_proposal_id == proposal.proposal_id


def test_consensus_threshold_leaves_session_open_when_votes_do_not_pass():
    manager = NegotiationManager()
    session = manager.create_session("consensus", participants=["a", "b"], consensus_threshold=0.8)
    proposal = manager.generate_proposal(session.session_id, "a", "approve")

    manager.vote(session.session_id, proposal.proposal_id, "a", True)
    manager.vote(session.session_id, proposal.proposal_id, "b", False)

    assert manager.consensus_score(session.session_id, proposal.proposal_id) == 0.5
    assert session.status == "OPEN"
    assert session.accepted_proposal_id == ""


def test_close_expired_marks_open_sessions_timed_out():
    manager = NegotiationManager()
    session = manager.create_session("stale", timeout_seconds=1.0)
    session.created_at = datetime.now(UTC) - timedelta(seconds=2)

    expired = manager.close_expired()

    assert expired == [session]
    assert session.status == "TIMED_OUT"


def test_evaluate_marks_expired_session_timed_out():
    manager = NegotiationManager()
    session = manager.create_session("stale", participants=["a"], timeout_seconds=1.0)
    proposal = manager.generate_proposal(session.session_id, "a", "draft")
    session.created_at = datetime.now(UTC) - timedelta(seconds=2)

    assert not manager.evaluate(session.session_id, proposal.proposal_id)
    assert session.status == "TIMED_OUT"
