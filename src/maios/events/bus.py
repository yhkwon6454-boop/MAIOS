from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Message:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    message_id: str = field(default_factory=lambda: f"MSG-{uuid4().hex[:8]}")
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class Subscription:
    event_type: str
    handler: Callable[[Message], Any]
    subscription_id: str = field(default_factory=lambda: f"SUB-{uuid4().hex[:8]}")


class EventBus:
    """In-process event bus for synchronous and asynchronous agent messaging."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Subscription]] = {}
        self.history: list[Message] = []

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Message], Any],
    ) -> Subscription:
        if not event_type:
            raise ValueError("event_type is required.")

        subscription = Subscription(event_type=event_type, handler=handler)
        self._subscriptions.setdefault(event_type, []).append(subscription)
        return subscription

    def unsubscribe(
        self,
        subscription: Subscription | None = None,
        event_type: str | None = None,
        handler: Callable[[Message], Any] | None = None,
    ) -> bool:
        if subscription is not None:
            return self._unsubscribe_subscription(subscription)

        if event_type is None:
            return False

        subscriptions = self._subscriptions.get(event_type, [])
        if handler is None:
            removed = bool(subscriptions)
            self._subscriptions.pop(event_type, None)
            return removed

        remaining = [item for item in subscriptions if item.handler is not handler]
        removed = len(remaining) != len(subscriptions)
        if remaining:
            self._subscriptions[event_type] = remaining
        else:
            self._subscriptions.pop(event_type, None)
        return removed

    def publish(
        self,
        event: Message | str,
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> list[Any]:
        message = self._message(event, payload=payload, source=source)
        self.history.append(message)

        results = []
        for subscription in self._handlers_for(message.event_type):
            results.append(subscription.handler(message))
        return results

    async def publish_async(
        self,
        event: Message | str,
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> list[Any]:
        message = self._message(event, payload=payload, source=source)
        self.history.append(message)

        results = []
        for subscription in self._handlers_for(message.event_type):
            result = subscription.handler(message)
            if inspect.isawaitable(result):
                result = await result
            results.append(result)
        return results

    def clear(self) -> None:
        self._subscriptions.clear()
        self.history.clear()

    def subscribers(self, event_type: str) -> list[Subscription]:
        return list(self._subscriptions.get(event_type, []))

    def _message(
        self,
        event: Message | str,
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> Message:
        if isinstance(event, Message):
            return event

        return Message(
            event_type=event,
            payload=payload or {},
            source=source,
        )

    def _handlers_for(self, event_type: str) -> list[Subscription]:
        return [
            *self._subscriptions.get(event_type, []),
            *self._subscriptions.get("*", []),
        ]

    def _unsubscribe_subscription(self, subscription: Subscription) -> bool:
        subscriptions = self._subscriptions.get(subscription.event_type, [])
        remaining = [
            item for item in subscriptions if item.subscription_id != subscription.subscription_id
        ]
        removed = len(remaining) != len(subscriptions)
        if remaining:
            self._subscriptions[subscription.event_type] = remaining
        else:
            self._subscriptions.pop(subscription.event_type, None)
        return removed
