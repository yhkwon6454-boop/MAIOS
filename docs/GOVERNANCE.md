# Governance

MAIOS governance is implemented as a policy layer for autonomous mission
execution.

## Components

- `PermissionModel`: maps subjects to allowed actions.
- `PolicyEngine`: evaluates permissions, blocked keywords, risk level, and
  approval gates.
- `GovernanceManager`: coordinates policy evaluation and audit logging.
- `AuditLog`: persists policy checks and autonomous decisions as JSON.

## Risk Classification

`PolicyEngine` classifies missions as:

- `LOW`
- `MEDIUM`
- `HIGH`

Risk can be provided explicitly in mission context or inferred from configured
keywords. High-risk missions require human approval by default.

## Autonomous Controller Integration

`AutonomousController` can receive a `GovernanceManager`. When configured, the
controller evaluates governance before acting:

```python
from maios.autonomous import AutonomousController
from maios.governance import GovernanceManager, PolicyEngine

controller = AutonomousController(
    governance_manager=GovernanceManager(policy_engine=PolicyEngine())
)
decision = controller.run_once({"goal": "Review local context."})
```

If a mission is blocked or requires approval, the controller records the
decision and does not execute until approved.

## Audit Events

The audit log records:

- `policy_check`
- `human_approval`
- `autonomous_decision`

Audit logs may contain sensitive mission context. Store them according to your
environment's data-handling requirements.
