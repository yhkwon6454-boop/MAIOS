from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from maios.agents import AgentRole, AgentRoleManager, NegotiationManager, SwarmManager
from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.reflection.engine import ImprovementReport, ReflectionEngine


class SourceCollector(Protocol):
    def collect(self, question: str, limit: int = 3) -> list[ResearchSource]: ...


@dataclass(frozen=True)
class ResearchSource:
    title: str
    content: str
    url: str = ""
    source_id: str = field(default_factory=lambda: f"RS-{uuid4().hex[:8]}")
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self, max_length: int = 160) -> str:
        compact = " ".join(self.content.split())
        if len(compact) <= max_length:
            return compact
        return f"{compact[: max_length - 3]}..."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchTask:
    question: str
    task_id: str = field(default_factory=lambda: f"RT-{uuid4().hex[:8]}")
    sub_questions: list[str] = field(default_factory=list)
    sources: list[ResearchSource] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    status: str = "DEFINED"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def mark(self, status: str) -> None:
        self.status = status
        self.updated_at = datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ResearchReport:
    question: str
    sub_questions: tuple[str, ...]
    findings: tuple[str, ...]
    gaps: tuple[str, ...]
    sources: tuple[ResearchSource, ...]
    report_id: str = field(default_factory=lambda: f"RR-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "question": self.question,
            "sub_questions": list(self.sub_questions),
            "findings": list(self.findings),
            "gaps": list(self.gaps),
            "sources": [source.to_dict() for source in self.sources],
            "created_at": self.created_at,
        }

    def to_markdown(self) -> str:
        return "\n".join(
            [
                f"# Research Report: {self.question}",
                "",
                "## Sub-questions",
                *[f"- {item}" for item in self.sub_questions],
                "",
                "## Findings",
                *[f"- {item}" for item in self.findings],
                "",
                "## Gaps",
                *[f"- {item}" for item in self.gaps],
                "",
                "## Sources",
                *[
                    f"- {source.title}{f' ({source.url})' if source.url else ''}"
                    for source in self.sources
                ],
            ]
        )


class InMemorySourceCollector:
    """Offline collector backed by configured source records."""

    def __init__(self, sources: list[ResearchSource] | None = None) -> None:
        self.sources = sources or []

    def collect(self, question: str, limit: int = 3) -> list[ResearchSource]:
        query_terms = [term.lower() for term in question.split() if len(term) > 2]
        matches = [
            source
            for source in self.sources
            if any(term in f"{source.title} {source.content}".lower() for term in query_terms)
        ]
        return (matches or self.sources)[:limit]


