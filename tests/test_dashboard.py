from fastapi.testclient import TestClient

from maios.adapters.gpt_adapter import GPTAdapter
from maios.autonomous import MAIOSAgent
from maios.core import MAIOSCore
from maios.service import create_app


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return f"dashboard output {len(self.prompts)}"


def make_client() -> TestClient:
    core = MAIOSCore(gpt_adapter=GPTAdapter(FakeClient()))
    agent = MAIOSAgent(core=core)
    return TestClient(create_app(agent))


def test_dashboard_html_is_served():
    client = make_client()

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "MAIOS Dashboard" in response.text
    assert "Mission Queue" in response.text
    assert "Running Missions" in response.text
    assert "Completed Missions" in response.text
    assert "Mission Details" in response.text
    assert "Memory Usage" in response.text
    assert "Knowledge Store Status" in response.text
    assert "Reflection Reports" in response.text
    assert "/dashboard.js" in response.text


def test_dashboard_assets_are_served():
    client = make_client()

    css = client.get("/dashboard.css")
    js = client.get("/dashboard.js")

    assert css.status_code == 200
    assert ".layout" in css.text
    assert js.status_code == 200
    assert "fetch('/dashboard/state')" in js.text
    assert "setInterval" in js.text


def test_dashboard_state_empty():
    client = make_client()

    response = client.get("/dashboard/state")

    assert response.status_code == 200
    state = response.json()
    assert state["mission_queue"] == []
    assert state["running_missions"] == []
    assert state["completed_missions"] == []
    assert state["mission_details"] == []
    assert state["memory_usage"]["short_term"] == 0
    assert state["knowledge_store"]["records"] == 0
    assert state["reflection_reports"] == []


def test_dashboard_state_after_mission_run():
    client = make_client()

    created = client.post("/run", json={"goal": "Show dashboard mission."}).json()
    response = client.get("/dashboard/state")

    assert response.status_code == 200
    state = response.json()
    assert state["mission_queue"] == []
    assert state["running_missions"] == []
    assert len(state["completed_missions"]) == 1
    assert state["completed_missions"][0]["mission_id"] == created["mission_id"]
    assert len(state["mission_details"]) == 1
    assert state["memory_usage"]["short_term"] >= 1
    assert state["memory_usage"]["conversation_history"] >= 1
    assert state["knowledge_store"]["records"] >= 1
    assert len(state["reflection_reports"]) == 1
    assert state["reflection_reports"][0]["success"] is True


def test_dashboard_openapi_paths_exist():
    client = make_client()

    schema = client.get("/openapi.json").json()

    assert "/dashboard" in schema["paths"]
    assert "/dashboard/state" in schema["paths"]
