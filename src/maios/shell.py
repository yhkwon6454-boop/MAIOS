from __future__ import annotations

from collections.abc import Callable

from maios.kernel.agi_foundation import AGIFoundation, GoalPursuit
from maios.kernel.workspace import Workspace

BANNER = "MAIOS shell - every line becomes a goal. /help for commands, /exit to leave."

HELP_TEXT = """Commands:
  <objective>          pursue the objective through the cognitive loop
  /project <objective> decompose a large objective and pursue the sub-goals
  /research <question> research the question against accumulated knowledge
  /ingest <path>       read documents (md, txt, html) into the knowledge graph
  /approve             re-run the last objective with human approval
  /history             show recent pursuits
  /introspect          show the self-model and readiness
  /evolve              show the accumulated evolution report
  /help                show this help
  /exit                leave the shell (also /quit, exit, quit)"""

EXIT_COMMANDS = {"/exit", "/quit", "exit", "quit"}


class MAIOSShell:
    """Interactive session sharing one foundation and workspace."""

    def __init__(
        self,
        foundation: AGIFoundation,
        workspace: Workspace,
        input_fn: Callable[[str], str] | None = None,
        output_fn: Callable[[str], None] = print,
    ) -> None:
        self.foundation = foundation
        self.workspace = workspace
        self.input_fn = input_fn or (lambda prompt: input(prompt))
        self.output_fn = output_fn
        self.last_objective: str | None = None

    def run(self) -> None:
        self.output_fn(BANNER)
        self._print_memory()
        while True:
            try:
                line = self.input_fn("maios> ")
            except (EOFError, KeyboardInterrupt):
                self.output_fn("bye")
                return
            if not self.handle(line):
                return

    def handle(self, line: str) -> bool:
        text = line.strip()
        if not text:
            return True
        if text in EXIT_COMMANDS:
            self.output_fn("bye")
            return False
        if text == "/help":
            self.output_fn(HELP_TEXT)
            return True
        if text == "/introspect":
            self._introspect()
            return True
        if text == "/history":
            self._history()
            return True
        if text == "/evolve":
            self._evolve()
            return True
        if text == "/approve":
            self._approve()
            return True
        if text == "/project" or text.startswith("/project "):
            self._project(text[len("/project") :].strip())
            return True
        if text == "/ingest" or text.startswith("/ingest "):
            self._ingest(text[len("/ingest") :].strip())
            return True
        if text == "/research" or text.startswith("/research "):
            question = text[len("/research") :].strip()
            if not question:
                self.output_fn("usage: /research <question>")
                return True
            self._pursue(question, capabilities=("research",))
            return True
        self._pursue(text)
        return True

    def _pursue(
        self,
        objective: str,
        human_approved: bool = False,
        capabilities: tuple[str, ...] = (),
    ) -> None:
        pursuit = self.foundation.pursue(
            objective,
            human_approved=human_approved,
            capabilities=capabilities,
        )
        self.workspace.save(self.foundation)
        self.last_objective = objective
        self._print_pursuit(pursuit)
        self._print_memory()

    def _project(self, objective: str) -> None:
        if not objective:
            self.output_fn("usage: /project <objective>")
            return
        project = self.foundation.pursue_project(objective)
        self.workspace.save(self.foundation)
        self.output_fn(f"[{project.status}] project: {project.objective}")
        pursuits = {pursuit.pursuit_id: pursuit for pursuit in self.foundation.pursuits}
        for index, (subgoal, pursuit_id) in enumerate(
            zip(project.subgoals, project.pursuit_ids), start=1
        ):
            status = pursuits[pursuit_id].status if pursuit_id in pursuits else "?"
            self.output_fn(f"  {index}. [{status}] {subgoal}")
        if project.output:
            preview = project.output if len(project.output) <= 300 else project.output[:300] + "..."
            self.output_fn(preview)
            self.output_fn(f"  artifact: {self.workspace.project_artifact_path(project)}")
        self._print_memory()

    def _ingest(self, path: str) -> None:
        if not path:
            self.output_fn("usage: /ingest <path>")
            return
        if self.foundation.knowledge_graph is None:
            self.output_fn("no knowledge graph available in this session")
            return
        from maios.kernel.ingestor import DocumentIngestor

        report = DocumentIngestor(self.foundation.knowledge_graph).ingest(path)
        for file in report.files:
            self.output_fn(f"  ingested: {file}")
        for file in report.skipped:
            self.output_fn(f"  skipped: {file}")
        self.output_fn(f"[done] files={len(report.files)} chunks={report.chunks}")
        self._print_memory()

    def _approve(self) -> None:
        if self.last_objective is None:
            self.output_fn("nothing to approve yet - pursue an objective first")
            return
        self._pursue(self.last_objective, human_approved=True)

    def _print_pursuit(self, pursuit: GoalPursuit) -> None:
        self.output_fn(f"[{pursuit.status}] {pursuit.objective}")
        for cycle in self.foundation.cognitive_loop.cycles:
            if cycle.cycle_id not in pursuit.cycle_ids:
                continue
            for record in cycle.phases:
                if record.phase == "understand":
                    for entry in record.data.get("recalled", []):
                        self.output_fn(f"  recall: {entry}")
        if pursuit.status == "PENDING_APPROVAL" and pursuit.governance is not None:
            self.output_fn(f"  governance: {pursuit.governance['reason']}")
            self.output_fn("  type /approve to re-run with human approval")
        if pursuit.status == "BLOCKED" and pursuit.governance is not None:
            self.output_fn(f"  governance: {pursuit.governance['reason']}")
        if pursuit.output:
            preview = pursuit.output if len(pursuit.output) <= 300 else pursuit.output[:300] + "..."
            self.output_fn(preview)
            self.output_fn(f"  artifact: {self.workspace.artifact_path(pursuit)}")
        for lesson in pursuit.lessons:
            self.output_fn(f"  lesson: {lesson}")

    def _introspect(self) -> None:
        model = self.foundation.introspect()
        self.output_fn(
            f"identity={model.identity} version={model.version} readiness={model.readiness:.2f}"
        )
        self.output_fn(f"available: {', '.join(model.available())}")
        self.output_fn(f"missing: {', '.join(model.missing()) or '(none)'}")

    def _history(self) -> None:
        pursuits = self.foundation.pursuits
        if not pursuits:
            self.output_fn("no pursuits yet")
            return
        for pursuit in pursuits[-10:]:
            self.output_fn(f"[{pursuit.status}] {pursuit.objective} ({pursuit.pursuit_id})")

    def _evolve(self) -> None:
        report = self.foundation.evolve()
        self.output_fn(
            f"pursuits={report['pursuits']} executed={report['executed']} "
            f"success_rate={report['success_rate']} readiness={report['readiness']:.2f}"
        )
        for lesson in report["lessons"][:5]:
            self.output_fn(f"  lesson: {lesson}")

    def _print_memory(self) -> None:
        stats = self.workspace.stats()
        self.output_fn(
            f"[memory] nodes={stats['nodes']} pursuits={stats['pursuits']} "
            f"workspace={self.workspace.root}"
        )
