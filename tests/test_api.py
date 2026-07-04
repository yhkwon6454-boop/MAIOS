from fastapi.testclient import TestClient

from maios.autonomous import MAIOSAgent
from maios.core import MAIOSCore
from maios.service import create_app


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return f"api output {len(self.prompts)}"


def make_client() -> TestClient:
    from maios.adapters.gpt_adapter import GPTAdapter

    core = MAIOSCore(gpt_adapter=GPTAdapter(FakeClient()))
    agent = MAIOSAgent(core=core)
    return TestClient(create_app(agent))


def test_health_endpoint():
    client = make_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "maios"


def test_run_endpoint_executes_mission_and_returns_result():
    client = make_client()

    response = client.post("/run", json={"goal": "Serve MAIOS over REST."})

    assert response.status_code == 200
    data = response.json()
    assert data["goal"] == "Serve MAIOS over REST."
    assert data["status"] == "COMPLETED"
    assert data["result"]["goal"] == "Serve MAIOS over REST."
    assert data["result"]["status"] == "COMPLETED"
    assert data["result"]["qa_result"]["score"] == 100
    assert data["result"]["reflection_report"]["success"] is True
    assert data["result"]["final_output"].startswith("# Multi-Agent Runtime Output")


def test_mission_endpoint_returns_existing_mission():
    client = make_client()
    created = client.post("/run", json={"goal": "Fetch mission by id."}).json()

    response = client.get(f"/mission/{created['mission_id']}")

    assert response.status_code == 200
    assert response.json()["mission_id"] == created["mission_id"]
    assert response.json()["result"]["goal"] == "Fetch mission by id."


def test_mission_endpoint_returns_404_for_missing_mission():
    client = make_client()

    response = client.get("/mission/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Mission not found"


def test_history_endpoint_lists_missions():
    client = make_client()
    first = client.post("/run", json={"goal": "History one."}).json()
    second = client.post("/run", json={"goal": "History two."}).json()

    response = client.get("/history")

    assert response.status_code == 200
    missions = response.json()
    assert [mission["mission_id"] for mission in missions] == [
        first["mission_id"],
        second["mission_id"],
    ]


def test_openapi_schema_is_available():
    client = make_client()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "MAIOS API"
    assert "/run" in schema["paths"]
    assert "/mission/{mission_id}" in schema["paths"]
