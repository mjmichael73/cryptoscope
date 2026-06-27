from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.schemas import AlertRuleOut, AlertTriggerOut, HealthResponse
from app.infra.db import AlertRuleModel, AlertTriggerModel

router = APIRouter()


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/v1/alert-rules", response_model=list[AlertRuleOut])
async def list_alert_rules(
    tenant_id: str | None = None,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> list[AlertRuleOut]:
    async with session_factory() as session:
        query = select(AlertRuleModel).order_by(AlertRuleModel.created_at.desc())
        if tenant_id:
            query = query.where(AlertRuleModel.tenant_id == tenant_id)
        result = await session.execute(query)
        rules = result.scalars().all()
        return [
            AlertRuleOut(
                id=r.id,
                tenant_id=r.tenant_id,
                symbol=r.symbol,
                comparator=r.comparator,
                threshold=r.threshold,
                status=r.status,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rules
        ]


@router.get("/v1/alert-rules/{rule_id}", response_model=AlertRuleOut)
async def get_alert_rule(
    rule_id: str,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AlertRuleOut:
    async with session_factory() as session:
        result = await session.execute(
            select(AlertRuleModel).where(AlertRuleModel.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise HTTPException(status_code=404, detail="alert rule not found")
        return AlertRuleOut(
            id=rule.id,
            tenant_id=rule.tenant_id,
            symbol=rule.symbol,
            comparator=rule.comparator,
            threshold=rule.threshold,
            status=rule.status,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )


@router.get("/v1/triggers", response_model=list[AlertTriggerOut])
async def list_triggers(
    tenant_id: str | None = None,
    limit: int = 50,
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> list[AlertTriggerOut]:
    async with session_factory() as session:
        query = (
            select(AlertTriggerModel)
            .order_by(AlertTriggerModel.triggered_at.desc())
            .limit(limit)
        )
        if tenant_id:
            query = query.where(AlertTriggerModel.tenant_id == tenant_id)
        result = await session.execute(query)
        triggers = result.scalars().all()
        return [
            AlertTriggerOut(
                id=t.id,
                tenant_id=t.tenant_id,
                rule_id=t.rule_id,
                symbol=t.symbol,
                comparator=t.comparator,
                threshold=t.threshold,
                current_value=t.current_value,
                triggered_at=t.triggered_at,
                acknowledged=t.acknowledged,
            )
            for t in triggers
        ]