class ResearchEngine:
    """Runs an autonomous, offline-testable research workflow."""

    def __init__(
        self,
        source_collector: SourceCollector | None = None,
        knowledge_store: KnowledgeStore | None = None,
        memory_kernel: MemoryKernel | None = None,
        reflection_engine: ReflectionEngine | None = None,
        swarm_manager: SwarmManager | None = None,
        role_manager: AgentRoleManager | None = None,
        negotiation_manager: NegotiationManager | None = None,
    ) -> None:
        self.source_collector = source_collector or InMemorySourceCollector()
        self.knowledge_store = knowledge_store or KnowledgeStore()
        self.memory_kernel = memory_kernel or MemoryKernel(knowledge_store=self.knowledge_store)
        self.reflection_engine = reflection_engine or ReflectionEngine(self.knowledge_store)
        self.swarm_manager = swarm_manager
        self.role_manager = role_manager
        self.negotiation_manager = negotiation_manager
        self.tasks: dict[str, ResearchTask] = {}
        self.reports: dict[str, ResearchReport] = {}

    def define_question(self, question: str) -> ResearchTask:
        task = ResearchTask(question=question.strip())
        if not task.question:
            raise ValueError("Research question is required.")
        self.tasks[task.task_id] = task
        self.memory_kernel.remember_short_term(
            {"research_task_id": task.task_id, "question": task.question}
        )
        return task

    def decompose(self, task: ResearchTask, max_sub_questions: int = 3) -> list[str]:
        normalized = task.question.rstrip("?.")
        parts = [part.strip() for part in normalized.replace(" and ", ",").split(",")]
        sub_questions = [part for part in parts if part]
        if len(sub_questions) <= 1:
            sub_questions = [
                f"What is the current state of {normalized}?",
                f"What evidence supports {normalized}?",
                f"What risks or gaps remain for {normalized}?",
            ]
        task.sub_questions = sub_questions[:max_sub_questions]
        task.mark("DECOMPOSED")
        return task.sub_questions

    def collect_sources(
        self,
        task: ResearchTask,
        limit_per_question: int = 3,
    ) -> list[ResearchSource]:
        if not task.sub_questions:
            self.decompose(task)

        seen: set[str] = set()
        for sub_question in task.sub_questions:
            for source in self.source_collector.collect(sub_question, limit=limit_per_question):
                if source.source_id in seen:
                    continue
                seen.add(source.source_id)
                task.sources.append(source)
                self.knowledge_store.add(
                    source.content,
                    metadata={
                        "memory_type": "research_source",
                        "source_id": source.source_id,
                        "title": source.title,
                        "url": source.url,
                        **source.metadata,
                    },
                    document_id=source.source_id,
                )
        task.mark("SOURCES_COLLECTED")
        return task.sources

    def summarize_findings(self, task: ResearchTask) -> list[str]:
        findings = []
        for sub_question in task.sub_questions:
            related_sources = self._sources_for_question(task.sources, sub_question)
            if not related_sources:
                continue
            source = related_sources[0]
            findings.append(f"{sub_question}: {source.summary()}")
        task.findings = findings
        task.mark("FINDINGS_SUMMARIZED")
        return findings

    def identify_gaps(self, task: ResearchTask) -> list[str]:
        gaps = []
        for sub_question in task.sub_questions:
            if not self._sources_for_question(task.sources, sub_question):
                gaps.append(f"No source evidence collected for: {sub_question}")
        if not task.sources:
            gaps.append("No research sources were collected.")
        if len(task.sources) < len(task.sub_questions):
            gaps.append("Source coverage is thinner than the sub-question set.")
        task.gaps = gaps or ["No critical evidence gaps identified."]
        task.mark("GAPS_IDENTIFIED")
        return task.gaps

    def generate_report(self, task: ResearchTask) -> ResearchReport:
        report = ResearchReport(
            question=task.question,
            sub_questions=tuple(task.sub_questions),
            findings=tuple(task.findings),
            gaps=tuple(task.gaps),
            sources=tuple(task.sources),
        )
        self.reports[report.report_id] = report
        task.mark("COMPLETED")
        self.knowledge_store.add(
            report.to_markdown(),
            metadata={"memory_type": "research_report", "question": report.question},
            document_id=report.report_id,
        )
        self.memory_kernel.remember_long_term(
            report.to_markdown(),
            metadata={"memory_type": "research_report", "report_id": report.report_id},
        )
        self._reflect(task, report)
        return report

    def run(self, question: str) -> ResearchReport:
        task = self.define_question(question)
        self.decompose(task)
        self._coordinate_swarm(task)
        self.collect_sources(task)
        self.summarize_findings(task)
        self.identify_gaps(task)
        self._negotiate_gaps(task)
        return self.generate_report(task)

    def _sources_for_question(
        self,
        sources: list[ResearchSource],
        question: str,
    ) -> list[ResearchSource]:
        terms = [term.lower() for term in question.split() if len(term) > 3]
        if not terms:
            return sources
        matches = [
            source
            for source in sources
            if any(term in f"{source.title} {source.content}".lower() for term in terms)
        ]
        return matches

    def _coordinate_swarm(self, task: ResearchTask) -> None:
        if self.swarm_manager is None:
            return
        swarm = self.swarm_manager.form_swarm(
            name=f"research:{task.task_id}",
            capabilities=["research"],
            role=AgentRole.SPECIALIST,
        )
        if swarm.members:
            self.swarm_manager.distribute_tasks(
                swarm.swarm_id,
                [("research", {"task": sub_question}) for sub_question in task.sub_questions],
            )

    def _negotiate_gaps(self, task: ResearchTask) -> None:
        if self.negotiation_manager is None or not task.gaps:
            return
        participants = []
        if self.role_manager is not None:
            participants = [
                agent.agent_id
                for agent in self.role_manager.select_agents(
                    ["research"],
                    role=AgentRole.SPECIALIST,
                )
            ]
        session = self.negotiation_manager.create_session(
            topic=f"Research gaps for {task.question}",
            participants=participants,
            consensus_threshold=0.5,
        )
        self.negotiation_manager.generate_proposal(
            session.session_id,
            proposer_id=participants[0] if participants else "research_engine",
            content={"gaps": list(task.gaps)},
        )

    def _reflect(self, task: ResearchTask, report: ResearchReport) -> None:
        reflection = ImprovementReport(
            mission_id=task.task_id,
            success=bool(report.findings),
            score=90 if report.findings else 40,
            summary=(
                f"Research completed for '{task.question}' with "
                f"{len(report.findings)} finding(s)."
            ),
            bottlenecks=[] if report.findings else ["No findings generated."],
            improvement_points=list(report.gaps),
        )
        self.reflection_engine.store(reflection)
