from __future__ import annotations

import asyncio

from maios.events import EventBus, Message


def test_event_bus_publish_subscribe_and_history():
    bus = EventBus()
    received = []

    subscription = bus.subscribe("mission.started", received.append)
    result = bus.publish(
        "mission.started",
        payload={"mission_id": "M-1"},
        source="runtime",
    )

    assert result == [None]
    assert len(received) == 1
    assert received[0].event_type == "mission.started"
    assert received[0].payload == {"mission_id": "M-1"}
    assert received[0].source == "runtime"
    assert bus.history == received
    assert bus.subscribers("mission.started") == [subscription]


def test_event_bus_unsubscribe_by_subscription_handler_and_event_type():
    bus = EventBus()
    received = []

    first = bus.subscribe("event", received.append)
    bus.subscribe("event", received.append)

    assert bus.unsubscribe(first)
    bus.publish("event")
    assert len(received) == 1

    assert bus.unsubscribe(event_type="event", handler=received.append) is False
    assert bus.unsubscribe(event_type="event")
    assert bus.publish("event") == []


def test_event_bus_supports_message_instances_and_wildcard_subscribers():
    bus = EventBus()
    received = []
    bus.subscribe("*", received.append)
    message = Message(event_type="custom", payload={"value": 1}, source="test")

    bus.publish(message)

    assert received == [message]
    assert bus.history == [message]


def test_event_bus_rejects_empty_event_type_and_clear():
    bus = EventBus()

    try:
        bus.subscribe("", lambda message: message)
    except ValueError as exc:
        assert str(exc) == "event_type is required."
    else:
        raise AssertionError("Expected empty event type to fail.")

    bus.subscribe("event", lambda message: message)
    bus.publish("event")
    bus.clear()

    assert bus.history == []
    assert bus.subscribers("event") == []


def test_event_bus_async_publish_supports_sync_and_async_handlers():
    bus = EventBus()
    received = []

    def sync_handler(message):
        received.append(("sync", message.event_type))
        return "sync-result"

    async def async_handler(message):
        await asyncio.sleep(0)
        received.append(("async", message.event_type))
        return "async-result"

    bus.subscribe("event", sync_handler)
    bus.subscribe("event", async_handler)

    results = asyncio.run(bus.publish_async("event", source="test"))

    assert results == ["sync-result", "async-result"]
    assert received == [("sync", "event"), ("async", "event")]
    assert bus.history[-1].source == "test"
