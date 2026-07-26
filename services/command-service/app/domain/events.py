"""Domain events emitted by the write side.

Events use the shared schema from cryptoscope_shared so all Python services
agree on the wire format. Consumer services import the event type constants
from the shared lib rather than hardcoding strings.
"""

from __future__ import annotations

from cryptoscope_shared.events import ALERT_RULE_CREATED, WATCHLIST_CREATED, DomainEvent


def watchlist_created(tenant_id: str, watchlist_id: str, name: str, symbols: list[str]) -> DomainEvent:
    return DomainEvent(
        event_type=WATCHLIST_CREATED,
        aggregate_id=watchlist_id,
        tenant_id=tenant_id,
        data={"id": watchlist_id, "name": name, "symbols": symbols},
    )


def alert_rule_created(
    tenant_id: str, rule_id: str, symbol: str, comparator: str, threshold: float
) -> DomainEvent:
    return DomainEvent(
        event_type=ALERT_RULE_CREATED,
        aggregate_id=rule_id,
        tenant_id=tenant_id,
        data={
            "id": rule_id,
            "symbol": symbol,
            "comparator": comparator,
            "threshold": threshold,
        },
    )
