"""Kafka backed domain event publisher.

Wraps the shared JSON producer so the application service depends only on the
small EventPublisher protocol. The event name is used as the partition key so
events of one kind for one tenant stay ordered.
"""

from __future__ import annotations

from cryptoscope_shared.kafka import JsonProducer

from app.domain import events


class KafkaEventPublisher:
    def __init__(self, producer: JsonProducer, topic: str) -> None:
        self._producer = producer
        self._topic = topic

    async def publish(self, event: events.DomainEvent) -> None:
        key = f"{event.tenant_id}:{event.event_type}"
        await self._producer.publish(self._topic, key, event.to_message())
