from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from maios.autonomous import MAIOSAgent, MissionRecord
from maios.core import MissionResult


class RunRequest(BaseModel):
    goal: str = Field(..., min_length=1)


def create_app(agent: MAIOSAgent | None = None) -> FastAPI:
    runtime_agent = agent or MAIOSAgent()
    app = FastAPI(
        title="MAIOS API",
        description="REST API for the MUSA AI Operating System runtime.",
        version="0.1.0-alpha",
    )
    app.state.maios_agent = runtime_agent

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "maios",
            "pending_missions": runtime_agent.scheduler.pending_count(),
        }

    @app.post("/run")
    def run_mission(request: RunRequest) -> dict[str, Any]:
        record = runtime_agent.submit_goal(request.goal)
        runtime_agent.run_next()
        completed = runtime_agent.scheduler.get(record.mission_id)
        return serialize_mission_record(completed)

    @app.get("/mission/{mission_id}")
    def get_mission(mission_id: str) -> dict[str, Any]:
        record = runtime_agent.scheduler.get(mission_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Mission not found")

        return serialize_mission_record(record)

    @app.get("/history")
    def history() -> list[dict[str, Any]]:
        return [
            serialize_mission_record(record)
            for record in runtime_agent.history()
        ]

    return app


def serialize_mission_record(record: MissionRecord | None) -> dict[str, Any]:
    if record is None:
        raise HTTPException(status_code=404, detail="Mission not found")

    return {
        "mission_id": record.mission_id,
        "goal": record.goal,
        "status": record.status,
        "error": record.error,
        "result": serialize_mission_result(record.result) if record.result else None,
    }


def serialize_mission_result(result: MissionResult) -> dict[str, Any]:
    return {
        "goal": result.goal,
        "status": result.status.value,
        "mission": _to_jsonable(result.mission),
        "plan": _to_jsonable(result.plan),
        "memory_context": result.memory_context,
        "model_output": result.model_output,
        "task_outputs": result.task_outputs,
        "execution_result": result.execution_result,
        "qa_result": _to_jsonable(result.qa_result),
        "reflection_report": _to_jsonable(result.reflection_report),
        "final_output": result.final_output,
        "knowledge_count": result.knowledge_count,
    }


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None

    if is_dataclass(value):
        return {
            key: _to_jsonable(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            key: _to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]

    if hasattr(value, "value"):
        return value.value

    return value


app = create_app()
