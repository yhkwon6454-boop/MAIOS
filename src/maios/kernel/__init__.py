from __future__ import annotations

from typing import Any

__all__ = [
    "AGIFoundation",
    "GoalPursuit",
    "SelfModel",
    "TaskExecutor",
    "Workspace",
    "CognitiveCycleResult",
    "CognitiveInterpreter",
    "CognitiveLoop",
    "CognitivePhase",
    "PhaseRecord",
    "DecisionContext",
    "ExecutiveBrain",
    "ExecutiveDecision",
    "ExecutiveKernel",
    "ExecutivePriorityEngine",
    "EnvironmentState",
    "Prediction",
    "PredictionEngine",
    "StateTransition",
    "StateTransitionEngine",
    "SystemState",
    "UserModel",
    "WorldContext",
    "WorldContextBuilder",
    "WorldModel",
]


def __getattr__(name: str) -> Any:
    if name in {"AGIFoundation", "GoalPursuit", "SelfModel"}:
        from maios.kernel.agi_foundation import AGIFoundation, GoalPursuit, SelfModel

        return {
            "AGIFoundation": AGIFoundation,
            "GoalPursuit": GoalPursuit,
            "SelfModel": SelfModel,
        }[name]
    if name == "Workspace":
        from maios.kernel.workspace import Workspace

        return Workspace
    if name == "TaskExecutor":
        from maios.kernel.task_executor import TaskExecutor

        return TaskExecutor
    if name == "CognitiveInterpreter":
        from maios.kernel.cognitive_interpreter import CognitiveInterpreter

        return CognitiveInterpreter
    if name in {
        "CognitiveCycleResult",
        "CognitiveLoop",
        "CognitivePhase",
        "PhaseRecord",
    }:
        from maios.kernel.cognitive_loop import (
            CognitiveCycleResult,
            CognitiveLoop,
            CognitivePhase,
            PhaseRecord,
        )

        return {
            "CognitiveCycleResult": CognitiveCycleResult,
            "CognitiveLoop": CognitiveLoop,
            "CognitivePhase": CognitivePhase,
            "PhaseRecord": PhaseRecord,
        }[name]
    if name == "ExecutiveKernel":
        from maios.kernel.executive_kernel import ExecutiveKernel

        return ExecutiveKernel
    if name in {
        "DecisionContext",
        "ExecutiveBrain",
        "ExecutiveDecision",
        "ExecutivePriorityEngine",
    }:
        from maios.kernel.executive_brain import (
            DecisionContext,
            ExecutiveBrain,
            ExecutiveDecision,
            ExecutivePriorityEngine,
        )

        return {
            "DecisionContext": DecisionContext,
            "ExecutiveBrain": ExecutiveBrain,
            "ExecutiveDecision": ExecutiveDecision,
            "ExecutivePriorityEngine": ExecutivePriorityEngine,
        }[name]
    if name in {
        "EnvironmentState",
        "Prediction",
        "PredictionEngine",
        "StateTransition",
        "StateTransitionEngine",
        "SystemState",
        "UserModel",
        "WorldContext",
        "WorldContextBuilder",
        "WorldModel",
    }:
        from maios.kernel.world_model import (
            EnvironmentState,
            Prediction,
            PredictionEngine,
            StateTransition,
            StateTransitionEngine,
            SystemState,
            UserModel,
            WorldContext,
            WorldContextBuilder,
            WorldModel,
        )

        return {
            "EnvironmentState": EnvironmentState,
            "Prediction": Prediction,
            "PredictionEngine": PredictionEngine,
            "StateTransition": StateTransition,
            "StateTransitionEngine": StateTransitionEngine,
            "SystemState": SystemState,
            "UserModel": UserModel,
            "WorldContext": WorldContext,
            "WorldContextBuilder": WorldContextBuilder,
            "WorldModel": WorldModel,
        }[name]
    raise AttributeError(f"module 'maios.kernel' has no attribute {name!r}")
