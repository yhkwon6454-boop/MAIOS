from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from maios.adapters.gpt_adapter import GPTAdapter
from maios.agents.executor_agent import ExecutorAgent
from maios.agents.memory_agent import MemoryAgent
from maios.agents.planner_agent import PlannerAgent
from maios.kernel.quality_kernel import QualityKernel
from maios.planning import GoalManager
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


class RuntimeOrchestrator:
    """Coordinates Planner -> Memory -> GPTAdapter -> Executor -> Quality."""

    def __init__(
        self,
        planner_agent: PlannerAgent | None = None,
        memory_agent: MemoryAgent | None = None,
        gpt_adapter: GPTAdapter | None = None,
        executor_agent: ExecutorAgent | None = None,
        quality_kernel: QualityKernel | None = None,
        goal_manager: GoalManager | None = None,
    ) -> None:
        self.planner_agent = planner_agent or PlannerAgent()
        self.memory_agent = memory_agent or MemoryAgent()
        self.gpt_adapter = gpt_adapter or GPTAdapter()
        self.executor_agent = executor_agent or ExecutorAgent()
        self.quality_kernel = quality_kernel or QualityKernel()
        self.goal_manager = goal_manager or GoalManager()

    def run(self, mission: Mission) -> MultiAgentRuntimeResult:
        mission.status = Status.RUNNING
        context: dict[str, Any] = {"mission": mission, "trace": []}

        context = self._execute_agent(self.planner_agent, context)
        context = self._execute_agent(self.memory_agent, context)

        if (
            getattr(self.gpt_adapter, "memory_kernel", None) is None
            and hasattr(self.memory_agent, "memory_kernel")
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

        qa_result = self.quality_kernel.evaluate([model_output])
        mission.status = qa_result.status
        final_output = self._compose_output(context, qa_result)
        context = {
            **context,
            "qa_result": qa_result,
            "final_output": final_output,
            "trace": [*context["trace"], "quality"],
        }

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
        )

    def _execute_task_queue(self, context: dict[str, Any]) -> list[str]:
        goal = context["goal"]
        outputs: list[str] = []

        while True:
            task = self.goal_manager.next_task(goal)
            if task is None:
                break

            prompt = self._build_task_prompt(context, task)
            output = self.gpt_adapter.generate(
                prompt,
                memory_context=context.get("memory_context", {}),
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
        next_context = agent.execute(context)
        return {
            **next_context,
            "trace": [*next_context.get("trace", []), agent.name],
        }

    def _build_prompt(self, context: dict[str, Any]) -> str:
        mission = context["mission"]
        plan = context["execution_plan"]
        memory = "\n".join(
            f"- {key}: {value}"
            for key, value in context.get("memory_context", {}).items()
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
