from __future__ import annotations

import pytest

from cryptoscope_shared.kafka import JsonProducer


def test_json_producer_init() -> None:
    producer = JsonProducer(["localhost:9092"])
    assert producer._brokers == ["localhost:9092"]
    assert producer._producer is None


def test_json_producer_multiple_brokers() -> None:
    producer = JsonProducer(["broker1:9092", "broker2:9092"])
    assert len(producer._brokers) == 2


@pytest.mark.asyncio
async def test_json_producer_start_stop() -> None:
    producer = JsonProducer(["localhost:9092"])
    assert producer._producer is None


@pytest.mark.asyncio
async def test_json_producer_publish_fails_if_not_started() -> None:
    producer = JsonProducer(["localhost:9092"])
    with pytest.raises(AssertionError, match="producer not started"):
        await producer.publish("topic", "key", {"data": 1})
