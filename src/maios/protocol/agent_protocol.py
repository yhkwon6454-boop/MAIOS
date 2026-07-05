from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from maios.events.bus import Message


class MessageType(StrEnum):
    PLAN_REQUEST = "PLAN_REQUEST"
    PLAN_RESULT = "PLAN_RESULT"
    MEMORY_QUERY = "MEMORY_QUERY"
    MEMORY_RESULT = "MEMORY_RESULT"
    LLM_REQUEST = "LLM_REQUEST"
    LLM_RESULT = "LLM_RESULT"
    EXECUTION_REQUEST = "EXECUTION_REQUEST"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    QUALITY_CHECK = "QUALITY_CHECK"
    QUALITY_RESULT = "QUALITY_RESULT"
    REFLECTION_REQUEST = "REFLECTION_REQUEST"
    REFLECTION_RESULT = "REFLECTION_RESULT"


class AgentProtocolError(ValueError):
    """Raised when a message violates the agent protocol."""


@dataclass(frozen=True)
class RouteRule:
    message_type: MessageType
    allowed_sources: set[str] = field(default_factory=set)
    allowed_targets: set[str] = field(default_factory=set)


class AgentProtocol:
    """Validates and routes standard MAIOS agent protocol messages."""

    def __init__(self, routes: list[RouteRule] | None = None) -> None:
        self.routes = {rule.message_type: rule for rule in (routes or self.default_routes())}

    @classmethod
    def default_routes(cls) -> list[RouteRule]:
        return [
            RouteRule(MessageType.PLAN_REQUEST, {"runtime"}, {"planner"}),
            RouteRule(MessageType.PLAN_RESULT, {"planner"}, {"runtime"}),
            RouteRule(MessageType.MEMORY_QUERY, {"runtime", "planner"}, {"memory"}),
            RouteRule(MessageType.MEMORY_RESULT, {"memory"}, {"runtime", "planner"}),
            RouteRule(MessageType.LLM_REQUEST, {"runtime", "planner"}, {"gpt_adapter"}),
            RouteRule(MessageType.LLM_RESULT, {"gpt_adapter"}, {"runtime"}),
            RouteRule(MessageType.EXECUTION_REQUEST, {"runtime"}, {"executor"}),
            RouteRule(MessageType.EXECUTION_RESULT, {"executor"}, {"runtime"}),
            RouteRule(MessageType.QUALITY_CHECK, {"runtime", "executor"}, {"quality"}),
            RouteRule(MessageType.QUALITY_RESULT, {"quality"}, {"runtime"}),
            RouteRule(MessageType.REFLECTION_REQUEST, {"runtime", "quality"}, {"reflection"}),
            RouteRule(MessageType.REFLECTION_RESULT, {"reflection"}, {"runtime"}),
        ]

    def create_message(
        self,
        message_type: MessageType | str,
        payload: dict[str, Any] | None = None,
        source: str = "",
        target: str = "",
    ) -> Message:
        normalized = self.normalize_type(message_type)
        message = Message(
            event_type=normalized.value,
            payload={
                **(payload or {}),
                "message_type": normalized.value,
                "target": target,
            },
            source=source,
        )
        self.validate(message)
        return message

    def validate(self, message: Message) -> bool:
        message_type = self.message_type(message)
        route = self.routes.get(message_type)
        if route is None:
            raise AgentProtocolError(f"No route configured for message type: {message_type.value}")

        target = self.target(message)
        if route.allowed_sources and message.source not in route.allowed_sources:
            raise AgentProtocolError(
                f"Source '{message.source}' is not allowed for {message_type.value}."
            )

        if route.allowed_targets and target not in route.allowed_targets:
            raise AgentProtocolError(f"Target '{target}' is not allowed for {message_type.value}.")

        return True

    def route_event_type(self, message: Message) -> str:
        self.validate(message)
        return f"agent.{self.message_type(message).value}"

    def route_target(self, message: Message) -> str:
        self.validate(message)
        return self.target(message)

    def message_type(self, message: Message) -> MessageType:
        raw_type = message.payload.get("message_type", message.event_type)
        return self.normalize_type(str(raw_type))

    def normalize_type(self, message_type: MessageType | str) -> MessageType:
        if isinstance(message_type, MessageType):
            return message_type

        try:
            return MessageType(message_type)
        except ValueError as exc:
            raise AgentProtocolError(f"Unknown message type: {message_type}") from exc

    def target(self, message: Message) -> str:
        target = message.payload.get("target", "")
        if not isinstance(target, str) or not target:
            raise AgentProtocolError("Protocol message target is required.")
        return target
