from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from maios.knowledge.store import KnowledgeStore
from maios.runtime.models import Mission, QAResult, Status


@dataclass
class ImprovementReport:
    mission_id: str
    success: bool
    score: int
    summary: str
    bottlenecks: list[str] = field(default_factory=list)
    improvement_points: list[str] = field(default_factory=list)
    report_id: str = field(default_factory=lambda: f"IR-{uuid4().hex[:8]}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReflectionEngine:
    """Analyzes completed mission execution and produces improvement guidance."""

    def __init__(self, knowledge_store: KnowledgeStore | None = None) -> None:
        self.knowledge_store = knowledge_store or KnowledgeStore()

    def analyze(
        self,
        mission: Mission,
        qa_result: QAResult,
        execution_result: dict[str, Any] | None = None,
        task_outputs: list[str] | None = None,
        goal=None,
    ) -> ImprovementReport:
        task_outputs = task_outputs or []
        bottlenecks = self._detect_bottlenecks(
            qa_result=qa_result,
            execution_result=execution_result or {},
            task_outputs=task_outputs,
            goal=goal,
        )
        improvement_points = self._build_improvement_points(bottlenecks, qa_result)
        success = (
            qa_result.status == Status.COMPLETED
            and qa_result.score >= 70
            and not any(not output.strip() for output in task_outputs)
        )

        report = ImprovementReport(
            mission_id=mission.mission_id,
            success=success,
            score=qa_result.score,
            summary=self._summary(mission, success, qa_result, bottlenecks),
            bottlenecks=bottlenecks,
            improvement_points=improvement_points,
        )
        self.store(report)
        return report

    def store(self, report: ImprovementReport) -> str:
        return self.knowledge_store.add(
            self.format_report(report),
            metadata={
                "memory_type": "reflection",
                "mission_id": report.mission_id,
                "report_id": report.report_id,
                "success": report.success,
                "score": report.score,
            },
            document_id=report.report_id,
        )

    def format_report(self, report: ImprovementReport) -> str:
        return "\n".join(
            [
                f"Reflection Report: {report.report_id}",
                f"Mission: {report.mission_id}",
                f"Success: {report.success}",
                f"Score: {report.score}",
                f"Summary: {report.summary}",
                "Bottlenecks:",
                *[f"- {item}" for item in report.bottlenecks],
                "Improvement Points:",
                *[f"- {item}" for item in report.improvement_points],
            ]
        )

    def _detect_bottlenecks(
        self,
        qa_result: QAResult,
        execution_result: dict[str, Any],
        task_outputs: list[str],
        goal,
    ) -> list[str]:
        bottlenecks: list[str] = []

        if qa_result.status != Status.COMPLETED:
            bottlenecks.append(f"Quality status is {qa_result.status.value}.")

        for issue in qa_result.issues:
            bottlenecks.append(f"QA issue: {issue}")

        for index, output in enumerate(task_outputs):
            if not output.strip():
                bottlenecks.append(f"Task output is empty: {index}")

        if execution_result and execution_result.get("status") != "EXECUTED":
            bottlenecks.append("Executor did not report EXECUTED status.")

        if goal is not None:
            for task in getattr(goal, "tasks", []):
                if any("retry" in item.lower() or "blocked" in item.lower() for item in task.feedback):
                    bottlenecks.append(f"Task required retry: {task.description}")

        return bottlenecks

    def _build_improvement_points(
        self,
        bottlenecks: list[str],
        qa_result: QAResult,
    ) -> list[str]:
        if not bottlenecks and qa_result.score >= 90:
            return ["Preserve the current execution pattern for similar missions."]

        improvement_points = []
        if qa_result.score < 70:
            improvement_points.append("Improve output quality before marking the mission complete.")

        if any("empty" in item.lower() for item in bottlenecks):
            improvement_points.append("Add validation before accepting empty model outputs.")

        if any("retry" in item.lower() or "blocked" in item.lower() for item in bottlenecks):
            improvement_points.append("Prioritize blocked or retried tasks earlier in the queue.")

        if not improvement_points:
            improvement_points.append("Review bottlenecks and refine planning, memory, or execution prompts.")

        return improvement_points

    def _summary(
        self,
        mission: Mission,
        success: bool,
        qa_result: QAResult,
        bottlenecks: list[str],
    ) -> str:
        outcome = "succeeded" if success else "needs improvement"
        return (
            f"Mission '{mission.title}' {outcome} with score {qa_result.score}. "
            f"Detected {len(bottlenecks)} bottleneck(s)."
        )
