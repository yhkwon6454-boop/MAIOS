from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents.executor_agent import ExecutorAgent
from maios.agents.memory_agent import MemoryAgent
from maios.agents.planner_agent import PlannerAgent
from maios.agents.quality_agent import QualityAgent
from maios.events import EventBus
from maios.kernel.quality_kernel import QualityKernel
from maios.knowledge.store import KnowledgeStore
from maios.planning import GoalManager
from maios.reflection import ImprovementReport, ReflectionEngine
from maios.runtime.models import Mission, QAResult, Status
from maios.runtime.plan import Plan


@dataclass
class MultiAgentRuntimeResult:
    mission: Mission
    plan: Plan
    memory_context: dict[str, str]
    model_output: str
    execution_result: dict[str, Any]
    qa_result: QAResult
    final_output: str
    context: dict[str, Any]
    task_outputs: list[str] | None = None
    reflection_report: ImprovementReport | None = None


class RuntimeOrchestrator:
    """Coordinates Planner -> Memory -> GPTAdapter -> Executor -> Quality."""

    def __init__(
        self,
        planner_agent: PlannerAgent | None = None,
        memory_agent: MemoryAgent | None = None,
        gpt_adapter: GPTAdapter | None = None,
        executor_agent: ExecutorAgent | None = None,
        quality_agent: QualityAgent | None = None,
        quality_kernel: QualityKernel | None = None,
        goal_manager: GoalManager | None = None,
        reflection_engine: ReflectionEngine | None = None,
        knowledge_store: KnowledgeStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.knowledge_store = knowledge_store or KnowledgeStore()
        self.planner_agent = planner_agent or PlannerAgent()
        self.memory_agent = memory_agent or MemoryAgent()
        self.gpt_adapter = gpt_adapter or GPTAdapter()
        self.executor_agent = executor_agent or ExecutorAgent()
        self.quality_kernel = quality_kernel or QualityKernel()
        self.quality_agent = quality_agent or QualityAgent(self.quality_kernel)
        self.goal_manager = goal_manager or GoalManager()
        self.reflection_engine = reflection_engine or ReflectionEngine(self.knowledge_store)
        self.event_bus = event_bus or EventBus()
        self._connect_memory_store()

    def run(self, mission: Mission) -> MultiAgentRuntimeResult:
        mission.status = Status.RUNNING
        context: dict[str, Any] = {"mission": mission, "trace": []}
        self._publish(
            "mission.started",
            "runtime",
            {"mission_id": mission.mission_id, "objective": mission.objective},
        )

        context = self._execute_agent(self.planner_agent, context)
        context = self._execute_agent(self.memory_agent, context)

        if getattr(self.gpt_adapter, "memory_kernel", None) is None and hasattr(
            self.memory_agent, "memory_kernel"
        ):
            self.gpt_adapter.memory_kernel = self.memory_agent.memory_kernel

        goal = self.goal_manager.create_goal(context["execution_plan"].objective)
        context = {**context, "goal": goal, "task_queue": goal.tasks}

        task_outputs = self._execute_task_queue(context)
        model_output = task_outputs[-1] if task_outputs else ""
        if hasattr(self.memory_agent, "memory_kernel"):
            self.memory_agent.memory_kernel.remember_conversation("assistant", model_output)
        context = {
            **context,
            "prompt": self._build_prompt(context),
            "model_output": model_output,
            "task_outputs": task_outputs,
            "trace": [*context["trace"], "gpt_adapter"],
        }

        context = self._execute_agent(self.executor_agent, context)

        context = self._execute_agent(self.quality_agent, context)
        qa_result = context["qa_result"]
        mission.status = qa_result.status
        reflection_report = self.reflection_engine.analyze(
            mission=mission,
            qa_result=qa_result,
            execution_result=context.get("execution_result", {}),
            task_outputs=task_outputs,
            goal=context.get("goal"),
        )
        final_output = self._compose_output(context, qa_result)
        context = {
            **context,
            "qa_result": qa_result,
            "reflection_report": reflection_report,
            "final_output": final_output,
        }
        self._publish(
            "mission.completed",
            "runtime",
            {
                "mission_id": mission.mission_id,
                "status": mission.status.value,
                "qa_score": qa_result.score,
            },
        )

        return MultiAgentRuntimeResult(
            mission=mission,
            plan=context["execution_plan"],
            memory_context=context["memory_context"],
            model_output=model_output,
            execution_result=context["execution_result"],
            qa_result=qa_result,
            final_output=final_output,
            context=context,
            task_outputs=task_outputs,
            reflection_report=reflection_report,
        )

    def _connect_memory_store(self) -> None:
        if hasattr(self.memory_agent, "memory_kernel"):
            self.memory_agent.memory_kernel.knowledge_store = self.knowledge_store

    def _execute_task_queue(self, context: dict[str, Any]) -> list[str]:
        goal = context["goal"]
        outputs: list[str] = []

        while True:
            task = self.goal_manager.next_task(goal)
            if task is None:
                break

            prompt = self._build_task_prompt(context, task)
            self._publish(
                "gpt.started",
                "gpt_adapter",
                {"task_id": task.task_id, "task": task.description},
            )
            output = self.gpt_adapter.generate(
                prompt,
                memory_context=context.get("memory_context", {}),
            )
            self._publish(
                "gpt.completed",
                "gpt_adapter",
                {
                    "task_id": task.task_id,
                    "task": task.description,
                    "output": output,
                },
            )
            outputs.append(output)
            feedback = "done" if output and output.strip() else "retry"
            self.goal_manager.complete_task(goal, task, feedback=feedback)

        return outputs

    def _build_task_prompt(self, context: dict[str, Any], task) -> str:
        return "\n".join(
            [
                self._build_prompt(context),
                "",
                f"Current task: {task.description}",
                f"Task priority: {task.priority}",
            ]
        )

    def _execute_agent(self, agent, context: dict[str, Any]) -> dict[str, Any]:
        self._publish(
            f"{agent.name}.started",
            agent.name,
            self._event_payload(context),
        )
        next_context = agent.execute(context)
        next_context = {
            **next_context,
            "trace": [*next_context.get("trace", []), agent.name],
        }
        self._publish(
            f"{agent.name}.completed",
            agent.name,
            self._event_payload(next_context),
        )
        return next_context

    def _build_prompt(self, context: dict[str, Any]) -> str:
        mission = context["mission"]
        plan = context["execution_plan"]
        memory = "\n".join(
            f"- {key}: {value}" for key, value in context.get("memory_context", {}).items()
        )

        return "\n".join(
            [
                f"Mission: {mission.title}",
                f"Objective: {plan.objective}",
                f"Tasks: {', '.join(plan.tasks)}",
                f"Risk: {plan.risk}",
                f"Priority: {plan.priority}",
                "Memory:",
                memory or "None",
                f"Output: {plan.output}",
            ]
        )

    def _compose_output(self, context: dict[str, Any], qa_result: QAResult) -> str:
        mission = context["mission"]
        return "\n".join(
            [
                f"# Multi-Agent Runtime Output: {mission.title}",
                "",
                "## Model Output",
                context["model_output"],
                "",
                "## QA Result",
                f"- Status: {qa_result.status.value}",
                f"- Score: {qa_result.score}",
            ]
        )

    def _publish(self, event_type: str, source: str, payload: dict[str, Any]) -> None:
        self.event_bus.publish(event_type, payload=payload, source=source)

    def _event_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        mission = context.get("mission")
        payload: dict[str, Any] = {
            "trace": list(context.get("trace", [])),
        }
        if isinstance(mission, Mission):
            payload.update(
                {
                    "mission_id": mission.mission_id,
                    "objective": mission.objective,
                    "status": mission.status.value,
                }
            )
        if "execution_plan" in context:
            payload["plan"] = context["execution_plan"].summary()
        if "memory_context" in context:
            payload["memory_context"] = dict(context["memory_context"])
        if "model_output" in context:
            payload["model_output"] = context["model_output"]
        if "execution_result" in context:
            payload["execution_result"] = context["execution_result"]
        if "qa_result" in context:
            payload["qa_result"] = {
                "status": context["qa_result"].status.value,
                "score": context["qa_result"].score,
                "issues": list(context["qa_result"].issues),
            }
        return payload
