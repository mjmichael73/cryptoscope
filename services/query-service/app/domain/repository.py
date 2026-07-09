"""Read repository port.

The query use cases depend on this interface, so they can be tested against an
in-memory fake without a running ClickHouse.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.models import Candle


class ReadRepository(Protocol):
    async def candles(
        self, tenant_id: str, symbol: str, interval: str, from_ms: int, to_ms: int
    ) -> list[Candle]: ...

    async def symbols(self, tenant_id: str) -> list[str]: ...
