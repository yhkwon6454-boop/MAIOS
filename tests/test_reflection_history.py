from __future__ import annotations

from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.store import KnowledgeStore
from maios.reflection import ReflectionRecord, SelfImprovementEngine


def test_self_improvement_stores_reflection_history_in_memory_kernel():
    knowledge_store = KnowledgeStore()
    memory_kernel = MemoryKernel(knowledge_store=knowledge_store)
    engine = SelfImprovementEngine(
        knowledge_store=knowledge_store,
        memory_kernel=memory_kernel,
    )

    record = engine.analyze_execution_history(
        [
            {"status": "FAILED", "error": "timeout"},
            {"status": "FAILED", "error": "timeout"},
            {"status": "COMPLETED"},
        ]
    )

    assert record.repeated_mistakes == ("timeout",)
    assert engine.records == [record]
    assert memory_kernel.session_memory[-1] == {
        "reflection_record": record.record_id,
        "status": "FAILED",
    }
    assert any(
        item.metadata.get("memory_type") == "reflection_record"
        for item in memory_kernel.long_term_memory
    )
    assert knowledge_store.exists(record.record_id)


def test_self_improvement_tracks_performance_metrics_over_time():
    engine = SelfImprovementEngine()

    engine.track_metric("research_success_rate", 0.5)
    engine.track_metric("research_success_rate", 0.75)
    trend = engine.metric_trend("research_success_rate")

    assert trend == {
        "count": 2.0,
        "latest": 0.75,
        "average": 0.625,
        "delta": 0.25,
    }
    assert engine.metric_trend("missing") == {
        "count": 0.0,
        "latest": 0.0,
        "average": 0.0,
        "delta": 0.0,
    }


def test_self_improvement_stores_plans_and_reflection_reports():
    knowledge_store = KnowledgeStore()
    engine = SelfImprovementEngine(knowledge_store=knowledge_store)
    record = ReflectionRecord(
        subject_id="history",
        source_type="execution",
        status="COMPLETED",
        observations=("No critical bottlenecks.",),
    )

    plan = engine.generate_plan(record, target="runtime")

    assert knowledge_store.exists(plan.plan_id)
    assert engine.memory_kernel.session_memory[-1] == {
        "improvement_plan": plan.plan_id,
        "priority": "medium",
    }
    assert knowledge_store.search("Generated improvement plan", top_k=5)
