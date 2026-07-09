from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import maios
from maios.runtime.loader import load_mission
from maios.runtime.runner import RuntimeRunner

if TYPE_CHECKING:
    from maios.kernel.agi_foundation import AGIFoundation, GoalPursuit


def _print_usage() -> None:
    print("Usage: maios <mission.yaml>")
    print("       maios pursue <objective> [--capability NAME ...] [--max-cycles N] [--approve]")
    print("       maios introspect")
    print("       maios --version")


def build_foundation() -> AGIFoundation:
    from maios.governance import GovernanceManager
    from maios.kernel.agi_foundation import AGIFoundation
    from maios.kernel.memory_kernel import MemoryKernel
    from maios.knowledge.graph import KnowledgeGraph

    return AGIFoundation(
        knowledge_graph=KnowledgeGraph(),
        memory_kernel=MemoryKernel(),
        governance=GovernanceManager(),
    )


def _print_pursuit(agi: AGIFoundation, pursuit: GoalPursuit) -> None:
    print(f"[MAIOS] objective: {pursuit.objective}")
    if pursuit.governance is not None:
        print(
            f"[governance] risk={pursuit.governance['risk_level']} "
            f"approved={pursuit.governance['approved']} "
            f"reason={pursuit.governance['reason']}"
        )
    cycles = [cycle for cycle in agi.cognitive_loop.cycles if cycle.cycle_id in pursuit.cycle_ids]
    print(f"[cycles] {len(cycles)} executed")
    for index, cycle in enumerate(cycles, start=1):
        print(f"  cycle {index}: {cycle.status} ({' -> '.join(cycle.phase_order())})")
    if pursuit.lessons:
        print("[lessons]")
        for lesson in pursuit.lessons:
            print(f"  - {lesson}")
    print(f"[status] {pursuit.status}")


def run_pursue(args: list[str]) -> None:
    objective_parts: list[str] = []
    capabilities: list[str] = []
    max_cycles = 3
    approve = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--capability":
            index += 1
            capabilities.append(args[index])
        elif arg == "--max-cycles":
            index += 1
            max_cycles = int(args[index])
        elif arg == "--approve":
            approve = True
        else:
            objective_parts.append(arg)
        index += 1
    objective = " ".join(objective_parts).strip()
    if not objective:
        _print_usage()
        raise SystemExit(1)

    agi = build_foundation()
    pursuit = agi.pursue(
        objective,
        capabilities=tuple(capabilities),
        max_cycles=max_cycles,
        human_approved=approve,
    )
    _print_pursuit(agi, pursuit)


def run_introspect() -> None:
    agi = build_foundation()
    model = agi.introspect()
    print(
        f"[MAIOS] identity={model.identity} version={model.version} "
        f"readiness={model.readiness:.2f}"
    )
    print(f"[available] {', '.join(model.available())}")
    print(f"[missing] {', '.join(model.missing()) or '(none)'}")


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] in {"--version", "-V"}:
        print(maios.__version__)
        return

    if not argv:
        _print_usage()
        raise SystemExit(1)

    if argv[0] == "pursue":
        run_pursue(argv[1:])
        return

    if argv[0] == "introspect":
        run_introspect()
        return

    mission_path = Path(argv[0])
    mission = load_mission(mission_path)

    runner = RuntimeRunner()
    result = runner.run(mission)

    print(result.final_output)
    print("\nSaved outputs under: outputs/")


if __name__ == "__main__":
    main()
