"""Command API routes.

The routes stay thin: they translate the HTTP request into a command, hand it
to the application service, and map domain errors to status codes.
"""

from __future__ import annotations

from typing import Annotated

from cryptoscope_shared.tenant import TenantIdentity
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import require_idempotency_key, require_tenant
from app.api.schemas import (
    AlertTemplateOut,
    CreateAlertRuleRequest,
    CreatedResponse,
    CreateWatchlistRequest,
    UpdateWatchlistRequest,
    WatchlistOut,
)
from app.domain.commands import CreateAlertRule, CreateWatchlist, UpdateWatchlist
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.service import CommandService
from app.domain.templates import ALERT_TEMPLATES
from app.infra.repository import SqlAlchemyWriteRepository

router = APIRouter(prefix="/v1")


async def _service(request: Request) -> CommandService:
    session_factory = request.app.state.session_factory
    publisher = request.app.state.publisher
    session = session_factory()
    request.state.session = session
    return CommandService(SqlAlchemyWriteRepository(session), publisher)


@router.post(
    "/watchlists",
    response_model=CreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_watchlist(
    body: CreateWatchlistRequest,
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> CreatedResponse:
    service = await _service(request)
    try:
        watchlist_id = await service.create_watchlist(
            CreateWatchlist(
                tenant_id=tenant.id,
                idempotency_key=idempotency_key,
                name=body.name,
                symbols=body.symbols,
            )
        )
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    finally:
        await request.state.session.close()
    return CreatedResponse(id=watchlist_id)


@router.post(
    "/alert-rules",
    response_model=CreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_alert_rule(
    body: CreateAlertRuleRequest,
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> CreatedResponse:
    service = await _service(request)
    try:
        rule_id = await service.create_alert_rule(
            CreateAlertRule(
                tenant_id=tenant.id,
                idempotency_key=idempotency_key,
                symbol=body.symbol,
                comparator=body.comparator,
                threshold=body.threshold,
                interval=body.interval,
                window_seconds=body.window_seconds,
                cooldown_seconds=body.cooldown_seconds,
            )
        )
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    finally:
        await request.state.session.close()
    return CreatedResponse(id=rule_id)


@router.get("/alert-templates", response_model=list[AlertTemplateOut])
async def list_alert_templates() -> list[AlertTemplateOut]:
    return [AlertTemplateOut(**template) for template in ALERT_TEMPLATES]


@router.get("/watchlists", response_model=list[WatchlistOut])
async def list_watchlists(
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
) -> list[WatchlistOut]:
    service = await _service(request)
    try:
        watchlists = await service.list_watchlists(tenant.id)
    finally:
        await request.state.session.close()
    return [
        WatchlistOut(
            id=w.id,
            tenant_id=w.tenant_id,
            name=w.name,
            symbols=list(w.symbols),
            created_at=w.created_at,
        )
        for w in watchlists
    ]


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistOut)
async def get_watchlist(
    watchlist_id: str,
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
) -> WatchlistOut:
    service = await _service(request)
    try:
        watchlist = await service.get_watchlist(tenant.id, watchlist_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    finally:
        await request.state.session.close()
    return WatchlistOut(
        id=watchlist.id,
        tenant_id=watchlist.tenant_id,
        name=watchlist.name,
        symbols=list(watchlist.symbols),
        created_at=watchlist.created_at,
    )


@router.put("/watchlists/{watchlist_id}", response_model=WatchlistOut)
async def update_watchlist(
    watchlist_id: str,
    body: UpdateWatchlistRequest,
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
) -> WatchlistOut:
    service = await _service(request)
    try:
        watchlist = await service.update_watchlist(
            UpdateWatchlist(
                tenant_id=tenant.id,
                watchlist_id=watchlist_id,
                name=body.name,
                symbols=body.symbols,
            )
        )
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    finally:
        await request.state.session.close()
    return WatchlistOut(
        id=watchlist.id,
        tenant_id=watchlist.tenant_id,
        name=watchlist.name,
        symbols=list(watchlist.symbols),
        created_at=watchlist.created_at,
    )


@router.delete("/watchlists/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: str,
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
) -> None:
    service = await _service(request)
    try:
        await service.delete_watchlist(tenant.id, watchlist_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    finally:
        await request.state.session.close()


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: str,
    request: Request,
    tenant: Annotated[TenantIdentity, Depends(require_tenant)],
) -> None:
    service = await _service(request)
    try:
        await service.delete_alert_rule(tenant.id, rule_id)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    finally:
        await request.state.session.close()
