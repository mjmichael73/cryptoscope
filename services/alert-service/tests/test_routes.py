from __future__ import annotations

from typing import Any

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
    def __call__(self) -> FakeSession:
        return FakeSession(rules=[], triggers=[])

    async def __aenter__(self) -> FakeSession:
        return FakeSession(rules=[], triggers=[])

    async def __aexit__(self, *args: Any) -> None:
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
        return FakeResult(self._rules)

    async def commit(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
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
