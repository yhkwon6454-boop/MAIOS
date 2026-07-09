from __future__ import annotations

from typing import Any

__all__ = [
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
