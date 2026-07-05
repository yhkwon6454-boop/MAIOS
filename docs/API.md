# API

This document covers the implemented public interfaces in `v1.0.0`.

## Python API

```python
import maios

result = maios.run("Analyze a mission goal.")
```

`maios.run(goal: str)` returns `MissionResult`.

```python
from maios.core import MAIOSCore

core = MAIOSCore()
result = core.run("Prepare a concise execution plan.")
```

`MissionResult` includes:

- `goal`
- `mission`
- `plan`
- `memory_context`
- `model_output`
- `task_outputs`
- `execution_result`
- `qa_result`
- `reflection_report`
- `final_output`
- `status`
- `knowledge_count`

## Autonomous Controller

```python
from maios.autonomous import AutonomousController

controller = AutonomousController()
decision = controller.run_once({"goal": "Review current context."})
```

The controller supports autonomous mode, human approval mode, decision history,
safety policies, and optional governance integration.

## Governance

```python
from maios.governance import GovernanceManager, PolicyEngine

governance = GovernanceManager(policy_engine=PolicyEngine())
decision = governance.evaluate("deploy to production", "EXECUTE_MISSION")
```

Governance decisions include risk level, permission checks, approval status, and
policy-check details.

## REST API

Start the service:

```bash
uvicorn maios.service.api:app --reload
```

### `GET /health`

Returns service health and pending mission count.

### `POST /run`

Request:

```json
{
  "goal": "Summarize MAIOS state."
}
```

Executes one mission and returns a serialized mission record.

### `GET /mission/{mission_id}`

Returns a serialized mission record or `404` if the mission does not exist.

### `GET /history`

Returns all mission records known to the service agent.

### `GET /dashboard`

Returns the built-in web dashboard.
