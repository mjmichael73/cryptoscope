from __future__ import annotations

import asyncio
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.domain.models import Candle


@dataclass
class CHConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


class _ClientSlot:
    def __init__(self, client: Client) -> None:
        self.client = client
        self.lock = threading.Lock()


class ClickHousePool:
    def __init__(self, config: CHConfig, size: int = 4) -> None:
        self._slots = [
            _ClientSlot(
                clickhouse_connect.get_client(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    username=config.user,
                    password=config.password,
                )
            )
            for _ in range(size)
        ]
        self._sem = asyncio.Semaphore(size)
        self._next = 0

    async def query(
        self, q: str, params: dict[str, object]
    ) -> Sequence[Sequence[Any]]:
        async with self._sem:
            slot = self._acquire()
            try:
                return await asyncio.to_thread(self._run, slot, q, params)
            finally:
                slot.lock.release()

    def _acquire(self) -> _ClientSlot:
        for _ in range(len(self._slots)):
            slot = self._slots[self._next]
            self._next = (self._next + 1) % len(self._slots)
            if slot.lock.acquire(blocking=False):
                return slot
        slot = self._slots[self._next]
        self._next = (self._next + 1) % len(self._slots)
        slot.lock.acquire(blocking=True)
        return slot

    @staticmethod
    def _run(
        slot: _ClientSlot, q: str, params: dict[str, object]
    ) -> Sequence[Sequence[Any]]:
        return slot.client.query(q, parameters=params).result_rows

    def close(self) -> None:
        for slot in self._slots:
            slot.client.close()


class ClickHouseReadRepository:
    def __init__(self, pool: ClickHousePool) -> None:
        self._pool = pool

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
        rows = await self._pool.query(query, params)
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
        rows = await self._pool.query(query, {"tenant_id": tenant_id})
        return [str(row[0]) for row in rows]
