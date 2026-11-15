from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, Self

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes import router


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    application.state.session_factory = FakeSessionFactory()
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class FakeSessionFactory:
    def __init__(self, rules: list[Any] | None = None, triggers: list[Any] | None = None) -> None:
        self._rules = rules or []
        self._triggers = triggers or []

    def __call__(self) -> FakeSession:
        return FakeSession(rules=self._rules, triggers=self._triggers)

    async def __aenter__(self) -> FakeSession:
        return self.__call__()

    async def __aexit__(self, *args: object) -> None:
        pass


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> FakeResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(self, rules: list[Any], triggers: list[Any]) -> None:
        self._rules = rules
        self._triggers = triggers
        self._added: list[Any] = []

    async def execute(self, query: Any) -> FakeResult:
        if "alert_triggers" in str(query):
            return FakeResult(self._triggers)
        return FakeResult(self._rules)

    async def commit(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def add(self, obj: Any) -> None:
        self._added.append(obj)


async def test_healthz(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_list_alert_rules_empty(client: AsyncClient) -> None:
    resp = await client.get("/v1/alert-rules")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_alert_rule_not_found(client: AsyncClient) -> None:
    resp = await client.get("/v1/alert-rules/non-existent")
    assert resp.status_code == 404


async def test_list_triggers_empty(client: AsyncClient) -> None:
    resp = await client.get("/v1/triggers")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Trigger acknowledgment
# ---------------------------------------------------------------------------


def _trigger(**overrides: Any) -> SimpleNamespace:
    defaults = {
        "id": "trg-1",
        "tenant_id": "tenant-1",
        "rule_id": "rule-1",
        "symbol": "BTCUSDT",
        "comparator": "above",
        "threshold": 50000.0,
        "current_value": 51000.0,
        "interval": "1m",
        "window_seconds": None,
        "triggered_at": datetime.now(UTC),
        "acknowledged": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture
def app_with_trigger(app: FastAPI) -> FastAPI:
    app.state.session_factory = FakeSessionFactory(triggers=[_trigger()])
    return app


@pytest.fixture
async def client_with_trigger(app_with_trigger: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app_with_trigger)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_ack_trigger_marks_acknowledged(client_with_trigger: AsyncClient) -> None:
    resp = await client_with_trigger.post("/v1/triggers/trg-1/ack")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "trg-1"
    assert data["acknowledged"] is True


async def test_ack_unknown_trigger_returns_404(client: AsyncClient) -> None:
    resp = await client.post("/v1/triggers/no-such-trigger/ack")
    assert resp.status_code == 404
