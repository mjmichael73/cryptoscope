"""Thin Kafka helpers shared by the Python services.

These wrap aiokafka with JSON envelopes and the small conveniences the services
need. Consumers commit offsets explicitly so processing stays at-least-once.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


class JsonProducer:
    """Publishes JSON encoded messages to Kafka."""

    def __init__(self, brokers: list[str], **client_options: Any) -> None:
        self._brokers = brokers
        self._client_options = client_options
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._brokers,
            enable_idempotence=True,
            acks="all",
            **self._client_options,
        )
        await self._producer.start()

    async def publish(self, topic: str, key: str, value: dict[str, Any]) -> None:
        assert self._producer is not None, "producer not started"
        await self._producer.send_and_wait(
            topic,
            key=key.encode(),
            value=json.dumps(value).encode(),
        )

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()


class JsonConsumer:
    """Consumes JSON encoded messages from a topic as part of a group."""

    def __init__(self, brokers: list[str], topic: str, group: str, **client_options: Any) -> None:
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=brokers,
            group_id=group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            **client_options,
        )

    async def start(self) -> None:
        await self._consumer.start()

    async def messages(self) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        async for message in self._consumer:
            key = message.key.decode() if message.key else ""
            value = json.loads(message.value)
            yield key, value
            await self._consumer.commit()

    async def stop(self) -> None:
        await self._consumer.stop()
