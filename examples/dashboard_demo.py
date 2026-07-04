from __future__ import annotations

from fastapi.testclient import TestClient

from maios.service import create_app


def main() -> None:
    client = TestClient(create_app())
    client.post("/run", json={"goal": "Populate the MAIOS dashboard demo."})
    dashboard = client.get("/dashboard")
    dashboard.raise_for_status()

    print("Dashboard available at /dashboard")
    print(dashboard.text[:120])


if __name__ == "__main__":
    main()
