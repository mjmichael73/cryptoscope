"""ClickHouse backed read repository.

Queries are always scoped by tenant_id and lead with the columns the candles
table is ordered by, so ClickHouse can prune partitions and read a tight range.
clickhouse-connect is synchronous, so the calls run in a thread to avoid
blocking the event loop.
"""

from __future__ import annotations

import asyncio

from clickhouse_connect.driver.client import Client

from app.domain.models import Candle


class ClickHouseReadRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    async def candles(
        self, tenant_id: str, symbol: str, interval: str, from_ms: int, to_ms: int
    ) -> list[Candle]:
        query = """
            SELECT open_time, open, high, low, close, volume
            FROM candles
            WHERE tenant_id = %(tenant_id)s
              AND symbol = %(symbol)s
              AND interval = %(interval)s
              AND open_time BETWEEN %(from_ms)s AND %(to_ms)s
            ORDER BY open_time
        """
        params = {
            "tenant_id": tenant_id,
            "symbol": symbol,
            "interval": interval,
            "from_ms": from_ms,
            "to_ms": to_ms,
        }
        rows = await asyncio.to_thread(self._run, query, params)
        return [
            Candle(
                open_time_ms=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in rows
        ]

    async def symbols(self, tenant_id: str) -> list[str]:
        query = """
            SELECT DISTINCT symbol
            FROM candles
            WHERE tenant_id = %(tenant_id)s
            ORDER BY symbol
        """
        rows = await asyncio.to_thread(self._run, query, {"tenant_id": tenant_id})
        return [str(row[0]) for row in rows]

    def _run(self, query: str, params: dict[str, object]) -> list[tuple]:
        return self._client.query(query, parameters=params).result_rows
