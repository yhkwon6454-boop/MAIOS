from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.reflection.engine import ImprovementReport, ReflectionEngine


@dataclass(frozen=True)
class ReflectionRecord:
    subject_id: str
    source_type: str
    status: str
    observations: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    bottlenecks: tuple[str, ...] = ()
    repeated_mistakes: tuple[str, ...] = ()
    metrics: dict[str, float] = field(default_factory=dict)
    record_id: str = field(default_factory=lambda: f"REF-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImprovementPlan:
    target: str
    actions: tuple[str, ...]
    prompt_updates: tuple[str, ...] = ()
    priority: str = "medium"
    metrics_baseline: dict[str, float] = field(default_factory=dict)
    source_record_ids: tuple[str, ...] = ()
    plan_id: str = field(default_factory=lambda: f"IP-{uuid4().hex[:8]}")
    status: str = "PROPOSED"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        return "\n".join(
            [
                f"# Improvement Plan: {self.target}",
                f"Priority: {self.priority}",
                "",
                "## Actions",
                *[f"- {action}" for action in self.actions],
                "",
                "## Prompt Updates",
                *[f"- {update}" for update in self.prompt_updates],
            ]
        )


class SelfImprovementEngine:
    """Analyzes research and execution traces to produce actionable improvements."""

    def __init__(
        self,
        reflection_engine: ReflectionEngine | None = None,
        research_engine: Any | None = None,
        knowledge_store: KnowledgeStore | None = None,
        memory_kernel: MemoryKernel | None = None,
        swarm_manager: Any | None = None,
        distributed_runtime: Any | None = None,
    ) -> None:
        self.knowledge_store = knowledge_store or KnowledgeStore()
        self.memory_kernel = memory_kernel or MemoryKernel(knowledge_store=self.knowledge_store)
        self.reflection_engine = reflection_engine or ReflectionEngine(self.knowledge_store)
        self.research_engine = research_engine
        self.swarm_manager = swarm_manager
        self.distributed_runtime = distributed_runtime
        self.records: list[ReflectionRecord] = []
        self.plans: list[ImprovementPlan] = []
        self.performance_metrics: dict[str, list[float]] = {}

    def analyze_research_task(
        self,
        task: Any,
        report: Any | None = None,
    ) -> ReflectionRecord:
        observations = [f"Research task status: {getattr(task, 'status', 'UNKNOWN')}"]
        failures = []
        bottlenecks = []

        sources = list(getattr(task, "sources", []))
        findings = list(getattr(task, "findings", []))
        gaps = list(getattr(task, "gaps", []))

        if getattr(task, "status", "") != "COMPLETED":
            failures.append("Research task did not complete.")
        if not sources:
            bottlenecks.append("No sources were collected.")
        if not findings:
            failures.append("No findings were generated.")
        bottlenecks.extend(gap for gap in gaps if "No " in gap or "thin" in gap.lower())

        if report is not None:
            observations.append(
                f"Report contains {len(getattr(report, 'findings', ()))} finding(s)."
            )

        metrics = {
            "source_count": float(len(sources)),
            "finding_count": float(len(findings)),
            "gap_count": float(len(gaps)),
        }
        record = ReflectionRecord(
            subject_id=getattr(task, "task_id", "research"),
            source_type="research",
            status="FAILED" if failures else "COMPLETED",
            observations=tuple(observations),
            failures=tuple(failures),
            bottlenecks=tuple(bottlenecks),
            repeated_mistakes=self.detect_repeated_mistakes([*failures, *bottlenecks]),
            metrics=metrics,
        )
        self._store_record(record)
        return record

    def analyze_execution_history(self, history: list[Any] | tuple[Any, ...]) -> ReflectionRecord:
        failures = []
        bottlenecks = []
        observations = [f"Analyzed {len(history)} execution item(s)."]

        for item in history:
            if isinstance(item, dict):
                status = str(item.get("status", ""))
                error = str(item.get("error", ""))
                active_tasks = item.get("active_tasks")
            else:
                status = str(getattr(item, "status", ""))
                error = str(getattr(item, "error", ""))
                active_tasks = getattr(item, "active_tasks", None)
            if status.upper() == "FAILED":
                failures.append(error or "Execution item failed.")
            if isinstance(active_tasks, int) and active_tasks > 3:
                bottlenecks.append(f"High active task load: {active_tasks}")

        repeated = self.detect_repeated_mistakes([*failures, *bottlenecks])
        record = ReflectionRecord(
            subject_id="execution_history",
            source_type="execution",
            status="FAILED" if failures else "COMPLETED",
            observations=tuple(observations),
            failures=tuple(failures),
            bottlenecks=tuple(bottlenecks),
            repeated_mistakes=repeated,
            metrics={
                "history_count": float(len(history)),
                "failure_count": float(len(failures)),
                "bottleneck_count": float(len(bottlenecks)),
            },
        )
        self._store_record(record)
        return record

    def detect_repeated_mistakes(self, issues: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        counts: dict[str, int] = {}
        for issue in issues:
            normalized = issue.strip().lower()
            if not normalized:
                continue
            counts[normalized] = counts.get(normalized, 0) + 1
        return tuple(issue for issue, count in counts.items() if count > 1)

    def generate_plan(
        self,
        records: ReflectionRecord | list[ReflectionRecord] | tuple[ReflectionRecord, ...],
        target: str = "maios",
    ) -> ImprovementPlan:
        record_list = [records] if isinstance(records, ReflectionRecord) else list(records)
        issues: list[str] = []
        for record in record_list:
            issues.extend(record.failures)
            issues.extend(record.bottlenecks)
            issues.extend(record.repeated_mistakes)

        actions = self._actions_for_issues(issues)
        prompt_updates = self.prompt_evolution_strategies(issues)
        priority = "high" if any(record.failures for record in record_list) else "medium"
        baseline = self._baseline_metrics(record_list)
        plan = ImprovementPlan(
            target=target,
            actions=tuple(actions),
            prompt_updates=tuple(prompt_updates),
            priority=priority,
            metrics_baseline=baseline,
            source_record_ids=tuple(record.record_id for record in record_list),
        )
        self._store_plan(plan)
        return plan

    def prompt_evolution_strategies(
        self,
        issues: list[str] | tuple[str, ...],
    ) -> list[str]:
        updates = []
        issue_text = " ".join(issues).lower()
        if "source" in issue_text or "evidence" in issue_text:
            updates.append("Require cited evidence before summarizing findings.")
        if "finding" in issue_text:
            updates.append("Ask agents to extract concrete findings from each source.")
        if "failed" in issue_text or "error" in issue_text:
            updates.append("Add failure-mode checks before marking tasks complete.")
        if not updates:
            updates.append("Preserve current prompts and monitor future regressions.")
        return updates

    def evolve_prompt(
        self,
        prompt: str,
        plan: ImprovementPlan,
        strategy: str = "append",
    ) -> str:
        guidance = "\n".join(f"- {update}" for update in plan.prompt_updates)
        if strategy == "prepend":
            return f"Improvement guidance:\n{guidance}\n\n{prompt}"
        if strategy == "replace":
            return f"{prompt}\n\nUpdated operating guidance:\n{guidance}"
        return f"{prompt}\n\nImprovement guidance:\n{guidance}"

    def track_metric(self, name: str, value: float) -> None:
        self.performance_metrics.setdefault(name, []).append(value)
        self.memory_kernel.remember_short_term({"metric": name, "value": value})

    def metric_trend(self, name: str) -> dict[str, float]:
        values = self.performance_metrics.get(name, [])
        if not values:
            return {"count": 0.0, "latest": 0.0, "average": 0.0, "delta": 0.0}
        return {
            "count": float(len(values)),
            "latest": values[-1],
            "average": sum(values) / len(values),
            "delta": values[-1] - values[0],
        }

    def improve_from_research(self, task: Any, report: Any | None = None) -> ImprovementPlan:
        record = self.analyze_research_task(task, report=report)
        return self.generate_plan(record, target=getattr(task, "question", "research"))

    def improve_from_runtime(self) -> ImprovementPlan:
        if self.distributed_runtime is None:
            raise RuntimeError("No distributed runtime configured.")
        record = self.analyze_execution_history(self.distributed_runtime.history())
        return self.generate_plan(record, target="distributed_runtime")

    def _actions_for_issues(self, issues: list[str]) -> list[str]:
        if not issues:
            return ["Continue monitoring performance metrics for regressions."]

        actions = []
        issue_text = " ".join(issues).lower()
        if "source" in issue_text:
            actions.append("Increase source collection breadth for weak research areas.")
        if "finding" in issue_text:
            actions.append("Add a finding extraction pass before final report generation.")
        if "failed" in issue_text or "error" in issue_text:
            actions.append("Route failed tasks through retry or swarm replacement.")
        if "load" in issue_text:
            actions.append("Rebalance overloaded agents before dispatching new work.")
        if not actions:
            actions.append("Review recorded bottlenecks and add targeted validation.")
        return actions

    def _baseline_metrics(self, records: list[ReflectionRecord]) -> dict[str, float]:
        baseline: dict[str, float] = {}
        for record in records:
            for key, value in record.metrics.items():
                baseline[key] = baseline.get(key, 0.0) + value
        return baseline

    def _store_record(self, record: ReflectionRecord) -> None:
        self.records.append(record)
        self.memory_kernel.remember_short_term(
            {"reflection_record": record.record_id, "status": record.status}
        )
        self.memory_kernel.remember_long_term(
            str(record.to_dict()),
            metadata={"memory_type": "reflection_record", "record_id": record.record_id},
        )
        self.knowledge_store.add(
            str(record.to_dict()),
            metadata={"memory_type": "reflection_record", "source_type": record.source_type},
            document_id=record.record_id,
        )

    def _store_plan(self, plan: ImprovementPlan) -> None:
        self.plans.append(plan)
        self.memory_kernel.remember_short_term(
            {"improvement_plan": plan.plan_id, "priority": plan.priority}
        )
        self.knowledge_store.add(
            plan.to_markdown(),
            metadata={"memory_type": "improvement_plan", "priority": plan.priority},
            document_id=plan.plan_id,
        )
        report = ImprovementReport(
            mission_id=plan.plan_id,
            success=True,
            score=90,
            summary=f"Generated improvement plan for {plan.target}.",
            improvement_points=list(plan.actions),
        )
        self.reflection_engine.store(report)
