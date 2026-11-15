"""Command inputs for the write side.

Keeping these as small dataclasses decouples the application service from the
transport, so the same handler serves both REST and gRPC.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateWatchlist:
    tenant_id: str
    idempotency_key: str
    name: str
    symbols: list[str]


@dataclass(frozen=True)
class CreateAlertRule:
    tenant_id: str
    idempotency_key: str
    symbol: str
    comparator: str
    threshold: float
    interval: str = "1m"
    window_seconds: int | None = None
    cooldown_seconds: int = 300
