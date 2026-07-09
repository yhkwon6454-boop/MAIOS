from __future__ import annotations

from fastapi.testclient import TestClient

from maios.service import create_app


def main() -> None:
    client = TestClient(create_app())
    response = client.post("/run", json={"goal": "Run a MAIOS API demo mission."})
    response.raise_for_status()
    data = response.json()

    print(f"Mission: {data['mission_id']}")
    print(f"Status: {data['status']}")
    print(data["result"]["final_output"])


if __name__ == "__main__":
    main()
