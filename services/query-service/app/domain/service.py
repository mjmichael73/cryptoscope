"""Read-side use cases.

The service fetches candles from the read repository and, for indicators, folds
them through a pure function. It stays free of transport and storage concerns so
the same instance serves both the REST and gRPC surfaces.
"""

from __future__ import annotations

from app.domain import indicators
from app.domain.errors import ValidationError
from app.domain.models import Candle, IndicatorPoint, SymbolSummary
from app.domain.repository import ReadRepository

_INTERVALS = {"1m", "5m", "1h", "1d"}


class QueryService:
    def __init__(self, repo: ReadRepository) -> None:
        self._repo = repo

    async def get_candles(
        self, tenant_id: str, symbol: str, interval: str, from_ms: int, to_ms: int
    ) -> list[Candle]:
        self._check_interval(interval)
        if from_ms > to_ms:
            raise ValidationError("from_ms must not be after to_ms")
        return await self._repo.candles(tenant_id, symbol.upper(), interval, from_ms, to_ms)

    async def get_indicator(
        self,
        tenant_id: str,
        symbol: str,
        interval: str,
        kind: str,
        period: int,
        from_ms: int,
        to_ms: int,
    ) -> list[IndicatorPoint]:
        self._check_interval(interval)
        candles = await self._repo.candles(
            tenant_id, symbol.upper(), interval, from_ms, to_ms
        )
        return indicators.compute(kind, candles, period)

    async def list_symbols(self, tenant_id: str) -> list[str]:
        return await self._repo.symbols(tenant_id)

    async def search_symbols(
        self, tenant_id: str, query: str, limit: int
    ) -> list[SymbolSummary]:
        if limit < 1 or limit > 200:
            raise ValidationError("limit must be between 1 and 200")
        if len(query) > 100:
            raise ValidationError("query must be at most 100 characters")
        normalized = query.strip().upper()
        return await self._repo.search_symbols(tenant_id, normalized, limit)

    @staticmethod
    def _check_interval(interval: str) -> None:
        if interval not in _INTERVALS:
            raise ValidationError(f"unsupported interval: {interval}")
