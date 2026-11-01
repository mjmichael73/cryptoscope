"""Tests for the candle export endpoint."""

from __future__ import annotations

import csv
import io
import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.settings import Settings
from tests.conftest import TENANT_ID, FakeReadRepository, make_candles


@pytest.fixture
def settings() -> Settings:
    return Settings(
        clickhouse_host="localhost",
        clickhouse_http_port=8123,
        clickhouse_db="test",
        clickhouse_user="test",
        clickhouse_password="test",
        grpc_port=9999,
    )


def _app(repo: FakeReadRepository) -> Any:
    """Build a test app wired to the given fake repo."""
    from app.main import create_app

    app = create_app()
    from app.domain.service import QueryService

    app.state.query_service = QueryService(repo)
    return app


class TestExportCSV:
    async def test_csv_download(self) -> None:
        repo = FakeReadRepository(
            candles=make_candles([100.0, 200.0, 300.0], start_ms=1_000_000),
            symbols=["BTCUSDT"],
        )
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "BTCUSDT", "interval": "1m", "format": "csv"},
                headers={"X-Tenant-Id": TENANT_ID, "X-Tenant-Slug": "test"},
            )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "BTCUSDT_1m_candles.csv" in resp.headers.get("content-disposition", "")

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        # Header + 3 data rows.
        assert len(rows) == 4
        assert rows[0] == ["open_time_ms", "open_time", "open", "high", "low", "close", "volume"]
        # First data row.
        assert rows[1][0] == "1000000"  # open_time_ms
        assert rows[1][2] == "100.0"  # open

    async def test_csv_empty_result(self) -> None:
        repo = FakeReadRepository(candles=[], symbols=[])
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "BTCUSDT", "interval": "1m"},
                headers={"X-Tenant-Id": TENANT_ID},
            )

        assert resp.status_code == 200
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        # Header only.
        assert len(rows) == 1


class TestExportJSON:
    async def test_json_download(self) -> None:
        repo = FakeReadRepository(
            candles=make_candles([42.0], start_ms=1_700_000_000_000),
            symbols=["ETHUSDT"],
        )
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "ETHUSDT", "interval": "1h", "format": "json"},
                headers={"X-Tenant-Id": TENANT_ID, "X-Tenant-Slug": "test"},
            )

        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "ETHUSDT_1h_candles.json" in resp.headers.get("content-disposition", "")

        payload = resp.json()
        assert isinstance(payload, list)
        assert len(payload) == 1
        candle = payload[0]
        assert candle["open_time_ms"] == 1_700_000_000_000
        assert candle["open"] == 42.0
        assert candle["high"] == 42.0
        assert candle["low"] == 42.0
        assert candle["close"] == 42.0
        assert "open_time" in candle  # ISO timestamp
        assert "T" in candle["open_time"]  # should be ISO format

    async def test_json_multiple_candles(self) -> None:
        repo = FakeReadRepository(
            candles=make_candles([100, 200, 300]),
            symbols=["BTCUSDT"],
        )
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "BTCUSDT", "interval": "1m", "format": "json"},
                headers={"X-Tenant-Id": TENANT_ID},
            )

        payload = resp.json()
        assert len(payload) == 3
        assert [c["close"] for c in payload] == [100.0, 200.0, 300.0]


class TestExportValidation:
    async def test_missing_symbol_returns_422(self) -> None:
        repo = FakeReadRepository()
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"interval": "1m"},
                headers={"X-Tenant-Id": TENANT_ID},
            )

        assert resp.status_code == 422

    async def test_invalid_interval_returns_422(self) -> None:
        repo = FakeReadRepository()
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "BTCUSDT", "interval": "3m"},
                headers={"X-Tenant-Id": TENANT_ID},
            )

        assert resp.status_code == 422

    async def test_missing_tenant_returns_401(self) -> None:
        repo = FakeReadRepository()
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "BTCUSDT", "interval": "1m"},
            )

        assert resp.status_code == 401


class TestExportCSVContent:
    async def test_csv_iso_timestamps(self) -> None:
        repo = FakeReadRepository(
            candles=make_candles([100.0], start_ms=1_700_000_000_000),
            symbols=["BTCUSDT"],
        )
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "BTCUSDT", "interval": "1m", "format": "csv"},
                headers={"X-Tenant-Id": TENANT_ID},
            )

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        # The open_time column (index 1) should be an ISO timestamp.
        ts = rows[1][1]
        assert "2023" in ts or "2026" in ts  # reasonable year
        assert "T" in ts  # ISO format separator

    async def test_csv_volume_column(self) -> None:
        repo = FakeReadRepository(
            candles=make_candles([100.0], start_ms=0),
            symbols=["BTCUSDT"],
        )
        app = _app(repo)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/v1/candles/export",
                params={"symbol": "BTCUSDT", "interval": "1m"},
                headers={"X-Tenant-Id": TENANT_ID},
            )

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert rows[1][6] == "1.0"  # volume column
