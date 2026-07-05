from __future__ import annotations

import asyncio

from maios.events import EventBus, Message
from maios.protocol import AgentProtocol, AgentProtocolError, MessageType, RouteRule


def test_agent_protocol_defines_standard_message_types():
    assert [item.value for item in MessageType] == [
        "PLAN_REQUEST",
        "PLAN_RESULT",
        "MEMORY_QUERY",
        "MEMORY_RESULT",
        "LLM_REQUEST",
        "LLM_RESULT",
        "EXECUTION_REQUEST",
        "EXECUTION_RESULT",
        "QUALITY_CHECK",
        "QUALITY_RESULT",
        "REFLECTION_REQUEST",
        "REFLECTION_RESULT",
    ]


def test_agent_protocol_creates_and_validates_messages():
    protocol = AgentProtocol()

    message = protocol.create_message(
        MessageType.PLAN_REQUEST,
        payload={"objective": "build plan"},
        source="runtime",
        target="planner",
    )

    assert message.event_type == "PLAN_REQUEST"
    assert message.payload["message_type"] == "PLAN_REQUEST"
    assert message.payload["target"] == "planner"
    assert protocol.validate(message)
    assert protocol.route_event_type(message) == "agent.PLAN_REQUEST"
    assert protocol.route_target(message) == "planner"


def test_agent_protocol_rejects_unknown_message_type():
    protocol = AgentProtocol()

    try:
        protocol.validate(Message(event_type="UNKNOWN", source="runtime", payload={"target": "x"}))
    except AgentProtocolError as exc:
        assert "Unknown message type" in str(exc)
    else:
        raise AssertionError("Expected unknown message type to fail.")


def test_agent_protocol_requires_valid_source_target_and_target_value():
    protocol = AgentProtocol()

    invalid_source = Message(
        event_type="PLAN_REQUEST",
        source="memory",
        payload={"target": "planner", "message_type": "PLAN_REQUEST"},
    )
    invalid_target = Message(
        event_type="PLAN_REQUEST",
        source="runtime",
        payload={"target": "memory", "message_type": "PLAN_REQUEST"},
    )
    missing_target = Message(
        event_type="PLAN_REQUEST",
        source="runtime",
        payload={"message_type": "PLAN_REQUEST"},
    )

    for message, expected in [
        (invalid_source, "Source 'memory' is not allowed"),
        (invalid_target, "Target 'memory' is not allowed"),
        (missing_target, "target is required"),
    ]:
        try:
            protocol.validate(message)
        except AgentProtocolError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("Expected invalid protocol message to fail.")


def test_agent_protocol_supports_custom_route_rules():
    protocol = AgentProtocol(
        routes=[
            RouteRule(
                MessageType.MEMORY_QUERY,
                allowed_sources={"planner"},
                allowed_targets={"memory"},
            )
        ]
    )

    message = protocol.create_message(
        "MEMORY_QUERY",
        payload={"query": "context"},
        source="planner",
        target="memory",
    )

    assert protocol.route_event_type(message) == "agent.MEMORY_QUERY"


def test_event_bus_routes_protocol_messages_to_agent_event_type():
    protocol = AgentProtocol()
    bus = EventBus(protocol=protocol)
    received = []
    wildcard = []
    bus.subscribe("agent.PLAN_REQUEST", received.append)
    bus.subscribe("*", wildcard.append)
    message = protocol.create_message(
        MessageType.PLAN_REQUEST,
        payload={"objective": "route"},
        source="runtime",
        target="planner",
    )

    result = bus.publish(message)

    assert result == [None, None]
    assert received == [message]
    assert wildcard == [message]
    assert bus.history == [message]


def test_event_bus_protocol_publish_rejects_invalid_route():
    bus = EventBus(protocol=AgentProtocol())

    try:
        bus.publish("PLAN_REQUEST", payload={"target": "memory"}, source="runtime")
    except AgentProtocolError as exc:
        assert "Target 'memory' is not allowed" in str(exc)
    else:
        raise AssertionError("Expected invalid route to fail.")


def test_event_bus_async_protocol_dispatch():
    bus = EventBus(protocol=AgentProtocol())
    received = []

    async def handler(message):
        received.append(message.payload["query"])
        return "ok"

    bus.subscribe("agent.MEMORY_QUERY", handler)

    results = asyncio.run(
        bus.publish_async(
            "MEMORY_QUERY",
            payload={"query": "mission", "target": "memory"},
            source="planner",
        )
    )

    assert results == ["ok"]
    assert received == ["mission"]
