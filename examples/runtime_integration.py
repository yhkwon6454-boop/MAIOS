from __future__ import annotations

from pathlib import Path

from maios.runtime.loader import load_mission
from maios.runtime.runner import RuntimeRunner


def main() -> None:
    mission = load_mission(Path(__file__).with_name("writing_project.yaml"))
    result = RuntimeRunner().run(mission)
    print(result.final_output)


if __name__ == "__main__":
    main()
