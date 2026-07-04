from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from typing import Any, Protocol

from maios.runtime.models import CognitivePacket
from maios.tools import ToolRegistry, ToolResult


class ModelAdapter(Protocol):
    def execute(
        self,
        packet: CognitivePacket,
        memory_context: dict[str, str],
    ) -> str:
        ...


@dataclass
class ReasoningStep:
    phase: str
    content: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    observation: ToolResult | None = None


@dataclass
class ReasoningResult:
    final_answer: str
    steps: list[ReasoningStep] = field(default_factory=list)
    iterations: int = 0
    completed: bool = True


class ReasoningEngine:
    """
    Iterative Plan -> Tool -> Observation -> Reasoning -> Final Answer engine.

    The engine is model-agnostic: any adapter that accepts a CognitivePacket and
    returns text can drive tool selection.
    """

    def __init__(
        self,
        model_adapter: ModelAdapter,
        tool_registry: ToolRegistry,
        max_iterations: int = 5,
    ) -> None:
        self.model_adapter = model_adapter
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations

    def execute(
        self,
        packet: CognitivePacket,
        memory_context: dict[str, str] | None = None,
    ) -> ReasoningResult:
        memory_context = memory_context or {}
        steps: list[ReasoningStep] = []
        transcript: list[str] = []

        for iteration in range(1, self.max_iterations + 1):
            reasoning_packet = self._build_reasoning_packet(packet, transcript)
            response = self.model_adapter.execute(reasoning_packet, memory_context)
            command = self._parse_response(response)

            if command["type"] == "final":
                steps.append(
                    ReasoningStep(phase="final_answer", content=command["final_answer"])
                )
                return ReasoningResult(
                    final_answer=command["final_answer"],
                    steps=steps,
                    iterations=iteration,
                    completed=True,
                )

            steps.append(ReasoningStep(phase="reasoning", content=command["reasoning"]))
            steps.append(ReasoningStep(phase="tool", tool_name=command["tool"], tool_input=command["input"]))

            observation = self.tool_registry.execute(command["tool"], command["input"])
            steps.append(ReasoningStep(phase="observation", observation=observation))

            transcript.extend(
                [
                    f"Reasoning: {command['reasoning']}",
                    f"Tool: {command['tool']}",
                    f"Tool Input: {json.dumps(command['input'], ensure_ascii=False)}",
                    f"Observation: {self._format_observation(observation)}",
                ]
            )

        final_answer = "Reasoning stopped before a final answer was produced."
        steps.append(ReasoningStep(phase="final_answer", content=final_answer))
        return ReasoningResult(
            final_answer=final_answer,
            steps=steps,
            iterations=self.max_iterations,
            completed=False,
        )

    def _build_reasoning_packet(
        self,
        packet: CognitivePacket,
        transcript: list[str],
    ) -> CognitivePacket:
        instruction = "\n\n".join(
            [
                self._system_instruction(),
                "Original instruction:",
                packet.instruction,
                "Previous reasoning trace:",
                "\n".join(transcript) if transcript else "None",
            ]
        )

        return replace(packet, instruction=instruction)

    def _system_instruction(self) -> str:
        tools = ", ".join(self.tool_registry.names()) or "none"
        return "\n".join(
            [
                "Use iterative reasoning: Plan -> Tool -> Observation -> Reasoning -> Final Answer.",
                f"Available tools: {tools}",
                "When a tool is needed, respond only with JSON:",
                '{"type": "tool", "reasoning": "...", "tool": "tool_name", "input": {...}}',
                "When ready to answer, respond only with JSON:",
                '{"type": "final", "final_answer": "..."}',
            ]
        )

    def _parse_response(self, response: str) -> dict[str, Any]:
        data = self._load_json(response)

        if not data:
            return {
                "type": "final",
                "final_answer": response.strip(),
            }

        if self._is_final(data):
            return {
                "type": "final",
                "final_answer": str(data.get("final_answer") or data.get("answer")),
            }

        tool_name = data.get("tool") or data.get("tool_name")
        if tool_name:
            tool_input = data.get("input") or data.get("tool_input") or {}
            if not isinstance(tool_input, dict):
                tool_input = {"value": tool_input}

            return {
                "type": "tool",
                "reasoning": str(data.get("reasoning") or data.get("plan") or ""),
                "tool": str(tool_name),
                "input": tool_input,
            }

        return {
            "type": "final",
            "final_answer": response.strip(),
        }

    def _load_json(self, response: str) -> dict[str, Any] | None:
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        if isinstance(data, dict):
            return data

        return None

    def _is_final(self, data: dict[str, Any]) -> bool:
        return data.get("type") == "final" or "final_answer" in data or "answer" in data

    def _format_observation(self, observation: ToolResult) -> str:
        if observation.success:
            return observation.output

        return observation.error
