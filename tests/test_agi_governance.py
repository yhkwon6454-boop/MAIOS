from __future__ import annotations

from maios.governance import GovernanceManager, PolicyEngine
from maios.kernel import AGIFoundation


def _governance(**kwargs) -> GovernanceManager:
    return GovernanceManager(policy_engine=PolicyEngine(**kwargs))


def test_agi_foundation_registers_pursue_permission():
    governance = _governance()

    agi = AGIFoundation(governance=governance)

    assert governance.policy_engine.permission_model.is_allowed(agi.identity, "PURSUE_GOAL")


def test_pursue_blocked_by_governance_keyword_runs_no_cycles():
    governance = _governance(blocked_keywords=["forbidden"])
    agi = AGIFoundation(governance=governance)

    pursuit = agi.pursue("Do the forbidden task")

    assert pursuit.status == "BLOCKED"
    assert pursuit.cycle_ids == ()
    assert pursuit.governance is not None
    assert pursuit.governance["approved"] is False
    assert agi.cognitive_loop.cycles == []


def test_pursue_high_risk_goal_requires_human_approval():
    governance = _governance()
    agi = AGIFoundation(governance=governance)

    pursuit = agi.pursue("Deploy the new service")

    assert pursuit.status == "PENDING_APPROVAL"
    assert pursuit.cycle_ids == ()
    assert pursuit.governance["requires_human_approval"] is True


def test_pursue_high_risk_goal_proceeds_with_human_approval():
    governance = _governance()
    agi = AGIFoundation(governance=governance)

    pursuit = agi.pursue("Deploy the new service", human_approved=True)

    assert pursuit.status == "COMPLETED"
    assert pursuit.cycle_ids
    assert pursuit.governance["approved"] is True


def test_pursue_low_risk_goal_is_audited_and_completed():
    governance = _governance()
    agi = AGIFoundation(governance=governance)

    pursuit = agi.pursue("Summarize the weekly report")

    assert pursuit.status == "COMPLETED"
    assert pursuit.governance["risk_level"] == "LOW"
    assert any(entry.event_type == "policy_check" for entry in governance.history())
