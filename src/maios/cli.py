from __future__ import annotations

import sys
from pathlib import Path

import maios
from maios.runtime.loader import load_mission
from maios.runtime.runner import RuntimeRunner


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] in {"--version", "-V"}:
        print(maios.__version__)
        return

    if len(sys.argv) < 2:
        print("Usage: maios <mission.yaml>")
        print("       maios --version")
        raise SystemExit(1)

    mission_path = Path(sys.argv[1])
    mission = load_mission(mission_path)

    runner = RuntimeRunner()
    result = runner.run(mission)

    print(result.final_output)
    print("\nSaved outputs under: outputs/")


if __name__ == "__main__":
    main()
