from __future__ import annotations

import sys
from pathlib import Path

from maios.runtime.loader import load_mission
from maios.runtime.runner import RuntimeRunner


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m maios.cli <mission.yaml>")
        raise SystemExit(1)

    mission_path = Path(sys.argv[1])
    mission = load_mission(mission_path)

    runner = RuntimeRunner()
    result = runner.run(mission)

    print(result.final_output)
    print(f"\nSaved outputs under: outputs/")


if __name__ == "__main__":
    main()
