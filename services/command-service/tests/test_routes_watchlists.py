"""Route tests for the watchlist CRUD endpoints.

Runs the real SQLAlchemy models against an in-memory SQLite database through
the same session factory the app uses, so tenant scoping and 404 semantics are
exercised against actual queries rather than fakes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes import router
from app.domain.models import Watchlist
from tests.conftest import FakePublisher

DEMO_TENANT = "11111111-2222-3333-4444-555555555555"
OTHER_TENANT = "22222222-2222-2222-2222-222222222222"

HEADERS = {"X-Tenant-Id": DEMO_TENANT, "X-Tenant-Slug": "demo"}


@pytest.fixture
def db():
    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _make_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Watchlist.metadata.create_all)

    return factory, _make_tables


@pytest.fixture
def app(db) -> FastAPI:
    factory, _ = db
    application = FastAPI()
    application.include_router(router)
    application.state.session_factory = factory
    application.state.publisher = FakePublisher()
    return application


@pytest.fixture
async def client(app: FastAPI, db) -> AsyncClient:
    _, _make_tables = db
    await _make_tables()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _watchlist(watchlist_id: str, tenant: str, name: str, symbols: list[str]) -> Watchlist:
    return Watchlist(
        id=watchlist_id,
        tenant_id=tenant,
        name=name,
        symbols=symbols,
        created_at=datetime(2026, 6, 1, tzinfo=UTC),
    )


async def _seed(db: Any, *watchlists: Watchlist) -> None:
    async with db[0]() as session:
        for wl in watchlists:
            session.add(wl)
        await session.commit()


async def test_list_watchlists_requires_tenant(client: AsyncClient) -> None:
    resp = await client.get("/v1/watchlists")
    assert resp.status_code == 401


async def test_list_watchlists_empty(client: AsyncClient, db) -> None:
    await _seed(db)
    resp = await client.get("/v1/watchlists", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_watchlists_returns_seeded_rows(
    client: AsyncClient, db
) -> None:
    await _seed(
        db,
        _watchlist("wl-1", DEMO_TENANT, "Majors", ["BTCUSDT"]),
        _watchlist("wl-2", OTHER_TENANT, "Theirs", ["ETHUSDT"]),
    )
    resp = await client.get("/v1/watchlists", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Majors"
    assert body[0]["symbols"] == ["BTCUSDT"]


async def test_get_watchlist_by_id(client: AsyncClient, db) -> None:
    await _seed(db, _watchlist("wl-1", DEMO_TENANT, "Majors", ["BTCUSDT"]))
    resp = await client.get("/v1/watchlists/wl-1", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Majors"


async def test_get_other_tenants_watchlist_returns_404(
    client: AsyncClient, db
) -> None:
    await _seed(
        db, _watchlist("wl-9", OTHER_TENANT, "Theirs", ["BTCUSDT"])
    )
    resp = await client.get("/v1/watchlists/wl-9", headers=HEADERS)
    assert resp.status_code == 404


async def test_update_watchlist(client: AsyncClient, db) -> None:
    await _seed(db, _watchlist("wl-1", DEMO_TENANT, "Majors", ["BTCUSDT"]))
    resp = await client.put(
        "/v1/watchlists/wl-1",
        headers=HEADERS,
        json={"name": "Renamed", "symbols": ["ethusdt", "solusdt"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed"
    assert body["symbols"] == ["ETHUSDT", "SOLUSDT"]


async def test_update_other_tenants_watchlist_returns_404(
    client: AsyncClient, db
) -> None:
    await _seed(
        db, _watchlist("wl-9", OTHER_TENANT, "Theirs", ["BTCUSDT"])
    )
    resp = await client.put(
        "/v1/watchlists/wl-9", headers=HEADERS, json={"name": "X", "symbols": []}
    )
    assert resp.status_code == 404


async def test_update_watchlist_blank_name_returns_422(
    client: AsyncClient, db
) -> None:
    await _seed(db, _watchlist("wl-1", DEMO_TENANT, "Majors", ["BTCUSDT"]))
    resp = await client.put(
        "/v1/watchlists/wl-1", headers=HEADERS, json={"name": "  ", "symbols": []}
    )
    assert resp.status_code == 422


async def test_delete_watchlist_returns_204(
    client: AsyncClient, db
) -> None:
    await _seed(db, _watchlist("wl-1", DEMO_TENANT, "Majors", ["BTCUSDT"]))
    resp = await client.delete("/v1/watchlists/wl-1", headers=HEADERS)
    assert resp.status_code == 204

    async with db[0]() as session:
        from sqlalchemy import select

        result = await session.execute(select(Watchlist).where(Watchlist.id == "wl-1"))
        assert result.scalar_one_or_none() is None


async def test_delete_other_tenants_watchlist_returns_404(
    client: AsyncClient, db
) -> None:
    await _seed(
        db, _watchlist("wl-9", OTHER_TENANT, "Theirs", ["BTCUSDT"])
    )
    resp = await client.delete("/v1/watchlists/wl-9", headers=HEADERS)
    assert resp.status_code == 404
