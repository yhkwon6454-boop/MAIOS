from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class PolicyCheck:
    name: str
    passed: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernanceDecision:
    goal: str
    action: str
    subject: str
    risk_level: str
    approved: bool
    requires_human_approval: bool
    reason: str
    policy_checks: list[PolicyCheck] = field(default_factory=list)
    decision_id: str = field(default_factory=lambda: f"GOV-{uuid4().hex[:8]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "policy_checks": [asdict(check) for check in self.policy_checks],
        }


@dataclass
class AuditEntry:
    event_type: str
    payload: dict[str, Any]
    entry_id: str = field(default_factory=lambda: f"AUD-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuditLog:
    """Append-only JSON-backed audit log for governance decisions."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._entries: list[AuditEntry] = []
        self._serialized_entries: list[dict[str, Any]] = []
        self._load()

    def record(self, event_type: str, payload: dict[str, Any]) -> AuditEntry:
        entry = AuditEntry(event_type=event_type, payload=payload)
        self._entries.append(entry)
        self._persist()
        return entry

    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def serialized_entries(self) -> list[dict[str, Any]]:
        if self._entries:
            return [entry.to_dict() for entry in self._entries]
        return list(self._serialized_entries)

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return

        data = json.loads(self.path.read_text(encoding="utf-8"))
        self._serialized_entries = data.get("entries", [])

    def _persist(self) -> None:
        if self.path is None:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"entries": [entry.to_dict() for entry in self._entries]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


class PermissionModel:
    """Action permission model for autonomous governance subjects."""

    def __init__(self, grants: dict[str, set[str] | list[str]] | None = None) -> None:
        grants = grants or {"autonomous_controller": {"EXECUTE_MISSION"}}
        self.grants = {subject: set(actions) for subject, actions in grants.items()}

    def allow(self, subject: str, action: str) -> None:
        self.grants.setdefault(subject, set()).add(action)

    def revoke(self, subject: str, action: str) -> None:
        self.grants.setdefault(subject, set()).discard(action)

    def is_allowed(self, subject: str, action: str) -> bool:
        actions = self.grants.get(subject, set())
        return "*" in actions or action in actions


class PolicyEngine:
    """Evaluates mission risk, permissions, and approval gates."""

    def __init__(
        self,
        permission_model: PermissionModel | None = None,
        blocked_keywords: list[str] | None = None,
        high_risk_keywords: list[str] | None = None,
        medium_risk_keywords: list[str] | None = None,
        approval_required_risks: set[str] | list[str] | None = None,
    ) -> None:
        self.permission_model = permission_model or PermissionModel()
        self.blocked_keywords = [item.lower() for item in (blocked_keywords or [])]
        self.high_risk_keywords = [
            item.lower()
            for item in (high_risk_keywords or ["deploy", "delete", "external", "production"])
        ]
        self.medium_risk_keywords = [
            item.lower() for item in (medium_risk_keywords or ["modify", "write", "commit"])
        ]
        self.approval_required_risks = set(approval_required_risks or {"HIGH"})

    def classify_risk(self, goal: str, context: dict[str, Any] | None = None) -> str:
        context = context or {}
        explicit_risk = str(context.get("risk", "")).upper()
        if explicit_risk in {"LOW", "MEDIUM", "HIGH"}:
            return explicit_risk

        goal_text = goal.lower()
        if any(keyword in goal_text for keyword in self.high_risk_keywords):
            return "HIGH"
        if any(keyword in goal_text for keyword in self.medium_risk_keywords):
            return "MEDIUM"
        return "LOW"

    def evaluate(
        self,
        goal: str,
        action: str,
        subject: str,
        context: dict[str, Any] | None = None,
    ) -> GovernanceDecision:
        context = context or {}
        risk_level = self.classify_risk(goal, context)
        checks = [
            self._permission_check(subject, action),
            self._blocked_keyword_check(goal),
            self._risk_gate_check(risk_level),
        ]
        failed_checks = [check for check in checks if not check.passed]
        requires_human_approval = any(
            check.name == "risk_approval_gate" and not check.passed for check in checks
        )
        approved = not failed_checks
        reason = "Allowed by governance policy."
        if failed_checks:
            reason = "; ".join(check.reason for check in failed_checks)

        return GovernanceDecision(
            goal=goal,
            action=action,
            subject=subject,
            risk_level=risk_level,
            approved=approved,
            requires_human_approval=requires_human_approval,
            reason=reason,
            policy_checks=checks,
        )

    def _permission_check(self, subject: str, action: str) -> PolicyCheck:
        passed = self.permission_model.is_allowed(subject, action)
        return PolicyCheck(
            name="permission",
            passed=passed,
            reason=(
                f"{subject} is allowed to perform {action}."
                if passed
                else f"{subject} is not allowed to perform {action}."
            ),
            metadata={"subject": subject, "action": action},
        )

    def _blocked_keyword_check(self, goal: str) -> PolicyCheck:
        goal_text = goal.lower()
        blocked = [keyword for keyword in self.blocked_keywords if keyword in goal_text]
        return PolicyCheck(
            name="blocked_keywords",
            passed=not blocked,
            reason=(
                "Goal does not contain blocked keywords."
                if not blocked
                else f"Goal contains blocked keyword: {blocked[0]}"
            ),
            metadata={"blocked": blocked},
        )

    def _risk_gate_check(self, risk_level: str) -> PolicyCheck:
        requires_approval = risk_level in self.approval_required_risks
        return PolicyCheck(
            name="risk_approval_gate",
            passed=not requires_approval,
            reason=(
                f"{risk_level} risk does not require approval."
                if not requires_approval
                else f"{risk_level} risk requires human approval."
            ),
            metadata={"risk_level": risk_level},
        )


class GovernanceManager:
    """Coordinates policy evaluation and audit persistence."""

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_log = audit_log or AuditLog()

    def evaluate(
        self,
        goal: str,
        action: str,
        subject: str = "autonomous_controller",
        context: dict[str, Any] | None = None,
    ) -> GovernanceDecision:
        decision = self.policy_engine.evaluate(goal, action, subject, context)
        self.audit_log.record("policy_check", decision.to_dict())
        return decision

    def approve(self, decision: GovernanceDecision, approver: str = "human") -> GovernanceDecision:
        decision.approved = True
        decision.requires_human_approval = False
        decision.reason = f"Approved by {approver}."
        self.audit_log.record("human_approval", decision.to_dict())
        return decision

    def record_autonomous_decision(self, decision: dict[str, Any]) -> AuditEntry:
        return self.audit_log.record("autonomous_decision", decision)

    def history(self) -> list[AuditEntry]:
        return self.audit_log.entries()
