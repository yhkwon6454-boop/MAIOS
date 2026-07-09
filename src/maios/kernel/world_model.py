from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from maios.kernel.memory_kernel import MemoryKernel
from maios.knowledge.graph import KnowledgeGraph


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EnvironmentState:
    signals: dict[str, Any] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    resources: dict[str, float] = field(default_factory=dict)
    risk_level: str = "NORMAL"
    state_id: str = field(default_factory=lambda: f"ENV-{uuid4().hex[:8]}")
    updated_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.constraints = tuple(self.constraints)
        self.risk_level = self.risk_level.upper()

    def update(
        self,
        *,
        signals: dict[str, Any] | None = None,
        constraints: list[str] | tuple[str, ...] | None = None,
        resources: dict[str, float] | None = None,
        risk_level: str | None = None,
    ) -> None:
        if signals:
            self.signals.update(signals)
        if constraints is not None:
            self.constraints = tuple(constraints)
        if resources:
            self.resources.update(resources)
        if risk_level is not None:
            self.risk_level = risk_level.upper()
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["constraints"] = list(self.constraints)
        return data


@dataclass
class UserModel:
    preferences: dict[str, Any] = field(default_factory=dict)
    intent_history: list[str] = field(default_factory=list)
    trust_level: float = 0.5
    user_id: str = "default"
    updated_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.trust_level = max(0.0, min(1.0, float(self.trust_level)))

    def observe_intent(self, intent: str) -> None:
        normalized = intent.strip()
        if normalized:
            self.intent_history.append(normalized)
            self.updated_at = _now()

    def update_preferences(self, preferences: dict[str, Any]) -> None:
        self.preferences.update(preferences)
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SystemState:
    active_missions: int = 0
    healthy_nodes: int = 0
    active_agents: int = 0
    failed_agents: int = 0
    failure_rate: float = 0.0
    planner_load: dict[str, float] = field(default_factory=dict)
    state_id: str = field(default_factory=lambda: f"SYS-{uuid4().hex[:8]}")
    updated_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.active_missions = max(0, self.active_missions)
        self.healthy_nodes = max(0, self.healthy_nodes)
        self.active_agents = max(0, self.active_agents)
        self.failed_agents = max(0, self.failed_agents)
        self.failure_rate = max(0.0, min(1.0, float(self.failure_rate)))

    @classmethod
    def from_runtime(cls, runtime: Any) -> SystemState:
        nodes = list(getattr(getattr(runtime, "node_manager", None), "nodes", {}).values())
        agents = []
        registry = getattr(runtime, "agent_registry", None)
        if registry is not None:
            agents = registry.all()
        history = []
        if hasattr(runtime, "history"):
            history = list(runtime.history())
        failures = [
            item
            for item in history
            if str(getattr(item, "status", "")).upper() in {"FAILED", "BLOCKED"}
        ]
        return cls(
            active_missions=sum(
                1 for item in history if str(getattr(item, "status", "")) == "RUNNING"
            ),
            healthy_nodes=sum(1 for node in nodes if getattr(node, "healthy", False)),
            active_agents=len(
                [agent for agent in agents if getattr(agent, "active_tasks", 0) >= 0]
            ),
            failed_agents=sum(1 for agent in agents if getattr(agent, "active_tasks", 0) < 0),
            failure_rate=len(failures) / len(history) if history else 0.0,
            planner_load={
                "distributed": float(sum(getattr(node, "active_tasks", 0) for node in nodes)),
                "agents": float(sum(getattr(agent, "active_tasks", 0) for agent in agents)),
            },
        )

    def update_from_outcome(self, outcome: dict[str, Any]) -> None:
        status = str(outcome.get("status", "")).upper()
        if status in {"FAILED", "BLOCKED"}:
            self.failure_rate = min(1.0, self.failure_rate + 0.1)
        elif status in {"COMPLETED", "SUCCESS"}:
            self.failure_rate = max(0.0, self.failure_rate - 0.05)
        self.updated_at = _now()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StateTransition:
    source_state_id: str
    target_state_id: str
    event: str
    changes: dict[str, Any]
    transition_id: str = field(default_factory=lambda: f"ST-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Prediction:
    target: str
    outcome: str
    confidence: float
    rationale: str
    prediction_id: str = field(default_factory=lambda: f"PRED-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorldContext:
    objective: str
    mission_id: str
    environment: EnvironmentState
    user: UserModel
    system: SystemState
    predictions: tuple[Prediction, ...] = ()
    context_id: str = field(default_factory=lambda: f"WC-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "objective": self.objective,
            "mission_id": self.mission_id,
            "environment": self.environment.to_dict(),
            "user": self.user.to_dict(),
            "system": self.system.to_dict(),
            "predictions": [prediction.to_dict() for prediction in self.predictions],
            "created_at": self.created_at,
        }


class StateTransitionEngine:
    def apply(
        self,
        world_model: WorldModel,
        event: str,
        changes: dict[str, Any],
    ) -> StateTransition:
        source_id = world_model.state_id
        world_model.apply_changes(changes)
        world_model.state_id = f"WM-{uuid4().hex[:8]}"
        world_model.updated_at = _now()
        transition = StateTransition(
            source_state_id=source_id,
            target_state_id=world_model.state_id,
            event=event,
            changes=dict(changes),
        )
        world_model.transitions.append(transition)
        world_model.persist_transition(transition)
        world_model.persist()
        return transition


class PredictionEngine:
    def predict_runtime(self, system_state: SystemState) -> Prediction:
        if system_state.healthy_nodes <= 0 and system_state.active_agents <= 0:
            return Prediction(
                target="runtime",
                outcome="degraded",
                confidence=0.9,
                rationale="No healthy nodes or active agents are available.",
            )
        if system_state.failure_rate >= 0.5:
            return Prediction(
                target="runtime",
                outcome="risky",
                confidence=0.75,
                rationale="Recent failure rate is high.",
            )
        return Prediction(
            target="runtime",
            outcome="stable",
            confidence=0.8,
            rationale="Runtime capacity and failure rate are acceptable.",
        )

    def predict_planner(
        self,
        capabilities: list[str] | tuple[str, ...],
        system_state: SystemState,
    ) -> Prediction:
        capability_set = set(capabilities)
        if "research" in capability_set:
            return Prediction("planner", "research", 0.82, "Research capability requested.")
        if len(capability_set) > 1:
            return Prediction("planner", "meta", 0.78, "Multiple capabilities require balancing.")
        if system_state.healthy_nodes > 0:
            return Prediction("planner", "distributed", 0.72, "Distributed capacity is available.")
        if capability_set:
            return Prediction("planner", "swarm", 0.66, "Agent capability work is requested.")
        return Prediction("planner", "direct", 0.6, "No specialized capability is required.")

    def predict_agent(
        self,
        capability: str,
        system_state: SystemState,
    ) -> Prediction:
        if system_state.active_agents <= 0:
            return Prediction("agent", "unavailable", 0.85, f"No agents for {capability}.")
        if system_state.failed_agents > 0:
            return Prediction("agent", "replacement_needed", 0.7, "Some agents have failed.")
        return Prediction("agent", "available", 0.8, f"Agents can handle {capability}.")


class WorldContextBuilder:
    def __init__(self, prediction_engine: PredictionEngine | None = None) -> None:
        self.prediction_engine = prediction_engine or PredictionEngine()

    def build(self, world_model: WorldModel, decision_context: Any) -> WorldContext:
        capabilities = tuple(getattr(decision_context, "requested_capabilities", ()))
        predictions = [
            self.prediction_engine.predict_runtime(world_model.system),
            self.prediction_engine.predict_planner(capabilities, world_model.system),
        ]
        if capabilities:
            predictions.append(
                self.prediction_engine.predict_agent(capabilities[0], world_model.system)
            )
        return WorldContext(
            objective=str(getattr(decision_context, "objective", "")),
            mission_id=str(getattr(decision_context, "mission_id", world_model.state_id)),
            environment=world_model.environment,
            user=world_model.user,
            system=world_model.system,
            predictions=tuple(predictions),
        )


class WorldModel:
    """Global state representation for executive decisions and runtime control."""

    def __init__(
        self,
        environment: EnvironmentState | None = None,
        user: UserModel | None = None,
        system: SystemState | None = None,
        transition_engine: StateTransitionEngine | None = None,
        prediction_engine: PredictionEngine | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        memory_kernel: MemoryKernel | None = None,
        state_id: str | None = None,
    ) -> None:
        self.environment = environment or EnvironmentState()
        self.user = user or UserModel()
        self.system = system or SystemState()
        self.transition_engine = transition_engine or StateTransitionEngine()
        self.prediction_engine = prediction_engine or PredictionEngine()
        self.context_builder = WorldContextBuilder(self.prediction_engine)
        self.knowledge_graph = knowledge_graph
        self.memory_kernel = memory_kernel
        self.state_id = state_id or f"WM-{uuid4().hex[:8]}"
        self.updated_at = _now()
        self.transitions: list[StateTransition] = []

    @classmethod
    def from_runtime(
        cls,
        runtime: Any,
        *,
        knowledge_graph: KnowledgeGraph | None = None,
        memory_kernel: MemoryKernel | None = None,
    ) -> WorldModel:
        return cls(
            system=SystemState.from_runtime(runtime),
            knowledge_graph=knowledge_graph,
            memory_kernel=memory_kernel,
        )

    def transition(self, event: str, changes: dict[str, Any]) -> StateTransition:
        return self.transition_engine.apply(self, event, changes)

    def apply_changes(self, changes: dict[str, Any]) -> None:
        environment_changes = changes.get("environment")
        if isinstance(environment_changes, dict):
            self.environment.update(**environment_changes)
        user_changes = changes.get("user")
        if isinstance(user_changes, dict):
            preferences = user_changes.get("preferences")
            if isinstance(preferences, dict):
                self.user.update_preferences(preferences)
            intent = user_changes.get("intent")
            if isinstance(intent, str):
                self.user.observe_intent(intent)
        system_changes = changes.get("system")
        if isinstance(system_changes, dict):
            outcome = system_changes.get("outcome")
            if isinstance(outcome, dict):
                self.system.update_from_outcome(outcome)
            for key in {
                "active_missions",
                "healthy_nodes",
                "active_agents",
                "failed_agents",
                "failure_rate",
            }:
                if key in system_changes:
                    setattr(self.system, key, system_changes[key])
            self.system.__post_init__()
            self.system.updated_at = _now()

    def build_context(self, decision_context: Any) -> WorldContext:
        world_context = self.context_builder.build(self, decision_context)
        self.persist_context(world_context)
        return world_context

    def predict(self, capabilities: list[str] | tuple[str, ...] = ()) -> dict[str, Prediction]:
        return {
            "runtime": self.prediction_engine.predict_runtime(self.system),
            "planner": self.prediction_engine.predict_planner(capabilities, self.system),
            "agent": self.prediction_engine.predict_agent(
                capabilities[0] if capabilities else "general",
                self.system,
            ),
        }

    def persist(self) -> None:
        data = self.to_dict()
        if self.memory_kernel is not None:
            self.memory_kernel.remember_short_term({"world_state": data})
            self.memory_kernel.remember_long_term(
                str(data)[:8000],
                metadata={"memory_type": "world_state", "state_id": self.state_id},
            )
        if self.knowledge_graph is not None:
            self.knowledge_graph.add_node(
                title=f"World State: {self.state_id}",
                content=str(data),
                node_type="world_state",
                metadata={"state_id": self.state_id},
                node_id=self.state_id,
            )

    def persist_transition(self, transition: StateTransition) -> None:
        if self.memory_kernel is not None:
            self.memory_kernel.remember_short_term({"world_transition": transition.to_dict()})
        if self.knowledge_graph is not None:
            self.knowledge_graph.add_node(
                title=f"World Transition: {transition.event}",
                content=str(transition.to_dict()),
                node_type="world_transition",
                metadata={
                    "transition_id": transition.transition_id,
                    "source_state_id": transition.source_state_id,
                    "target_state_id": transition.target_state_id,
                },
                node_id=transition.transition_id,
            )

    def persist_context(self, context: WorldContext) -> None:
        if self.memory_kernel is not None:
            self.memory_kernel.remember_short_term({"world_context": context.to_dict()})
        if self.knowledge_graph is not None:
            self.knowledge_graph.add_node(
                title=f"World Context: {context.objective}",
                content=str(context.to_dict()),
                node_type="world_context",
                metadata={
                    "context_id": context.context_id,
                    "mission_id": context.mission_id,
                },
                node_id=context.context_id,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "updated_at": self.updated_at,
            "environment": self.environment.to_dict(),
            "user": self.user.to_dict(),
            "system": self.system.to_dict(),
            "transitions": [transition.to_dict() for transition in self.transitions],
        }
