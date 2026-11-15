from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Self

import pytest


class FakeSession:
    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        self._rules = rules or []
        self._added: list[Any] = []

    async def execute(self, query: Any) -> Any:
        return FakeResult(self._rules)

    async def commit(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def add(self, obj: Any) -> None:
        self._added.append(obj)


class FakeResult:
    def __init__(self, rules: list[dict[str, Any]]) -> None:
        self._rules = rules

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rules

    def scalar_one_or_none(self) -> dict[str, Any] | None:
        return self._rules[0] if self._rules else None


class FakeConsumer:
    def __init__(self, messages: list[tuple[str, dict[str, Any]]]) -> None:
        self._messages = messages
        self._started = False

    async def start(self) -> None:
        self._started = True

    async def messages(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        for msg in self._messages:
            yield msg

    async def stop(self) -> None:
        self._started = False


class FakeProducer:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, dict[str, Any]]] = []

    async def start(self) -> None:
        pass

    async def publish(self, topic: str, key: str, value: dict[str, Any]) -> None:
        self.published.append((topic, key, value))

    async def stop(self) -> None:
        pass


@pytest.fixture
def fake_producer() -> FakeProducer:
    return FakeProducer()
