from __future__ import annotations

from maios.kernel import DecisionContext, ExecutivePriorityEngine
from maios.planning import MetaGoal


def test_executive_priority_engine_orders_by_weighted_priority():
    high = MetaGoal("Critical", urgency=1.0, impact=0.9, risk=0.4)
    low = MetaGoal("Routine", urgency=0.2, impact=0.2, risk=0.0)
    engine = ExecutivePriorityEngine()

    ordered = engine.prioritize([low, high])

    assert ordered == [high, low]
    assert high.priority_score > low.priority_score


def test_executive_priority_engine_adds_failure_pressure_and_capability_match():
    context = DecisionContext("Recover", requested_capabilities=("research",))
    context.record_outcome({"status": "FAILED", "error": "gap"})
    context.record_outcome({"status": "FAILED", "error": "gap"})
    matched = MetaGoal("Investigate", required_capabilities=("research",))
    unmatched = MetaGoal("Execute", required_capabilities=("execute",))
    engine = ExecutivePriorityEngine()

    matched_score = engine.score(matched, context)
    unmatched_score = engine.score(unmatched, context)

    assert matched_score > unmatched_score
    assert matched_score > engine.score(matched, DecisionContext("Clean"))


def test_executive_priority_engine_penalizes_progress():
    fresh = MetaGoal("Fresh", urgency=0.8, impact=0.8)
    nearly_done = MetaGoal("Nearly done", urgency=0.8, impact=0.8, progress=0.9)

    ordered = ExecutivePriorityEngine().prioritize([nearly_done, fresh])

    assert ordered[0] is fresh
