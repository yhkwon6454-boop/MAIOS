from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
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

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> str:
        return DASHBOARD_HTML

    @app.get("/dashboard.css", response_class=PlainTextResponse)
    def dashboard_css() -> str:
        return DASHBOARD_CSS

    @app.get("/dashboard.js", response_class=PlainTextResponse)
    def dashboard_js() -> str:
        return DASHBOARD_JS

    @app.get("/dashboard/state")
    def dashboard_state() -> dict[str, Any]:
        history_items = [
            serialize_mission_record(record)
            for record in runtime_agent.history()
        ]
        completed = [
            item for item in history_items
            if item["status"] == "COMPLETED"
        ]
        running = [
            item for item in history_items
            if item["status"] == "RUNNING"
        ]
        queued = [
            item for item in history_items
            if item["status"] == "QUEUED"
        ]
        reflections = [
            item["result"]["reflection_report"]
            for item in completed
            if item.get("result") and item["result"].get("reflection_report")
        ]
        core = runtime_agent.core
        knowledge_count = core.knowledge_store.count() if core else 0
        memory_usage = {}
        if core:
            memory_usage = {
                "short_term": len(core.memory_kernel.session_memory),
                "long_term": len(core.memory_kernel.long_term_memory),
                "conversation_history": len(core.memory_kernel.conversation_history),
            }

        return {
            "mission_queue": queued,
            "running_missions": running,
            "completed_missions": completed,
            "mission_details": history_items,
            "memory_usage": memory_usage,
            "knowledge_store": {
                "records": knowledge_count,
            },
            "reflection_reports": reflections,
        }

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


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MAIOS Dashboard</title>
  <link rel="stylesheet" href="/dashboard.css">
</head>
<body>
  <header class="topbar">
    <div>
      <h1>MAIOS Dashboard</h1>
      <p>Mission runtime, memory, knowledge, and reflection status</p>
    </div>
    <button id="refresh">Refresh</button>
  </header>

  <main class="layout">
    <section>
      <h2>Mission Queue</h2>
      <div id="mission-queue" class="list"></div>
    </section>

    <section>
      <h2>Running Missions</h2>
      <div id="running-missions" class="list"></div>
    </section>

    <section>
      <h2>Completed Missions</h2>
      <div id="completed-missions" class="list"></div>
    </section>

    <section>
      <h2>Mission Details</h2>
      <div id="mission-details" class="list"></div>
    </section>

    <section>
      <h2>Memory Usage</h2>
      <div id="memory-usage" class="metrics"></div>
    </section>

    <section>
      <h2>Knowledge Store Status</h2>
      <div id="knowledge-store" class="metrics"></div>
    </section>

    <section class="wide">
      <h2>Reflection Reports</h2>
      <div id="reflection-reports" class="list"></div>
    </section>
  </main>

  <script src="/dashboard.js"></script>
</body>
</html>
"""


DASHBOARD_CSS = """
:root {
  color-scheme: light;
  font-family: Arial, sans-serif;
  background: #f5f7f9;
  color: #1d2329;
}

body {
  margin: 0;
}

.topbar {
  align-items: center;
  background: #ffffff;
  border-bottom: 1px solid #dce2e8;
  display: flex;
  justify-content: space-between;
  padding: 20px 28px;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: 24px;
}

h2 {
  font-size: 16px;
  margin-bottom: 12px;
}

p {
  color: #5c6670;
  margin-top: 4px;
}

button {
  background: #1f6feb;
  border: 0;
  color: white;
  cursor: pointer;
  font-weight: 600;
  padding: 10px 14px;
}

.layout {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 20px;
}

section {
  background: #ffffff;
  border: 1px solid #dce2e8;
  padding: 16px;
}

.wide {
  grid-column: 1 / -1;
}

.item,
.metric {
  border-top: 1px solid #edf0f2;
  padding: 10px 0;
}

.item:first-child,
.metric:first-child {
  border-top: 0;
}

.meta {
  color: #66717d;
  font-size: 13px;
  margin-top: 4px;
}

@media (max-width: 760px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
"""


DASHBOARD_JS = """
async function loadDashboard() {
  const response = await fetch('/dashboard/state');
  const state = await response.json();

  renderList('mission-queue', state.mission_queue);
  renderList('running-missions', state.running_missions);
  renderList('completed-missions', state.completed_missions);
  renderList('mission-details', state.mission_details, true);
  renderMetrics('memory-usage', state.memory_usage);
  renderMetrics('knowledge-store', state.knowledge_store);
  renderReflections('reflection-reports', state.reflection_reports);
}

function renderList(id, items, details = false) {
  const element = document.getElementById(id);
  if (!items.length) {
    element.innerHTML = '<div class="meta">No records</div>';
    return;
  }

  element.innerHTML = items.map((item) => {
    const result = item.result || {};
    const finalOutput = details && result.final_output
      ? `<div class="meta">${escapeHtml(result.final_output.slice(0, 240))}</div>`
      : '';
    return `
      <div class="item">
        <strong>${escapeHtml(item.goal)}</strong>
        <div class="meta">${item.mission_id} · ${item.status}</div>
        ${finalOutput}
      </div>
    `;
  }).join('');
}

function renderMetrics(id, metrics) {
  const element = document.getElementById(id);
  const entries = Object.entries(metrics || {});
  if (!entries.length) {
    element.innerHTML = '<div class="meta">No metrics</div>';
    return;
  }

  element.innerHTML = entries.map(([key, value]) => `
    <div class="metric">
      <strong>${escapeHtml(key)}</strong>
      <div class="meta">${escapeHtml(String(value))}</div>
    </div>
  `).join('');
}

function renderReflections(id, reports) {
  const element = document.getElementById(id);
  if (!reports.length) {
    element.innerHTML = '<div class="meta">No reflection reports</div>';
    return;
  }

  element.innerHTML = reports.map((report) => `
    <div class="item">
      <strong>${escapeHtml(report.report_id)}</strong>
      <div class="meta">Success: ${report.success} · Score: ${report.score}</div>
      <div class="meta">${escapeHtml(report.summary || '')}</div>
    </div>
  `).join('');
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

document.getElementById('refresh').addEventListener('click', loadDashboard);
loadDashboard();
setInterval(loadDashboard, 5000);
"""
