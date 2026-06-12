"""Domain events emitted by the write side.

Events are the contract between the command service and the rest of the
platform. They are intentionally small and versioned by name so consumers can
evolve independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DomainEvent:
    name: str
    tenant_id: str
    payload: dict[str, Any]
    occurred_at: str = field(default_factory=_now_iso)

    def to_message(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tenant_id": self.tenant_id,
            "occurred_at": self.occurred_at,
            "payload": self.payload,
        }


def watchlist_created(tenant_id: str, watchlist_id: str, name: str, symbols: list[str]) -> DomainEvent:
    return DomainEvent(
        name="watchlist.created",
        tenant_id=tenant_id,
        payload={"id": watchlist_id, "name": name, "symbols": symbols},
    )


def alert_rule_created(
    tenant_id: str, rule_id: str, symbol: str, comparator: str, threshold: float
) -> DomainEvent:
    return DomainEvent(
        name="alert_rule.created",
        tenant_id=tenant_id,
        payload={
            "id": rule_id,
            "symbol": symbol,
            "comparator": comparator,
            "threshold": threshold,
        },
    )
