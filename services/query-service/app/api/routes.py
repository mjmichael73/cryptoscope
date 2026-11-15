"""Query API routes.

Routes translate the request into a call on the read service and shape the
result for the wire. Query parameter validation errors map to 422.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Annotated

from cryptoscope_shared.tenant import TenantIdentity
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.deps import require_tenant
from app.api.schemas import CandleOut, IndicatorPointOut, SymbolsOut
from app.domain.errors import ValidationError
from app.domain.service import QueryService

router = APIRouter(prefix="/v1")


def _service(request: Request) -> QueryService:
    return request.app.state.query_service


@router.get("/candles", response_model=list[CandleOut])
async def get_candles(
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
    symbol: str = Query(min_length=1),
    interval: str = Query(default="1m"),
    from_ms: int = Query(default=0),
    to_ms: int = Query(default=2**63 - 1),
) -> list[CandleOut]:
    try:
        candles = await _service(request).get_candles(
            tenant.id, symbol, interval, from_ms, to_ms
        )
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return [
        CandleOut(
            open_time_ms=c.open_time_ms,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in candles
    ]


@router.get("/indicators", response_model=list[IndicatorPointOut])
async def get_indicator(
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
    symbol: str = Query(min_length=1),
    kind: str = Query(alias="type"),
    interval: str = Query(default="1m"),
    period: int = Query(default=14, ge=1),
    from_ms: int = Query(default=0),
    to_ms: int = Query(default=2**63 - 1),
) -> list[IndicatorPointOut]:
    try:
        points = await _service(request).get_indicator(
            tenant.id, symbol, interval, kind, period, from_ms, to_ms
        )
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return [IndicatorPointOut(time_ms=p.time_ms, value=p.value) for p in points]


@router.get("/symbols", response_model=SymbolsOut)
async def list_symbols(
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
) -> SymbolsOut:
    symbols = await _service(request).list_symbols(tenant.id)
    return SymbolsOut(symbols=symbols)


@router.get("/candles/export")
async def export_candles(
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
    symbol: str = Query(min_length=1),
    interval: str = Query(default="1m"),
    from_ms: int = Query(default=0),
    to_ms: int = Query(default=2**63 - 1),
    fmt: str = Query(default="csv", alias="format"),
) -> Response:
    try:
        candles = await _service(request).get_candles(
            tenant.id, symbol, interval, from_ms, to_ms
        )
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    if fmt == "json":
        payload = [
            {
                "open_time_ms": c.open_time_ms,
                "open_time": datetime.fromtimestamp(
                    c.open_time_ms / 1000, tz=UTC
                ).isoformat(),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        return Response(
            content=json.dumps(payload, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{symbol}_{interval}_candles.json"'
            },
        )

    # Default: CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "open_time_ms", "open_time", "open", "high", "low", "close", "volume",
    ])
    for c in candles:
        ts = datetime.fromtimestamp(c.open_time_ms / 1000, tz=UTC).isoformat()
        writer.writerow([c.open_time_ms, ts, c.open, c.high, c.low, c.close, c.volume])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{symbol}_{interval}_candles.csv"'
        },
    )
