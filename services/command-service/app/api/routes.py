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
)
from app.domain.commands import CreateAlertRule, CreateWatchlist
from app.domain.errors import ConflictError, ValidationError
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
