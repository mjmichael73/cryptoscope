"""Tests for the symbol search and discovery endpoint."""

from __future__ import annotations

from typing import Any

from httpx import ASGITransport, AsyncClient

from app.domain.models import SymbolSummary
from app.main import create_app
from tests.conftest import TENANT_ID, FakeReadRepository


def _app(repo: FakeReadRepository) -> Any:
    """Build a test app wired to the given fake repo."""

    app = create_app()
    from app.domain.service import QueryService

    app.state.query_service = QueryService(repo)
    return app


def _summary(symbol: str) -> SymbolSummary:
    return SymbolSummary(
        symbol=symbol,
        first_open_time_ms=1_700_000_000_000,
        last_open_time_ms=1_700_000_060_000,
        candle_count=60,
        intervals=["1m"],
    )


class TestSymbolSearch:
    async def test_search_returns_summaries(self) -> None:
        repo = FakeReadRepository(summaries=[_summary("BTCUSDT"), _summary("ETHUSDT")])
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/symbols/search",
                params={"q": "USDT", "limit": 10},
                headers={"X-Tenant-Id": TENANT_ID, "X-Tenant-Slug": "test"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert [s["symbol"] for s in body["symbols"]] == ["BTCUSDT", "ETHUSDT"]
        first = body["symbols"][0]
        assert first["first_open_time_ms"] == 1_700_000_000_000
        assert first["last_open_time_ms"] == 1_700_000_060_000
        assert first["candle_count"] == 60
        assert first["intervals"] == ["1m"]

    async def test_search_without_query_returns_all(self) -> None:
        repo = FakeReadRepository(summaries=[_summary("BTCUSDT")])
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/symbols/search",
                headers={"X-Tenant-Id": TENANT_ID, "X-Tenant-Slug": "test"},
            )

        assert resp.status_code == 200
        assert len(resp.json()["symbols"]) == 1

    async def test_search_missing_tenant_returns_401(self) -> None:
        repo = FakeReadRepository()
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/v1/symbols/search")

        assert resp.status_code == 401

    async def test_search_limit_out_of_range_returns_422(self) -> None:
        repo = FakeReadRepository()
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/symbols/search",
                params={"limit": 500},
                headers={"X-Tenant-Id": TENANT_ID, "X-Tenant-Slug": "test"},
            )

        assert resp.status_code == 422

    async def test_search_overlong_query_returns_422(self) -> None:
        repo = FakeReadRepository()
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/symbols/search",
                params={"q": "A" * 101},
                headers={"X-Tenant-Id": TENANT_ID, "X-Tenant-Slug": "test"},
            )

        assert resp.status_code == 422

    async def test_search_service_error_returns_422(self) -> None:
        repo = FakeReadRepository()
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/symbols/search",
                params={"limit": 0},
                headers={"X-Tenant-Id": TENANT_ID, "X-Tenant-Slug": "test"},
            )

        assert resp.status_code == 422
