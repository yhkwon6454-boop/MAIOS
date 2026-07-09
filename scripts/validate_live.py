"""Live validation harness for MAIOS with a real LLM provider.

Runs the full cognitive stack end-to-end and reports pass/fail per stage:

    python scripts/validate_live.py                # uses claude
    python scripts/validate_live.py --provider mock  # offline dry run

Stages: provider connectivity, goal pursuit with a generated deliverable,
document ingestion + memory recall, research over ingested knowledge, and
project decomposition with sub-goal chaining and synthesis.

Requires the provider's API key (e.g. ANTHROPIC_API_KEY in .env) and
credits. Designed so that the morning after credits arrive, one command
answers "does the whole pipeline work with a real model?".
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from maios.adapters.llm_provider import create_llm_provider
from maios.config import load_config
from maios.governance import GovernanceManager
from maios.kernel import DocumentIngestor, Workspace

RESULTS: list[tuple[str, bool, str]] = []


def record(stage: str, passed: bool, detail: str) -> None:
    RESULTS.append((stage, passed, detail))
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {stage}: {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="claude", help="mock | openai | claude | gemini")
    parser.add_argument("--keep", action="store_true", help="keep the validation workspace")
    args = parser.parse_args()

    config = load_config()
    config.model_provider = args.provider
    provider = create_llm_provider(config)

    # Stage 1: provider connectivity (also proves credits exist)
    try:
        reply = provider.generate("Reply with exactly: OK")
        record("provider", bool(reply.strip()), f"{args.provider} replied ({reply.strip()[:40]})")
    except Exception as error:  # noqa: BLE001 - report any provider failure
        record("provider", False, f"{type(error).__name__}: {str(error)[:160]}")
        print("\nProvider unreachable - fix credits/key first. Aborting.")
        return 1

    workdir = Path(tempfile.mkdtemp(prefix="maios-live-"))
    space = Workspace(workdir / ".maios")
    agi = space.build_foundation(governance=GovernanceManager(), llm_provider=provider)

    # Stage 2: goal pursuit produces a real deliverable
    pursuit = agi.pursue("Write a three-sentence summary of why drones changed modern war")
    space.save(agi)
    generated = bool(pursuit.output) and pursuit.output != pursuit.objective
    record(
        "pursue",
        pursuit.success and generated,
        f"status={pursuit.status} output_chars={len(pursuit.output)}",
    )

    # Stage 3: ingestion + recall
    doc = workdir / "doctrine.md"
    doc.write_text(
        "# Swarm Defense\nLayered jamming plus interceptor drones covers the low tier. "
        "Exercises showed point defenses alone failed against saturation attacks.",
        encoding="utf-8",
    )
    report = DocumentIngestor(agi.knowledge_graph).ingest(doc)
    recall_pursuit = agi.pursue("Summarize our swarm defense doctrine in two sentences")
    space.save(agi)
    recalled = any(
        "doctrine.md" in entry
        for cycle in agi.cognitive_loop.cycles
        if cycle.cycle_id in recall_pursuit.cycle_ids
        for record_ in cycle.phases
        for entry in record_.data.get("recalled", [])
    )
    record(
        "ingest+recall",
        report.chunks > 0 and recalled,
        f"chunks={report.chunks} recalled_doc={recalled}",
    )

    # Stage 4: research over accumulated knowledge
    research = agi.pursue("swarm defense options", capabilities=("research",))
    space.save(agi)
    record(
        "research",
        research.success and research.output.startswith("# Research Report"),
        f"status={research.status} cites_doc={'doctrine.md' in research.output}",
    )

    # Stage 5: project decomposition and synthesis
    project = agi.pursue_project(
        "Produce a short two-part brief: current drone threats, then countermeasures",
        max_subgoals=3,
    )
    space.save(agi)
    decomposed = len(project.subgoals) >= 2
    record(
        "project",
        project.success and bool(project.output),
        f"subgoals={len(project.subgoals)} decomposed={decomposed} "
        f"output_chars={len(project.output)}",
    )
    if not decomposed:
        print(
            "  note: decomposition fell back to a single goal - "
            "check GoalDecomposer prompt against real model output"
        )

    evolution = agi.evolve()
    print(
        f"\n[evolution] pursuits={evolution['pursuits']} "
        f"success_rate={evolution['success_rate']}"
    )
    print(f"[workspace] {space.root}" + ("" if args.keep else " (temporary)"))

    failed = [stage for stage, passed, _ in RESULTS if not passed]
    print("\n=== RESULT:", "ALL PASS" if not failed else f"FAILED: {', '.join(failed)}", "===")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
